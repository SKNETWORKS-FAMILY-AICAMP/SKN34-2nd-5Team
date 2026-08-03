"""Train and compare the v05_06 Multi-scale TCN H2 model using OOF only.

The frozen v05_05 development features are reused so the comparison isolates
the model-family change. Selection-year 2018 and target-year 2019 are never
loaded, predicted, thresholded, or evaluated.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# PyTorch must initialize its bundled Windows runtime before NumPy/sklearn.
import torch
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import average_precision_score, confusion_matrix, f1_score
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.v05_05_dl import train as base


VERSION = "v05_06_dl"
BASELINE_VERSION = "v05_05_dl"
CONFIG_PATH = Path(__file__).with_name("config.json")
REPORT_DIR = ROOT / "reports" / "experiments" / VERSION
MODEL_DIR = ROOT / "models" / "experiments" / VERSION
BASELINE_REPORT_DIR = ROOT / "reports" / "experiments" / BASELINE_VERSION


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


class ResidualTemporalBlock(nn.Module):
    def __init__(
        self,
        input_channels: int,
        output_channels: int,
        kernel_size: int,
        dilation: int,
        dropout: float,
    ) -> None:
        super().__init__()
        padding = dilation * (kernel_size - 1) // 2
        self.conv1 = nn.Conv1d(
            input_channels,
            output_channels,
            kernel_size,
            padding=padding,
            dilation=dilation,
        )
        self.norm1 = nn.GroupNorm(1, output_channels)
        self.conv2 = nn.Conv1d(
            output_channels,
            output_channels,
            kernel_size,
            padding=padding,
            dilation=dilation,
        )
        self.norm2 = nn.GroupNorm(1, output_channels)
        self.activation = nn.GELU()
        self.dropout = nn.Dropout(dropout)
        self.shortcut = (
            nn.Identity()
            if input_channels == output_channels
            else nn.Conv1d(input_channels, output_channels, kernel_size=1)
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        residual = self.shortcut(values)
        encoded = self.dropout(self.activation(self.norm1(self.conv1(values))))
        encoded = self.dropout(self.norm2(self.conv2(encoded)))
        return self.activation(encoded + residual)


class MultiScaleTCNH2(nn.Module):
    def __init__(
        self,
        sequence_dim: int,
        lifecycle_dim: int,
        sequence_length: int,
        config: dict,
    ) -> None:
        super().__init__()
        channels = [int(value) for value in config["tcn_channels"]]
        dilations = [int(value) for value in config["tcn_dilations"]]
        if len(channels) != len(dilations):
            raise ValueError("tcn_channels and tcn_dilations must have equal length")
        dropout = float(config["dropout"])
        kernel_size = int(config["kernel_size"])
        self.input_projection = nn.Conv1d(sequence_dim, channels[0], kernel_size=1)
        self.position_embedding = nn.Parameter(
            torch.zeros(1, channels[0], sequence_length)
        )
        blocks = []
        input_channels = channels[0]
        for output_channels, dilation in zip(channels, dilations, strict=True):
            blocks.append(
                ResidualTemporalBlock(
                    input_channels,
                    output_channels,
                    kernel_size,
                    dilation,
                    dropout,
                )
            )
            input_channels = output_channels
        self.temporal_blocks = nn.Sequential(*blocks)
        self.attention = nn.Conv1d(channels[-1], 1, kernel_size=1)
        self.lifecycle_encoder = nn.Sequential(
            nn.Linear(lifecycle_dim, int(config["lifecycle_hidden_dim"])),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        fusion_input = channels[-1] * 2 + int(config["lifecycle_hidden_dim"])
        self.fusion = nn.Sequential(
            nn.Linear(fusion_input, int(config["fusion_hidden_dim"])),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.risk_head = nn.Linear(int(config["fusion_hidden_dim"]), 1)
        self.conditional_stopped_head = nn.Linear(
            int(config["fusion_hidden_dim"]), 1
        )
        nn.init.normal_(self.position_embedding, mean=0.0, std=0.02)

    def forward(
        self, sequence: torch.Tensor, lifecycle: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        temporal = self.input_projection(sequence.transpose(1, 2))
        temporal = self.temporal_blocks(temporal + self.position_embedding)
        attention = torch.softmax(self.attention(temporal), dim=-1)
        pooled = torch.sum(temporal * attention, dim=-1)
        recent = temporal[:, :, -1]
        lifecycle_encoded = self.lifecycle_encoder(lifecycle)
        fused = self.fusion(torch.cat([pooled, recent, lifecycle_encoded], dim=1))
        return (
            self.risk_head(fused).squeeze(1),
            self.conditional_stopped_head(fused).squeeze(1),
        )


def make_model(config: dict, device: torch.device) -> MultiScaleTCNH2:
    return MultiScaleTCNH2(4, 5, 24, config).to(device)


def train_model(
    sequence: np.ndarray,
    lifecycle: np.ndarray,
    labels: np.ndarray,
    model_config: dict,
    seed: int,
    device: torch.device,
) -> MultiScaleTCNH2:
    base.set_seed(seed)
    model = make_model(model_config, device)
    dataset = TensorDataset(
        torch.from_numpy(sequence),
        torch.from_numpy(lifecycle),
        torch.from_numpy(labels.astype(np.int64)),
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
    state_loss = nn.BCEWithLogitsLoss()
    model.train()
    for _ in range(int(model_config["epochs"])):
        for sequence_batch, lifecycle_batch, label_batch in loader:
            sequence_batch = sequence_batch.to(device)
            lifecycle_batch = lifecycle_batch.to(device)
            label_batch = label_batch.to(device)
            risk_logits, stopped_logits = model(sequence_batch, lifecycle_batch)
            loss = risk_loss(risk_logits, label_batch.ne(0).float())
            at_risk = label_batch.ne(0)
            if at_risk.any():
                loss = loss + float(model_config["state_loss_weight"]) * state_loss(
                    stopped_logits[at_risk], label_batch[at_risk].eq(2).float()
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
    model: MultiScaleTCNH2,
    sequence: np.ndarray,
    lifecycle: np.ndarray,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    model.eval()
    loader = DataLoader(
        TensorDataset(torch.from_numpy(sequence), torch.from_numpy(lifecycle)),
        batch_size=4096,
        shuffle=False,
        num_workers=0,
    )
    risk_parts = []
    stopped_parts = []
    for sequence_batch, lifecycle_batch in loader:
        risk_logits, stopped_logits = model(
            sequence_batch.to(device), lifecycle_batch.to(device)
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
    config: dict,
    device: torch.device,
) -> pd.DataFrame:
    parts = []
    total = len(base.TIME_FOLDS) * len(config["seeds"])
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
        labels = frame.loc[train_mask, "retention_state"].to_numpy(dtype=np.int64)
        fold_scores = []
        fold_risk = []
        fold_stopped = []
        for seed in config["seeds"]:
            run += 1
            print(
                f"MultiScaleTCNH2 {run}/{total}: train 2010-{train_end}, "
                f"validation {validation_year}, seed {seed}",
                flush=True,
            )
            model = train_model(
                train_sequence,
                train_lifecycle,
                labels,
                config["model"],
                int(seed),
                device,
            )
            scores, risk, stopped = predict_scores(
                model, validation_sequence, validation_lifecycle, device
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
    ensemble: pd.DataFrame, predictions: np.ndarray, metrics: dict
) -> dict:
    labels = ensemble["retention_state"].to_numpy()
    at_risk = labels != 0
    top_k = base.top_k_tables(ensemble)[1]
    row = top_k.loc[top_k["requested_k"].eq(1000)].iloc[0]
    return {
        **metrics,
        "risk_pr_auc": float(
            average_precision_score(at_risk, ensemble["risk_score"].to_numpy())
        ),
        "conditional_stopped_pr_auc": float(
            average_precision_score(
                labels[at_risk] == 2,
                ensemble.loc[at_risk, "conditional_stopped_score"].to_numpy(),
            )
        ),
        "mean_precision_at_1000": float(row["mean_precision_at_k"]),
        "mean_lift_at_1000": float(row["mean_lift_at_k"]),
    }


def evaluate_2017(oof: pd.DataFrame, config: dict) -> dict:
    ensemble = oof.loc[oof["record_type"].eq("ensemble")].copy()
    early = ensemble["selection_year"].between(2013, 2016)
    holdout = ensemble["selection_year"].eq(2017)
    candidates = []
    for risk_threshold in config["risk_thresholds"]:
        for stopped_threshold in config["conditional_stopped_thresholds"]:
            predictions = base.h2_predictions(
                ensemble.loc[early, "risk_score"].to_numpy(),
                ensemble.loc[early, "conditional_stopped_score"].to_numpy(),
                float(risk_threshold),
                float(stopped_threshold),
            )
            metrics = base.evaluate(
                ensemble.loc[early, "retention_state"].to_numpy(),
                predictions,
                ensemble.loc[early, base.SCORE_COLUMNS].to_numpy(),
            )
            candidates.append(
                (metrics["macro_f1"], risk_threshold, stopped_threshold)
            )
    _, risk_threshold, stopped_threshold = max(candidates, key=lambda item: item[0])
    predictions = base.h2_predictions(
        ensemble.loc[holdout, "risk_score"].to_numpy(),
        ensemble.loc[holdout, "conditional_stopped_score"].to_numpy(),
        float(risk_threshold),
        float(stopped_threshold),
    )
    return {
        "threshold_selection_years": [2013, 2016],
        "evaluation_year": 2017,
        "risk_threshold": float(risk_threshold),
        "conditional_stopped_threshold": float(stopped_threshold),
        "metrics": base.evaluate(
            ensemble.loc[holdout, "retention_state"].to_numpy(),
            predictions,
            ensemble.loc[holdout, base.SCORE_COLUMNS].to_numpy(),
        ),
    }


def train_full_development(
    frame: pd.DataFrame,
    raw_sequence: np.ndarray,
    raw_lifecycle: np.ndarray,
    config: dict,
    device: torch.device,
) -> dict:
    sequence_scaler = StandardScaler()
    lifecycle_scaler = StandardScaler()
    sequence = sequence_scaler.fit_transform(
        raw_sequence.reshape(-1, 4)
    ).reshape(raw_sequence.shape).astype(np.float32)
    lifecycle = lifecycle_scaler.fit_transform(raw_lifecycle).astype(np.float32)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    preprocessing_path = MODEL_DIR / "preprocessing.joblib"
    joblib.dump(
        {
            "sequence_scaler": sequence_scaler,
            "lifecycle_scaler": lifecycle_scaler,
            "sequence_log1p_channels": [0, 2, 3],
            "feature_contract_source": BASELINE_VERSION,
        },
        preprocessing_path,
    )
    labels = frame["retention_state"].to_numpy(dtype=np.int64)
    weight_hashes = {}
    for seed in config["seeds"]:
        print(f"full development TCN training 2010-2017, seed {seed}", flush=True)
        model = train_model(
            sequence,
            lifecycle,
            labels,
            config["model"],
            int(seed),
            device,
        )
        path = MODEL_DIR / f"seed_{seed}_state_dict.pt"
        torch.save(
            {key: value.detach().cpu() for key, value in model.state_dict().items()},
            path,
        )
        reloaded = make_model(config["model"], device)
        reloaded.load_state_dict(
            torch.load(path, map_location=device, weights_only=True)
        )
        expected = predict_scores(model, sequence[:256], lifecycle[:256], device)[0]
        actual = predict_scores(reloaded, sequence[:256], lifecycle[:256], device)[0]
        if not np.allclose(expected, actual, rtol=0, atol=1e-7):
            raise ValueError("Reloaded v05_06 model changed scores")
        weight_hashes[str(seed)] = base.sha256(path)
    return {
        "artifact_status": "development_candidate_not_test_evaluated",
        "training_selection_years": [2010, 2017],
        "preprocessing_path": str(preprocessing_path),
        "preprocessing_sha256": base.sha256(preprocessing_path),
        "weight_sha256": weight_hashes,
    }


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    selected_path = REPORT_DIR / "selected_oof_candidate.json"
    if selected_path.exists() and not args.overwrite:
        raise FileExistsError(f"{selected_path} exists; use --overwrite")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    frame, raw_sequence, raw_lifecycle, base_config, build_metadata = (
        base.load_contract()
    )
    if config["sequence_channels"] != base_config["sequence_channels"]:
        raise ValueError("v05_06 sequence feature contract changed")
    if config["lifecycle_features"] != base_config["lifecycle_features"]:
        raise ValueError("v05_06 lifecycle feature contract changed")
    if frame["selection_year"].max() >= 2018:
        raise ValueError("Final-Test row entered v05_06")
    torch.set_num_threads(min(4, max(1, torch.get_num_threads())))
    device = torch.device("cpu")
    print(
        f"version={VERSION}, model=MultiScaleTCNH2, "
        f"development_rows={len(frame):,}, final_test_rows=0",
        flush=True,
    )
    oof = run_oof(frame, raw_sequence, raw_lifecycle, config, device)
    thresholds, selected = base.threshold_search(oof, config)
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

    baseline_oof = pd.read_parquet(BASELINE_REPORT_DIR / "oof_predictions.parquet")
    baseline_ensemble = baseline_oof.loc[
        baseline_oof["record_type"].eq("ensemble")
    ].copy()
    if baseline_ensemble["sample_id"].tolist() != ensemble["sample_id"].tolist():
        raise ValueError("v05_05 and v05_06 OOF sample order differs")
    baseline_metadata = json.loads(
        (BASELINE_REPORT_DIR / "selected_oof_candidate.json").read_text(
            encoding="utf-8"
        )
    )
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
            {"candidate": BASELINE_VERSION, **baseline_metrics},
            {"candidate": VERSION, **candidate_metrics},
        ]
    )
    user_map = pd.read_parquet(
        base.SOURCE_PATH,
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
    ).rename(
        columns={
            "mean_difference_v05_05_minus_v05_04": (
                "mean_difference_v05_06_minus_v05_05"
            )
        }
    )
    holdout = evaluate_2017(oof, config)
    matrix = confusion_matrix(
        ensemble["retention_state"], predictions, labels=base.CLASS_CODES
    )
    top_k_detail, top_k_summary = base.top_k_tables(ensemble)
    model_artifacts = train_full_development(
        frame, raw_sequence, raw_lifecycle, config, device
    )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    oof.to_parquet(REPORT_DIR / "oof_predictions.parquet", index=False)
    thresholds.to_csv(
        REPORT_DIR / "threshold_candidates.csv", index=False, encoding="utf-8-sig"
    )
    comparison.to_csv(
        REPORT_DIR / "oof_comparison.csv", index=False, encoding="utf-8-sig"
    )
    bootstrap.to_csv(
        REPORT_DIR / "paired_bootstrap.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(
        matrix,
        index=[f"actual_{name}" for name in base.CLASS_NAMES],
        columns=[f"predicted_{name}" for name in base.CLASS_NAMES],
    ).to_csv(REPORT_DIR / "oof_confusion.csv", encoding="utf-8-sig")
    top_k_detail.to_csv(
        REPORT_DIR / "oof_top_k_by_year.csv", index=False, encoding="utf-8-sig"
    )
    top_k_summary.to_csv(
        REPORT_DIR / "oof_top_k_summary.csv", index=False, encoding="utf-8-sig"
    )

    delta_keys = [
        "macro_f1",
        "macro_pr_auc",
        "balanced_accuracy",
        "weakened_recall",
        "stopped_recall",
        "conditional_stopped_pr_auc",
        "severe_error_rate",
        "mean_precision_at_1000",
    ]
    metadata = {
        "version": VERSION,
        "status": "development_candidate_complete",
        "baseline_version": BASELINE_VERSION,
        "model_family": (
            "Core4 Multi-scale TCN with attention/recent pooling + "
            "Lifecycle MLP + H2 hierarchical heads"
        ),
        "change_from_baseline": (
            "GRU sequence encoder replaced by residual dilated TCN; "
            "features, folds, seeds, losses, and threshold grid frozen"
        ),
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
            "conditional_stopped_score": float(
                selected["conditional_stopped_threshold"]
            ),
        },
        "oof_metrics": candidate_metrics,
        "baseline_oof_metrics": baseline_metrics,
        "delta_vs_baseline": {
            key: candidate_metrics[key] - baseline_metrics[key]
            for key in delta_keys
        },
        "seed_macro_f1_mean": float(selected["seed_macro_f1_mean"]),
        "seed_macro_f1_std": float(selected["seed_macro_f1_std"]),
        "internal_2017_holdout": holdout,
        "model_config": config["model"],
        "sequence_channels": config["sequence_channels"],
        "lifecycle_features": config["lifecycle_features"],
        "feature_artifacts": build_metadata["artifacts"],
        "model_artifacts": model_artifacts,
        "test_policy": config["test_policy"],
        "historical_holdout_note": (
            "The historical 2018 holdout remains untouched by v05_06; "
            "this version receives no new final-Test score."
        ),
        "runtime": {
            "device": str(device),
            "python_version": sys.version.split()[0],
            "torch_version": torch.__version__,
            "sklearn_version": sklearn.__version__,
            "pandas_version": pd.__version__,
            "elapsed_seconds": time.perf_counter() - started,
        },
    }
    base.save_json(MODEL_DIR / "metadata.json", metadata)
    base.save_json(selected_path, metadata)
    report = f"""# v05_06 Multi-scale TCN H2 — development OOF result

