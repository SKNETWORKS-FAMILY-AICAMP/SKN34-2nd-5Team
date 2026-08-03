"""Validate and summarize the v05_05_01~05 development-only OOF ablations."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score


ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = ROOT / "reports" / "experiments"
BASELINE_VERSION = "v05_05_dl"
VERSIONS = [f"v05_05_0{index}_dl" for index in range(1, 6)]
OUTPUT_DIR = REPORT_ROOT / "v05_05_ablation_summary"
EXPECTED_YEARS = [2013, 2014, 2015, 2016, 2017]
EXPECTED_SEEDS = [42, 2026, 3405]

LABELS = {
    "v05_05_01_dl": "상태 정적 피처 5개",
    "v05_05_02_dl": "최근 1·3·6개월 shortcut",
    "v05_05_03_dl": "신규 탐색 중단 신호",
    "v05_05_04_dl": "stopped 손실 가중치 1.5",
    "v05_05_05_dl": "weakened 하위유형 보조학습",
}

DECISIONS = {
    "v05_05_01_dl": (
        "보류",
        "조건부 stopped PR-AUC와 2017 F1은 올랐지만 pooled Macro F1과 stopped Recall이 하락",
    ),
    "v05_05_02_dl": (
        "보류",
        "최근 활동 shortcut의 pooled Macro F1과 stopped Recall이 기준보다 낮음",
    ),
    "v05_05_03_dl": (
        "제외",
        "Macro F1·Macro PR-AUC·조건부 stopped PR-AUC가 모두 하락",
    ),
    "v05_05_04_dl": (
        "제외",
        "가중치를 높였지만 Macro F1·stopped Recall·조건부 stopped PR-AUC가 모두 개선되지 않음",
    ),
    "v05_05_05_dl": (
        "보류",
        "Macro F1 상승이 +0.0002에 그치고 95% CI가 0을 포함하며 stopped·운영 지표가 소폭 하락",
    ),
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def h2_predictions(
    risk_score: np.ndarray,
    stopped_score: np.ndarray,
    risk_threshold: float,
    stopped_threshold: float,
) -> np.ndarray:
    predictions = np.zeros(len(risk_score), dtype=np.int64)
    at_risk = risk_score >= risk_threshold
    predictions[at_risk] = 1
    predictions[at_risk & (stopped_score >= stopped_threshold)] = 2
    return predictions


def baseline_2017_macro_f1(
    baseline_oof: pd.DataFrame, baseline_metadata: dict
) -> float:
    ensemble = baseline_oof.loc[
        baseline_oof["record_type"].eq("ensemble")
        & baseline_oof["selection_year"].eq(2017)
    ]
    thresholds = baseline_metadata["selected_thresholds"]
    predictions = h2_predictions(
        ensemble["risk_score"].to_numpy(),
        ensemble["conditional_stopped_score"].to_numpy(),
        thresholds["risk_score"],
        thresholds["conditional_stopped_score"],
    )
    return float(
        f1_score(
            ensemble["retention_state"].to_numpy(), predictions, average="macro"
        )
    )


def validate_oof(path: Path, baseline_ids: list[str]) -> pd.DataFrame:
    oof = pd.read_parquet(path)
    ensemble = oof.loc[oof["record_type"].eq("ensemble")].copy()
    seed_rows = oof.loc[oof["record_type"].eq("seed")]
    years = sorted(ensemble["selection_year"].unique().tolist())
    seeds = sorted(seed_rows["seed"].dropna().astype(int).unique().tolist())
    if years != EXPECTED_YEARS:
        raise ValueError(f"Unexpected OOF years at {path}: {years}")
    if seeds != EXPECTED_SEEDS:
        raise ValueError(f"Unexpected OOF seeds at {path}: {seeds}")
    if ensemble["sample_id"].tolist() != baseline_ids:
        raise ValueError(f"OOF sample order differs from baseline: {path}")
    if (oof["selection_year"] >= 2018).any():
        raise ValueError(f"Final-Test year found in OOF artifact: {path}")
    if len(seed_rows) != len(ensemble) * len(EXPECTED_SEEDS):
        raise ValueError(f"Incomplete seed predictions: {path}")
    return ensemble


def bootstrap_interval(path: Path) -> tuple[float, float, float]:
    frame = pd.read_csv(path)
    row = frame.loc[frame["metric"].eq("macro_f1")].iloc[0]
    difference_columns = [
        column for column in frame.columns if column.startswith("mean_difference")
    ]
    if len(difference_columns) != 1:
        raise ValueError(f"Cannot identify bootstrap difference column: {path}")
    return (
        float(row[difference_columns[0]]),
        float(row["ci_2_5"]),
        float(row["ci_97_5"]),
    )


def main() -> None:
    baseline_dir = REPORT_ROOT / BASELINE_VERSION
    baseline_metadata = load_json(baseline_dir / "selected_oof_candidate.json")
    baseline_oof = pd.read_parquet(baseline_dir / "oof_predictions.parquet")
    baseline_ensemble = baseline_oof.loc[
        baseline_oof["record_type"].eq("ensemble")
    ].copy()
    baseline_ids = baseline_ensemble["sample_id"].tolist()
    if sorted(baseline_ensemble["selection_year"].unique().tolist()) != EXPECTED_YEARS:
        raise ValueError("Baseline OOF years do not match the frozen contract")
    if (baseline_oof["selection_year"] >= 2018).any():
        raise ValueError("Final-Test year found in baseline OOF")

    metadata_by_version: dict[str, dict] = {}
    for version in VERSIONS:
        report_dir = REPORT_ROOT / version
        metadata = load_json(report_dir / "selected_oof_candidate.json")
        metadata_by_version[version] = metadata
        validate_oof(report_dir / "oof_predictions.parquet", baseline_ids)
        test_counts = [
            metadata["final_test_rows_loaded"],
            metadata["final_test_predictions_created"],
            metadata["final_test_metrics_created"],
        ]
        if test_counts != [0, 0, 0]:
            raise ValueError(f"Final-Test contract violated by {version}: {test_counts}")
        if metadata["development_samples"] != 31_420 or metadata["oof_samples"] != 24_596:
            raise ValueError(f"Unexpected sample counts for {version}")

    baseline_metrics = metadata_by_version[VERSIONS[0]]["baseline_oof_metrics"]
    baseline_2017_f1 = baseline_2017_macro_f1(baseline_oof, baseline_metadata)
    rows = [
        {
            "version": BASELINE_VERSION,
            "experiment": "현재 기준 모델",
            "decision": "유지",
            "macro_f1": baseline_metrics["macro_f1"],
            "delta_macro_f1": 0.0,
            "macro_pr_auc": baseline_metrics["macro_pr_auc"],
            "weakened_recall": baseline_metrics["weakened_recall"],
            "stopped_recall": baseline_metrics["stopped_recall"],
            "conditional_stopped_pr_auc": baseline_metrics[
                "conditional_stopped_pr_auc"
            ],
            "severe_error_rate": baseline_metrics["severe_error_rate"],
            "retained_to_stopped_count": baseline_metrics[
                "retained_to_stopped_count"
            ],
            "stopped_to_retained_count": baseline_metrics[
                "stopped_to_retained_count"
            ],
            "precision_at_1000": baseline_metrics["mean_precision_at_1000"],
            "seed_macro_f1_std": baseline_metadata["seed_macro_f1_std"],
            "holdout_2017_macro_f1": baseline_2017_f1,
            "bootstrap_ci_low": np.nan,
            "bootstrap_ci_high": np.nan,
            "final_test_rows": 0,
            "reason": "비교 기준",
        }
    ]

    for version in VERSIONS:
        metadata = metadata_by_version[version]
        metrics = metadata["oof_metrics"]
        _, ci_low, ci_high = bootstrap_interval(
            REPORT_ROOT / version / "paired_bootstrap.csv"
        )
        decision, reason = DECISIONS[version]
        rows.append(
            {
                "version": version,
                "experiment": LABELS[version],
                "decision": decision,
                "macro_f1": metrics["macro_f1"],
                "delta_macro_f1": metadata["delta_vs_baseline"]["macro_f1"],
                "macro_pr_auc": metrics["macro_pr_auc"],
                "weakened_recall": metrics["weakened_recall"],
                "stopped_recall": metrics["stopped_recall"],
                "conditional_stopped_pr_auc": metrics[
                    "conditional_stopped_pr_auc"
                ],
                "severe_error_rate": metrics["severe_error_rate"],
                "retained_to_stopped_count": metrics["retained_to_stopped_count"],
                "stopped_to_retained_count": metrics["stopped_to_retained_count"],
                "precision_at_1000": metrics["mean_precision_at_1000"],
                "seed_macro_f1_std": metadata["seed_macro_f1_std"],
                "holdout_2017_macro_f1": metadata["internal_2017_holdout"][
                    "metrics"
                ]["macro_f1"],
                "bootstrap_ci_low": ci_low,
                "bootstrap_ci_high": ci_high,
                "final_test_rows": metadata["final_test_rows_loaded"],
                "reason": reason,
            }
        )

    summary = pd.DataFrame(rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUTPUT_DIR / "comparison.csv", index=False, encoding="utf-8-sig")
    (OUTPUT_DIR / "validation.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "baseline_version": BASELINE_VERSION,
                "ablation_versions": VERSIONS,
                "development_selection_years": [2010, 2017],
                "oof_validation_years": EXPECTED_YEARS,
                "seeds": EXPECTED_SEEDS,
                "development_samples_per_experiment": 31_420,
                "oof_samples_per_experiment": 24_596,
                "final_test_rows_loaded_or_scored": 0,
                "adopted_ablation_count": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    table_rows = []
    for row in rows:
        ci = "—"
        if not pd.isna(row["bootstrap_ci_low"]):
            ci = f"[{row['bootstrap_ci_low']:+.4f}, {row['bootstrap_ci_high']:+.4f}]"
        table_rows.append(
            "| {version} | {macro_f1:.4f} | {delta:+.4f} | {weak:.2%} | "
            "{stopped:.2%} | {state_auc:.4f} | {p_at_k:.2%} | {holdout:.4f} | "
            "{ci} | {decision} |".format(
                version=row["version"],
                macro_f1=row["macro_f1"],
                delta=row["delta_macro_f1"],
                weak=row["weakened_recall"],
                stopped=row["stopped_recall"],
                state_auc=row["conditional_stopped_pr_auc"],
                p_at_k=row["precision_at_1000"],
                holdout=row["holdout_2017_macro_f1"],
                ci=ci,
                decision=row["decision"],
            )
        )

    reasons = "\n".join(
        f"- `{version}`: **{DECISIONS[version][0]}** — {DECISIONS[version][1]}"
        for version in VERSIONS
    )
    report = f"""# v05_05_01~05 OOF ablation 종합 결과

