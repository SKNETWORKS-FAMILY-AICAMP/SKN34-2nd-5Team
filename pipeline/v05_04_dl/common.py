"""Shared contracts and OOF helpers for the v05_04 DL stages."""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

# PyTorch must initialize its bundled Windows runtime before NumPy/sklearn.
import torch
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.v05_01_dl import train as base
from pipeline.v05_03_dl import train as hybrid


CONFIG_PATH = Path(__file__).with_name("config.json")
DATA_PATH = (
    ROOT
    / "data"
    / "processed"
    / "experiments"
    / "modeling_dataset_v05_2_dl_features_v05_04.parquet"
)
FEATURE_SETS_PATH = (
    ROOT
    / "reports"
    / "experiments"
    / "v05_04_dl_features"
    / "feature_sets.json"
)
FEATURE_BUILD_METADATA_PATH = (
    ROOT
    / "reports"
    / "experiments"
    / "v05_04_dl_features"
    / "feature_build_metadata.json"
)
SEQUENCE_PATH = (
    ROOT
    / "data"
    / "processed"
    / "experiments"
    / "monthly_sequence_v04_v05_03_dl.parquet"
)
SEQUENCE_METADATA_PATH = (
    ROOT
    / "reports"
    / "experiments"
    / "v05_03_dl"
    / "sequence_build_metadata.json"
)
MODEL_ROOT = ROOT / "models" / "experiments"
REPORT_ROOT = ROOT / "reports" / "experiments"
PROFILE_ROOT = ROOT / "data" / "processed" / "experiments"

