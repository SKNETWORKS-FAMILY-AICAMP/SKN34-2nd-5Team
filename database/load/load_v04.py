from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


MODEL_VERSION = "v04"
EXPECTED_COHORT_ROWS = 37_953
EXPECTED_TEST_ROWS = 6_533
EXPECTED_CRM_TARGETS = 1_307
EXPECTED_TEST_STATE_COUNTS = {0: 2_584, 1: 3_065, 2: 884}
EXPECTED_TEST_NO_PRIOR = 1_692


@dataclass(frozen=True)
class SourcePaths:
    project_root: Path
    cohort: Path
    modeling: Path
    profiles: Path
    metadata: Path
    model: Path
    validation_metrics: Path
    topk_metrics: Path
    confusion_matrix: Path
    feature_importance: Path
    feature_group_importance: Path


@dataclass
class SourceBundle:
    paths: SourcePaths
    metadata: dict[str, Any]
    cohort: pd.DataFrame
    modeling: pd.DataFrame
    profiles: pd.DataFrame
    validation_metrics: pd.DataFrame
    topk_metrics: pd.DataFrame
    confusion_matrix: pd.DataFrame
    feature_importance: pd.DataFrame
    feature_group_importance: pd.DataFrame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="검증된 Yelp 리텐션 v04 산출물을 MySQL에 적재합니다."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="SKN34-2nd-5Team 프로젝트 루트",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="파일 계약만 검증하고 DB에는 연결하지 않습니다.",
    )
    parser.add_argument(
        "--apply-schema",
        action="store_true",
        help="적재 전에 database/ddl/001~007 SQL을 순서대로 실행합니다.",
    )
    parser.add_argument(
        "--confirm-database",
        help="실제 연결된 DB 이름과 정확히 일치해야 적재를 진행합니다.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1_000,
        help="MySQL 배치 적재 행 수",
    )
    return parser.parse_args()


def source_paths(project_root: Path) -> SourcePaths:
    root = project_root.resolve()
    return SourcePaths(
        project_root=root,
        cohort=(
            root
            / "data"
            / "interim"
            / "rolling"
            / "culinary_rolling_cohort_master_v04.parquet"
        ),
        modeling=root / "data" / "processed" / "modeling_dataset_rolling_v04.parquet",
        profiles=(
            root
            / "data"
            / "processed"
            / "predictions"
            / "final_test_retention_profiles_v04.parquet"
        ),
        metadata=root / "models" / "final_core_logistic_multiclass_metadata_v04.json",
        model=root / "models" / "final_core_logistic_multiclass_v04.joblib",
        validation_metrics=(
            root / "reports" / "tables" / "multiclass_validation_results_v04.csv"
        ),
        topk_metrics=(
            root / "reports" / "tables" / "multiclass_top_k_performance_v04.csv"
        ),
        confusion_matrix=(
            root / "reports" / "tables" / "multiclass_confusion_matrix_v04.csv"
        ),
        feature_importance=(
            root / "reports" / "tables" / "final_feature_importance_v04.csv"
        ),
        feature_group_importance=(
            root / "reports" / "tables" / "final_feature_group_importance_v04.csv"
        ),
    )


