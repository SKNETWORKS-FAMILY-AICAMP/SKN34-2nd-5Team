"""Run one v05_05_01~05 development-only OOF ablation."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

# PyTorch must initialize before NumPy/sklearn on Windows.
import torch
import numpy as np
import pandas as pd
import sklearn
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, confusion_matrix
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.v05_05_dl import train as base


SUITE_CONFIG_PATH = Path(__file__).with_name("ablation_config.json")
SOURCE_PATH = base.SOURCE_PATH
SEQUENCE_PATH = base.SEQUENCE_PATH
EXPLORATION_PATH = (
    ROOT
    / "data"
    / "processed"
    / "experiments"
    / "monthly_exploration_sequence_v05_05_03.parquet"
)
EXPLORATION_METADATA_PATH = (
    ROOT
    / "reports"
    / "experiments"
    / "v05_05_03_dl"
    / "exploration_feature_metadata.json"
)
BASELINE_OOF_PATH = base.REPORT_DIR / "oof_predictions.parquet"
BASELINE_METADATA_PATH = base.MODEL_DIR / "metadata.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


class AblationH2(nn.Module):
    def __init__(
        self,
        model_config: dict,
        extra_dim: int,
        extra_hidden_dim: int,
        auxiliary_subtype: bool,
    ):
        super().__init__()
        self.extra_dim = extra_dim
        self.gru = nn.GRU(
            input_size=4,
            hidden_size=int(model_config["gru_hidden_dim"]),
            batch_first=True,
        )
        dropout = float(model_config["dropout"])
        self.lifecycle_encoder = nn.Sequential(
            nn.Linear(5, int(model_config["lifecycle_hidden_dim"])),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.fusion = nn.Sequential(
            nn.Linear(
                int(model_config["gru_hidden_dim"])
                + int(model_config["lifecycle_hidden_dim"]),
                int(model_config["fusion_hidden_dim"]),
            ),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.risk_head = nn.Linear(int(model_config["fusion_hidden_dim"]), 1)
        self.conditional_stopped_head = nn.Linear(
            int(model_config["fusion_hidden_dim"]), 1
        )
        if extra_dim:
            self.extra_encoder = nn.Sequential(
                nn.Linear(extra_dim, extra_hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
            )
            self.extra_state_head = nn.Linear(extra_hidden_dim, 1)
        else:
            self.extra_encoder = None
            self.extra_state_head = None
        self.auxiliary_subtype_head = (
            nn.Linear(int(model_config["fusion_hidden_dim"]), 3)
            if auxiliary_subtype
            else None
        )

    def forward(
        self,
        sequence: torch.Tensor,
        lifecycle: torch.Tensor,
        extra: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor | None]:
        _, hidden = self.gru(sequence)
        lifecycle_encoded = self.lifecycle_encoder(lifecycle)
        fused = self.fusion(torch.cat([hidden[-1], lifecycle_encoded], dim=1))
        risk = self.risk_head(fused).squeeze(1)
        stopped = self.conditional_stopped_head(fused).squeeze(1)
        if self.extra_encoder is not None:
            stopped = stopped + self.extra_state_head(
                self.extra_encoder(extra)
            ).squeeze(1)
        auxiliary = (
            self.auxiliary_subtype_head(fused)
            if self.auxiliary_subtype_head is not None
            else None
        )
        return risk, stopped, auxiliary


def make_model(
    model_config: dict,
    extra_dim: int,
    extra_hidden_dim: int,
    auxiliary_subtype: bool,
    device: torch.device,
) -> AblationH2:
    return AblationH2(
        model_config,
        extra_dim,
        extra_hidden_dim,
        auxiliary_subtype,
    ).to(device)


def load_source(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    source = pd.read_parquet(
        SOURCE_PATH,
        columns=[
            "sample_id",
            "selection_year",
            "target_review_count",
            "target_active_months",
            *columns,
        ],
        filters=[("selection_year", "<=", 2017)],
    ).sort_values("sample_id", kind="stable").reset_index(drop=True)
    if source["sample_id"].tolist() != frame["sample_id"].tolist():
        raise ValueError("Ablation source sample order changed")
    if source["selection_year"].max() >= 2018:
        raise ValueError("Final Test entered ablation source")
    return source


def row_slope(values: np.ndarray) -> np.ndarray:
    x = np.arange(values.shape[1], dtype=np.float32)
    centered = x - x.mean()
    denominator = float(np.square(centered).sum())
    return ((values - values.mean(axis=1, keepdims=True)) * centered).sum(axis=1) / denominator


def build_last_k(frame: pd.DataFrame, names: list[str]) -> np.ndarray:
    sequence = pd.read_parquet(SEQUENCE_PATH)
    if sequence["sample_id"].drop_duplicates().tolist() != frame["sample_id"].tolist():
        raise ValueError("Last-K sequence sample order changed")
    review = sequence["monthly_review_count"].to_numpy(np.float32).reshape(-1, 24)
    unique = sequence["monthly_unique_business_count"].to_numpy(np.float32).reshape(-1, 24)
    inactive_streak = np.zeros(len(review), dtype=np.float32)
    for index in range(len(review)):
        for value in review[index, ::-1]:
            if value > 0:
                break
            inactive_streak[index] += 1
    values = np.column_stack(
        [
            review[:, -1],
            review[:, -3:].sum(axis=1),
            review[:, -6:].sum(axis=1),
            (review[:, -3:] == 0).sum(axis=1),
            (review[:, -6:] == 0).sum(axis=1),
            inactive_streak,
            unique[:, -3:].sum(axis=1),
            unique[:, -6:].sum(axis=1),
            row_slope(review[:, -6:]),
        ]
    ).astype(np.float32)
    if values.shape[1] != len(names):
        raise ValueError("Last-K feature count changed")
    return values


def build_exploration(frame: pd.DataFrame, names: list[str]) -> np.ndarray:
    required = [EXPLORATION_PATH, EXPLORATION_METADATA_PATH]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing exploration inputs:\n- " + "\n- ".join(missing))
    metadata = json.loads(EXPLORATION_METADATA_PATH.read_text(encoding="utf-8"))
    if metadata["final_test_rows_loaded"] != 0:
        raise ValueError("Exploration artifact is not development-only")
    if metadata["output_sha256"] != sha256(EXPLORATION_PATH):
        raise ValueError("Exploration artifact checksum mismatch")
    sequence = pd.read_parquet(EXPLORATION_PATH)
    if sequence["sample_id"].drop_duplicates().tolist() != frame["sample_id"].tolist():
        raise ValueError("Exploration sample order changed")
    new = sequence["monthly_new_business_count"].to_numpy(np.float32).reshape(-1, 24)
    unique = sequence["monthly_unique_business_count"].to_numpy(np.float32).reshape(-1, 24)
    revisited = sequence["monthly_revisited_business_count"].to_numpy(np.float32).reshape(-1, 24)
    months_since_new = np.full(len(new), 24, dtype=np.float32)
    for index in range(len(new)):
        locations = np.flatnonzero(new[index] > 0)
        if len(locations):
            months_since_new[index] = 23 - locations[-1]
    new3 = new[:, -3:].sum(axis=1)
    new6 = new[:, -6:].sum(axis=1)
    unique3 = unique[:, -3:].sum(axis=1)
    unique6 = unique[:, -6:].sum(axis=1)
    values = np.column_stack(
        [
            new3,
            new6,
            np.divide(new3, unique3, out=np.zeros_like(new3), where=unique3 > 0),
            np.divide(new6, unique6, out=np.zeros_like(new6), where=unique6 > 0),
            months_since_new,
            row_slope(new[:, -6:]),
            revisited[:, -6:].sum(axis=1),
        ]
    ).astype(np.float32)
    if values.shape[1] != len(names):
        raise ValueError("Exploration feature count changed")
    return values


def load_extra_features(
    frame: pd.DataFrame,
    suite_config: dict,
    group: str,
) -> tuple[np.ndarray, list[str]]:
    if group == "none":
        return np.empty((len(frame), 0), dtype=np.float32), []
    names = list(suite_config[group])
    if group == "state_static5":
        source = load_source(frame, names)
        values = source[names].replace([np.inf, -np.inf], np.nan).to_numpy(np.float32)
    elif group == "last_k9":
        values = build_last_k(frame, names)
    elif group == "exploration7":
        values = build_exploration(frame, names)
    else:
        raise ValueError(f"Unknown extra feature group: {group}")
    return values, names


def auxiliary_labels(frame: pd.DataFrame) -> np.ndarray:
    source = load_source(frame, [])
    labels = np.full(len(source), -1, dtype=np.int64)
    stopped = frame["retention_state"].eq(2).to_numpy()
    weakened = frame["retention_state"].eq(1).to_numpy()
    low_active = source["target_active_months"].lt(3).to_numpy()
    labels[stopped] = 0
    labels[weakened & ~low_active] = 1
    labels[weakened & low_active] = 2
    if (labels[frame["retention_state"].ne(0).to_numpy()] < 0).any():
        raise ValueError("Missing at-risk auxiliary subtype")
    return labels


def scale_extra(
    train: np.ndarray,
    validation: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    if train.shape[1] == 0:
        return train.astype(np.float32), validation.astype(np.float32)
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    train_imputed = imputer.fit_transform(train)
    validation_imputed = imputer.transform(validation)
    return (
        scaler.fit_transform(train_imputed).astype(np.float32),
        scaler.transform(validation_imputed).astype(np.float32),
    )


def train_model(
    sequence: np.ndarray,
    lifecycle: np.ndarray,
    extra: np.ndarray,
    labels: np.ndarray,
    auxiliary: np.ndarray,
    model_config: dict,
    experiment_config: dict,
    extra_hidden_dim: int,
    seed: int,
    device: torch.device,
) -> AblationH2:
    set_seed(seed)
    auxiliary_weight = float(experiment_config["auxiliary_subtype_weight"])
    model = make_model(
        model_config,
        extra.shape[1],
        extra_hidden_dim,
        auxiliary_weight > 0,
        device,
    )
    dataset = TensorDataset(
        torch.from_numpy(sequence),
        torch.from_numpy(lifecycle),
        torch.from_numpy(extra),
        torch.from_numpy(labels.astype(np.int64)),
        torch.from_numpy(auxiliary.astype(np.int64)),
    )
    loader = DataLoader(
        dataset,
        batch_size=int(model_config["batch_size"]),
        shuffle=True,
        generator=torch.Generator().manual_seed(seed),
        num_workers=0,
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(model_config["learning_rate"]),
        weight_decay=float(model_config["weight_decay"]),
    )
    risk_loss = nn.BCEWithLogitsLoss(
        pos_weight=torch.tensor(
            float(model_config["risk_positive_weight"]), device=device
        )
    )
    state_loss = nn.BCEWithLogitsLoss(
        pos_weight=torch.tensor(
            float(experiment_config["state_positive_weight"]), device=device
        )
    )
    subtype_loss = nn.CrossEntropyLoss()
    model.train()
    for _ in range(int(model_config["epochs"])):
        for seq_batch, life_batch, extra_batch, label_batch, aux_batch in loader:
            seq_batch = seq_batch.to(device)
            life_batch = life_batch.to(device)
            extra_batch = extra_batch.to(device)
            label_batch = label_batch.to(device)
            aux_batch = aux_batch.to(device)
            risk_logits, stopped_logits, auxiliary_logits = model(
                seq_batch, life_batch, extra_batch
            )
            at_risk = label_batch.ne(0)
            loss = risk_loss(risk_logits, at_risk.float())
            if at_risk.any():
                loss = loss + float(model_config["state_loss_weight"]) * state_loss(
                    stopped_logits[at_risk], label_batch[at_risk].eq(2).float()
                )
                if auxiliary_logits is not None:
                    loss = loss + auxiliary_weight * subtype_loss(
                        auxiliary_logits[at_risk], aux_batch[at_risk]
                    )
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(
                model.parameters(), float(model_config["gradient_clip_norm"])
            )
            optimizer.step()
    return model


@torch.inference_mode()
def predict_scores(
    model: AblationH2,
    sequence: np.ndarray,
    lifecycle: np.ndarray,
    extra: np.ndarray,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    model.eval()
    dataset = TensorDataset(
        torch.from_numpy(sequence),
        torch.from_numpy(lifecycle),
        torch.from_numpy(extra),
    )
    loader = DataLoader(dataset, batch_size=4096, shuffle=False, num_workers=0)
    risk_parts = []
    stopped_parts = []
    for sequence_batch, lifecycle_batch, extra_batch in loader:
        risk_logits, stopped_logits, _ = model(
            sequence_batch.to(device),
            lifecycle_batch.to(device),
            extra_batch.to(device),
        )
        risk_parts.append(torch.sigmoid(risk_logits).cpu().numpy())
        stopped_parts.append(torch.sigmoid(stopped_logits).cpu().numpy())
    risk = np.concatenate(risk_parts)
    stopped = np.concatenate(stopped_parts)
    scores = np.column_stack(
        [1.0 - risk, risk * (1.0 - stopped), risk * stopped]
    )
    return scores, risk, stopped


def run_oof(
    frame: pd.DataFrame,
    raw_sequence: np.ndarray,
    raw_lifecycle: np.ndarray,
    raw_extra: np.ndarray,
    auxiliary: np.ndarray,
    base_config: dict,
    suite_config: dict,
    experiment_config: dict,
    version: str,
    device: torch.device,
) -> pd.DataFrame:
    parts = []
    total = len(base.TIME_FOLDS) * len(base_config["seeds"])
    run = 0
    for train_end, validation_year in base.TIME_FOLDS:
        train_mask = frame["selection_year"].between(2010, train_end).to_numpy()
        validation_mask = frame["selection_year"].eq(validation_year).to_numpy()
        scaled = base.scale_inputs(
            raw_sequence[train_mask],
            raw_sequence[validation_mask],
            raw_lifecycle[train_mask],
            raw_lifecycle[validation_mask],
        )
        train_sequence, validation_sequence = scaled[:2]
        train_lifecycle, validation_lifecycle = scaled[2:4]
        train_extra, validation_extra = scale_extra(
            raw_extra[train_mask], raw_extra[validation_mask]
        )
        labels = frame.loc[train_mask, "retention_state"].to_numpy(np.int64)
        fold_scores = []
        fold_risk = []
        fold_stopped = []
        for seed in base_config["seeds"]:
            run += 1
            print(
                f"{version} {run}/{total}: train 2010-{train_end}, "
                f"validation {validation_year}, seed {seed}",
                flush=True,
            )
            model = train_model(
                train_sequence,
                train_lifecycle,
                train_extra,
                labels,
                auxiliary[train_mask],
                base_config["model"],
                experiment_config,
                int(suite_config["extra_hidden_dim"]),
                int(seed),
                device,
            )
            scores, risk, stopped = predict_scores(
                model,
                validation_sequence,
                validation_lifecycle,
                validation_extra,
                device,
            )
            fold_scores.append(scores)
            fold_risk.append(risk)
            fold_stopped.append(stopped)
            part = frame.loc[
                validation_mask,
                ["sample_id", "selection_year", "retention_state"],
            ].copy()
            part["seed"] = int(seed)
            part[base.SCORE_COLUMNS] = scores
            part["risk_score"] = risk
            part["conditional_stopped_score"] = stopped
            part["record_type"] = "seed"
            parts.append(part)
        ensemble = frame.loc[
            validation_mask,
            ["sample_id", "selection_year", "retention_state"],
        ].copy()
        ensemble["seed"] = -1
        ensemble[base.SCORE_COLUMNS] = np.mean(fold_scores, axis=0)
        ensemble["risk_score"] = np.mean(fold_risk, axis=0)
        ensemble["conditional_stopped_score"] = np.mean(fold_stopped, axis=0)
        ensemble["record_type"] = "ensemble"
        parts.append(ensemble)
    return pd.concat(parts, ignore_index=True)


def stage_metrics(
    ensemble: pd.DataFrame,
    predictions: np.ndarray,
    metrics: dict,
) -> dict:
    labels = ensemble["retention_state"].to_numpy()
    risk_labels = labels != 0
    at_risk = risk_labels
    result = dict(metrics)
    result["risk_pr_auc"] = float(
        average_precision_score(risk_labels, ensemble["risk_score"])
    )
    result["conditional_stopped_pr_auc"] = float(
        average_precision_score(
            labels[at_risk] == 2,
            ensemble.loc[at_risk, "conditional_stopped_score"],
        )
    )
    top_k_detail, top_k_summary = base.top_k_tables(ensemble)
    result["mean_precision_at_1000"] = float(
        top_k_summary.loc[
            top_k_summary["requested_k"].eq(1000), "mean_precision_at_k"
        ].iloc[0]
    )
    result["mean_lift_at_1000"] = float(
        top_k_summary.loc[
            top_k_summary["requested_k"].eq(1000), "mean_lift_at_k"
        ].iloc[0]
    )
    return result


def select_on_early_oof_evaluate_2017(
    oof: pd.DataFrame,
    base_config: dict,
) -> dict:
    ensemble = oof.loc[oof["record_type"].eq("ensemble")]
    early = ensemble["selection_year"].lt(2017).to_numpy()
    holdout = ensemble["selection_year"].eq(2017).to_numpy()
    rows = []
    for risk_threshold in base_config["risk_thresholds"]:
        for stopped_threshold in base_config["conditional_stopped_thresholds"]:
            predictions = base.h2_predictions(
                ensemble["risk_score"].to_numpy(),
                ensemble["conditional_stopped_score"].to_numpy(),
                risk_threshold,
                stopped_threshold,
            )
            metrics = base.evaluate(
                ensemble.loc[early, "retention_state"].to_numpy(),
                predictions[early],
                ensemble.loc[early, base.SCORE_COLUMNS].to_numpy(),
            )
            rows.append((metrics["macro_f1"], risk_threshold, stopped_threshold))
    _, risk_threshold, stopped_threshold = max(rows)
    predictions = base.h2_predictions(
        ensemble["risk_score"].to_numpy(),
        ensemble["conditional_stopped_score"].to_numpy(),
        risk_threshold,
        stopped_threshold,
    )
    metrics = base.evaluate(
        ensemble.loc[holdout, "retention_state"].to_numpy(),
        predictions[holdout],
        ensemble.loc[holdout, base.SCORE_COLUMNS].to_numpy(),
    )
    return {
        "threshold_selection_years": [2013, 2016],
        "evaluation_year": 2017,
        "risk_threshold": risk_threshold,
        "conditional_stopped_threshold": stopped_threshold,
        "metrics": metrics,
    }


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    suite_config = json.loads(SUITE_CONFIG_PATH.read_text(encoding="utf-8"))
    if args.experiment not in suite_config["experiments"]:
        raise ValueError(f"Unknown experiment: {args.experiment}")
    experiment_config = suite_config["experiments"][args.experiment]
    report_dir = ROOT / "reports" / "experiments" / args.experiment
    selected_path = report_dir / "selected_oof_candidate.json"
    if selected_path.exists() and not args.overwrite:
        raise FileExistsError(f"{selected_path} exists; use --overwrite")
    required = [BASELINE_OOF_PATH, BASELINE_METADATA_PATH]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing v05_05 baseline:\n- " + "\n- ".join(missing))

    frame, raw_sequence, raw_lifecycle, base_config, build_metadata = base.load_contract()
    raw_extra, extra_names = load_extra_features(
        frame, suite_config, experiment_config["extra_feature_group"]
    )
    aux = auxiliary_labels(frame)
    device = torch.device("cpu")
    torch.set_num_threads(min(4, max(1, torch.get_num_threads())))
    print(
        f"version={args.experiment}, label={experiment_config['label']}, "
        f"extra_features={len(extra_names)}, development_rows={len(frame):,}, "
        "final_test_rows=0",
        flush=True,
    )
    oof = run_oof(
        frame,
        raw_sequence,
        raw_lifecycle,
        raw_extra,
        aux,
        base_config,
        suite_config,
        experiment_config,
        args.experiment,
        device,
    )
    thresholds, selected = base.threshold_search(oof, base_config)
    ensemble = oof.loc[oof["record_type"].eq("ensemble")].copy()
    predictions = base.h2_predictions(
        ensemble["risk_score"].to_numpy(),
        ensemble["conditional_stopped_score"].to_numpy(),
        float(selected["risk_threshold"]),
        float(selected["conditional_stopped_threshold"]),
    )
    candidate_metrics = stage_metrics(
        ensemble,
        predictions,
        base.evaluate(
            ensemble["retention_state"].to_numpy(),
            predictions,
            ensemble[base.SCORE_COLUMNS].to_numpy(),
        ),
    )
    baseline_oof = pd.read_parquet(BASELINE_OOF_PATH)
    baseline_ensemble = baseline_oof.loc[
        baseline_oof["record_type"].eq("ensemble")
    ].copy()
    if baseline_ensemble["sample_id"].tolist() != ensemble["sample_id"].tolist():
        raise ValueError("Baseline and ablation OOF sample order differ")
    baseline_metadata = json.loads(BASELINE_METADATA_PATH.read_text(encoding="utf-8"))
    baseline_thresholds = baseline_metadata["selected_thresholds"]
    baseline_predictions = base.h2_predictions(
        baseline_ensemble["risk_score"].to_numpy(),
        baseline_ensemble["conditional_stopped_score"].to_numpy(),
        baseline_thresholds["risk_score"],
        baseline_thresholds["conditional_stopped_score"],
    )
    baseline_metrics = stage_metrics(
        baseline_ensemble,
        baseline_predictions,
        base.evaluate(
            baseline_ensemble["retention_state"].to_numpy(),
            baseline_predictions,
            baseline_ensemble[base.SCORE_COLUMNS].to_numpy(),
        ),
    )
    comparison = pd.DataFrame(
        [
            {"candidate": "v05_05_dl_baseline", **baseline_metrics},
            {"candidate": args.experiment, **candidate_metrics},
        ]
    )
    user_map = pd.read_parquet(
        SOURCE_PATH,
        columns=["sample_id", "user_id", "selection_year"],
        filters=[("selection_year", "<=", 2017)],
    )[["sample_id", "user_id"]]
    bootstrap_frame = ensemble[["sample_id", "retention_state"]].merge(
        user_map, on="sample_id", how="left", validate="one_to_one"
    )
    bootstrap = base.bootstrap_comparison(
        bootstrap_frame["retention_state"].to_numpy(),
        baseline_predictions,
        predictions,
        bootstrap_frame["user_id"].to_numpy(),
    )
    bootstrap = bootstrap.rename(
        columns={
            "mean_difference_v05_05_minus_v05_04": (
                "mean_difference_candidate_minus_baseline"
            )
        }
    )
    holdout = select_on_early_oof_evaluate_2017(oof, base_config)
    matrix = confusion_matrix(
        ensemble["retention_state"], predictions, labels=base.CLASS_CODES
    )

    report_dir.mkdir(parents=True, exist_ok=True)
    oof.to_parquet(report_dir / "oof_predictions.parquet", index=False)
    thresholds.to_csv(
        report_dir / "threshold_candidates.csv", index=False, encoding="utf-8-sig"
    )
    comparison.to_csv(
        report_dir / "oof_comparison.csv", index=False, encoding="utf-8-sig"
    )
    bootstrap.to_csv(
        report_dir / "paired_bootstrap.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(
        matrix,
        index=[f"actual_{name}" for name in base.CLASS_NAMES],
        columns=[f"predicted_{name}" for name in base.CLASS_NAMES],
    ).to_csv(report_dir / "oof_confusion.csv", encoding="utf-8-sig")

    metadata = {
        "version": args.experiment,
        "status": "development_ablation_complete",
        "baseline_version": "v05_05_dl",
        "description": experiment_config["description"],
        "change_from_baseline": experiment_config,
        "extra_features": extra_names,
        "selection_basis": "pooled expanding-time OOF only",
        "development_samples": len(frame),
        "oof_samples": len(ensemble),
        "final_test_rows_loaded": 0,
        "final_test_predictions_created": 0,
        "final_test_metrics_created": 0,
        "selected_thresholds": {
            "risk_score": float(selected["risk_threshold"]),
            "conditional_stopped_score": float(
                selected["conditional_stopped_threshold"]
            ),
        },
        "oof_metrics": candidate_metrics,
        "baseline_oof_metrics": baseline_metrics,
        "delta_vs_baseline": {
            key: candidate_metrics[key] - baseline_metrics[key]
            for key in [
                "macro_f1",
                "macro_pr_auc",
                "balanced_accuracy",
                "weakened_recall",
                "stopped_recall",
                "conditional_stopped_pr_auc",
                "severe_error_rate",
                "mean_precision_at_1000",
            ]
        },
        "seed_macro_f1_mean": float(selected["seed_macro_f1_mean"]),
        "seed_macro_f1_std": float(selected["seed_macro_f1_std"]),
        "internal_2017_holdout": holdout,
        "feature_artifacts": build_metadata["artifacts"],
        "test_policy": suite_config["test_policy"],
        "runtime": {
            "device": str(device),
            "python_version": sys.version.split()[0],
            "torch_version": torch.__version__,
            "sklearn_version": sklearn.__version__,
            "pandas_version": pd.__version__,
            "elapsed_seconds": time.perf_counter() - started,
        },
    }
    base.save_json(selected_path, metadata)
    report = f"""# {args.experiment} — {experiment_config['label']}

