"""Train the v05_03_dl Core43 plus 24-month GRU challenger."""

from __future__ import annotations

import hashlib
import itertools
import json
import random
import sys
import time
from pathlib import Path

import torch
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import confusion_matrix
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.v05_01_dl import train as base


VERSION = "v05_03_dl"
CONFIG_PATH = Path(__file__).with_name("config.json")
DATA_PATH = ROOT / "data" / "processed" / "modeling_dataset_rolling_v04.parquet"
SEQUENCE_PATH = (
    ROOT
    / "data"
    / "processed"
    / "experiments"
    / "monthly_sequence_v04_v05_03_dl.parquet"
)
SEQUENCE_METADATA_PATH = (
    ROOT / "reports" / "experiments" / VERSION / "sequence_build_metadata.json"
)
CORE_METADATA_PATH = ROOT / "models" / "final_core_hgb_metadata_v02.json"
ML_METADATA_PATH = (
    ROOT / "models" / "final_core_logistic_multiclass_metadata_v04.json"
)
DL01_METADATA_PATH = (
    ROOT / "models" / "experiments" / "v05_01_dl" / "metadata.json"
)
DL02_METADATA_PATH = (
    ROOT / "models" / "experiments" / "v05_02_dl" / "metadata.json"
)
MODEL_DIR = ROOT / "models" / "experiments" / VERSION
REPORT_DIR = ROOT / "reports" / "experiments" / VERSION
PROFILE_PATH = (
    ROOT
    / "data"
    / "processed"
    / "experiments"
    / "final_test_retention_profiles_v05_03_dl.parquet"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class HybridGRU(nn.Module):
    def __init__(
        self,
        static_input_dim: int,
        sequence_input_dim: int,
        static_hidden_dims: tuple[int, int],
        gru_hidden_dim: int,
        fusion_hidden_dim: int,
        dropout: float,
    ) -> None:
        super().__init__()
        self.static_branch = nn.Sequential(
            nn.Linear(static_input_dim, static_hidden_dims[0]),
            nn.BatchNorm1d(static_hidden_dims[0]),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(static_hidden_dims[0], static_hidden_dims[1]),
            nn.GELU(),
        )
        self.gru = nn.GRU(
            input_size=sequence_input_dim,
            hidden_size=gru_hidden_dim,
            num_layers=1,
            batch_first=True,
        )
        self.classifier = nn.Sequential(
            nn.Linear(static_hidden_dims[1] + gru_hidden_dim, fusion_hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(fusion_hidden_dim, len(base.CLASS_CODES)),
        )

    def forward(
        self,
        static_features: torch.Tensor,
        sequence_features: torch.Tensor,
    ) -> torch.Tensor:
        static_embedding = self.static_branch(static_features)
        _, hidden = self.gru(sequence_features)
        temporal_embedding = hidden[-1]
        return self.classifier(
            torch.cat([static_embedding, temporal_embedding], dim=1)
        )


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def make_model(
    static_input_dim: int,
    config: dict,
    device: torch.device,
) -> HybridGRU:
    model_config = config["model"]
    return HybridGRU(
        static_input_dim=static_input_dim,
        sequence_input_dim=len(config["sequence_channels"]),
        static_hidden_dims=tuple(model_config["static_hidden_dims"]),
        gru_hidden_dim=int(model_config["gru_hidden_dim"]),
        fusion_hidden_dim=int(model_config["fusion_hidden_dim"]),
        dropout=float(model_config["dropout"]),
    ).to(device)


def train_model(
    x_static: np.ndarray,
    x_sequence: np.ndarray,
    labels: np.ndarray,
    config: dict,
    seed: int,
    device: torch.device,
) -> HybridGRU:
    set_seed(seed)
    model = make_model(x_static.shape[1], config, device)
    model_config = config["model"]
    dataset = TensorDataset(
        torch.from_numpy(x_static.astype(np.float32, copy=False)),
        torch.from_numpy(x_sequence.astype(np.float32, copy=False)),
        torch.from_numpy(labels.astype(np.int64, copy=False)),
    )
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(
        dataset,
        batch_size=int(model_config["batch_size"]),
        shuffle=True,
        generator=generator,
        num_workers=0,
    )
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(model_config["learning_rate"]),
        weight_decay=float(model_config["weight_decay"]),
    )
    model.train()
    for _ in range(int(model_config["epochs"])):
        for static_batch, sequence_batch, label_batch in loader:
            optimizer.zero_grad(set_to_none=True)
            logits = model(
                static_batch.to(device),
                sequence_batch.to(device),
            )
            loss = criterion(logits, label_batch.to(device))
            loss.backward()
            optimizer.step()
    return model


@torch.inference_mode()
def predict_scores(
    model: HybridGRU,
    x_static: np.ndarray,
    x_sequence: np.ndarray,
    device: torch.device,
) -> np.ndarray:
    model.eval()
    dataset = TensorDataset(
        torch.from_numpy(x_static.astype(np.float32, copy=False)),
        torch.from_numpy(x_sequence.astype(np.float32, copy=False)),
    )
    loader = DataLoader(dataset, batch_size=2048, shuffle=False, num_workers=0)
    parts = []
    for static_batch, sequence_batch in loader:
        logits = model(static_batch.to(device), sequence_batch.to(device))
        parts.append(torch.softmax(logits, dim=1).cpu().numpy())
    return np.concatenate(parts)


def load_contract() -> tuple[pd.DataFrame, np.ndarray, list[str], dict, dict]:
    required = [
        CONFIG_PATH,
        DATA_PATH,
        SEQUENCE_PATH,
        SEQUENCE_METADATA_PATH,
        CORE_METADATA_PATH,
        ML_METADATA_PATH,
        DL01_METADATA_PATH,
        DL02_METADATA_PATH,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing inputs:\n- " + "\n- ".join(missing))
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    sequence_metadata = json.loads(
        SEQUENCE_METADATA_PATH.read_text(encoding="utf-8")
    )
    if sequence_metadata["output_sha256"] != sha256(SEQUENCE_PATH):
        raise ValueError("Sequence checksum mismatch")
    frame = pd.read_parquet(DATA_PATH)
    core_metadata = json.loads(CORE_METADATA_PATH.read_text(encoding="utf-8"))
    feature_columns = list(core_metadata["feature_columns"])
    sequence = pd.read_parquet(SEQUENCE_PATH)
    if len(frame) != 37_953 or len(feature_columns) != 43:
        raise ValueError("v04 Core43 contract changed")
    if len(sequence) != len(frame) * 24:
        raise ValueError("Expected 24 sequence rows per sample")
    sample_order = sequence["sample_id"].drop_duplicates().tolist()
    if sample_order != frame["sample_id"].tolist():
        raise ValueError("Sequence sample order differs from v04")
    if not np.array_equal(
        sequence["month_index"].to_numpy().reshape(-1, 24),
        np.tile(np.arange(24), (len(frame), 1)),
    ):
        raise ValueError("Sequence month order changed")
    raw_sequence = sequence[config["sequence_channels"]].to_numpy(
        dtype=np.float32
    ).reshape(len(frame), 24, -1)
    raw_sequence[:, :, :2] = np.log1p(raw_sequence[:, :, :2])
    if np.isinf(raw_sequence).any() or np.isnan(raw_sequence).any():
        raise ValueError("Invalid sequence value")
    final_test = frame.loc[frame["selection_year"].eq(2018)]
    if len(final_test) != 6_533 or not final_test["target_year"].eq(2019).all():
        raise ValueError("Final test contract changed")
    return frame, raw_sequence, feature_columns, config, sequence_metadata


def transform_sequence(
    train_sequence: np.ndarray,
    validation_sequence: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, StandardScaler]:
    scaler = StandardScaler()
    scaler.fit(train_sequence.reshape(-1, train_sequence.shape[-1]))
    transformed_train = scaler.transform(
        train_sequence.reshape(-1, train_sequence.shape[-1])
    ).reshape(train_sequence.shape)
    transformed_validation = scaler.transform(
        validation_sequence.reshape(-1, validation_sequence.shape[-1])
    ).reshape(validation_sequence.shape)
    return (
        transformed_train.astype(np.float32),
        transformed_validation.astype(np.float32),
        scaler,
    )


def run_oof(
    frame: pd.DataFrame,
    raw_sequence: np.ndarray,
    feature_columns: list[str],
    config: dict,
    device: torch.device,
) -> pd.DataFrame:
    parts = []
    total = len(base.TIME_FOLDS) * len(base.SEEDS)
    run = 0
    for train_end, validation_year in base.TIME_FOLDS:
        train_mask = frame["selection_year"].between(2010, train_end).to_numpy()
        validation_mask = frame["selection_year"].eq(validation_year).to_numpy()
        train = frame.loc[train_mask]
        validation = frame.loc[validation_mask]
        static_preprocessor = base.build_preprocessor()
        x_static_train = static_preprocessor.fit_transform(
            train[feature_columns]
        ).astype(np.float32)
        x_static_validation = static_preprocessor.transform(
            validation[feature_columns]
        ).astype(np.float32)
        x_sequence_train, x_sequence_validation, _ = transform_sequence(
            raw_sequence[train_mask],
            raw_sequence[validation_mask],
        )
        labels = train["retention_state"].to_numpy(dtype=np.int64)
        fold_scores = []
        for seed in base.SEEDS:
            run += 1
            print(
                f"hybrid_gru: run {run}/{total}, train 2010-{train_end}, "
                f"validation {validation_year}, seed {seed}",
                flush=True,
            )
            model = train_model(
                x_static_train,
                x_sequence_train,
                labels,
                config,
                seed,
                device,
            )
            scores = predict_scores(
                model,
                x_static_validation,
                x_sequence_validation,
                device,
            )
            fold_scores.append(scores)
            part = validation[
                ["sample_id", "selection_year", "retention_state"]
            ].copy()
            part["seed"] = seed
            part[["retained_score", "weakened_score", "stopped_score"]] = scores
            part["record_type"] = "seed"
            parts.append(part)
        ensemble = validation[
            ["sample_id", "selection_year", "retention_state"]
        ].copy()
        ensemble["seed"] = -1
        ensemble[
            ["retained_score", "weakened_score", "stopped_score"]
        ] = np.mean(fold_scores, axis=0)
        ensemble["record_type"] = "ensemble"
        parts.append(ensemble)
    return pd.concat(parts, ignore_index=True)


def select_thresholds(oof: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    ensemble = oof.loc[oof["record_type"].eq("ensemble")]
    scores = ensemble[
        ["retained_score", "weakened_score", "stopped_score"]
    ].to_numpy()
    labels = ensemble["retention_state"].to_numpy()
    records = []
    for weakened, stopped in itertools.product(
        base.WEAKENED_THRESHOLDS,
        base.STOPPED_THRESHOLDS,
    ):
        predictions = base.threshold_predictions(scores, weakened, stopped)
        metrics = base.evaluate(labels, predictions, scores)
        seed_f1 = []
        for seed in base.SEEDS:
            seed_frame = oof.loc[
                oof["record_type"].eq("seed") & oof["seed"].eq(seed)
            ]
            seed_scores = seed_frame[
                ["retained_score", "weakened_score", "stopped_score"]
            ].to_numpy()
            seed_predictions = base.threshold_predictions(
                seed_scores, weakened, stopped
            )
            seed_f1.append(
                base.evaluate(
                    seed_frame["retention_state"].to_numpy(),
                    seed_predictions,
                    seed_scores,
                )["macro_f1"]
            )
        records.append(
            {
                "weakened_threshold": weakened,
                "stopped_threshold": stopped,
                "seed_macro_f1_mean": float(np.mean(seed_f1)),
                "seed_macro_f1_std": float(np.std(seed_f1, ddof=1)),
                **{f"oof_{key}": value for key, value in metrics.items()},
            }
        )
    candidates = pd.DataFrame(records).sort_values(
        [
            "oof_macro_f1",
            "oof_macro_pr_auc",
            "oof_balanced_accuracy",
            "oof_stopped_recall",
            "seed_macro_f1_std",
        ],
        ascending=[False, False, False, False, True],
        kind="stable",
    ).reset_index(drop=True)
    candidates.insert(0, "selection_rank", np.arange(1, len(candidates) + 1))
    candidates["selected"] = candidates["selection_rank"].eq(1)
    return candidates, candidates.iloc[0]


def save_and_reload(
    model: HybridGRU,
    path: Path,
    static_dim: int,
    config: dict,
    x_static: np.ndarray,
    x_sequence: np.ndarray,
    device: torch.device,
) -> tuple[str, np.ndarray]:
    torch.save(
        {key: value.detach().cpu() for key, value in model.state_dict().items()},
        path,
    )
    checksum = sha256(path)
    reloaded = make_model(static_dim, config, device)
    reloaded.load_state_dict(
        torch.load(path, map_location=device, weights_only=True)
    )
    return checksum, predict_scores(
        reloaded, x_static, x_sequence, device
    )


def metric_row(name: str, feature_count: str, metadata: dict) -> dict:
    metrics = metadata["test_metrics"]
    top20 = metadata["top20_policy"]
    return {
        "candidate": name,
        "inputs": feature_count,
        "macro_f1": metrics["macro_f1"],
        "macro_pr_auc": metrics["macro_pr_auc"],
        "balanced_accuracy": metrics["balanced_accuracy"],
        "retained_recall": metrics["retained_recall"],
        "weakened_recall": metrics["weakened_recall"],
        "stopped_recall": metrics["stopped_recall"],
        "top20_precision": top20["status_loss_precision"],
        "top20_recall": top20["status_loss_recall"],
        "top20_lift": top20["status_loss_lift"],
    }


def main() -> None:
    started = time.perf_counter()
    for directory in [MODEL_DIR, REPORT_DIR, PROFILE_PATH.parent]:
        directory.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(min(4, max(1, torch.get_num_threads())))
    device = torch.device("cpu")
    frame, raw_sequence, feature_columns, config, sequence_metadata = (
        load_contract()
    )
    print(
        f"device={device}, Core43+monthly24 contract validated, "
        f"torch={torch.__version__}",
        flush=True,
    )
    oof = run_oof(
        frame, raw_sequence, feature_columns, config, device
    )
    candidates, selected = select_thresholds(oof)
    weakened_threshold = float(selected["weakened_threshold"])
    stopped_threshold = float(selected["stopped_threshold"])
    candidates.to_csv(
        REPORT_DIR / "threshold_candidates.csv",
        index=False,
        encoding="utf-8-sig",
    )
    oof.to_parquet(REPORT_DIR / "selected_oof_predictions.parquet", index=False)
    ensemble_oof = oof.loc[oof["record_type"].eq("ensemble")]
    oof_scores = ensemble_oof[
        ["retained_score", "weakened_score", "stopped_score"]
    ].to_numpy()
    oof_labels = ensemble_oof["retention_state"].to_numpy()
    oof_metrics = base.evaluate(
        oof_labels,
        base.threshold_predictions(
            oof_scores, weakened_threshold, stopped_threshold
        ),
        oof_scores,
    )

    train_mask = frame["selection_year"].between(2010, 2017).to_numpy()
    test_mask = frame["selection_year"].eq(2018).to_numpy()
    final_train = frame.loc[train_mask].copy()
    final_test = frame.loc[test_mask].copy()
    static_preprocessor = base.build_preprocessor()
    x_static_train = static_preprocessor.fit_transform(
        final_train[feature_columns]
    ).astype(np.float32)
    x_static_test = static_preprocessor.transform(
        final_test[feature_columns]
    ).astype(np.float32)
    x_sequence_train, x_sequence_test, sequence_scaler = transform_sequence(
        raw_sequence[train_mask],
        raw_sequence[test_mask],
    )
    preprocessing_path = MODEL_DIR / "preprocessing.joblib"
    joblib.dump(
        {
            "static_preprocessor": static_preprocessor,
            "sequence_scaler": sequence_scaler,
            "sequence_transform": "log1p first two channels, then StandardScaler",
        },
        preprocessing_path,
    )
    labels_train = final_train["retention_state"].to_numpy(dtype=np.int64)
    labels_test = final_test["retention_state"].to_numpy(dtype=np.int64)
    seed_scores = []
    weight_checksums = {}
    seed_test_metrics = {}
    for seed in base.SEEDS:
        print(f"final training seed {seed}", flush=True)
        model = train_model(
            x_static_train,
            x_sequence_train,
            labels_train,
            config,
            seed,
            device,
        )
        scores = predict_scores(
            model, x_static_test, x_sequence_test, device
        )
        path = MODEL_DIR / f"seed_{seed}_state_dict.pt"
        checksum, reloaded_scores = save_and_reload(
            model,
            path,
            x_static_train.shape[1],
            config,
            x_static_test,
            x_sequence_test,
            device,
        )
        if not np.allclose(scores, reloaded_scores, rtol=0, atol=1e-7):
            raise ValueError("Reloaded GRU scores changed")
        weight_checksums[str(seed)] = checksum
        seed_scores.append(scores)
        seed_predictions = base.threshold_predictions(
            scores, weakened_threshold, stopped_threshold
        )
        seed_test_metrics[str(seed)] = base.evaluate(
            labels_test, seed_predictions, scores
        )
    test_scores = np.mean(seed_scores, axis=0)
    test_predictions = base.threshold_predictions(
        test_scores, weakened_threshold, stopped_threshold
    )
    test_metrics = base.evaluate(
        labels_test, test_predictions, test_scores
    )
    top_k = pd.DataFrame(
        base.top_k_records("final_test", labels_test, test_scores)
    )
    top_k.to_csv(REPORT_DIR / "top_k.csv", index=False, encoding="utf-8-sig")
    top20 = top_k.loc[
        top_k["target_rate"].eq(base.PRIMARY_TARGET_RATE)
    ].iloc[0]
    matrix = confusion_matrix(
        labels_test, test_predictions, labels=base.CLASS_CODES
    )
    pd.DataFrame(
        matrix,
        index=[f"actual_{name}" for name in base.CLASS_NAMES],
        columns=[f"predicted_{name}" for name in base.CLASS_NAMES],
    ).to_csv(REPORT_DIR / "confusion.csv", encoding="utf-8-sig")

    profile = final_test.copy()
    profile[["retained_score", "weakened_score", "stopped_score"]] = test_scores
    profile["priority_score"] = (
        profile["weakened_score"] + profile["stopped_score"]
    )
    profile["predicted_state"] = test_predictions
    profile["predicted_state_label"] = profile["predicted_state"].map(
        base.CLASS_LABELS_KO
    )
    profile["priority_rank"] = profile["priority_score"].rank(
        method="first", ascending=False
    ).astype(int)
    profile["priority_top_percent"] = (
        profile["priority_rank"].div(len(profile)).mul(100)
    )
    profile["selected_for_crm"] = profile["priority_rank"].le(
        int(np.ceil(len(profile) * base.PRIMARY_TARGET_RATE))
    ).astype("int8")
    profile.sort_values(
        ["priority_rank", "sample_id"]
    ).reset_index(drop=True).to_parquet(PROFILE_PATH, index=False)

    ml = json.loads(ML_METADATA_PATH.read_text(encoding="utf-8"))
    dl01 = json.loads(DL01_METADATA_PATH.read_text(encoding="utf-8"))
    dl02 = json.loads(DL02_METADATA_PATH.read_text(encoding="utf-8"))
    current_stub = {
        "test_metrics": test_metrics,
        "top20_policy": {
            key: float(top20[key])
            for key in [
                "status_loss_precision",
                "status_loss_recall",
                "status_loss_lift",
            ]
        },
    }
    comparison = pd.DataFrame(
        [
            metric_row("v04_ml", "Core43", ml),
            metric_row("v05_01_dl", "Core43", dl01),
            metric_row("v05_02_dl", "Extended81", dl02),
            metric_row("v05_03_dl", "Core43+Monthly24", current_stub),
        ]
    )
    comparison.to_csv(
        REPORT_DIR / "model_comparison.csv",
        index=False,
        encoding="utf-8-sig",
    )

    seed_f1 = [value["macro_f1"] for value in seed_test_metrics.values()]
    model_metadata = {
        "version": VERSION,
        "dataset_version": "v04",
        "feature_set": "core43+monthly24",
        "status": "challenger_experiment",
        "model_name": "Core43 MLP + Monthly24 GRU 3-seed ensemble",
        "model_type": "PyTorch HybridGRU",
        "class_map": {"0": "retained", "1": "weakened", "2": "stopped"},
        "cohort_definition": ml["cohort_definition"],
        "time_structure": ml["time_structure"],
        "static_feature_count": 43,
        "static_feature_columns": feature_columns,
        "static_input_dim_after_imputation": int(x_static_train.shape[1]),
        "sequence_length": 24,
        "sequence_channels": config["sequence_channels"],
        "model_config": config["model"],
        "seeds": base.SEEDS,
        "decision_thresholds": {
            "weakened_score": weakened_threshold,
            "stopped_score": stopped_threshold,
        },
        "train_samples": len(final_train),
        "test_samples": len(final_test),
        "oof_metrics": oof_metrics,
        "test_metrics": test_metrics,
        "seed_test_metrics": seed_test_metrics,
        "seed_test_macro_f1_mean": float(np.mean(seed_f1)),
        "seed_test_macro_f1_std": float(np.std(seed_f1, ddof=1)),
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
            "sequence_sha256": sequence_metadata["output_sha256"],
            "preprocessing_sha256": sha256(preprocessing_path),
            "weight_sha256": weight_checksums,
        },
        "runtime": {
            "device": str(device),
            "torch_version": torch.__version__,
            "python_version": sys.version.split()[0],
            "sklearn_version": sklearn.__version__,
            "pandas_version": pd.__version__,
            "elapsed_seconds": time.perf_counter() - started,
        },
        "score_warning": (
            "클래스 점수는 보정된 실제 확률이 아니라 위험 순위용 모델 점수다."
        ),
    }
    (MODEL_DIR / "metadata.json").write_text(
        json.dumps(model_metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = f"""# v05_03_dl Core43 + Monthly24 GRU

- 파워 리뷰어·유지/약화/중단 정의와 v04 시간 분할을 유지했다.
- Core 43 정적 피처와 Y-1~Y 24개월 활동 시퀀스를 결합했다.
- Y+1 정보는 정답 생성과 최종 평가에만 사용했다.
- OOF Macro F1: {oof_metrics['macro_f1']:.4f}
- OOF Macro PR-AUC: {oof_metrics['macro_pr_auc']:.4f}
- Test Macro F1: {test_metrics['macro_f1']:.4f}
- Test Macro PR-AUC: {test_metrics['macro_pr_auc']:.4f}
- 유지 Recall: {test_metrics['retained_recall']:.2%}
- 약화 Recall: {test_metrics['weakened_recall']:.2%}
- 중단 Recall: {test_metrics['stopped_recall']:.2%}
- Top 20% Precision/Recall/Lift:
  {top20['status_loss_precision']:.2%} /
  {top20['status_loss_recall']:.2%} /
  {top20['status_loss_lift']:.2f}×
- Seed Macro F1 표준편차: {np.std(seed_f1, ddof=1):.4f}

클래스 점수는 보정된 실제 확률이 아니라 위험 순위용 모델 점수다.
"""
    (REPORT_DIR / "performance.md").write_text(report, encoding="utf-8")
    print(
        f"thresholds=({weakened_threshold:.2f},{stopped_threshold:.2f}), "
        f"OOF Macro F1={oof_metrics['macro_f1']:.4f}, "
        f"Test Macro F1={test_metrics['macro_f1']:.4f}, "
        f"Test Macro PR-AUC={test_metrics['macro_pr_auc']:.4f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