def require_files(paths: SourcePaths) -> None:
    missing = [
        str(path)
        for path in [
            paths.cohort,
            paths.modeling,
            paths.profiles,
            paths.metadata,
            paths.model,
            paths.validation_metrics,
            paths.topk_metrics,
            paths.confusion_matrix,
            paths.feature_importance,
            paths.feature_group_importance,
        ]
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError("필수 v04 파일 누락:\n- " + "\n- ".join(missing))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def assert_unique(frame: pd.DataFrame, name: str) -> None:
    if frame["sample_id"].isna().any():
        raise ValueError(f"{name}: sample_id NULL이 있습니다.")
    if not frame["sample_id"].is_unique:
        raise ValueError(f"{name}: sample_id가 중복됩니다.")


def assert_no_infinite(frame: pd.DataFrame, name: str) -> None:
    numeric = frame.select_dtypes(include=[np.number])
    infinite_cells = int(np.isinf(numeric.to_numpy(dtype=float)).sum())
    if infinite_cells:
        raise ValueError(f"{name}: 무한값 {infinite_cells}개가 있습니다.")


def load_and_validate(paths: SourcePaths) -> SourceBundle:
    require_files(paths)
    metadata = json.loads(paths.metadata.read_text(encoding="utf-8"))
    cohort = pd.read_parquet(paths.cohort)
    modeling = pd.read_parquet(paths.modeling)
    profiles = pd.read_parquet(paths.profiles)
    validation_metrics = pd.read_csv(paths.validation_metrics)
    topk_metrics = pd.read_csv(paths.topk_metrics)
    confusion_matrix = pd.read_csv(paths.confusion_matrix)
    feature_importance = pd.read_csv(paths.feature_importance)
    feature_group_importance = pd.read_csv(paths.feature_group_importance)

    if metadata.get("version") != MODEL_VERSION:
        raise ValueError("메타데이터 version이 v04가 아닙니다.")
    feature_columns = list(metadata.get("feature_columns", []))
    if len(feature_columns) != int(metadata.get("feature_count", -1)):
        raise ValueError("메타데이터 Core 피처 수가 43개가 아닙니다.")
    if len(feature_columns) != 43 or len(set(feature_columns)) != 43:
        raise ValueError("메타데이터 feature_columns가 정확한 43개 고유 피처가 아닙니다.")

    actual_model_sha = sha256(paths.model)
    if actual_model_sha != str(metadata.get("model_sha256", "")).lower():
        raise ValueError("joblib SHA256이 메타데이터와 다릅니다.")

    if len(cohort) != EXPECTED_COHORT_ROWS:
        raise ValueError(f"코호트 행 수가 {EXPECTED_COHORT_ROWS:,}이 아닙니다.")
    if len(modeling) != EXPECTED_COHORT_ROWS:
        raise ValueError(f"모델링 데이터 행 수가 {EXPECTED_COHORT_ROWS:,}이 아닙니다.")
    if len(profiles) != EXPECTED_TEST_ROWS:
        raise ValueError(f"프로필 행 수가 {EXPECTED_TEST_ROWS:,}이 아닙니다.")

    for name, frame in [
        ("cohort", cohort),
        ("modeling", modeling),
        ("profiles", profiles),
    ]:
        assert_unique(frame, name)
        assert_no_infinite(frame, name)

    if set(cohort["sample_id"]) != set(modeling["sample_id"]):
        raise ValueError("코호트와 모델링 데이터의 sample_id 집합이 다릅니다.")
    if not set(profiles["sample_id"]).issubset(set(cohort["sample_id"])):
        raise ValueError("프로필에 코호트에 없는 sample_id가 있습니다.")

    missing_modeling_features = set(feature_columns) - set(modeling.columns)
    missing_profile_features = set(feature_columns) - set(profiles.columns)
    if missing_modeling_features or missing_profile_features:
        raise ValueError(
            "Core 피처 누락: "
            f"modeling={sorted(missing_modeling_features)}, "
            f"profiles={sorted(missing_profile_features)}"
        )

    test_year = int(metadata["test_selection_year"])
    target_year = int(metadata["test_target_year"])
    if not profiles["selection_year"].eq(test_year).all():
        raise ValueError("프로필 selection_year가 메타데이터와 다릅니다.")
    if not profiles["target_year"].eq(target_year).all():
        raise ValueError("프로필 target_year가 메타데이터와 다릅니다.")
    if int(metadata["test_samples"]) != len(profiles):
        raise ValueError("메타데이터 test_samples가 프로필 행 수와 다릅니다.")

    state_counts = {
        int(key): int(value)
        for key, value in profiles["retention_state"].value_counts().items()
    }
    if state_counts != EXPECTED_TEST_STATE_COUNTS:
        raise ValueError(f"Test 실제 상태 분포가 다릅니다: {state_counts}")
    if int(profiles["selected_for_crm"].sum()) != EXPECTED_CRM_TARGETS:
        raise ValueError("Top 20% 관리 대상 수가 1,307명이 아닙니다.")
    if int(profiles["prior_activity_available"].eq(0).sum()) != EXPECTED_TEST_NO_PRIOR:
        raise ValueError("Test 비교 활동 없음 표본이 1,692명이 아닙니다.")

    if len(feature_importance) != 43:
        raise ValueError("개별 피처 중요도가 43행이 아닙니다.")
    if set(feature_importance["feature"]) != set(feature_columns):
        raise ValueError("피처 중요도와 metadata feature_columns가 다릅니다.")
    if int(feature_group_importance["feature_count"].sum()) != 43:
        raise ValueError("그룹 중요도 feature_count 합이 43이 아닙니다.")

    final_validation = validation_metrics.loc[
        validation_metrics["record_type"].eq("final_test")
    ]
    if len(final_validation) != 1:
        raise ValueError("검증 결과의 final_test 행이 정확히 1개가 아닙니다.")
    if not np.isclose(
        float(final_validation.iloc[0]["macro_pr_auc"]),
        float(metadata["test_metrics"]["macro_pr_auc"]),
    ):
        raise ValueError("검증 CSV와 메타데이터의 Test Macro PR-AUC가 다릅니다.")

    top20 = topk_metrics.loc[
        topk_metrics["split"].eq("final_test")
        & topk_metrics["ranking"].eq("unified")
        & np.isclose(topk_metrics["target_rate"], 0.20)
    ]
    if len(top20) != 1 or int(top20.iloc[0]["target_users"]) != EXPECTED_CRM_TARGETS:
        raise ValueError("Top-K CSV의 final_test 통합 Top 20% 계약이 다릅니다.")

    final_confusion = confusion_matrix.loc[
        confusion_matrix["split"].eq("final_test")
    ]
    if len(final_confusion) != 9 or int(final_confusion["users"].sum()) != len(
        profiles
    ):
        raise ValueError("최종 혼동행렬이 9행/6,533명 계약과 다릅니다.")

    return SourceBundle(
        paths=paths,
        metadata=metadata,
        cohort=cohort,
        modeling=modeling,
        profiles=profiles,
        validation_metrics=validation_metrics,
        topk_metrics=topk_metrics,
        confusion_matrix=confusion_matrix,
        feature_importance=feature_importance,
        feature_group_importance=feature_group_importance,
    )


def validation_summary(bundle: SourceBundle) -> dict[str, Any]:
    profiles = bundle.profiles
    return {
        "model_version": bundle.metadata["version"],
        "model_sha256": bundle.metadata["model_sha256"],
        "feature_count": bundle.metadata["feature_count"],
        "cohort_rows": len(bundle.cohort),
        "modeling_rows": len(bundle.modeling),
        "profile_rows": len(profiles),
        "test_selection_year": int(profiles["selection_year"].iloc[0]),
        "test_target_year": int(profiles["target_year"].iloc[0]),
        "test_state_counts": {
            str(int(key)): int(value)
            for key, value in profiles["retention_state"]
            .value_counts()
            .sort_index()
            .items()
        },
        "crm_target_users": int(profiles["selected_for_crm"].sum()),
        "test_no_prior_activity": int(
            profiles["prior_activity_available"].eq(0).sum()
        ),
    }


def load_dotenv_if_available(project_root: Path) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(project_root / "database" / ".env")


def create_engine_from_env(project_root: Path):
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.engine import URL
    except ImportError as error:
        raise RuntimeError(
            "DB 패키지가 없습니다. "
            "pip install -r database/requirements-db.txt를 먼저 실행하세요."
        ) from error

    load_dotenv_if_available(project_root)
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return create_engine(database_url, future=True, pool_pre_ping=True)

    required = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [key for key in required if os.getenv(key) is None]
    if missing:
        raise RuntimeError("DB 환경변수 누락: " + ", ".join(missing))

    url = URL.create(
        drivername="mysql+pymysql",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.environ["DB_NAME"],
        query={"charset": os.getenv("DB_CHARSET", "utf8mb4")},
    )
    return create_engine(url, future=True, pool_pre_ping=True)


def sql_statements(path: Path) -> list[str]:
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("--")
    ]
    return [
        statement.strip()
        for statement in "\n".join(lines).split(";")
        if statement.strip()
    ]