- Final Test rows loaded/predicted/evaluated: 0 / 0 / 0
- OOF Macro F1: {candidate_metrics['macro_f1']:.4f} ({metadata['delta_vs_baseline']['macro_f1']:+.4f} vs baseline)
- OOF conditional Stopped PR-AUC: {candidate_metrics['conditional_stopped_pr_auc']:.4f} ({metadata['delta_vs_baseline']['conditional_stopped_pr_auc']:+.4f})
- OOF weakened Recall: {candidate_metrics['weakened_recall']:.2%}
- OOF stopped Recall: {candidate_metrics['stopped_recall']:.2%}
- OOF stopped Precision: {candidate_metrics['stopped_precision']:.2%}
- OOF severe error rate: {candidate_metrics['severe_error_rate']:.2%}
- OOF mean Precision@1000: {candidate_metrics['mean_precision_at_1000']:.2%}
- 2017 internal holdout Macro F1: {holdout['metrics']['macro_f1']:.4f}

This is an OOF development ablation, not a final-Test-approved model.
"""
    (report_dir / "performance.md").write_text(report, encoding="utf-8")
    print(
        f"{args.experiment}: Macro F1={candidate_metrics['macro_f1']:.4f}, "
        f"state PR-AUC={candidate_metrics['conditional_stopped_pr_auc']:.4f}, "
        f"delta F1={metadata['delta_vs_baseline']['macro_f1']:+.4f}, "
        "final_test_rows=0",
        flush=True,
    )


if __name__ == "__main__":
    main()
