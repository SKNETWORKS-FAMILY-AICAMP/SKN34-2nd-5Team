"""검증된 v05_05_dl(Lifecycle Fusion H2) Test 산출물을 MySQL에 적재한다.

v04(`load_v04.py`)와 같은 model_versions/cohort_samples/reviewer_features/
validation_outcomes/model_predictions 스키마를 그대로 쓴다. v05_05_dl은 v04와
달리 별도의 코호트·모델링 parquet 대신, 코호트·43개 v04 스타일 피처·예측 점수를
모두 담은 단일 Test 프로필 parquet
(`data/processed/predictions/test_retention_profiles_v05_05_dl.parquet`)에서
값을 가져온다. 이 parquet는 `pipeline/v05_05_dl/evaluate_test.py`가 생성한다.

reviewer_region·reviewer_monthly_activity는 v05_05_dl 전용 파일이 없다. 같은
2018 선정연도 6,533명 코호트가 v04와 완전히 동일해(sample_id 집합 일치를 이 스크립트가
직접 검증한다) v04 산출물(`reviewer_region_v04.parquet`,
`reviewer_monthly_activity_v04.parquet`)을 model_version만 바꿔 재사용한다.

model_validation_metrics/model_topk_metrics/model_confusion_matrix와
feature_importance/feature_group_importance는 이 스크립트가 다루지 않는다. 전자는
v05_05_dl의 `evaluate()`가 클래스별 ROC-AUC를 계산하지 않아 DDL의 NOT NULL 컬럼과
맞지 않고, 후자는 순열 중요도 산출물이 아직 없다. Trust Center의 모델별 상세 지표
비교는 이 값들이 채워지기 전까지 v05_05_dl 행이 비어 있는 채로 유지된다.

v05/database/load/가 아니라 이 경로(database/load/)에 두는 이유: v05/는 README에
명시된 대로 spatial·recommendation·운영 테이블 같은 "v04 정의를 바꾸지 않는 파생
데이터"만 다룬다. model_versions/cohort_samples/model_predictions은 v02~v04가 이미
쓰고 있는 핵심 모델 스키마이므로 그 짝인 database/load/에 속한다.
"""

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


MODEL_VERSION = "v05_05_dl"
EXPECTED_TEST_ROWS = 6_533
EXPECTED_TEST_STATE_COUNTS = {0: 2_584, 1: 3_065, 2: 884}
EXPECTED_CRM_TARGETS = 1_307
EXPECTED_TEST_NO_PRIOR = 1_692
CLASS_LABELS_KO = {0: "파워 지위 유지", 1: "파워 지위 약화", 2: "리뷰 활동 중단"}


@dataclass(frozen=True)
class SourcePaths:
    project_root: Path
    profile: Path
    test_metrics: Path
    config: Path
    v04_feature_metadata: Path
    reviewer_region: Path
    monthly_activity: Path


@dataclass
class SourceBundle:
    paths: SourcePaths
    test_metrics: dict[str, Any]
    config: dict[str, Any]
    feature_columns: list[str]
    profile: pd.DataFrame
    reviewer_region: pd.DataFrame
    monthly_activity: pd.DataFrame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="검증된 v05_05_dl(Lifecycle Fusion H2) Test 산출물을 MySQL에 적재합니다."
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
        help="적재 전에 database/ddl/001~010 SQL을 순서대로 실행합니다.",
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
        profile=(
            root
            / "data"
            / "processed"
            / "predictions"
            / "test_retention_profiles_v05_05_dl.parquet"
        ),
        test_metrics=root / "reports" / "experiments" / "v05_05_dl" / "test_metrics.json",
        config=root / "pipeline" / "v05_05_dl" / "config.json",
        v04_feature_metadata=(
            root / "models" / "final_core_logistic_multiclass_metadata_v04.json"
        ),
        reviewer_region=root / "data" / "processed" / "reviewer_region_v04.parquet",
        monthly_activity=(
            root / "data" / "processed" / "reviewer_monthly_activity_v04.parquet"
        ),
    )