def apply_schema(connection, project_root: Path) -> None:
    ddl_dir = project_root / "database" / "ddl"
    ddl_files = sorted(path for path in ddl_dir.glob("*.sql") if path.name != "000_create_database.sql")
    if not ddl_files:
        raise RuntimeError("database/ddl SQL 파일이 없습니다.")
    for path in ddl_files:
        for statement in sql_statements(path):
            connection.exec_driver_sql(statement)
        print(f"schema applied: {path.name}")


def database_name(connection) -> str:
    return str(connection.exec_driver_sql("SELECT DATABASE()").scalar_one())


def assert_clean_target(connection, model_version: str) -> None:
    tables = [
        "model_versions",
        "cohort_samples",
        "reviewer_features",
        "validation_outcomes",
        "model_predictions",
        "model_validation_metrics",
        "model_topk_metrics",
        "model_confusion_matrix",
        "feature_importance",
        "feature_group_importance",
    ]
    occupied: dict[str, int] = {}
    for table in tables:
        count = int(
            connection.exec_driver_sql(
                f"SELECT COUNT(*) FROM {table} WHERE model_version = %s",
                (model_version,),
            ).scalar_one()
        )
        if count:
            occupied[table] = count
    if occupied:
        raise RuntimeError(
            "이미 v04 데이터가 있어 안전상 중단합니다. 자동 삭제/덮어쓰기는 하지 않습니다: "
            + json.dumps(occupied, ensure_ascii=False)
        )


