"""Train the v05_02_dl extended81 challenger under the v05_01 conditions.

Only the feature set changes from v05_01_dl. The cohort, labels, time folds,
MLP architecture, optimizer settings, training epochs, and three seeds remain
fixed. Decision thresholds are selected on pooled expanding-time OOF scores,
then the 2018 -> 2019 final test is evaluated once.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

# PyTorch must initialize before NumPy/scikit-learn on Windows.
import torch
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import confusion_matrix

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.v05_01_dl import train as base


VERSION = "v05_02_dl"

DATA_PATH = (
    ROOT
    / "data"
    / "processed"
    / "experiments"
    / "modeling_dataset_v04_extended81_v05_02_dl.parquet"
)
FEATURE_CONFIG_PATH = Path(__file__).with_name("feature_config.json")
FEATURE_METADATA_PATH = (
    ROOT
    / "reports"
    / "experiments"
    / VERSION
    / "feature_build_metadata.json"
)
V04_ML_METADATA_PATH = (
    ROOT / "models" / "final_core_logistic_multiclass_metadata_v04.json"
)
V05_01_METADATA_PATH = (
    ROOT / "models" / "experiments" / "v05_01_dl" / "metadata.json"
)

MODEL_DIR = ROOT / "models" / "experiments" / VERSION
REPORT_DIR = ROOT / "reports" / "experiments" / VERSION
PROFILE_PATH = (
    ROOT
    / "data"
    / "processed"
    / "experiments"
    / "final_test_retention_profiles_v05_02_dl.parquet"
)

FIXED_CONFIG = base.CandidateConfig(
    name="mlp_medium_unweighted",
    hidden_dims=(128, 64, 32),
    dropout=0.20,
    learning_rate=7e-4,
    weight_decay=5e-4,
    epochs=50,
    batch_size=512,
    class_weighted_loss=False,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_contract() -> tuple[pd.DataFrame, list[str], dict, dict, dict]:
    required = [
        DATA_PATH,
        FEATURE_CONFIG_PATH,
        FEATURE_METADATA_PATH,
        V04_ML_METADATA_PATH,
        V05_01_METADATA_PATH,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing required inputs:\n- " + "\n- ".join(missing))

    feature_config = json.loads(FEATURE_CONFIG_PATH.read_text(encoding="utf-8"))
    feature_metadata = json.loads(FEATURE_METADATA_PATH.read_text(encoding="utf-8"))
    ml_metadata = json.loads(V04_ML_METADATA_PATH.read_text(encoding="utf-8"))
    dl01_metadata = json.loads(V05_01_METADATA_PATH.read_text(encoding="utf-8"))
    frame = pd.read_parquet(DATA_PATH)
    feature_columns = list(feature_metadata["feature_columns"])

    if feature_config["model_version"] != VERSION:
        raise ValueError("Feature config version mismatch")
    if feature_metadata["version"] != VERSION:
        raise ValueError("Feature metadata version mismatch")
    if feature_metadata["output_sha256"] != sha256(DATA_PATH):
        raise ValueError("Extended dataset checksum mismatch")
    if len(frame) != 37_953 or not frame["sample_id"].is_unique:
        raise ValueError("Expected 37,953 unique v04 samples")
    if len(feature_columns) != 81 or len(set(feature_columns)) != 81:
        raise ValueError("Expected 81 unique model features")
    if set(feature_columns) - set(frame.columns):
        raise ValueError("Extended feature columns are missing")
    forbidden = set(feature_config["excluded_columns"])
    if forbidden & set(feature_columns):
        raise ValueError("Target-derived or reaction columns found in features")
    if np.isinf(frame[feature_columns].to_numpy(dtype=float)).any():
        raise ValueError("Infinite feature value")

    final_train = frame.loc[frame["selection_year"].between(2010, 2017)]
    final_test = frame.loc[frame["selection_year"].eq(2018)]
    if len(final_train) != 31_420 or len(final_test) != 6_533:
        raise ValueError("v04 train/test row count changed")
    if not final_test["target_year"].eq(2019).all():
        raise ValueError("Final test must be selection 2018 -> target 2019")
    if final_test["retention_state"].value_counts().to_dict() != {
        1: 3_065,
        0: 2_584,
        2: 884,
    }:
        raise ValueError("Final test class distribution changed")

    expected_dl01 = {
        "hidden_dims": list(FIXED_CONFIG.hidden_dims),
        "dropout": FIXED_CONFIG.dropout,
        "learning_rate": FIXED_CONFIG.learning_rate,
        "weight_decay": FIXED_CONFIG.weight_decay,
        "epochs": FIXED_CONFIG.epochs,
        "batch_size": FIXED_CONFIG.batch_size,
        "class_weighted_loss": FIXED_CONFIG.class_weighted_loss,
    }
    for key, value in expected_dl01.items():
        if dl01_metadata["selected_config"][key] != value:
            raise ValueError(f"v05_01 fixed condition changed: {key}")
    if dl01_metadata["dataset_version"] != "v04":
        raise ValueError("v05_01 dataset version changed")
    return frame, feature_columns, feature_metadata, ml_metadata, dl01_metadata


def select_thresholds(oof: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    candidates = pd.DataFrame(base.candidate_records(FIXED_CONFIG, oof)).sort_values(
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
    return candidates, candidates.iloc[0]


def comparison_row(
    candidate: str,
    family: str,
    feature_count: int,
    metrics: dict,
    top20: dict,
    test_samples: int,
) -> dict:
    return {
        "candidate": candidate,
        "model_family": family,
        "feature_count": feature_count,
        "test_samples": test_samples,
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
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(
        f"device={device}, torch={torch.__version__}, "
        f"threads={torch.get_num_threads()}",
        flush=True,
    )

    (
        frame,
        feature_columns,
        feature_metadata,
        ml_metadata,
        dl01_metadata,
    ) = load_contract()
    print("v05_02 extended81 contract validated", flush=True)

    oof = base.run_candidate_oof(
        frame,
        feature_columns,
        FIXED_CONFIG,
        device,
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

    ensemble_oof = oof.loc[oof["record_type"].eq("ensemble")].copy()
    oof_scores = ensemble_oof[
        ["retained_score", "weakened_score", "stopped_score"]
    ].to_numpy()
    oof_y = ensemble_oof["retention_state"].to_numpy()
    oof_predictions = base.threshold_predictions(
        oof_scores,
        weakened_threshold,
        stopped_threshold,
    )
    oof_metrics = base.evaluate(oof_y, oof_predictions, oof_scores)

    final_train = frame.loc[frame["selection_year"].between(2010, 2017)].copy()
    final_test = frame.loc[frame["selection_year"].eq(2018)].copy()
    preprocessor = base.build_preprocessor()
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
    preprocessor_checksum = sha256(preprocessor_path)

    final_seed_scores = []
    weight_checksums = {}
    seed_test_metrics = {}
    for seed in base.SEEDS:
        print(f"final training seed {seed}", flush=True)
        model = base.train_model(
            x_train,
            y_train,
            FIXED_CONFIG,
            seed,
            device,
        )
        scores = base.predict_scores(model, x_test, device)
        weights_path = MODEL_DIR / f"seed_{seed}_state_dict.pt"
        checksum, reloaded_scores = base.save_and_reload_model(
            model,
            weights_path,
            FIXED_CONFIG,
            x_train.shape[1],
            x_test,
            device,
        )
        if not np.allclose(scores, reloaded_scores, rtol=0, atol=1e-7):
            raise ValueError(f"Reloaded model scores changed for seed {seed}")
        weight_checksums[str(seed)] = checksum
        final_seed_scores.append(scores)
        seed_predictions = base.threshold_predictions(
            scores,
            weakened_threshold,
            stopped_threshold,
        )
        seed_test_metrics[str(seed)] = base.evaluate(
            y_test,
            seed_predictions,
            scores,
        )

    test_scores = np.mean(final_seed_scores, axis=0)
    test_predictions = base.threshold_predictions(
        test_scores,
        weakened_threshold,
        stopped_threshold,
    )
    test_metrics = base.evaluate(y_test, test_predictions, test_scores)
    top_k = pd.DataFrame(base.top_k_records("final_test", y_test, test_scores))
    top_k.to_csv(REPORT_DIR / "top_k.csv", index=False, encoding="utf-8-sig")
    top20 = top_k.loc[top_k["target_rate"].eq(base.PRIMARY_TARGET_RATE)].iloc[0]

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
        method="first",
        ascending=False,
    ).astype(int)
    profile["priority_top_percent"] = (
        profile["priority_rank"].div(len(profile)).mul(100)
    )
    profile["selected_for_crm"] = profile["priority_rank"].le(
        int(np.ceil(len(profile) * base.PRIMARY_TARGET_RATE))
    ).astype("int8")
    profile = profile.sort_values(["priority_rank", "sample_id"]).reset_index(drop=True)
    profile.to_parquet(PROFILE_PATH, index=False)

    matrix = confusion_matrix(y_test, test_predictions, labels=base.CLASS_CODES)
    pd.DataFrame(
        matrix,
        index=[f"actual_{name}" for name in base.CLASS_NAMES],
        columns=[f"predicted_{name}" for name in base.CLASS_NAMES],
    ).to_csv(REPORT_DIR / "confusion.csv", encoding="utf-8-sig")

    ml_metrics = ml_metadata["test_metrics"]
    ml_top20 = ml_metadata["top20_policy"]
    dl01_metrics = dl01_metadata["test_metrics"]
    dl01_top20 = dl01_metadata["top20_policy"]
    comparison = pd.DataFrame(
        [
            comparison_row(
                "v04_ml_logistic_core43",
                "machine_learning",
                43,
                ml_metrics,
                ml_top20,
                int(ml_metadata["test_samples"]),
            ),
            comparison_row(
                "v05_01_dl_mlp_core43",
                "deep_learning",
                43,
                dl01_metrics,
                dl01_top20,
                int(dl01_metadata["test_samples"]),
            ),
            comparison_row(
                "v05_02_dl_mlp_extended81",
                "deep_learning",
                81,
                test_metrics,
                top20,
                len(final_test),
            ),
        ]
    )
    comparison.to_csv(
        REPORT_DIR / "model_comparison.csv",
        index=False,
        encoding="utf-8-sig",
    )

    seed_test_f1 = [
        metrics["macro_f1"] for metrics in seed_test_metrics.values()
    ]
    elapsed_seconds = time.perf_counter() - started
    metadata = {
        "version": VERSION,
        "dataset_version": "v04",
        "feature_set": "extended81",
        "status": "challenger_experiment",
        "model_name": "Extended81 PyTorch MLP 3-seed ensemble",
        "model_type": "PyTorch TabularMLP",
        "problem_type": "multiclass_classification",
        "class_map": {"0": "retained", "1": "weakened", "2": "stopped"},
        "fixed_condition_from": "v05_01_dl",
        "cohort_definition": ml_metadata["cohort_definition"],
        "time_structure": ml_metadata["time_structure"],
        "feature_count": len(feature_columns),
        "feature_columns": feature_columns,
        "feature_groups": feature_metadata["feature_groups"],
        "input_dim_after_imputation": int(x_train.shape[1]),
        "selected_config": asdict(FIXED_CONFIG),
        "seeds": base.SEEDS,
        "decision_thresholds": {
            "weakened_score": weakened_threshold,
            "stopped_score": stopped_threshold,
            "evaluation_order": ["stopped", "weakened", "retained"],
        },
        "selection_rule": (
            "fixed v05_01 architecture; thresholds selected by highest "
            "3-seed ensemble pooled time-OOF Macro F1"
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
            "dataset_sha256": feature_metadata["output_sha256"],
            "preprocessor_sha256": preprocessor_checksum,
            "weight_sha256": weight_checksums,
        },
        "runtime": {
            "device": str(device),
            "torch_version": torch.__version__,
            "python_version": sys.version.split()[0],
            "sklearn_version": sklearn.__version__,
            "pandas_version": pd.__version__,
            "elapsed_seconds": elapsed_seconds,
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

    report = f"""# v05_02_dl Extended 81 비교 실험

