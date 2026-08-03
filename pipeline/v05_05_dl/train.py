"""Train and evaluate the v05_05 Lifecycle Fusion H2 candidate with OOF only.

No selection-year 2018 row or target-year 2019 label is loaded, predicted, or
reported by this module. The saved weights are development-candidate weights
trained on selection years 2010-2017 after all OOF reporting is complete.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import sys
import time
from pathlib import Path

# PyTorch must initialize its bundled Windows runtime before NumPy/sklearn.
import torch
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler, label_binarize
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


ROOT = Path(__file__).resolve().parents[2]
VERSION = "v05_05_dl"
CONFIG_PATH = Path(__file__).with_name("config.json")
SOURCE_PATH = ROOT / "data" / "processed" / "modeling_dataset_rolling_v05_2.parquet"
LIFECYCLE_PATH = ROOT / "data" / "processed" / "experiments" / "lifecycle_features_v05_05.parquet"
SEQUENCE_PATH = ROOT / "data" / "processed" / "experiments" / "monthly_core4_sequence_v05_05.parquet"
BUILD_METADATA_PATH = ROOT / "reports" / "experiments" / VERSION / "feature_build_metadata.json"
REPORT_DIR = ROOT / "reports" / "experiments" / VERSION
MODEL_DIR = ROOT / "models" / "experiments" / VERSION
BASELINE_OOF_PATH = ROOT / "reports" / "experiments" / "v05_04_04_dl" / "selected_oof_predictions.parquet"
BASELINE_COMPARISON_PATH = ROOT / "reports" / "experiments" / "v05_04_04_dl" / "oof_finalist_comparison.csv"

CLASS_CODES = [0, 1, 2]
CLASS_NAMES = ["retained", "weakened", "stopped"]
TIME_FOLDS = [(2012, 2013), (2013, 2014), (2014, 2015), (2015, 2016), (2016, 2017)]
SCORE_COLUMNS = ["retained_score", "weakened_score", "stopped_score"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


class LifecycleFusionH2(nn.Module):
    def __init__(self, sequence_dim: int, lifecycle_dim: int, config: dict):
        super().__init__()
        self.gru = nn.GRU(
            input_size=sequence_dim,
            hidden_size=int(config["gru_hidden_dim"]),
            batch_first=True,
        )
        dropout = float(config["dropout"])
        self.lifecycle_encoder = nn.Sequential(
            nn.Linear(lifecycle_dim, int(config["lifecycle_hidden_dim"])),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.fusion = nn.Sequential(
            nn.Linear(
                int(config["gru_hidden_dim"]) + int(config["lifecycle_hidden_dim"]),
                int(config["fusion_hidden_dim"]),
            ),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.risk_head = nn.Linear(int(config["fusion_hidden_dim"]), 1)
        self.conditional_stopped_head = nn.Linear(int(config["fusion_hidden_dim"]), 1)

    def forward(self, sequence: torch.Tensor, lifecycle: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        _, hidden = self.gru(sequence)
        lifecycle_encoded = self.lifecycle_encoder(lifecycle)
        fused = self.fusion(torch.cat([hidden[-1], lifecycle_encoded], dim=1))
        return self.risk_head(fused).squeeze(1), self.conditional_stopped_head(fused).squeeze(1)


def make_model(config: dict, device: torch.device) -> LifecycleFusionH2:
    return LifecycleFusionH2(4, 5, config).to(device)


def load_contract() -> tuple[pd.DataFrame, np.ndarray, np.ndarray, dict, dict]:
    required = [CONFIG_PATH, SOURCE_PATH, LIFECYCLE_PATH, SEQUENCE_PATH, BUILD_METADATA_PATH]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing v05_05 inputs:\n- " + "\n- ".join(missing))
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    metadata = json.loads(BUILD_METADATA_PATH.read_text(encoding="utf-8"))
    if metadata["final_test_rows_loaded"] != 0 or metadata["selection_year_max"] >= 2018:
        raise ValueError("Feature artifact is not development-only")
    if metadata["artifacts"]["lifecycle_sha256"] != sha256(LIFECYCLE_PATH):
        raise ValueError("Lifecycle feature checksum mismatch")
    if metadata["artifacts"]["sequence_sha256"] != sha256(SEQUENCE_PATH):
        raise ValueError("Core4 sequence checksum mismatch")
    frame = pd.read_parquet(
        SOURCE_PATH,
        columns=["sample_id", "selection_year", "retention_state"],
        filters=[("selection_year", "<=", 2017)],
    ).sort_values("sample_id", kind="stable").reset_index(drop=True)
    if len(frame) != 31_420 or frame["selection_year"].max() >= 2018:
        raise ValueError("Final Test row entered v05_05 training contract")
    lifecycle = pd.read_parquet(LIFECYCLE_PATH).sort_values("sample_id", kind="stable")
    if lifecycle["sample_id"].tolist() != frame["sample_id"].tolist():
        raise ValueError("Lifecycle sample order changed")
    lifecycle_values = lifecycle[config["lifecycle_features"]].to_numpy(dtype=np.float32)
    sequence = pd.read_parquet(SEQUENCE_PATH)
    if len(sequence) != len(frame) * 24:
        raise ValueError("Expected 24 Core4 months per development sample")
    if sequence["sample_id"].drop_duplicates().tolist() != frame["sample_id"].tolist():
        raise ValueError("Core4 sequence sample order changed")
    month_matrix = sequence["month_index"].to_numpy().reshape(-1, 24)
    if not np.array_equal(month_matrix, np.tile(np.arange(24), (len(frame), 1))):
        raise ValueError("Core4 month order changed")
    sequence_values = sequence[config["sequence_channels"]].to_numpy(dtype=np.float32).reshape(len(frame), 24, 4)
    sequence_values[:, :, 0] = np.log1p(sequence_values[:, :, 0])
    sequence_values[:, :, 2] = np.log1p(sequence_values[:, :, 2])
    sequence_values[:, :, 3] = np.log1p(sequence_values[:, :, 3])
    if np.isnan(sequence_values).any() or np.isinf(sequence_values).any():
        raise ValueError("Invalid Core4 sequence value")
    return frame, sequence_values, lifecycle_values, config, metadata


def scale_inputs(
    train_sequence: np.ndarray,
    validation_sequence: np.ndarray,
    train_lifecycle: np.ndarray,
    validation_lifecycle: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, StandardScaler, StandardScaler]:
    sequence_scaler = StandardScaler()
    lifecycle_scaler = StandardScaler()
    train_sequence_scaled = sequence_scaler.fit_transform(train_sequence.reshape(-1, 4)).reshape(train_sequence.shape).astype(np.float32)
    validation_sequence_scaled = sequence_scaler.transform(validation_sequence.reshape(-1, 4)).reshape(validation_sequence.shape).astype(np.float32)
    train_lifecycle_scaled = lifecycle_scaler.fit_transform(train_lifecycle).astype(np.float32)
    validation_lifecycle_scaled = lifecycle_scaler.transform(validation_lifecycle).astype(np.float32)
    return (
        train_sequence_scaled,
        validation_sequence_scaled,
        train_lifecycle_scaled,
        validation_lifecycle_scaled,
        sequence_scaler,
        lifecycle_scaler,
    )


def train_model(
    sequence: np.ndarray,
    lifecycle: np.ndarray,
    labels: np.ndarray,
    model_config: dict,
    seed: int,
    device: torch.device,
) -> LifecycleFusionH2:
    set_seed(seed)
    model = make_model(model_config, device)
    dataset = TensorDataset(
        torch.from_numpy(sequence),
        torch.from_numpy(lifecycle),
        torch.from_numpy(labels.astype(np.int64)),
    )
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(
        dataset,
        batch_size=int(model_config["batch_size"]),
        shuffle=True,
        generator=generator,
        num_workers=0,
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(model_config["learning_rate"]),
        weight_decay=float(model_config["weight_decay"]),
    )
    risk_loss = nn.BCEWithLogitsLoss(
        pos_weight=torch.tensor(float(model_config["risk_positive_weight"]), device=device)
    )
    state_loss = nn.BCEWithLogitsLoss()
    model.train()
    for _ in range(int(model_config["epochs"])):
        for sequence_batch, lifecycle_batch, label_batch in loader:
            sequence_batch = sequence_batch.to(device)
            lifecycle_batch = lifecycle_batch.to(device)
            label_batch = label_batch.to(device)
            risk_logits, stopped_logits = model(sequence_batch, lifecycle_batch)
            risk_target = label_batch.ne(0).float()
            loss = risk_loss(risk_logits, risk_target)
            at_risk = label_batch.ne(0)
            if at_risk.any():
                stopped_target = label_batch[at_risk].eq(2).float()
                loss = loss + float(model_config["state_loss_weight"]) * state_loss(
                    stopped_logits[at_risk], stopped_target
                )
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), float(model_config["gradient_clip_norm"]))
            optimizer.step()
    return model


@torch.inference_mode()
def predict_scores(
    model: LifecycleFusionH2,
    sequence: np.ndarray,
    lifecycle: np.ndarray,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    model.eval()
    dataset = TensorDataset(torch.from_numpy(sequence), torch.from_numpy(lifecycle))
    loader = DataLoader(dataset, batch_size=4096, shuffle=False, num_workers=0)
    risk_parts = []
    stopped_parts = []
    for sequence_batch, lifecycle_batch in loader:
        risk_logits, stopped_logits = model(sequence_batch.to(device), lifecycle_batch.to(device))
        risk_parts.append(torch.sigmoid(risk_logits).cpu().numpy())
        stopped_parts.append(torch.sigmoid(stopped_logits).cpu().numpy())
    risk = np.concatenate(risk_parts)
    conditional_stopped = np.concatenate(stopped_parts)
    scores = np.column_stack(
        [
            1.0 - risk,
            risk * (1.0 - conditional_stopped),
            risk * conditional_stopped,
        ]
    )
    return scores, risk, conditional_stopped


def h2_predictions(risk: np.ndarray, stopped: np.ndarray, risk_threshold: float, stopped_threshold: float) -> np.ndarray:
    predictions = np.zeros(len(risk), dtype=np.int8)
    at_risk = risk >= risk_threshold
    predictions[at_risk] = 1
    predictions[at_risk & (stopped >= stopped_threshold)] = 2
    return predictions


def legacy_predictions(scores: np.ndarray, weakened_threshold: float, stopped_threshold: float) -> np.ndarray:
    predictions = np.zeros(len(scores), dtype=np.int8)
    predictions[scores[:, 1] >= weakened_threshold] = 1
    predictions[scores[:, 2] >= stopped_threshold] = 2
    return predictions


def evaluate(labels: np.ndarray, predictions: np.ndarray, scores: np.ndarray) -> dict:
    precision, recall, per_class_f1, support = precision_recall_fscore_support(
        labels, predictions, labels=CLASS_CODES, zero_division=0
    )
    binary = label_binarize(labels, classes=CLASS_CODES)
    matrix = confusion_matrix(labels, predictions, labels=CLASS_CODES)
    severe = int(matrix[0, 2] + matrix[2, 0])
    result = {
        "accuracy": float(accuracy_score(labels, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(labels, predictions)),
        "macro_precision": float(precision.mean()),
        "macro_recall": float(recall.mean()),
        "macro_f1": float(f1_score(labels, predictions, average="macro")),
        "weighted_f1": float(f1_score(labels, predictions, average="weighted")),
        "macro_pr_auc": float(np.mean([average_precision_score(binary[:, index], scores[:, index]) for index in CLASS_CODES])),
        "macro_ovr_roc_auc": float(roc_auc_score(labels, scores, multi_class="ovr", average="macro")),
        "retained_to_stopped_count": int(matrix[0, 2]),
        "retained_to_stopped_rate": float(matrix[0, 2] / matrix[0].sum()),
        "stopped_to_retained_count": int(matrix[2, 0]),
        "stopped_to_retained_rate": float(matrix[2, 0] / matrix[2].sum()),
        "severe_error_count": severe,
        "severe_error_rate": float(severe / matrix.sum()),
    }
    for index, name in enumerate(CLASS_NAMES):
        result[f"{name}_precision"] = float(precision[index])
        result[f"{name}_recall"] = float(recall[index])
        result[f"{name}_f1"] = float(per_class_f1[index])
        result[f"{name}_support"] = int(support[index])
        result[f"{name}_pr_auc"] = float(average_precision_score(binary[:, index], scores[:, index]))
    return result


def run_oof(
    frame: pd.DataFrame,
    raw_sequence: np.ndarray,
    raw_lifecycle: np.ndarray,
    config: dict,
    device: torch.device,
) -> pd.DataFrame:
    parts = []
    total = len(TIME_FOLDS) * len(config["seeds"])
    run = 0
    for train_end, validation_year in TIME_FOLDS:
        train_mask = frame["selection_year"].between(2010, train_end).to_numpy()
        validation_mask = frame["selection_year"].eq(validation_year).to_numpy()
        scaled = scale_inputs(
            raw_sequence[train_mask],
            raw_sequence[validation_mask],
            raw_lifecycle[train_mask],
            raw_lifecycle[validation_mask],
        )
        train_sequence, validation_sequence, train_lifecycle, validation_lifecycle = scaled[:4]
        labels = frame.loc[train_mask, "retention_state"].to_numpy(dtype=np.int64)
        fold_scores = []
        fold_risk = []
        fold_stopped = []
        for seed in config["seeds"]:
            run += 1
            print(
                f"LifecycleFusionH2 {run}/{total}: train 2010-{train_end}, "
                f"validation {validation_year}, seed {seed}",
                flush=True,
            )
            model = train_model(train_sequence, train_lifecycle, labels, config["model"], int(seed), device)
            scores, risk, stopped = predict_scores(model, validation_sequence, validation_lifecycle, device)
            fold_scores.append(scores)
            fold_risk.append(risk)
            fold_stopped.append(stopped)
            part = frame.loc[validation_mask, ["sample_id", "selection_year", "retention_state"]].copy()
            part["seed"] = int(seed)
            part[SCORE_COLUMNS] = scores
            part["risk_score"] = risk
            part["conditional_stopped_score"] = stopped
            part["record_type"] = "seed"
            parts.append(part)
        ensemble = frame.loc[validation_mask, ["sample_id", "selection_year", "retention_state"]].copy()
        ensemble["seed"] = -1
        ensemble[SCORE_COLUMNS] = np.mean(fold_scores, axis=0)
        ensemble["risk_score"] = np.mean(fold_risk, axis=0)
        ensemble["conditional_stopped_score"] = np.mean(fold_stopped, axis=0)
        ensemble["record_type"] = "ensemble"
        parts.append(ensemble)
    return pd.concat(parts, ignore_index=True)


def threshold_search(oof: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, pd.Series]:
    ensemble = oof.loc[oof["record_type"].eq("ensemble")]
    labels = ensemble["retention_state"].to_numpy()
    scores = ensemble[SCORE_COLUMNS].to_numpy()
    rows = []
    for risk_threshold, stopped_threshold in itertools.product(
        config["risk_thresholds"], config["conditional_stopped_thresholds"]
    ):
        predictions = h2_predictions(
            ensemble["risk_score"].to_numpy(),
            ensemble["conditional_stopped_score"].to_numpy(),
            float(risk_threshold),
            float(stopped_threshold),
        )
        metrics = evaluate(labels, predictions, scores)
        seed_f1 = []
        for seed in config["seeds"]:
            part = oof.loc[oof["record_type"].eq("seed") & oof["seed"].eq(seed)]
            seed_predictions = h2_predictions(
                part["risk_score"].to_numpy(),
                part["conditional_stopped_score"].to_numpy(),
                float(risk_threshold),
                float(stopped_threshold),
            )
            seed_f1.append(
                evaluate(part["retention_state"].to_numpy(), seed_predictions, part[SCORE_COLUMNS].to_numpy())["macro_f1"]
            )
        rows.append(
            {
                "risk_threshold": risk_threshold,
                "conditional_stopped_threshold": stopped_threshold,
                **{f"oof_{key}": value for key, value in metrics.items()},
                "seed_macro_f1_mean": float(np.mean(seed_f1)),
                "seed_macro_f1_std": float(np.std(seed_f1, ddof=1)),
            }
        )
    candidates = pd.DataFrame(rows).sort_values(
        [
            "oof_macro_f1",
            "oof_macro_pr_auc",
            "oof_balanced_accuracy",
            "oof_severe_error_rate",
            "oof_stopped_recall",
            "oof_weakened_recall",
            "seed_macro_f1_std",
        ],
        ascending=[False, False, False, True, False, False, True],
        kind="stable",
    ).reset_index(drop=True)
    candidates.insert(0, "selection_rank", np.arange(1, len(candidates) + 1))
    candidates["selected"] = candidates["selection_rank"].eq(1)
    return candidates, candidates.iloc[0]


def top_k_tables(ensemble: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for year, part in ensemble.groupby("selection_year", sort=True):
        labels = part["retention_state"].to_numpy()
        risk = part["risk_score"].to_numpy()
        order = np.argsort(-risk, kind="stable")
        for requested_k in [500, 1000, 2000]:
            k = min(requested_k, len(part))
            selected = order[:k]
            at_risk = labels != 0
            precision = float(at_risk[selected].mean())
            rows.append(
                {
                    "selection_year": int(year),
                    "requested_k": requested_k,
                    "actual_k": k,
                    "precision_at_k": precision,
                    "recall_at_k": float(at_risk[selected].sum() / at_risk.sum()),
                    "lift_at_k": float(precision / at_risk.mean()),
                    "weakened_selected": int((labels[selected] == 1).sum()),
                    "stopped_selected": int((labels[selected] == 2).sum()),
                }
            )
    details = pd.DataFrame(rows)
    summary = details.groupby("requested_k", as_index=False).agg(
        folds=("selection_year", "count"),
        mean_precision_at_k=("precision_at_k", "mean"),
        mean_recall_at_k=("recall_at_k", "mean"),
        mean_lift_at_k=("lift_at_k", "mean"),
    )
    return details, summary


def bootstrap_comparison(
    labels: np.ndarray,
    baseline_predictions: np.ndarray,
    candidate_predictions: np.ndarray,
    cluster_ids: np.ndarray,
    repeats: int = 1000,
) -> pd.DataFrame:
    rng = np.random.default_rng(20260802)
    _, cluster_codes = np.unique(cluster_ids, return_inverse=True)
    cluster_count = int(cluster_codes.max()) + 1
    rows = []
    for _ in range(repeats):
        sampled_clusters = rng.integers(0, cluster_count, cluster_count)
        cluster_weights = np.bincount(sampled_clusters, minlength=cluster_count)
        weights = cluster_weights[cluster_codes]
        base_f1 = f1_score(
            labels,
            baseline_predictions,
            average="macro",
            sample_weight=weights,
        )
        candidate_f1 = f1_score(
            labels,
            candidate_predictions,
            average="macro",
            sample_weight=weights,
        )
        weak = labels == 1
        weak_weight = weights[weak].sum()
        base_weak = weights[weak & (baseline_predictions == 1)].sum() / weak_weight
        candidate_weak = weights[weak & (candidate_predictions == 1)].sum() / weak_weight
        rows.append((candidate_f1 - base_f1, candidate_weak - base_weak))
    values = np.asarray(rows)
    return pd.DataFrame(
        [
            {
                "metric": "macro_f1",
                "resampling_unit": "user_id_cluster",
                "mean_difference_v05_05_minus_v05_04": values[:, 0].mean(),
                "ci_2_5": np.quantile(values[:, 0], 0.025),
                "ci_97_5": np.quantile(values[:, 0], 0.975),
            },
            {
                "metric": "weakened_recall",
                "resampling_unit": "user_id_cluster",
                "mean_difference_v05_05_minus_v05_04": values[:, 1].mean(),
                "ci_2_5": np.quantile(values[:, 1], 0.025),
                "ci_97_5": np.quantile(values[:, 1], 0.975),
            },
        ]
    )


def baseline_comparison(
    candidate_ensemble: pd.DataFrame,
    candidate_predictions: np.ndarray,
    candidate_metrics: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = [BASELINE_OOF_PATH, BASELINE_COMPARISON_PATH]
    if any(not path.is_file() for path in required):
        return pd.DataFrame([{"candidate": VERSION, **candidate_metrics}]), pd.DataFrame()
    baseline = pd.read_parquet(BASELINE_OOF_PATH)
    baseline = baseline.loc[baseline["record_type"].eq("ensemble")].copy()
    selected_table = pd.read_csv(BASELINE_COMPARISON_PATH)
    selected_row = selected_table.loc[selected_table["selected"].astype(str).str.lower().eq("true")].iloc[0]
    merged = candidate_ensemble[["sample_id", "retention_state"]].merge(
        baseline[["sample_id", *SCORE_COLUMNS]],
        on="sample_id",
        how="inner",
        validate="one_to_one",
    )
    if len(merged) != len(candidate_ensemble):
        raise ValueError("v05_04 and v05_05 OOF samples differ")
    user_map = pd.read_parquet(
        SOURCE_PATH,
        columns=["sample_id", "user_id", "selection_year"],
        filters=[("selection_year", "<=", 2017)],
    )[["sample_id", "user_id"]]
    merged = merged.merge(user_map, on="sample_id", how="left", validate="one_to_one")
    if merged["user_id"].isna().any():
        raise ValueError("Missing user cluster for OOF bootstrap")
    baseline_predictions = legacy_predictions(
        merged[SCORE_COLUMNS].to_numpy(),
        float(selected_row["weakened_threshold"]),
        float(selected_row["stopped_threshold"]),
    )
    baseline_metrics = evaluate(
        merged["retention_state"].to_numpy(), baseline_predictions, merged[SCORE_COLUMNS].to_numpy()
    )
    comparison = pd.DataFrame(
        [
            {"candidate": "v05_04_oof_selected", **baseline_metrics},
            {"candidate": VERSION, **candidate_metrics},
        ]
    )
    bootstrap = bootstrap_comparison(
        merged["retention_state"].to_numpy(),
        baseline_predictions,
        candidate_predictions,
        merged["user_id"].to_numpy(),
    )
    return comparison, bootstrap


def train_full_development(
    frame: pd.DataFrame,
    raw_sequence: np.ndarray,
    raw_lifecycle: np.ndarray,
    config: dict,
    device: torch.device,
) -> dict:
    sequence_scaler = StandardScaler()
    lifecycle_scaler = StandardScaler()
    sequence = sequence_scaler.fit_transform(raw_sequence.reshape(-1, 4)).reshape(raw_sequence.shape).astype(np.float32)
    lifecycle = lifecycle_scaler.fit_transform(raw_lifecycle).astype(np.float32)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    preprocessing_path = MODEL_DIR / "preprocessing.joblib"
    joblib.dump(
        {
            "sequence_scaler": sequence_scaler,
            "lifecycle_scaler": lifecycle_scaler,
            "sequence_log1p_channels": [0, 2, 3],
        },
        preprocessing_path,
    )
    labels = frame["retention_state"].to_numpy(dtype=np.int64)
    weights = {}
    for seed in config["seeds"]:
        print(f"full development training 2010-2017, seed {seed}", flush=True)
        model = train_model(sequence, lifecycle, labels, config["model"], int(seed), device)
        path = MODEL_DIR / f"seed_{seed}_state_dict.pt"
        torch.save({key: value.detach().cpu() for key, value in model.state_dict().items()}, path)
        reloaded = make_model(config["model"], device)
        reloaded.load_state_dict(torch.load(path, map_location=device, weights_only=True))
        expected = predict_scores(model, sequence[:256], lifecycle[:256], device)[0]
        actual = predict_scores(reloaded, sequence[:256], lifecycle[:256], device)[0]
        if not np.allclose(expected, actual, rtol=0, atol=1e-7):
            raise ValueError("Reloaded v05_05 development model changed scores")
        weights[str(seed)] = sha256(path)
    return {
        "artifact_status": "development_candidate_not_test_evaluated",
        "training_selection_years": [2010, 2017],
        "preprocessing_path": str(preprocessing_path),
        "preprocessing_sha256": sha256(preprocessing_path),
        "weight_sha256": weights,
    }


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    selected_path = REPORT_DIR / "selected_oof_candidate.json"
    if selected_path.exists() and not args.overwrite:
        raise FileExistsError(f"{selected_path} exists; use --overwrite")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(min(4, max(1, torch.get_num_threads())))
    device = torch.device("cpu")
    frame, raw_sequence, raw_lifecycle, config, build_metadata = load_contract()
    print(
        f"version={VERSION}, device={device}, development_rows={len(frame):,}, "
        "final_test_rows=0",
        flush=True,
    )
    oof = run_oof(frame, raw_sequence, raw_lifecycle, config, device)
    thresholds, selected = threshold_search(oof, config)
    ensemble = oof.loc[oof["record_type"].eq("ensemble")].copy()
    predictions = h2_predictions(
        ensemble["risk_score"].to_numpy(),
        ensemble["conditional_stopped_score"].to_numpy(),
        float(selected["risk_threshold"]),
        float(selected["conditional_stopped_threshold"]),
    )
    metrics = evaluate(
        ensemble["retention_state"].to_numpy(), predictions, ensemble[SCORE_COLUMNS].to_numpy()
    )
    matrix = confusion_matrix(ensemble["retention_state"], predictions, labels=CLASS_CODES)
    confusion = pd.DataFrame(
        matrix,
        index=[f"actual_{name}" for name in CLASS_NAMES],
        columns=[f"predicted_{name}" for name in CLASS_NAMES],
    )
    top_k_detail, top_k_summary = top_k_tables(ensemble)
    comparison, bootstrap = baseline_comparison(ensemble, predictions, metrics)
    model_artifacts = train_full_development(frame, raw_sequence, raw_lifecycle, config, device)

    oof.to_parquet(REPORT_DIR / "oof_predictions.parquet", index=False)
    thresholds.to_csv(REPORT_DIR / "threshold_candidates.csv", index=False, encoding="utf-8-sig")
    confusion.to_csv(REPORT_DIR / "oof_confusion.csv", encoding="utf-8-sig")
    top_k_detail.to_csv(REPORT_DIR / "oof_top_k_by_year.csv", index=False, encoding="utf-8-sig")
    top_k_summary.to_csv(REPORT_DIR / "oof_top_k_summary.csv", index=False, encoding="utf-8-sig")
    comparison.to_csv(REPORT_DIR / "oof_model_comparison.csv", index=False, encoding="utf-8-sig")
    if not bootstrap.empty:
        bootstrap.to_csv(REPORT_DIR / "paired_bootstrap.csv", index=False, encoding="utf-8-sig")

    metadata = {
        "version": VERSION,
        "status": "development_candidate_complete",
        "model_family": "Core4 GRU + Lifecycle MLP + H2 hierarchical heads",
        "selection_basis": "pooled expanding-time OOF only",
        "development_samples": len(frame),
        "oof_samples": len(ensemble),
        "development_selection_years": config["development_selection_years"],
        "oof_validation_years": config["oof_validation_years"],
        "final_test_rows_loaded": 0,
        "final_test_predictions_created": 0,
        "final_test_metrics_created": 0,
        "selected_thresholds": {
            "risk_score": float(selected["risk_threshold"]),
            "conditional_stopped_score": float(selected["conditional_stopped_threshold"]),
        },
        "oof_metrics": metrics,
        "seed_macro_f1_mean": float(selected["seed_macro_f1_mean"]),
        "seed_macro_f1_std": float(selected["seed_macro_f1_std"]),
        "model_config": config["model"],
        "sequence_channels": config["sequence_channels"],
        "lifecycle_features": config["lifecycle_features"],
        "feature_artifacts": build_metadata["artifacts"],
        "model_artifacts": model_artifacts,
        "test_policy": config["test_policy"],
        "historical_holdout_note": "The 2018 holdout was exposed by earlier experiments, so v05_05 is reported as an OOF development candidate and is not assigned a new final-Test score.",
        "runtime": {
            "device": str(device),
            "python_version": sys.version.split()[0],
            "torch_version": torch.__version__,
            "sklearn_version": sklearn.__version__,
            "pandas_version": pd.__version__,
            "elapsed_seconds": time.perf_counter() - started,
        },
    }
    save_json(MODEL_DIR / "metadata.json", metadata)
    save_json(selected_path, metadata)
    comparison_text = ""
    if "v05_04_oof_selected" in comparison["candidate"].values:
        baseline_row = comparison.loc[
            comparison["candidate"].eq("v05_04_oof_selected")
        ].iloc[0]
        comparison_text = f"""