## 결론

`v05_05_dl`을 현 개발 기준 모델로 유지한다. 다섯 ablation 중 독립 채택 조건을 충족한 실험은 없다.
`v05_05_05_dl`의 Macro F1이 +0.0002 상승했지만 사용자 단위 95% 신뢰구간이 0을 포함하고,
stopped Recall·조건부 stopped PR-AUC·Precision@1000이 모두 소폭 하락했다.

## 동일 조건 비교

| 버전 | Macro F1 | Δ F1 | Weakened Recall | Stopped Recall | 조건부 Stopped PR-AUC | P@1000 | 2017 F1 | Δ F1 95% CI | 판정 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
{chr(10).join(table_rows)}

## 실험별 판정

{reasons}

## 혼동행렬 해석

- 우측 상단(`actual retained → predicted stopped`)과 좌측 하단(`actual stopped → predicted retained`)을 중증 오분류로 함께 집계했다.
- 기준 모델은 각각 319건, 219건(합계 538건)이었다.
- 가장 적은 중증 오분류는 `v05_05_01_dl`의 524건이지만, stopped Recall이 43.25%에서 41.53%로 내려가므로 교체 근거가 되지 않는다.

## 검증 계약

- 개발 코호트: selection year 2010~2017, 31,420건
- OOF 검증: selection year 2013~2017 expanding-time 5-Fold × 3 seeds
- 각 실험 OOF ensemble: 24,596건, 기준 모델과 sample 순서 동일
- Final Test(selection year 2018 / target year 2019): 로드·예측·평가 모두 0건
- 본 결과는 최종 Test 승인 모델이 아니라 개발 OOF 실험 결과다.
"""
    (OUTPUT_DIR / "summary.md").write_text(report, encoding="utf-8")
    print(
        f"summary_rows={len(summary)}, adopted_ablation_count=0, "
        "final_test_rows=0, validation=passed"
    )


if __name__ == "__main__":
    main()