## 실험 계약

- 데이터·코호트·라벨·시간 분할은 승인된 v04와 같다.
- `v05_01_dl`과 동일한 MLP 구조·optimizer·epoch·seed를 사용했다.
- 변경한 주요 조건은 Core 43에서 Extended 81로의 피처 확장뿐이다.
- 확장 피처는 카테고리 14, 맛집 탐방 반경 12, 평점 변화 12다.
- Useful·Cool·Funny와 타깃 연도 정보는 입력에서 제외했다.
- 임계값은 2013~2017 확장형 시간 OOF에서 선택했다.
- 최종 Test는 2018→2019이며 후보 선택에 사용하지 않았다.

## 고정 모델 조건

- 은닉층: `128 → 64 → 32`
- Dropout: {FIXED_CONFIG.dropout}
- Learning rate: {FIXED_CONFIG.learning_rate}
- Weight decay: {FIXED_CONFIG.weight_decay}
- Epochs: {FIXED_CONFIG.epochs}
- Batch size: {FIXED_CONFIG.batch_size}
- 클래스 가중 손실: {FIXED_CONFIG.class_weighted_loss}
- 약화 임계값: {weakened_threshold:.2f}
- 중단 임계값: {stopped_threshold:.2f}
- 최종 모델: seed {', '.join(map(str, base.SEEDS))} 점수 평균 앙상블

