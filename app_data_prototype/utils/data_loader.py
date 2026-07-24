from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st


VERSION = "v01"


def find_project_root() -> Path:
    configured = os.getenv("YELP_PROJECT_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()

    module_root = Path(__file__).resolve().parents[2]
    candidates = [Path.cwd().resolve(), module_root, *Path.cwd().resolve().parents]
    for candidate in candidates:
        if (candidate / "data" / "interim").exists():
            return candidate
    return module_root


def _merge_features(base: pd.DataFrame, feature_path: Path) -> pd.DataFrame:
    if not feature_path.exists():
        return base
    feature = pd.read_parquet(feature_path)
    drop_columns = [column for column in ("churn",) if column in feature.columns]
    feature = feature.drop(columns=drop_columns)
    duplicate_columns = [
        column for column in feature.columns if column != "user_id" and column in base.columns
    ]
    feature = feature.drop(columns=duplicate_columns)
    return base.merge(feature, on="user_id", how="left", validate="one_to_one")


def _default_decisions() -> pd.DataFrame:
    rows = [
        ("리뷰 활동량", "review_count_decline_rate", "채택", "P0", "이탈자 리뷰 감소율이 크게 나타남"),
        ("리뷰 활동량", "active_month_decline_rate", "채택", "P0", "활동 월수 감소가 뚜렷함"),
        ("작성 간격", "recent_mean_interval_days", "채택", "P0", "이탈자의 작성 간격 증가"),
        ("작성 간격", "recent_recency_days", "채택", "P0", "이탈자의 최근 활동 공백 증가"),
        ("신규 음식점", "new_business_rate_decline", "제외", "-", "활동량 통제 후 집단 차이가 작음"),
        ("카테고리", "category_entropy_decline", "제외", "-", "리뷰 수 구간 통제 후 차이가 사라짐"),
        ("탐방 반경", "log_p90_radius_decline", "실험용", "P1", "구간별 방향이 일관되지 않음"),
        ("활동 중심지", "log_center_shift", "보조 후보", "P1", "장거리 이동 비율이 이탈자에게 높음"),
        ("평점", "mean_rating_change", "보조 후보", "P1", "이탈자의 평균 평점이 소폭 하락"),
        ("리뷰 반응", "useful/cool/funny", "제외", "-", "반응 시점 부재로 미래 정보 누수 위험"),
    ]
    return pd.DataFrame(
        rows, columns=["feature_group", "feature", "decision", "priority", "reason"]
    )


def _demo_data(seed: int = 42) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    users = 720
    churn = np.zeros(users, dtype=np.int8)
    churn[rng.choice(users, size=112, replace=False)] = 1
    user_ids = [f"reviewer_{index:04d}" for index in range(users)]

    baseline_reviews = np.maximum(10, rng.negative_binomial(8, 0.35, users))
    decline = np.where(churn == 1, rng.beta(5, 3, users), rng.beta(2, 7, users))
    recent_reviews = np.maximum(1, np.round(baseline_reviews * (1 - decline))).astype(int)
    baseline_months = np.clip(rng.normal(7, 2, users).round(), 3, 12).astype(int)
    recent_months = np.maximum(
        1, np.round(baseline_months * (1 - np.where(churn == 1, 0.35, 0.08)))
    ).astype(int)

    features = pd.DataFrame(
        {
            "user_id": user_ids,
            "churn": churn,
            "baseline_review_count": baseline_reviews,
            "recent_review_count": recent_reviews,
            "review_count_decline_rate": decline,
            "baseline_active_months": baseline_months,
            "recent_active_months": recent_months,
            "active_month_decline_rate": (baseline_months - recent_months) / baseline_months,
            "recent_mean_interval_days": np.where(
                churn == 1, rng.normal(48, 18, users), rng.normal(32, 14, users)
            ).clip(1),
            "mean_interval_increase_days": np.where(
                churn == 1, rng.normal(30, 20, users), rng.normal(15, 15, users)
            ),
            "recent_recency_days": np.where(
                churn == 1, rng.normal(93, 35, users), rng.normal(46, 28, users)
            ).clip(0),
            "recent_interval_available": (recent_reviews >= 2).astype(np.int8),
            "unique_business_decline_rate": np.clip(decline + rng.normal(0, 0.04, users), -1, 1),
            "unique_category_decline_rate": np.clip(decline * 0.75 + rng.normal(0, 0.12, users), -1, 1),
            "log_p90_radius_decline": np.where(
                churn == 1, rng.normal(0.15, 0.8, users), rng.normal(0.05, 0.7, users)
            ),
            "log_center_shift": np.where(
                churn == 1, rng.normal(2.0, 1.0, users), rng.normal(1.5, 0.8, users)
            ).clip(0),
            "mean_rating_change": np.where(
                churn == 1, rng.normal(-0.07, 0.4, users), rng.normal(0.02, 0.3, users)
            ),
            "low_rating_rate_increase": np.where(
                churn == 1, rng.normal(0.05, 0.13, users), rng.normal(0.006, 0.08, users)
            ),
        }
    )

    month_rows: list[dict[str, Any]] = []
    months = pd.period_range("2017-01", "2018-12", freq="M")
    sample_users = user_ids[:180]
    for user_id in sample_users:
        row = features.loc[features["user_id"] == user_id].iloc[0]
        for index, month in enumerate(months):
            base = row["baseline_review_count"] / 12
            if index >= 12:
                base = row["recent_review_count"] / 12
            count = max(0, int(rng.poisson(max(base, 0.1))))
            for review_index in range(count):
                period = "baseline" if index < 12 else "recent"
                month_rows.append(
                    {
                        "user_id": user_id,
                        "period": period,
                        "date": month.to_timestamp() + pd.Timedelta(days=int(rng.integers(0, 25))),
                        "business_id": f"biz_{rng.integers(1, 4000):04d}",
                        "stars": float(rng.integers(2, 6)),
                        "latitude": 39.9526 + rng.normal(0, 0.06),
                        "longitude": -75.1652 + rng.normal(0, 0.07),
                        "city": "Philadelphia",
                        "state": "PA",
                    }
                )
    observation = pd.DataFrame(month_rows)
    cohort = features[["user_id", "churn", "baseline_review_count", "recent_review_count"]].copy()
    return {
        "cohort": cohort,
        "features": features,
        "decisions": _default_decisions(),
        "observation": observation,
        "metadata": {
            "restaurant_businesses": 52_268,
            "restaurant_reviews": 4_724_471,
            "restaurant_users": 1_445_990,
            "power_reviewers": 5_511,
        },
    }


@st.cache_data(show_spinner=False)
def load_bundle() -> tuple[dict[str, Any], bool, Path]:
    root = find_project_root()
    interim = root / "data" / "interim"
    cohort_path = interim / f"power_reviewer_cohort_{VERSION}.parquet"
    if not cohort_path.exists():
        return _demo_data(), True, root

    cohort = pd.read_parquet(cohort_path)
    features = cohort[["user_id", "churn"]].copy()
    feature_dir = interim / "features"
    feature_names = [
        "activity",
        "interval",
        "historical_exploration",
        "category",
        "spatial",
        "rating",
    ]
    for name in feature_names:
        features = _merge_features(
            features, feature_dir / f"{name}_features_{VERSION}.parquet"
        )

    decisions_path = root / "reports" / "tables" / f"feature_feasibility_decisions_{VERSION}.csv"
    decisions = pd.read_csv(decisions_path) if decisions_path.exists() else _default_decisions()

    metadata = {
        "restaurant_businesses": 52_268,
        "restaurant_reviews": 4_724_471,
        "restaurant_users": 1_445_990,
        "power_reviewers": 5_511,
    }
    return {
        "cohort": cohort,
        "features": features,
        "decisions": decisions,
        "metadata": metadata,
    }, False, root


@st.cache_data(show_spinner="리뷰어 활동 데이터를 불러오는 중입니다...")
def load_observation(root_string: str) -> pd.DataFrame:
    root = Path(root_string)
    path = root / "data" / "interim" / f"cohort_observation_reviews_{VERSION}.parquet"
    if path.exists():
        frame = pd.read_parquet(path)
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        return frame
    return _demo_data()["observation"]
