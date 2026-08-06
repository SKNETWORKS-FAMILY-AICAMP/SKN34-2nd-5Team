"""Evaluate the frozen v05_05 model on the selection-year 2018 Test set.

No training or threshold search occurs here. The script loads the three model
weights trained on selection years 2010-2017, applies the saved preprocessing,
averages seed scores, and evaluates the fixed OOF thresholds against 2019
outcomes.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

# PyTorch must initialize its bundled Windows runtime before NumPy/sklearn.
import torch
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import confusion_matrix

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.v05_05_dl import build_features as feature_base
from pipeline.v05_05_dl import train as model_base


VERSION = "v05_05_dl"
TEST_SELECTION_YEAR = 2018
TEST_TARGET_YEAR = 2019
EXPECTED_TEST_SAMPLES = 6_533
PRIMARY_TARGET_RATE = 0.20
CLASS_LABELS_KO = {
    0: "파워 지위 유지",
    1: "파워 지위 약화",
    2: "리뷰 활동 중단",
}

CONFIG_PATH = Path(__file__).with_name("config.json")
SOURCE_PATH = ROOT / "data" / "processed" / "modeling_dataset_rolling_v05_ml.parquet"
TEST_LIFECYCLE_PATH = (
    ROOT / "data" / "processed" / "experiments" / "test_lifecycle_features_v05_05.parquet"
)
TEST_SEQUENCE_PATH = (
    ROOT / "data" / "processed" / "experiments" / "test_monthly_core4_sequence_v05_05.parquet"
)
TEST_FEATURE_METADATA_PATH = (
    ROOT / "reports" / "experiments" / VERSION / "test_feature_build_metadata.json"
)
MODEL_DIR = ROOT / "models" / "experiments" / VERSION
MODEL_METADATA_PATH = MODEL_DIR / "metadata.json"
PREPROCESSING_PATH = MODEL_DIR / "preprocessing.joblib"
REPORT_DIR = ROOT / "reports" / "experiments" / VERSION
PREDICTION_DIR = ROOT / "data" / "processed" / "predictions"

TEST_PREDICTIONS_PATH = REPORT_DIR / "test_predictions.parquet"
TEST_METRICS_PATH = REPORT_DIR / "test_metrics.json"
TEST_METRICS_TABLE_PATH = REPORT_DIR / "test_metrics.csv"
TEST_CONFUSION_PATH = REPORT_DIR / "test_confusion.csv"
TEST_TOP_K_PATH = REPORT_DIR / "test_top_k.csv"
TEST_PERFORMANCE_PATH = REPORT_DIR / "test_performance.md"
TEST_PROFILE_PATH = PREDICTION_DIR / "test_retention_profiles_v05_05_dl.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def check_outputs(overwrite: bool) -> None:
    outputs = [
        TEST_PREDICTIONS_PATH,
        TEST_METRICS_PATH,
        TEST_METRICS_TABLE_PATH,
        TEST_CONFUSION_PATH,
        TEST_TOP_K_PATH,
        TEST_PERFORMANCE_PATH,
        TEST_PROFILE_PATH,
    ]
    existing = [path for path in outputs if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(f"{existing[0]} exists; use --overwrite")


def verify_model_artifacts(config: dict, metadata: dict) -> list[Path]:
    if metadata.get("version") != VERSION:
        raise ValueError("Model metadata version mismatch")
    if metadata.get("development_selection_years") != [2010, 2017]:
        raise ValueError("Model was not trained on the frozen 2010-2017 range")
    if metadata.get("model_config") != config.get("model"):
        raise ValueError("Model config differs from the saved model metadata")
    if feature_base.sha256(PREPROCESSING_PATH) != metadata["model_artifacts"][
        "preprocessing_sha256"
    ]:
        raise ValueError("Saved preprocessing checksum mismatch")

    paths = []
    for seed in config["seeds"]:
        path = MODEL_DIR / f"seed_{seed}_state_dict.pt"
        expected = metadata["model_artifacts"]["weight_sha256"].get(str(seed))
        if expected is None or feature_base.sha256(path) != expected:
            raise ValueError(f"Saved model checksum mismatch for seed {seed}")
        paths.append(path)
    return paths


def load_test_inputs() -> tuple[pd.DataFrame, np.ndarray, np.ndarray, dict, dict, list[Path]]:
    required = [
        CONFIG_PATH,
        SOURCE_PATH,
        TEST_LIFECYCLE_PATH,
        TEST_SEQUENCE_PATH,
        TEST_FEATURE_METADATA_PATH,
        MODEL_METADATA_PATH,
        PREPROCESSING_PATH,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing v05_05 Test inputs:\n- " + "\n- ".join(missing))

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    model_metadata = json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8"))
    test_metadata = json.loads(TEST_FEATURE_METADATA_PATH.read_text(encoding="utf-8"))
    if test_metadata.get("samples") != EXPECTED_TEST_SAMPLES:
        raise ValueError("Unexpected Test sample count in feature metadata")
    if test_metadata.get("selection_year") != TEST_SELECTION_YEAR:
        raise ValueError("Unexpected Test selection year in feature metadata")
    if test_metadata.get("target_columns_loaded") != []:
        raise ValueError("Target data entered Test feature generation")
    artifacts = test_metadata["artifacts"]
    if feature_base.sha256(TEST_LIFECYCLE_PATH) != artifacts["test_lifecycle_sha256"]:
        raise ValueError("Test Lifecycle feature checksum mismatch")
    if feature_base.sha256(TEST_SEQUENCE_PATH) != artifacts["test_sequence_sha256"]:
        raise ValueError("Test Core4 sequence checksum mismatch")

    weight_paths = verify_model_artifacts(config, model_metadata)
    frame = pd.read_parquet(
        SOURCE_PATH,
        filters=[("selection_year", "==", TEST_SELECTION_YEAR)],
    ).sort_values("sample_id", kind="stable").reset_index(drop=True)
    if len(frame) != EXPECTED_TEST_SAMPLES or not frame["sample_id"].is_unique:
        raise ValueError("Unexpected Test cohort contract")
    if not frame["target_year"].eq(TEST_TARGET_YEAR).all():
        raise ValueError("Test target year must be 2019")
    if not set(frame["retention_state"].unique()).issubset(set(model_base.CLASS_CODES)):
        raise ValueError("Unexpected Test class label")

    lifecycle = pd.read_parquet(TEST_LIFECYCLE_PATH).sort_values(
        "sample_id", kind="stable"
    )
    if lifecycle["sample_id"].tolist() != frame["sample_id"].tolist():
        raise ValueError("Test Lifecycle sample order changed")
    lifecycle_values = lifecycle[config["lifecycle_features"]].to_numpy(dtype=np.float32)

    sequence = pd.read_parquet(TEST_SEQUENCE_PATH)
    if len(sequence) != len(frame) * int(config["sequence_length"]):
        raise ValueError("Expected 24 Core4 months per Test sample")
    if sequence["sample_id"].drop_duplicates().tolist() != frame["sample_id"].tolist():
        raise ValueError("Test Core4 sample order changed")
    month_matrix = sequence["month_index"].to_numpy().reshape(-1, 24)
    if not np.array_equal(month_matrix, np.tile(np.arange(24), (len(frame), 1))):
        raise ValueError("Test Core4 month order changed")
    sequence_values = sequence[config["sequence_channels"]].to_numpy(dtype=np.float32)
    sequence_values = sequence_values.reshape(len(frame), 24, 4)

    preprocessing = joblib.load(PREPROCESSING_PATH)
    log_channels = preprocessing.get("sequence_log1p_channels")
    if log_channels != [0, 2, 3]:
        raise ValueError("Saved sequence transform contract changed")
    for channel in log_channels:
        sequence_values[:, :, channel] = np.log1p(sequence_values[:, :, channel])
    sequence_values = preprocessing["sequence_scaler"].transform(
        sequence_values.reshape(-1, 4)
    ).reshape(sequence_values.shape).astype(np.float32)
    lifecycle_values = preprocessing["lifecycle_scaler"].transform(
        lifecycle_values
    ).astype(np.float32)
    if not np.isfinite(sequence_values).all() or not np.isfinite(lifecycle_values).all():
        raise ValueError("Invalid scaled Test feature value")
    return frame, sequence_values, lifecycle_values, config, model_metadata, weight_paths


def create_top_k(frame: pd.DataFrame) -> pd.DataFrame:
    labels = frame["retention_state"].to_numpy()
    risk_scores = frame["risk_score"].to_numpy()
    order = np.argsort(-risk_scores, kind="stable")
    at_risk = labels != 0
    rows = []
    requests = [
        ("k_500", 500),
        ("k_1000", 1_000),
        ("top_20_percent", int(math.ceil(len(frame) * PRIMARY_TARGET_RATE))),
        ("k_2000", 2_000),
    ]
    for name, requested_k in requests:
        actual_k = min(requested_k, len(frame))
        selected = order[:actual_k]
        precision = float(at_risk[selected].mean())
        rows.append(
            {
                "split": "test",
                "selection_year": TEST_SELECTION_YEAR,
                "target_year": TEST_TARGET_YEAR,
                "ranking": "risk_score",
                "target_name": name,
                "requested_k": requested_k,
                "actual_k": actual_k,
                "precision_at_k": precision,
                "recall_at_k": float(at_risk[selected].sum() / at_risk.sum()),
                "lift_at_k": float(precision / at_risk.mean()),
                "weakened_selected": int((labels[selected] == 1).sum()),
                "stopped_selected": int((labels[selected] == 2).sum()),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    check_outputs(args.overwrite)
    torch.set_num_threads(min(4, max(1, torch.get_num_threads())))
    device = torch.device("cpu")
    frame, sequence, lifecycle, config, model_metadata, weight_paths = load_test_inputs()
    thresholds = model_metadata["selected_thresholds"]
    risk_threshold = float(thresholds["risk_score"])
    stopped_threshold = float(thresholds["conditional_stopped_score"])
    print(
        f"version={VERSION}, Test rows={len(frame):,}, "
        f"thresholds=({risk_threshold:.2f}, {stopped_threshold:.2f})",
        flush=True,
    )

    seed_scores = []
    seed_risk = []
    seed_stopped = []
    for seed, path in zip(config["seeds"], weight_paths):
        print(f"Test prediction seed {seed}", flush=True)
        model = model_base.make_model(config["model"], device)
        model.load_state_dict(torch.load(path, map_location=device, weights_only=True))
        scores, risk, stopped = model_base.predict_scores(model, sequence, lifecycle, device)
        seed_scores.append(scores)
        seed_risk.append(risk)
        seed_stopped.append(stopped)

    scores = np.mean(seed_scores, axis=0)
    risk = np.mean(seed_risk, axis=0)
    stopped = np.mean(seed_stopped, axis=0)
    if not np.allclose(scores.sum(axis=1), 1.0, rtol=0, atol=1e-6):
        raise ValueError("Test class scores no longer sum to one")
    if not np.allclose(scores[:, 1] + scores[:, 2], risk, rtol=0, atol=1e-6):
        raise ValueError("Test risk score differs from class score sum")

    predictions = model_base.h2_predictions(
        risk,
        stopped,
        risk_threshold,
        stopped_threshold,
    )
    labels = frame["retention_state"].to_numpy(dtype=np.int64)
    metrics = model_base.evaluate(labels, predictions, scores)

    prediction_table = frame[
        ["sample_id", "user_id", "comparison_year", "selection_year", "target_year", "retention_state"]
    ].copy()
    prediction_table[model_base.SCORE_COLUMNS] = scores
    prediction_table["risk_score"] = risk
    prediction_table["conditional_stopped_score"] = stopped
    prediction_table["predicted_state"] = predictions
    prediction_table["predicted_state_label"] = prediction_table["predicted_state"].map(
        CLASS_LABELS_KO
    )
    prediction_table["retention_state_label"] = prediction_table["retention_state"].map(
        CLASS_LABELS_KO
    )

    matrix = confusion_matrix(labels, predictions, labels=model_base.CLASS_CODES)
    confusion = pd.DataFrame(
        matrix,
        index=[f"actual_{name}" for name in model_base.CLASS_NAMES],
        columns=[f"predicted_{name}" for name in model_base.CLASS_NAMES],
    )
    confusion.index.name = "actual_state"
    top_k = create_top_k(prediction_table)

    profile = frame.copy()
    profile[model_base.SCORE_COLUMNS] = scores
    profile["risk_score"] = risk
    profile["conditional_stopped_score"] = stopped
    profile["priority_score"] = risk
    profile["predicted_state"] = predictions
    profile["predicted_state_label"] = profile["predicted_state"].map(CLASS_LABELS_KO)
    profile["retention_state_label"] = profile["retention_state"].map(CLASS_LABELS_KO)
    profile["priority_rank"] = profile["priority_score"].rank(
        method="first", ascending=False
    ).astype(int)
    profile["priority_top_percent"] = profile["priority_rank"] / len(profile) * 100
    target_users = int(math.ceil(len(profile) * PRIMARY_TARGET_RATE))
    profile["selected_for_crm"] = profile["priority_rank"].le(target_users).astype("int8")
    profile = profile.sort_values(["priority_rank", "sample_id"], kind="stable").reset_index(
        drop=True
    )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    PREDICTION_DIR.mkdir(parents=True, exist_ok=True)
    feature_base.atomic_parquet(prediction_table, TEST_PREDICTIONS_PATH)
    feature_base.atomic_parquet(profile, TEST_PROFILE_PATH)
    pd.DataFrame([{"record_type": "test", "split": "selection_2018_target_2019", **metrics}]).to_csv(
        TEST_METRICS_TABLE_PATH, index=False, encoding="utf-8-sig"
    )
    confusion.to_csv(TEST_CONFUSION_PATH, encoding="utf-8-sig")
    top_k.to_csv(TEST_TOP_K_PATH, index=False, encoding="utf-8-sig")

    oof_metrics = model_metadata["oof_metrics"]
    test_metadata = {
        "version": VERSION,
        "status": "test_evaluation_complete",
        "evaluation_policy": "frozen 2010-2017 model, fixed OOF thresholds, no Test tuning",
        "comparison_year": TEST_SELECTION_YEAR - 1,
        "selection_year": TEST_SELECTION_YEAR,
        "target_year": TEST_TARGET_YEAR,
        "test_samples": len(frame),
        "thresholds": {
            "risk_score": risk_threshold,
            "conditional_stopped_score": stopped_threshold,
        },
        "test_metrics": metrics,
        "oof_reference_metrics": oof_metrics,
        "test_minus_oof": {
            "macro_f1": metrics["macro_f1"] - float(oof_metrics["macro_f1"]),
            "macro_pr_auc": metrics["macro_pr_auc"] - float(oof_metrics["macro_pr_auc"]),
            "weakened_recall": metrics["weakened_recall"] - float(oof_metrics["weakened_recall"]),
            "stopped_recall": metrics["stopped_recall"] - float(oof_metrics["stopped_recall"]),
        },
        "model_artifacts": {
            "preprocessing_sha256": feature_base.sha256(PREPROCESSING_PATH),
            "weight_sha256": {
                str(seed): feature_base.sha256(path)
                for seed, path in zip(config["seeds"], weight_paths)
            },
        },
        "outputs": {
            "test_predictions_path": str(TEST_PREDICTIONS_PATH),
            "test_predictions_sha256": feature_base.sha256(TEST_PREDICTIONS_PATH),
            "test_profile_path": str(TEST_PROFILE_PATH),
            "test_profile_sha256": feature_base.sha256(TEST_PROFILE_PATH),
            "test_confusion_path": str(TEST_CONFUSION_PATH),
            "test_top_k_path": str(TEST_TOP_K_PATH),
        },
        "runtime": {
            "device": str(device),
            "python_version": sys.version.split()[0],
            "torch_version": torch.__version__,
            "sklearn_version": sklearn.__version__,
            "pandas_version": pd.__version__,
            "elapsed_seconds": time.perf_counter() - started,
        },
    }
    TEST_METRICS_PATH.write_text(
        json.dumps(test_metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    top_1000 = top_k.loc[top_k["target_name"].eq("k_1000")].iloc[0]
    top_20 = top_k.loc[top_k["target_name"].eq("top_20_percent")].iloc[0]
    report = f"""# v05_05 Lifecycle Fusion H2 — Test result