## Same-sample OOF comparison with v05_04

- Macro F1: {float(baseline_row['macro_f1']):.4f} → {metrics['macro_f1']:.4f} ({metrics['macro_f1'] - float(baseline_row['macro_f1']):+.4f})
- Macro PR-AUC: {float(baseline_row['macro_pr_auc']):.4f} → {metrics['macro_pr_auc']:.4f} ({metrics['macro_pr_auc'] - float(baseline_row['macro_pr_auc']):+.4f})
- Weakened Recall: {float(baseline_row['weakened_recall']):.2%} → {metrics['weakened_recall']:.2%}
- Stopped Recall: {float(baseline_row['stopped_recall']):.2%} → {metrics['stopped_recall']:.2%}
- Severe error rate: {float(baseline_row['severe_error_rate']):.2%} → {metrics['severe_error_rate']:.2%}
"""
    report = f"""# v05_05 Lifecycle Fusion H2 — development OOF result

- Evaluation boundary: expanding-time OOF only (validation selection years 2013–2017)
- Final Test rows loaded/predicted/evaluated: 0 / 0 / 0
- OOF Macro F1: {metrics['macro_f1']:.4f}
- OOF Macro PR-AUC: {metrics['macro_pr_auc']:.4f}
- OOF balanced accuracy: {metrics['balanced_accuracy']:.4f}
- OOF weakened Recall: {metrics['weakened_recall']:.2%}
- OOF stopped Recall: {metrics['stopped_recall']:.2%}
- OOF retained→stopped: {metrics['retained_to_stopped_count']:,} ({metrics['retained_to_stopped_rate']:.2%})
- OOF stopped→retained: {metrics['stopped_to_retained_count']:,} ({metrics['stopped_to_retained_rate']:.2%})
- OOF severe error rate: {metrics['severe_error_rate']:.2%}
{comparison_text}

This is a development candidate, not a newly final-Test-approved or deployed model.
The class and risk scores are ranking/model scores, not calibrated probabilities.
"""
    (REPORT_DIR / "performance.md").write_text(report, encoding="utf-8")
    print(
        f"OOF Macro F1={metrics['macro_f1']:.4f}, PR-AUC={metrics['macro_pr_auc']:.4f}, "
        f"severe={metrics['severe_error_rate']:.2%}, final_test_rows=0, "
        f"elapsed={time.perf_counter() - started:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
