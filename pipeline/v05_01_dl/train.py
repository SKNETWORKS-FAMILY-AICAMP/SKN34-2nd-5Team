"""Train a PyTorch MLP challenger on the approved annual v04 data contract.

Protected inputs:
    data/processed/modeling_dataset_rolling_v04.parquet
    models/final_core_hgb_metadata_v02.json
    models/final_core_logistic_multiclass_metadata_v04.json

This experiment never overwrites approved v04 artifacts. Candidate selection
uses only expanding-time OOF predictions for selection years 2013-2017.
The final test is selection 2018 -> target 2019 and is evaluated once after
the architecture, loss weighting, and thresholds are fixed.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

# Import PyTorch before NumPy/scikit-learn on Windows so its bundled runtime
# initializes first and does not collide with an already-loaded OpenMP DLL.
import torch
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, label_binarize
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_VERSION = "v05_01_dl"

DATA_PATH = ROOT / "data" / "processed" / "modeling_dataset_rolling_v04.parquet"
V02_METADATA_PATH = ROOT / "models" / "final_core_hgb_metadata_v02.json"
V04_METADATA_PATH = (
    ROOT / "models" / "final_core_logistic_multiclass_metadata_v04.json"
)
V04_MODEL_PATH = ROOT / "models" / "final_core_logistic_multiclass_v04.joblib"

MODEL_DIR = ROOT / "models" / "experiments" / EXPERIMENT_VERSION
REPORT_DIR = ROOT / "reports" / "experiments" / EXPERIMENT_VERSION
PROFILE_PATH = (
    ROOT
    / "data"
    / "processed"
    / "experiments"
    / "final_test_retention_profiles_v05_01_dl.parquet"
)

SEEDS = [42, 2026, 3405]
CLASS_CODES = [0, 1, 2]
CLASS_NAMES = ["retained", "weakened", "stopped"]
CLASS_LABELS_KO = {0: "파워 지위 유지", 1: "파워 지위 약화", 2: "리뷰 활동 중단"}
TIME_FOLDS = [
    (2012, 2013),
    (2013, 2014),
    (2014, 2015),
    (2015, 2016),
    (2016, 2017),
]
WEAKENED_THRESHOLDS = [0.30, 0.36, 0.42]
STOPPED_THRESHOLDS = [0.35, 0.45, 0.55]
PRIMARY_TARGET_RATE = 0.20
TOP_K_RATES = [0.10, 0.20, 0.30]


@dataclass(frozen=True)
class CandidateConfig:
    name: str
    hidden_dims: tuple[int, ...]
    dropout: float
    learning_rate: float
    weight_decay: float
    epochs: int
    batch_size: int
    class_weighted_loss: bool


CANDIDATES = [
    CandidateConfig(
        name="mlp_small_weighted",
        hidden_dims=(64, 32),
        dropout=0.10,
        learning_rate=1e-3,
        weight_decay=1e-4,
        epochs=40,
        batch_size=512,
        class_weighted_loss=True,
    ),
    CandidateConfig(
        name="mlp_medium_weighted",
        hidden_dims=(128, 64, 32),
        dropout=0.20,
        learning_rate=7e-4,
        weight_decay=5e-4,
        epochs=50,
        batch_size=512,
        class_weighted_loss=True,
    ),
    CandidateConfig(
        name="mlp_medium_unweighted",
        hidden_dims=(128, 64, 32),
        dropout=0.20,
        learning_rate=7e-4,
        weight_decay=5e-4,
        epochs=50,
        batch_size=512,
        class_weighted_loss=False,
    ),
]


class TabularMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dims: tuple[int, ...],
        dropout: float,
    ) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        previous_dim = input_dim
        for hidden_dim in hidden_dims:
            layers.extend(
                [
                    nn.Linear(previous_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.GELU(),
                    nn.Dropout(dropout),
                ]
            )
            previous_dim = hidden_dim
        layers.append(nn.Linear(previous_dim, len(CLASS_CODES)))
        self.network = nn.Sequential(*layers)

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.network(features)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def build_preprocessor() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
        ]
    )


def inverse_frequency_weights(labels: np.ndarray) -> torch.Tensor:
    counts = np.bincount(labels, minlength=len(CLASS_CODES)).astype(float)
    weights = len(labels) / (len(CLASS_CODES) * counts)
    return torch.tensor(weights, dtype=torch.float32)


def train_model(
    x_train: np.ndarray,
    y_train: np.ndarray,
    config: CandidateConfig,
    seed: int,
    device: torch.device,
) -> TabularMLP:
    set_seed(seed)
    model = TabularMLP(
        input_dim=x_train.shape[1],
        hidden_dims=config.hidden_dims,
        dropout=config.dropout,
    ).to(device)
    train_dataset = TensorDataset(
        torch.from_numpy(x_train.astype(np.float32, copy=False)),
        torch.from_numpy(y_train.astype(np.int64, copy=False)),
    )
    generator = torch.Generator()
    generator.manual_seed(seed)
    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        generator=generator,
        num_workers=0,
        drop_last=False,
    )
    class_weights = (
        inverse_frequency_weights(y_train).to(device)
        if config.class_weighted_loss
        else None
    )
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    model.train()
    for _ in range(config.epochs):
        for batch_features, batch_labels in train_loader:
            batch_features = batch_features.to(device)
            batch_labels = batch_labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(batch_features)
            loss = criterion(logits, batch_labels)
            loss.backward()
            optimizer.step()
    return model


@torch.inference_mode()
def predict_scores(
    model: TabularMLP,
    features: np.ndarray,
    device: torch.device,
    batch_size: int = 2_048,
) -> np.ndarray:
    model.eval()
    dataset = TensorDataset(
        torch.from_numpy(features.astype(np.float32, copy=False))
    )
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
    )
    score_parts = []
    for (batch_features,) in loader:
        logits = model(batch_features.to(device))
        score_parts.append(torch.softmax(logits, dim=1).cpu().numpy())
    return np.concatenate(score_parts, axis=0)


def threshold_predictions(
    scores: np.ndarray,
    weakened_threshold: float,
    stopped_threshold: float,
) -> np.ndarray:
    predictions = np.zeros(len(scores), dtype="int8")
    predictions[scores[:, 1] >= weakened_threshold] = 1
    predictions[scores[:, 2] >= stopped_threshold] = 2
    return predictions


def evaluate(
    y_true: np.ndarray,
    predictions: np.ndarray,
    scores: np.ndarray,
) -> dict[str, float | int]:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        predictions,
        labels=CLASS_CODES,
        zero_division=0,
    )
    y_binary = label_binarize(y_true, classes=CLASS_CODES)
    result: dict[str, float | int] = {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, predictions)),
        "macro_precision": float(precision.mean()),
        "macro_recall": float(recall.mean()),
        "macro_f1": float(f1_score(y_true, predictions, average="macro")),
        "weighted_f1": float(f1_score(y_true, predictions, average="weighted")),
        "macro_pr_auc": float(
            np.mean(
                [
                    average_precision_score(y_binary[:, index], scores[:, index])
                    for index in CLASS_CODES
                ]
            )
        ),
        "macro_ovr_roc_auc": float(
            roc_auc_score(
                y_true,
                scores,
                multi_class="ovr",
                average="macro",
            )
        ),
    }
    for index, class_name in enumerate(CLASS_NAMES):
        result[f"{class_name}_precision"] = float(precision[index])
        result[f"{class_name}_recall"] = float(recall[index])
        result[f"{class_name}_f1"] = float(f1[index])
        result[f"{class_name}_support"] = int(support[index])
        result[f"{class_name}_pr_auc"] = float(
            average_precision_score(y_binary[:, index], scores[:, index])
        )
    return result


def top_k_records(
    split: str,
    y_true: np.ndarray,
    scores: np.ndarray,
) -> list[dict]:
    status_loss = y_true != 0
    stopped = y_true == 2
    weakened = y_true == 1
    ranking_score = scores[:, 1] + scores[:, 2]
    order = np.argsort(-ranking_score, kind="stable")
    records = []
    for rate in TOP_K_RATES:
        users = int(np.ceil(len(y_true) * rate))
        selected = order[:users]
        captured_status = int(status_loss[selected].sum())
        captured_stopped = int(stopped[selected].sum())
        captured_weakened = int(weakened[selected].sum())
        precision = captured_status / users
        records.append(
            {
                "split": split,
                "target_rate": rate,
                "target_users": users,
                "status_loss_captured": captured_status,
                "status_loss_precision": precision,
                "status_loss_recall": captured_status / status_loss.sum(),
                "status_loss_lift": precision / status_loss.mean(),
                "stopped_captured": captured_stopped,
                "stopped_recall": captured_stopped / stopped.sum(),
                "weakened_captured": captured_weakened,
                "weakened_recall": captured_weakened / weakened.sum(),
            }
        )
    return records


def validate_contract(
    frame: pd.DataFrame,
    feature_columns: list[str],
    v04_metadata: dict,
) -> None:
    if len(frame) != 37_953:
        raise ValueError(f"expected 37,953 rows, found {len(frame):,}")
    if len(feature_columns) != 43:
        raise ValueError(f"expected 43 features, found {len(feature_columns)}")
    if set(feature_columns) - set(frame.columns):
        raise ValueError("Core feature columns are missing")
    if not frame["sample_id"].is_unique:
        raise ValueError("sample_id must be unique")
    forbidden = {
        "target_review_count",
        "target_active_months",
        "retention_state",
        "churn",
    }
    if forbidden & set(feature_columns):
        raise ValueError("target-derived columns found in features")
    if np.isinf(frame[feature_columns].to_numpy(dtype=float)).any():
        raise ValueError("infinite Core feature value")

    final_train = frame.loc[frame["selection_year"].between(2010, 2017)]
    final_test = frame.loc[frame["selection_year"].eq(2018)]
    if len(final_train) != 31_420:
        raise ValueError(f"expected 31,420 train rows, found {len(final_train):,}")
    if len(final_test) != 6_533:
        raise ValueError(f"expected 6,533 test rows, found {len(final_test):,}")
    if not final_test["target_year"].eq(2019).all():
        raise ValueError("final test target year must be 2019")
    if final_test["retention_state"].value_counts().to_dict() != {
        1: 3_065,
        0: 2_584,
        2: 884,
    }:
        raise ValueError("final test class distribution changed")
    if v04_metadata["feature_columns"] != feature_columns:
        raise ValueError("feature order differs from approved v04 metadata")
    actual_checksum = hashlib.sha256(V04_MODEL_PATH.read_bytes()).hexdigest()
    if actual_checksum != v04_metadata["model_sha256"]:
        raise ValueError("approved v04 model checksum changed")


def run_candidate_oof(
    frame: pd.DataFrame,
    feature_columns: list[str],
    config: CandidateConfig,
    device: torch.device,
) -> pd.DataFrame:
    parts = []
    total_runs = len(TIME_FOLDS) * len(SEEDS)
    run_number = 0
    for train_end, validation_year in TIME_FOLDS:
        train = frame.loc[frame["selection_year"].between(2010, train_end)]
        validation = frame.loc[frame["selection_year"].eq(validation_year)]
        preprocessor = build_preprocessor()
        x_train = preprocessor.fit_transform(train[feature_columns]).astype(
            np.float32,
            copy=False,
        )
        x_validation = preprocessor.transform(validation[feature_columns]).astype(
            np.float32,
            copy=False,
        )
        y_train = train["retention_state"].to_numpy(dtype=np.int64)
        fold_scores = []
        for seed in SEEDS:
            run_number += 1
            print(
                f"{config.name}: run {run_number}/{total_runs}, "
                f"train 2010-{train_end}, validation {validation_year}, seed {seed}",
                flush=True,
            )
            model = train_model(
                x_train,
                y_train,
                config,
                seed,
                device,
            )
            scores = predict_scores(model, x_validation, device)
            fold_scores.append(scores)
            seed_part = validation[
                ["sample_id", "selection_year", "retention_state"]
            ].copy()
            seed_part["seed"] = seed
            seed_part[["retained_score", "weakened_score", "stopped_score"]] = scores
            seed_part["record_type"] = "seed"
            parts.append(seed_part)

        ensemble_scores = np.mean(fold_scores, axis=0)
        ensemble_part = validation[
            ["sample_id", "selection_year", "retention_state"]
        ].copy()
        ensemble_part["seed"] = -1
        ensemble_part[
            ["retained_score", "weakened_score", "stopped_score"]
        ] = ensemble_scores
        ensemble_part["record_type"] = "ensemble"
        parts.append(ensemble_part)
    return pd.concat(parts, ignore_index=True)


def candidate_records(
    config: CandidateConfig,
    oof: pd.DataFrame,
) -> list[dict]:
    ensemble = oof.loc[oof["record_type"].eq("ensemble")].copy()
    ensemble_scores = ensemble[
        ["retained_score", "weakened_score", "stopped_score"]
    ].to_numpy()
    ensemble_y = ensemble["retention_state"].to_numpy()
    records = []
    for weakened_threshold, stopped_threshold in itertools.product(
        WEAKENED_THRESHOLDS,
        STOPPED_THRESHOLDS,
    ):
        predictions = threshold_predictions(
            ensemble_scores,
            weakened_threshold,
            stopped_threshold,
        )
        metrics = evaluate(ensemble_y, predictions, ensemble_scores)
        seed_f1 = []
        seed_pr_auc = []
        for seed in SEEDS:
            seed_frame = oof.loc[
                oof["record_type"].eq("seed") & oof["seed"].eq(seed)
            ]
            seed_scores = seed_frame[
                ["retained_score", "weakened_score", "stopped_score"]
            ].to_numpy()
            seed_y = seed_frame["retention_state"].to_numpy()
            seed_predictions = threshold_predictions(
                seed_scores,
                weakened_threshold,
                stopped_threshold,
            )
            seed_metrics = evaluate(seed_y, seed_predictions, seed_scores)
            seed_f1.append(seed_metrics["macro_f1"])
            seed_pr_auc.append(seed_metrics["macro_pr_auc"])
        records.append(
            {
                "candidate_name": config.name,
                "hidden_dims": "x".join(map(str, config.hidden_dims)),
                "dropout": config.dropout,
                "learning_rate": config.learning_rate,
                "weight_decay": config.weight_decay,
                "epochs": config.epochs,
                "batch_size": config.batch_size,
                "class_weighted_loss": config.class_weighted_loss,
                "weakened_threshold": weakened_threshold,
                "stopped_threshold": stopped_threshold,
                "validation_samples": len(ensemble),
                "seed_macro_f1_mean": float(np.mean(seed_f1)),
                "seed_macro_f1_std": float(np.std(seed_f1, ddof=1)),
                "seed_macro_pr_auc_mean": float(np.mean(seed_pr_auc)),
                "seed_macro_pr_auc_std": float(np.std(seed_pr_auc, ddof=1)),
                **{f"oof_{key}": value for key, value in metrics.items()},
            }
        )
    return records


def save_and_reload_model(
    model: TabularMLP,
    path: Path,
    config: CandidateConfig,
    input_dim: int,
    verification_features: np.ndarray,
    device: torch.device,
) -> tuple[str, np.ndarray]:
    state = {
        key: value.detach().cpu()
        for key, value in model.state_dict().items()
    }
    torch.save(state, path)
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    reloaded = TabularMLP(
        input_dim=input_dim,
        hidden_dims=config.hidden_dims,
        dropout=config.dropout,
    ).to(device)
    reloaded.load_state_dict(
        torch.load(path, map_location=device, weights_only=True)
    )
    reloaded_scores = predict_scores(reloaded, verification_features, device)
    return checksum, reloaded_scores


def main() -> None:
    start_time = time.perf_counter()
    for directory in [MODEL_DIR, REPORT_DIR, PROFILE_PATH.parent]:
        directory.mkdir(parents=True, exist_ok=True)

    torch.set_num_threads(min(4, max(1, torch.get_num_threads())))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(
        f"device={device}, torch={torch.__version__}, "
        f"threads={torch.get_num_threads()}",
        flush=True,
    )

    v02_metadata = json.loads(V02_METADATA_PATH.read_text(encoding="utf-8"))
    v04_metadata = json.loads(V04_METADATA_PATH.read_text(encoding="utf-8"))
    feature_columns = v02_metadata["feature_columns"]
    frame = pd.read_parquet(DATA_PATH)
    validate_contract(frame, feature_columns, v04_metadata)
    print("v04 data contract validated", flush=True)

    all_oof: dict[str, pd.DataFrame] = {}
    all_candidate_records = []
    for config in CANDIDATES:
        oof = run_candidate_oof(
            frame,
            feature_columns,
            config,
            device,
        )
        all_oof[config.name] = oof
        all_candidate_records.extend(candidate_records(config, oof))

    candidates = pd.DataFrame(all_candidate_records).sort_values(
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
    candidates.insert(0, "selection_rank", np.arange(1, len(candidates) + 1))
    candidates["selected"] = candidates["selection_rank"].eq(1)
    candidates.to_csv(
        REPORT_DIR / "dl_core43_candidates.csv",
        index=False,
        encoding="utf-8-sig",
    )

    selected = candidates.iloc[0]
    selected_config = next(
        config
        for config in CANDIDATES
        if config.name == selected["candidate_name"]
    )
    weakened_threshold = float(selected["weakened_threshold"])
    stopped_threshold = float(selected["stopped_threshold"])
    selected_oof = all_oof[selected_config.name]
    selected_oof.to_parquet(
        REPORT_DIR / "selected_oof_predictions.parquet",
        index=False,
    )

    ensemble_oof = selected_oof.loc[
        selected_oof["record_type"].eq("ensemble")
    ].copy()
    oof_scores = ensemble_oof[
        ["retained_score", "weakened_score", "stopped_score"]
    ].to_numpy()
    oof_y = ensemble_oof["retention_state"].to_numpy()
    oof_predictions = threshold_predictions(
        oof_scores,
        weakened_threshold,
        stopped_threshold,
    )
    oof_metrics = evaluate(oof_y, oof_predictions, oof_scores)

    final_train = frame.loc[frame["selection_year"].between(2010, 2017)].copy()
    final_test = frame.loc[frame["selection_year"].eq(2018)].copy()
    preprocessor = build_preprocessor()
    x_train = preprocessor.fit_transform(final_train[feature_columns]).astype(
        np.float32,
        copy=False,
    )
    x_test = preprocessor.transform(final_test[feature_columns]).astype(
        np.float32,
        copy=False,
    )
    y_train = final_train["retention_state"].to_numpy(dtype=np.int64)
    y_test = final_test["retention_state"].to_numpy(dtype=np.int64)

    preprocessor_path = MODEL_DIR / "preprocessor.joblib"
    joblib.dump(preprocessor, preprocessor_path)
    preprocessor_checksum = hashlib.sha256(
        preprocessor_path.read_bytes()
    ).hexdigest()

    final_seed_scores = []
    weight_checksums = {}
    seed_test_metrics = {}
    for seed in SEEDS:
        print(f"final training seed {seed}", flush=True)
        model = train_model(
            x_train,
            y_train,
            selected_config,
            seed,
            device,
        )
        scores = predict_scores(model, x_test, device)
        weights_path = MODEL_DIR / f"seed_{seed}_state_dict.pt"
        checksum, reloaded_scores = save_and_reload_model(
            model,
            weights_path,
            selected_config,
            x_train.shape[1],
            x_test,
            device,
        )
        if not np.allclose(scores, reloaded_scores, rtol=0, atol=1e-7):
            raise ValueError(f"reloaded model scores changed for seed {seed}")
        weight_checksums[str(seed)] = checksum
        final_seed_scores.append(scores)
        seed_predictions = threshold_predictions(
            scores,
            weakened_threshold,
            stopped_threshold,
        )
        seed_test_metrics[str(seed)] = evaluate(
            y_test,
            seed_predictions,
            scores,
        )

    test_scores = np.mean(final_seed_scores, axis=0)
    test_predictions = threshold_predictions(
        test_scores,
        weakened_threshold,
        stopped_threshold,
    )
    test_metrics = evaluate(y_test, test_predictions, test_scores)
    top_k = pd.DataFrame(top_k_records("final_test", y_test, test_scores))
    top_k.to_csv(
        REPORT_DIR / "dl_core43_top_k.csv",
        index=False,
        encoding="utf-8-sig",
    )
    top20 = top_k.loc[
        top_k["target_rate"].eq(PRIMARY_TARGET_RATE)
    ].iloc[0]

    profile = final_test.copy()
    profile[["retained_score", "weakened_score", "stopped_score"]] = test_scores
    profile["priority_score"] = (
        profile["weakened_score"] + profile["stopped_score"]
    )
    profile["predicted_state"] = test_predictions
    profile["predicted_state_label"] = profile["predicted_state"].map(
        CLASS_LABELS_KO
    )
    profile["priority_rank"] = profile["priority_score"].rank(
        method="first",
        ascending=False,
    ).astype(int)
    profile["priority_top_percent"] = (
        profile["priority_rank"].div(len(profile)).mul(100)
    )
    profile["selected_for_crm"] = profile["priority_rank"].le(
        int(np.ceil(len(profile) * PRIMARY_TARGET_RATE))
    ).astype("int8")
    profile = profile.sort_values(
        ["priority_rank", "sample_id"]
    ).reset_index(drop=True)
    profile.to_parquet(PROFILE_PATH, index=False)

    matrix = confusion_matrix(y_test, test_predictions, labels=CLASS_CODES)
    pd.DataFrame(
        matrix,
        index=[f"actual_{name}" for name in CLASS_NAMES],
        columns=[f"predicted_{name}" for name in CLASS_NAMES],
    ).to_csv(
        REPORT_DIR / "dl_core43_confusion.csv",
        encoding="utf-8-sig",
    )

    ml_metrics = v04_metadata["test_metrics"]
    ml_top20 = v04_metadata["top20_policy"]
    comparison = pd.DataFrame(
        [
            {
                "candidate": "ml_logistic_core43_v04",
                "model_family": "machine_learning",
                "feature_count": 43,
                "test_samples": v04_metadata["test_samples"],
                "macro_f1": ml_metrics["macro_f1"],
                "macro_pr_auc": ml_metrics["macro_pr_auc"],
                "balanced_accuracy": ml_metrics["balanced_accuracy"],
                "retained_recall": ml_metrics["retained_recall"],
                "weakened_recall": ml_metrics["weakened_recall"],
                "stopped_recall": ml_metrics["stopped_recall"],
                "top20_precision": ml_top20["status_loss_precision"],
                "top20_recall": ml_top20["status_loss_recall"],
                "top20_lift": ml_top20["status_loss_lift"],
            },
            {
                "candidate": "v05_01_dl_mlp_ensemble_core43",
                "model_family": "deep_learning",
                "feature_count": 43,
                "test_samples": len(final_test),
                "macro_f1": test_metrics["macro_f1"],
                "macro_pr_auc": test_metrics["macro_pr_auc"],
                "balanced_accuracy": test_metrics["balanced_accuracy"],
                "retained_recall": test_metrics["retained_recall"],
                "weakened_recall": test_metrics["weakened_recall"],
                "stopped_recall": test_metrics["stopped_recall"],
                "top20_precision": top20["status_loss_precision"],
                "top20_recall": top20["status_loss_recall"],
                "top20_lift": top20["status_loss_lift"],
            },
        ]
    )
    comparison.to_csv(
        REPORT_DIR / "ml_v04_vs_v05_01_dl.csv",
        index=False,
        encoding="utf-8-sig",
    )

    seed_test_f1 = [
        metrics["macro_f1"]
        for metrics in seed_test_metrics.values()
    ]
    metadata = {
        "version": EXPERIMENT_VERSION,
        "dataset_version": "v04",
        "feature_set": "core43",
        "status": "challenger_experiment",
        "model_name": "Core43 PyTorch MLP 3-seed ensemble",
        "model_type": "PyTorch TabularMLP",
        "problem_type": "multiclass_classification",
        "class_map": {"0": "retained", "1": "weakened", "2": "stopped"},
        "cohort_definition": v04_metadata["cohort_definition"],
        "time_structure": v04_metadata["time_structure"],
        "feature_count": len(feature_columns),
        "feature_columns": feature_columns,
        "input_dim_after_imputation": int(x_train.shape[1]),
        "selected_config": asdict(selected_config),
        "seeds": SEEDS,
        "decision_thresholds": {
            "weakened_score": weakened_threshold,
            "stopped_score": stopped_threshold,
            "evaluation_order": ["stopped", "weakened", "retained"],
        },
        "selection_rule": (
            "highest 3-seed ensemble pooled time-OOF Macro F1; "
            "ties by PR-AUC, balanced accuracy, class recall and seed stability"
        ),
        "train_samples": len(final_train),
        "test_samples": len(final_test),
        "oof_metrics": oof_metrics,
        "test_metrics": test_metrics,
        "seed_test_metrics": seed_test_metrics,
        "seed_test_macro_f1_mean": float(np.mean(seed_test_f1)),
        "seed_test_macro_f1_std": float(np.std(seed_test_f1, ddof=1)),
        "top20_policy": {
            key: float(top20[key])
            for key in [
                "target_users",
                "status_loss_captured",
                "status_loss_precision",
                "status_loss_recall",
                "status_loss_lift",
                "stopped_captured",
                "stopped_recall",
                "weakened_captured",
                "weakened_recall",
            ]
        },
        "artifacts": {
            "preprocessor_sha256": preprocessor_checksum,
            "weight_sha256": weight_checksums,
        },
        "runtime": {
            "device": str(device),
            "torch_version": torch.__version__,
            "python_version": sys.version.split()[0],
            "sklearn_version": sklearn.__version__,
            "pandas_version": pd.__version__,
            "elapsed_seconds": time.perf_counter() - start_time,
        },
        "score_warning": (
            "클래스 점수와 통합 점수는 보정된 실제 확률이 아니라 "
            "위험 순위 산정을 위한 모델 점수다."
        ),
    }
    (MODEL_DIR / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    report = f"""# v05_01_dl 딥러닝 Core 43 비교 실험