- Test structure: comparison 2017 → selection/feature cutoff 2018 → target 2019
- Test samples: {len(frame):,}
- Training range: selection years 2010–2017
- Fixed thresholds: risk {risk_threshold:.2f}, conditional stopped {stopped_threshold:.2f}
- Test Macro F1: {metrics['macro_f1']:.4f}
- Test Macro PR-AUC: {metrics['macro_pr_auc']:.4f}
- Test balanced accuracy: {metrics['balanced_accuracy']:.4f}
- Test weakened Recall: {metrics['weakened_recall']:.2%}
- Test stopped Recall: {metrics['stopped_recall']:.2%}
- Test retained→stopped: {metrics['retained_to_stopped_count']:,} ({metrics['retained_to_stopped_rate']:.2%})
- Test stopped→retained: {metrics['stopped_to_retained_count']:,} ({metrics['stopped_to_retained_rate']:.2%})
- Test severe error rate: {metrics['severe_error_rate']:.2%}
- Test Precision@1000: {float(top_1000['precision_at_k']):.2%}
- Test top 20% Precision/Recall/Lift: {float(top_20['precision_at_k']):.2%} / {float(top_20['recall_at_k']):.2%} / {float(top_20['lift_at_k']):.2f}x

The model weights and thresholds were fixed before this Test evaluation.
Class and risk scores are ranking/model scores, not calibrated probabilities.
"""
    TEST_PERFORMANCE_PATH.write_text(report, encoding="utf-8")
    print(
        f"Test Macro F1={metrics['macro_f1']:.4f}, "
        f"PR-AUC={metrics['macro_pr_auc']:.4f}, "
        f"weakened Recall={metrics['weakened_recall']:.2%}, "
        f"stopped Recall={metrics['stopped_recall']:.2%}, "
        f"elapsed={time.perf_counter() - started:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