SCORE_COLUMNS = ["retained_score", "weakened_score", "stopped_score"]
META_COLUMNS = ["sample_id", "selection_year", "retention_state"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(to_builtin(value), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def to_builtin(value):
    if isinstance(value, dict):
        return {str(key): to_builtin(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_builtin(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    return value


def candidate_from_dict(value: dict) -> base.CandidateConfig:
    return base.CandidateConfig(
        name=str(value["name"]),
        hidden_dims=tuple(int(item) for item in value["hidden_dims"]),
        dropout=float(value["dropout"]),
        learning_rate=float(value["learning_rate"]),
        weight_decay=float(value["weight_decay"]),
        epochs=int(value["epochs"]),
        batch_size=int(value["batch_size"]),
        class_weighted_loss=bool(value["class_weighted_loss"]),
    )


def candidate_to_dict(config: base.CandidateConfig) -> dict:
    return asdict(config)


def load_static_contract() -> tuple[pd.DataFrame, dict[str, list[str]], dict, dict]:
    required = [
        CONFIG_PATH,
        DATA_PATH,
        FEATURE_SETS_PATH,
        FEATURE_BUILD_METADATA_PATH,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing v05_04 inputs:\n- " + "\n- ".join(missing))
    config = load_json(CONFIG_PATH)
    feature_contract = load_json(FEATURE_SETS_PATH)
    build_metadata = load_json(FEATURE_BUILD_METADATA_PATH)
    if build_metadata["output_sha256"] != sha256(DATA_PATH):
        raise ValueError("v05_04 feature dataset checksum mismatch")
    frame = pd.read_parquet(DATA_PATH)
    if len(frame) != 37_953 or len(frame.columns) != 73:
        raise ValueError("Expected the validated 37,953 x 73 v05_04 dataset")
    if not frame["sample_id"].is_unique:
        raise ValueError("sample_id must be unique")
    final_test = frame.loc[frame["selection_year"].eq(2018)]
    if len(final_test) != 6_533 or not final_test["target_year"].eq(2019).all():
        raise ValueError("Final test time contract changed")
    if final_test["retention_state"].value_counts().to_dict() != {
        1: 3_065,
        0: 2_584,
        2: 884,
    }:
        raise ValueError("Final test class distribution changed")
    forbidden = set(build_metadata["metadata_columns"])
    feature_sets = {
        name: list(columns)
        for name, columns in feature_contract["feature_sets"].items()
    }
    for name, columns in feature_sets.items():
        if len(columns) != len(set(columns)):
            raise ValueError(f"Duplicate feature in {name}")
        if set(columns) - set(frame.columns):
            raise ValueError(f"Missing feature in {name}")
        if forbidden & set(columns):
            raise ValueError(f"Forbidden metadata found in {name}")
        values = frame[columns].to_numpy(dtype=float)
        if np.isinf(values).any():
            raise ValueError(f"Infinite feature found in {name}")
    return frame, feature_sets, config, build_metadata


def load_raw_sequence(frame: pd.DataFrame, channels: list[str]) -> np.ndarray:
    required = [SEQUENCE_PATH, SEQUENCE_METADATA_PATH]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing sequence inputs:\n- " + "\n- ".join(missing))
    metadata = load_json(SEQUENCE_METADATA_PATH)
    if metadata["output_sha256"] != sha256(SEQUENCE_PATH):
        raise ValueError("Monthly sequence checksum mismatch")
    sequence = pd.read_parquet(SEQUENCE_PATH)
    if len(sequence) != len(frame) * 24:
        raise ValueError("Expected 24 monthly rows per sample")
    if sequence["sample_id"].drop_duplicates().tolist() != frame["sample_id"].tolist():
        raise ValueError("Sequence sample order changed")
    month_matrix = sequence["month_index"].to_numpy().reshape(-1, 24)
    if not np.array_equal(month_matrix, np.tile(np.arange(24), (len(frame), 1))):
        raise ValueError("Sequence month order changed")
    raw = sequence[channels].to_numpy(dtype=np.float32).reshape(len(frame), 24, -1)
    raw[:, :, :2] = np.log1p(raw[:, :, :2])
    if np.isnan(raw).any() or np.isinf(raw).any():
        raise ValueError("Invalid monthly sequence value")
    return raw


def oof_metrics(
    oof: pd.DataFrame,
    weakened_threshold: float,
    stopped_threshold: float,
) -> dict:
    ensemble = oof.loc[oof["record_type"].eq("ensemble")]
    scores = ensemble[SCORE_COLUMNS].to_numpy()
    labels = ensemble["retention_state"].to_numpy()
    predictions = base.threshold_predictions(
        scores,
        weakened_threshold,
        stopped_threshold,
    )
    return base.evaluate(labels, predictions, scores)


def selected_threshold_row(
    config: base.CandidateConfig,
    oof: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    rows = pd.DataFrame(base.candidate_records(config, oof)).sort_values(
        [
            "oof_macro_f1",
            "oof_macro_pr_auc",
            "oof_balanced_accuracy",
            "oof_stopped_recall",
            "oof_weakened_recall",
            "seed_macro_f1_std",
        ],
        ascending=[False, False, False, False, False, True],
        kind="stable",
    ).reset_index(drop=True)
    rows.insert(0, "selection_rank", np.arange(1, len(rows) + 1))
    rows["selected"] = rows["selection_rank"].eq(1)
    return rows, rows.iloc[0]


def summary_from_selected(
    stage: str,
    model_family: str,
    feature_set: str,
    config: base.CandidateConfig | dict,
    selected: pd.Series,
) -> dict:
    config_value = candidate_to_dict(config) if isinstance(config, base.CandidateConfig) else config
    result = {
        "stage": stage,
        "model_family": model_family,
        "feature_set": feature_set,
        "feature_count": int(selected["feature_count"]),
        "candidate_name": config_value.get("name", model_family),
        "config_json": json.dumps(config_value, ensure_ascii=False, sort_keys=True),
        "weakened_threshold": float(selected["weakened_threshold"]),
        "stopped_threshold": float(selected["stopped_threshold"]),
    }
    for column in selected.index:
        if column.startswith("oof_") or column.startswith("seed_"):
            result[column] = selected[column]
    return to_builtin(result)


def sort_summary(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(
        [
            "oof_macro_f1",
            "oof_macro_pr_auc",
            "oof_balanced_accuracy",
            "oof_stopped_recall",
            "oof_weakened_recall",
            "seed_macro_f1_std",
        ],
        ascending=[False, False, False, False, False, True],
        kind="stable",
    ).reset_index(drop=True)


def configure_runtime() -> torch.device:
    torch.set_num_threads(min(4, max(1, torch.get_num_threads())))
    return torch.device("cpu")