## 최종 Test 비교

| 후보 | 피처 | Macro F1 | Macro PR-AUC | Balanced Acc. | 유지 Recall | 약화 Recall | 중단 Recall | Top20 Precision | Top20 Recall | Lift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ML Logistic v04 | 43 | {ml_metrics['macro_f1']:.4f} | {ml_metrics['macro_pr_auc']:.4f} | {ml_metrics['balanced_accuracy']:.2%} | {ml_metrics['retained_recall']:.2%} | {ml_metrics['weakened_recall']:.2%} | {ml_metrics['stopped_recall']:.2%} | {ml_top20['status_loss_precision']:.2%} | {ml_top20['status_loss_recall']:.2%} | {ml_top20['status_loss_lift']:.2f}× |
| DL v05_01 Core43 | 43 | {dl01_metrics['macro_f1']:.4f} | {dl01_metrics['macro_pr_auc']:.4f} | {dl01_metrics['balanced_accuracy']:.2%} | {dl01_metrics['retained_recall']:.2%} | {dl01_metrics['weakened_recall']:.2%} | {dl01_metrics['stopped_recall']:.2%} | {dl01_top20['status_loss_precision']:.2%} | {dl01_top20['status_loss_recall']:.2%} | {dl01_top20['status_loss_lift']:.2f}× |
| DL v05_02 Extended81 | 81 | {test_metrics['macro_f1']:.4f} | {test_metrics['macro_pr_auc']:.4f} | {test_metrics['balanced_accuracy']:.2%} | {test_metrics['retained_recall']:.2%} | {test_metrics['weakened_recall']:.2%} | {test_metrics['stopped_recall']:.2%} | {top20['status_loss_precision']:.2%} | {top20['status_loss_recall']:.2%} | {top20['status_loss_lift']:.2f}× |