- Final Test rows loaded/predicted/evaluated: 0 / 0 / 0
- OOF Macro F1: {candidate_metrics['macro_f1']:.4f} ({metadata['delta_vs_baseline']['macro_f1']:+.4f} vs v05_05)
- OOF Macro PR-AUC: {candidate_metrics['macro_pr_auc']:.4f} ({metadata['delta_vs_baseline']['macro_pr_auc']:+.4f})
- OOF weakened Recall: {candidate_metrics['weakened_recall']:.2%}
- OOF stopped Recall: {candidate_metrics['stopped_recall']:.2%}
- OOF conditional Stopped PR-AUC: {candidate_metrics['conditional_stopped_pr_auc']:.4f}
- OOF severe error rate: {candidate_metrics['severe_error_rate']:.2%}
- OOF mean Precision@1000: {candidate_metrics['mean_precision_at_1000']:.2%}
- 2017 internal holdout Macro F1: {holdout['metrics']['macro_f1']:.4f}

This is a development candidate, not a final-Test-approved or deployed model.
Model outputs are ranking/classification scores, not calibrated probabilities.
"""
    (REPORT_DIR / "performance.md").write_text(report, encoding="utf-8")
    print(
        f"{VERSION}: Macro F1={candidate_metrics['macro_f1']:.4f}, "
        f"delta={metadata['delta_vs_baseline']['macro_f1']:+.4f}, "
        f"state PR-AUC={candidate_metrics['conditional_stopped_pr_auc']:.4f}, "
        "final_test_rows=0",
        flush=True,
    )


if __name__ == "__main__":
    main()