## 실험 계약

- 기존 v04 연간 코호트, Core 43, 3클래스 라벨을 그대로 사용했다.
- 2013~2017 확장형 시간 5-Fold의 OOF에서 구조·가중치·임계값을 선택했다.
- 최종 학습은 선정연도 2010~2017, 최종 Test는 2018→2019다.
- Test는 후보 선택에 사용하지 않았다.
- 딥러닝 결과는 기존 v04를 대체하지 않는 challenger 산출물이다.
- 클래스 점수는 보정된 실제 확률이 아니라 위험 순위용 모델 점수다.

## 선택된 딥러닝 조건

- 후보: `{selected_config.name}`
- 은닉층: `{' → '.join(map(str, selected_config.hidden_dims))}`
- Dropout: {selected_config.dropout}
- Learning rate: {selected_config.learning_rate}
- Weight decay: {selected_config.weight_decay}
- Epochs: {selected_config.epochs}
- Batch size: {selected_config.batch_size}
- 클래스 가중 손실: {selected_config.class_weighted_loss}
- 약화 임계값: {weakened_threshold:.2f}
- 중단 임계값: {stopped_threshold:.2f}
- 최종 모델: seed {', '.join(map(str, SEEDS))} 점수 평균 앙상블

## 최종 Test 비교