## OOF 및 seed 안정성

- OOF Macro F1: {oof_metrics['macro_f1']:.4f}
- OOF Macro PR-AUC: {oof_metrics['macro_pr_auc']:.4f}
- 단일 seed Test Macro F1 평균: {np.mean(seed_test_f1):.4f}
- 단일 seed Test Macro F1 표준편차: {np.std(seed_test_f1, ddof=1):.4f}
- 3-seed 앙상블 Test Macro F1: {test_metrics['macro_f1']:.4f}

## 해석 원칙

운영 모델 승격은 Macro F1 하나가 아니라 PR-AUC, 클래스별 Recall,
Top 20% Lift, seed 안정성, 추론 비용을 함께 검토한다. 클래스 점수는
보정된 실제 확률이 아니라 위험 순위 산정을 위한 모델 점수다.
"""
    (REPORT_DIR / "performance.md").write_text(report, encoding="utf-8")

    print(
        f"selected thresholds=({weakened_threshold:.2f}, {stopped_threshold:.2f}), "
        f"OOF Macro F1={oof_metrics['macro_f1']:.4f}, "
        f"Test Macro F1={test_metrics['macro_f1']:.4f}, "
        f"Test Macro PR-AUC={test_metrics['macro_pr_auc']:.4f}",
        flush=True,
    )
    print(f"report={REPORT_DIR / 'performance.md'}", flush=True)


if __name__ == "__main__":
    main()