def require_files(paths: SourcePaths) -> None:
    missing = [
        str(path)
        for path in [
            paths.profile,
            paths.test_metrics,
            paths.config,
            paths.v04_feature_metadata,
            paths.reviewer_region,
            paths.monthly_activity,
        ]
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError("필수 v05_05_dl 파일 누락:\n- " + "\n- ".join(missing))


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
    test_metrics = json.loads(paths.test_metrics.read_text(encoding="utf-8"))
    config = json.loads(paths.config.read_text(encoding="utf-8"))
    v04_metadata = json.loads(paths.v04_feature_metadata.read_text(encoding="utf-8"))
    feature_columns = list(v04_metadata.get("feature_columns", []))
    if len(feature_columns) != 43 or len(set(feature_columns)) != 43:
        raise ValueError("v04 feature_columns가 정확한 43개 고유 피처가 아닙니다.")

    profile = pd.read_parquet(paths.profile)
    reviewer_region = pd.read_parquet(paths.reviewer_region)
    monthly_activity = pd.read_parquet(paths.monthly_activity)

    if test_metrics.get("version") != MODEL_VERSION:
        raise ValueError("test_metrics.json version이 v05_05_dl이 아닙니다.")
    if config.get("version") != MODEL_VERSION:
        raise ValueError("config.json version이 v05_05_dl이 아닙니다.")

    if len(profile) != EXPECTED_TEST_ROWS:
        raise ValueError(f"Test 프로필 행 수가 {EXPECTED_TEST_ROWS:,}이 아닙니다.")
    assert_unique(profile, "profile")
    assert_no_infinite(profile, "profile")

    missing_features = set(feature_columns) - set(profile.columns)
    if missing_features:
        raise ValueError(f"Test 프로필에 v04 스타일 피처가 없습니다: {sorted(missing_features)}")

    test_year = int(test_metrics["selection_year"])
    target_year = int(test_metrics["target_year"])
    if not profile["selection_year"].eq(test_year).all():
        raise ValueError("프로필 selection_year가 test_metrics.json과 다릅니다.")
    if not profile["target_year"].eq(target_year).all():
        raise ValueError("프로필 target_year가 test_metrics.json과 다릅니다.")
    if int(test_metrics["test_samples"]) != len(profile):
        raise ValueError("test_metrics.json test_samples가 프로필 행 수와 다릅니다.")

    state_counts = {
        int(key): int(value) for key, value in profile["retention_state"].value_counts().items()
    }
    if state_counts != EXPECTED_TEST_STATE_COUNTS:
        raise ValueError(f"Test 실제 상태 분포가 v04와 다릅니다: {state_counts}")
    if int(profile["selected_for_crm"].sum()) != EXPECTED_CRM_TARGETS:
        raise ValueError("Top 20% 관리 대상 수가 1,307명이 아닙니다.")
    if int(profile["prior_activity_available"].eq(0).sum()) != EXPECTED_TEST_NO_PRIOR:
        raise ValueError("Test 비교 활동 없음 표본이 1,692명이 아닙니다.")

    # v05_05_dl 전용 reviewer_region/monthly_activity가 없어 v04 것을 재사용한다.
    # 재사용이 안전한지(같은 6,533명 코호트인지)를 여기서 직접 검증한다.
    if set(reviewer_region["sample_id"]) != set(profile["sample_id"]):
        raise ValueError("reviewer_region_v04의 sample_id 집합이 v05_05_dl Test와 다릅니다.")
    if not set(monthly_activity["sample_id"]).issubset(set(profile["sample_id"])):
        raise ValueError("reviewer_monthly_activity_v04에 v05_05_dl Test에 없는 sample_id가 있습니다.")

    return SourceBundle(
        paths=paths,
        test_metrics=test_metrics,
        config=config,
        feature_columns=feature_columns,
        profile=profile,
        reviewer_region=reviewer_region,
        monthly_activity=monthly_activity,
    )


def validation_summary(bundle: SourceBundle) -> dict[str, Any]:
    profile = bundle.profile
    return {
        "model_version": MODEL_VERSION,
        "profile_rows": len(profile),
        "test_selection_year": int(profile["selection_year"].iloc[0]),
        "test_target_year": int(profile["target_year"].iloc[0]),
        "test_state_counts": {
            str(int(key)): int(value)
            for key, value in profile["retention_state"].value_counts().sort_index().items()
        },
        "crm_target_users": int(profile["selected_for_crm"].sum()),
        "test_no_prior_activity": int(profile["prior_activity_available"].eq(0).sum()),
        "reviewer_region_rows": len(bundle.reviewer_region),
        "monthly_activity_rows": len(bundle.monthly_activity),
        "test_macro_f1": bundle.test_metrics["test_metrics"]["macro_f1"],
        "test_macro_pr_auc": bundle.test_metrics["test_metrics"]["macro_pr_auc"],
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
            try:
                connection.exec_driver_sql(statement)
            except Exception as error:
                original = getattr(error, "orig", None)
                args = getattr(original, "args", ())
                error_code = args[0] if args else None
                if error_code == 1061:
                    print(f"schema already applied: duplicate index in {path.name}")
                    continue
                raise
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
        "reviewer_region",
        "reviewer_monthly_activity",
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
            "이미 v05_05_dl 데이터가 있어 안전상 중단합니다. 자동 삭제/덮어쓰기는 하지 않습니다: "
            + json.dumps(occupied, ensure_ascii=False)
        )


def nullable(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.astype(object).where(pd.notna(frame), None)


def composite_model_sha256(bundle: SourceBundle) -> str:
    artifacts = bundle.test_metrics["model_artifacts"]
    parts = [artifacts["preprocessing_sha256"]] + [
        artifacts["weight_sha256"][str(seed)] for seed in sorted(bundle.config["seeds"])
    ]
    return hashlib.sha256("|".join(parts).encode("ascii")).hexdigest()


def frames_for_mysql(bundle: SourceBundle) -> list[tuple[str, pd.DataFrame]]:
    profile = bundle.profile
    test_metrics = bundle.test_metrics
    config = bundle.config
    feature_columns = bundle.feature_columns

    model_versions = pd.DataFrame(
        [
            {
                "model_version": MODEL_VERSION,
                "model_name": "Lifecycle Fusion H2 (Core4 GRU + Lifecycle MLP)",
                "model_type": "pytorch_gru_mlp_hierarchical",
                "problem_type": "multiclass_classification",
                # "4 GRU + 5 MLP": GRU 브랜치가 받는 월별 시퀀스 채널 4개(24개월),
                # MLP 브랜치가 받는 Lifecycle 피처 5개. reviewer_features에 저장하는
                # 43개 v04 스타일 컬럼은 근거·증거 표시용으로 재사용하는 것일 뿐
                # 모델 입력이 아니므로 여기 섞지 않는다.
                "feature_set": (
                    f"{len(config['sequence_channels'])} GRU + "
                    f"{len(config['lifecycle_features'])} MLP"
                ),
                "feature_count": len(config["sequence_channels"]) + len(config["lifecycle_features"]),
                "test_selection_year": test_metrics["selection_year"],
                "test_target_year": test_metrics["target_year"],
                "test_samples": test_metrics["test_samples"],
                "priority_target_rate": 0.20,
                "model_sha256": composite_model_sha256(bundle),
                "python_version": test_metrics["runtime"].get("python_version"),
                "sklearn_version": test_metrics["runtime"].get("sklearn_version"),
                "pandas_version": test_metrics["runtime"].get("pandas_version"),
                "model_parameters": json.dumps(config["model"], ensure_ascii=False),
                "decision_thresholds": json.dumps(test_metrics["thresholds"], ensure_ascii=False),
                "metadata_json": json.dumps(
                    {"config": config, "test_metrics": test_metrics}, ensure_ascii=False
                ),
            }
        ]
    )

    cohort_samples = profile[
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

    reviewer_features = profile[["sample_id", *feature_columns]].copy()
    reviewer_features.insert(0, "model_version", MODEL_VERSION)

    validation_outcomes = profile[
        ["sample_id", "target_review_count", "target_active_months", "retention_state", "churn"]
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
    model_predictions = profile[prediction_columns].copy()
    model_predictions.insert(0, "model_version", MODEL_VERSION)

    reviewer_region = bundle.reviewer_region[["sample_id", "state", "top_city"]].copy()
    reviewer_region.insert(0, "model_version", MODEL_VERSION)

    monthly_activity = bundle.monthly_activity[
        ["sample_id", "year_month", "review_count", "unique_business_count"]
    ].copy()
    monthly_activity.insert(0, "model_version", MODEL_VERSION)

    return [
        ("model_versions", model_versions),
        ("cohort_samples", cohort_samples),
        ("reviewer_features", reviewer_features),
        ("validation_outcomes", validation_outcomes),
        ("model_predictions", model_predictions),
        ("reviewer_region", reviewer_region),
        ("reviewer_monthly_activity", monthly_activity),
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
        print("v05_05_dl MySQL load complete")
        return 0
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