| 후보 | Macro F1 | Macro PR-AUC | Balanced Acc. | 유지 Recall | 약화 Recall | 중단 Recall | Top20 Precision | Top20 Recall | Lift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ML Logistic Core43 v04 | {ml_metrics['macro_f1']:.4f} | {ml_metrics['macro_pr_auc']:.4f} | {ml_metrics['balanced_accuracy']:.2%} | {ml_metrics['retained_recall']:.2%} | {ml_metrics['weakened_recall']:.2%} | {ml_metrics['stopped_recall']:.2%} | {ml_top20['status_loss_precision']:.2%} | {ml_top20['status_loss_recall']:.2%} | {ml_top20['status_loss_lift']:.2f}× |
| DL MLP Ensemble Core43 v05_01 | {test_metrics['macro_f1']:.4f} | {test_metrics['macro_pr_auc']:.4f} | {test_metrics['balanced_accuracy']:.2%} | {test_metrics['retained_recall']:.2%} | {test_metrics['weakened_recall']:.2%} | {test_metrics['stopped_recall']:.2%} | {top20['status_loss_precision']:.2%} | {top20['status_loss_recall']:.2%} | {top20['status_loss_lift']:.2f}× |

## Seed 안정성

- 단일 seed Test Macro F1 평균: {np.mean(seed_test_f1):.4f}
- 단일 seed Test Macro F1 표준편차: {np.std(seed_test_f1, ddof=1):.4f}
- 3-seed 앙상블 Test Macro F1: {test_metrics['macro_f1']:.4f}

## 해석 원칙

운영 모델 승격은 Macro F1 하나가 아니라 PR-AUC, 클래스별 Recall,
Top 20% Lift, seed 안정성, 추론 비용과 설명 가능성을 함께 검토한다.
"""
    (REPORT_DIR / "dl_core43_performance.md").write_text(
        report,
        encoding="utf-8",
    )

    print(
        f"selected={selected_config.name}, "
        f"OOF Macro F1={oof_metrics['macro_f1']:.4f}, "
        f"Test Macro F1={test_metrics['macro_f1']:.4f}, "
        f"Test Macro PR-AUC={test_metrics['macro_pr_auc']:.4f}",
        flush=True,
    )
    print(f"report={REPORT_DIR / 'dl_core43_performance.md'}", flush=True)


if __name__ == "__main__":
    main()