def nullable(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.astype(object).where(pd.notna(frame), None)


def frames_for_mysql(bundle: SourceBundle) -> list[tuple[str, pd.DataFrame]]:
    metadata = bundle.metadata
    feature_columns = list(metadata["feature_columns"])

    model_versions = pd.DataFrame(
        [
            {
                "model_version": metadata["version"],
                "model_name": metadata["model_name"],
                "model_type": metadata["model_type"],
                "problem_type": metadata["problem_type"],
                "feature_set": metadata["feature_set"],
                "feature_count": metadata["feature_count"],
                "test_selection_year": metadata["test_selection_year"],
                "test_target_year": metadata["test_target_year"],
                "test_samples": metadata["test_samples"],
                "priority_target_rate": metadata["priority_policy"][
                    "primary_target_rate"
                ],
                "model_sha256": metadata["model_sha256"],
                "python_version": metadata.get("python_version"),
                "sklearn_version": metadata.get("sklearn_version"),
                "pandas_version": metadata.get("pandas_version"),
                "model_parameters": json.dumps(
                    metadata["model_parameters"], ensure_ascii=False
                ),
                "decision_thresholds": json.dumps(
                    metadata["decision_thresholds"], ensure_ascii=False
                ),
                "metadata_json": json.dumps(metadata, ensure_ascii=False),
            }
        ]
    )

    cohort_samples = bundle.cohort[
        [
            "sample_id",
            "user_id",
            "comparison_year",
            "selection_year",
            "target_year",
            "prior_activity_available",
            "scope",
            "split_v04",
        ]
    ].copy()
    cohort_samples.insert(0, "model_version", MODEL_VERSION)

    reviewer_features = bundle.modeling[["sample_id", *feature_columns]].copy()
    reviewer_features.insert(0, "model_version", MODEL_VERSION)

    validation_outcomes = bundle.cohort[
        [
            "sample_id",
            "target_review_count",
            "target_active_months",
            "retention_state",
            "churn",
        ]
    ].copy()
    validation_outcomes.insert(0, "model_version", MODEL_VERSION)

    prediction_columns = [
        "sample_id",
        "retained_score",
        "weakened_score",
        "stopped_score",
        "priority_score",
        "predicted_state",
        "predicted_state_label",
        "priority_rank",
        "priority_top_percent",
        "selected_for_crm",
    ]
    model_predictions = bundle.profiles[prediction_columns].copy()
    model_predictions.insert(0, "model_version", MODEL_VERSION)

    validation_metrics = bundle.validation_metrics.copy()
    validation_metrics.insert(0, "model_version", MODEL_VERSION)

    topk_metrics = bundle.topk_metrics.copy()
    topk_metrics.insert(0, "model_version", MODEL_VERSION)

    confusion_matrix = bundle.confusion_matrix.copy()
    confusion_matrix.insert(0, "model_version", MODEL_VERSION)

    feature_importance = bundle.feature_importance.rename(
        columns={"rank": "rank_no"}
    ).copy()
    feature_importance = feature_importance[
        [
            "model_version",
            "split",
            "feature",
            "rank_no",
            "feature_group",
            "feature_group_label",
            "importance_mean",
            "importance_std",
            "importance_share_pct",
            "baseline_pr_auc",
            "metric",
            "method",
            "repeats",
        ]
    ]

    feature_group_importance = bundle.feature_group_importance.rename(
        columns={"rank": "rank_no"}
    ).copy()
    feature_group_importance = feature_group_importance[
        [
            "model_version",
            "split",
            "feature_group",
            "feature_count",
            "rank_no",
            "feature_group_label",
            "importance_mean",
            "importance_std",
            "baseline_pr_auc",
            "metric",
            "method",
            "repeats",
        ]
    ]

    return [
        ("model_versions", model_versions),
        ("cohort_samples", cohort_samples),
        ("reviewer_features", reviewer_features),
        ("validation_outcomes", validation_outcomes),
        ("model_predictions", model_predictions),
        ("model_validation_metrics", validation_metrics),
        ("model_topk_metrics", topk_metrics),
        ("model_confusion_matrix", confusion_matrix),
        ("feature_importance", feature_importance),
        ("feature_group_importance", feature_group_importance),
    ]


def load_mysql(bundle: SourceBundle, args: argparse.Namespace) -> None:
    if not args.confirm_database:
        raise RuntimeError(
            "오적재 방지를 위해 --confirm-database에 대상 DB 이름을 입력해야 합니다."
        )
    engine = create_engine_from_env(bundle.paths.project_root)
    try:
        if args.apply_schema:
            with engine.begin() as connection:
                actual_database = database_name(connection)
                if actual_database != args.confirm_database:
                    raise RuntimeError(
                        f"연결 DB({actual_database})와 확인값"
                        f"({args.confirm_database})이 다릅니다."
                    )
                apply_schema(connection, bundle.paths.project_root)

        with engine.begin() as connection:
            actual_database = database_name(connection)
            if actual_database != args.confirm_database:
                raise RuntimeError(
                    f"연결 DB({actual_database})와 확인값"
                    f"({args.confirm_database})이 다릅니다."
                )
            assert_clean_target(connection, MODEL_VERSION)
            for table_name, frame in frames_for_mysql(bundle):
                nullable(frame).to_sql(
                    table_name,
                    con=connection,
                    if_exists="append",
                    index=False,
                    chunksize=args.chunk_size,
                    method="multi",
                )
                print(f"loaded: {table_name} ({len(frame):,} rows)")
    finally:
        engine.dispose()


def main() -> int:
    args = parse_args()
    paths = source_paths(args.project_root)
    try:
        bundle = load_and_validate(paths)
        print(json.dumps(validation_summary(bundle), ensure_ascii=False, indent=2))
        if args.dry_run:
            print("dry-run complete: DB 변경 없음")
            return 0
        load_mysql(bundle, args)
        print("v04 MySQL load complete")
        return 0
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
