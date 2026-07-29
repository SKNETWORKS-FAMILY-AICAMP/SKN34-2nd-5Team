from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from database.load.historical_metrics import (  # noqa: E402
    HistoricalMetricBundle,
    load_v02_bundle,
    load_v03_bundle,
)
from database.load.load_v04 import (  # noqa: E402
    SourceBundle,
    apply_schema,
    create_engine_from_env,
    database_name,
    frames_for_mysql,
    load_and_validate,
    nullable,
    source_paths,
    validation_summary,
)
from database.load.seed_reference_data import (  # noqa: E402
    build_reference_rows,
    load_source,
    seed_reference_data,
)


TARGET_DATABASE = "yelp_data"
MODEL_VERSIONS = ("v04", "v03", "v02")
REFERENCE_TABLES = (
    "retention_playbooks",
    "retention_playbook_risk_actions",
)
EMPTY_OPERATION_TABLES = ("operator_decisions",)


@dataclass
class YelpDataBundle:
    project_root: Path
    frames: list[tuple[str, pd.DataFrame]]
    parent_rows: list[dict[str, Any]]
    risk_action_rows: list[dict[str, Any]]
    source_summaries: dict[str, dict[str, Any]]
    expected_version_counts: dict[str, dict[str, int]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "빈 yelp_data DB에 v04 운영 데이터, v03/v02 Trust Center 비교 "
            "지표와 리텐션 플레이북 기준정보를 빠짐없이 적재합니다."
        )
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
        help="모든 원본 파일 계약과 예상 적재 건수만 검증하고 DB에는 연결하지 않습니다.",
    )
    parser.add_argument(
        "--confirm-database",
        help="yelp_data를 정확히 입력해야 실제 적재를 진행합니다.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1_000,
        help="MySQL 배치 적재 행 수",
    )
    return parser.parse_args()


def expected_counts_for_frames(
    frames: list[tuple[str, pd.DataFrame]],
) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for table_name, frame in frames:
        if "model_version" not in frame.columns:
            raise ValueError(f"{table_name}: model_version 컬럼이 없습니다.")
        versions = frame["model_version"].dropna().astype(str)
        if len(versions) != len(frame):
            raise ValueError(f"{table_name}: model_version NULL이 있습니다.")
        for model_version, row_count in versions.value_counts().items():
            counts[table_name][model_version] += int(row_count)
    return {
        table_name: dict(sorted(version_counts.items()))
        for table_name, version_counts in sorted(counts.items())
    }


def validate_expected_contract(
    expected_version_counts: dict[str, dict[str, int]],
) -> None:
    expected_versions = {version: 1 for version in sorted(MODEL_VERSIONS)}
    if expected_version_counts.get("model_versions") != expected_versions:
        raise ValueError(
            "전체 적재 모델 버전 계약이 v02/v03/v04 각 1행과 다릅니다: "
            + json.dumps(
                expected_version_counts.get("model_versions", {}),
                ensure_ascii=False,
            )
        )

    required_version_tables = {
        "v04": {
            "cohort_samples",
            "reviewer_features",
            "validation_outcomes",
            "model_predictions",
            "reviewer_region",
            "reviewer_monthly_activity",
            "model_validation_metrics",
            "model_topk_metrics",
            "model_confusion_matrix",
            "feature_importance",
            "feature_group_importance",
        },
        "v03": {
            "model_validation_metrics",
            "model_topk_metrics",
            "model_confusion_matrix",
            "feature_importance",
            "feature_group_importance",
        },
        "v02": {
            "model_binary_validation_metrics",
            "model_binary_topk_metrics",
            "model_confusion_matrix",
            "feature_importance",
            "feature_group_importance",
        },
    }
    missing: dict[str, list[str]] = {}
    for model_version, required_tables in required_version_tables.items():
        missing_tables = sorted(
            table_name
            for table_name in required_tables
            if expected_version_counts.get(table_name, {}).get(model_version, 0)
            <= 0
        )
        if missing_tables:
            missing[model_version] = missing_tables
    if missing:
        raise ValueError(
            "전체 적재 원본에서 필수 버전별 자료가 누락됐습니다: "
            + json.dumps(missing, ensure_ascii=False)
        )


def build_bundle(project_root: Path) -> YelpDataBundle:
    root = project_root.resolve()

    v04_bundle: SourceBundle = load_and_validate(source_paths(root))
    v03_bundle: HistoricalMetricBundle = load_v03_bundle(root)
    v02_bundle: HistoricalMetricBundle = load_v02_bundle(root)
    playbooks, strategies = load_source(root)
    parent_rows, risk_action_rows = build_reference_rows(playbooks, strategies)

    frames = [
        *frames_for_mysql(v04_bundle),
        *v03_bundle.frames,
        *v02_bundle.frames,
    ]
    expected_version_counts = expected_counts_for_frames(frames)
    validate_expected_contract(expected_version_counts)

    return YelpDataBundle(
        project_root=root,
        frames=frames,
        parent_rows=parent_rows,
        risk_action_rows=risk_action_rows,
        source_summaries={
            "v04": validation_summary(v04_bundle),
            "v03": v03_bundle.summary,
            "v02": v02_bundle.summary,
        },
        expected_version_counts=expected_version_counts,
    )


def bundle_summary(bundle: YelpDataBundle) -> dict[str, Any]:
    return {
        "target_database": TARGET_DATABASE,
        "load_scope": [
            "v04 운영 데이터와 파생 리뷰어 데이터",
            "v03 Trust Center 비교 지표",
            "v02 Trust Center 비교 지표",
            "리텐션 플레이북 기준정보",
        ],
        "source_contracts": bundle.source_summaries,
        "expected_version_counts": bundle.expected_version_counts,
        "expected_reference_counts": {
            "retention_playbooks": len(bundle.parent_rows),
            "retention_playbook_risk_actions": len(bundle.risk_action_rows),
            "operator_decisions": 0,
        },
    }


def managed_tables(bundle: YelpDataBundle) -> list[str]:
    return sorted(
        {
            *bundle.expected_version_counts,
            *REFERENCE_TABLES,
            *EMPTY_OPERATION_TABLES,
        }
    )


def existing_managed_tables(connection, bundle: YelpDataBundle) -> set[str]:
    rows = connection.exec_driver_sql(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_type = 'BASE TABLE'
        """
    ).all()
    existing = {str(row[0]) for row in rows}
    return existing.intersection(managed_tables(bundle))


def assert_empty_target(connection, bundle: YelpDataBundle) -> None:
    occupied: dict[str, int] = {}
    for table_name in sorted(existing_managed_tables(connection, bundle)):
        row_count = int(
            connection.exec_driver_sql(
                f"SELECT COUNT(*) FROM `{table_name}`"
            ).scalar_one()
        )
        if row_count:
            occupied[table_name] = row_count
    if occupied:
        raise RuntimeError(
            "전체 초기 적재는 비어 있는 yelp_data만 허용합니다. "
            "자동 삭제나 기존 데이터 혼합은 하지 않습니다: "
            + json.dumps(occupied, ensure_ascii=False)
        )


def actual_version_counts(
    connection,
    table_names: list[str],
) -> dict[str, dict[str, int]]:
    actual: dict[str, dict[str, int]] = {}
    for table_name in table_names:
        rows = connection.exec_driver_sql(
            f"""
            SELECT model_version, COUNT(*) AS row_count
            FROM `{table_name}`
            GROUP BY model_version
            ORDER BY model_version
            """
        ).all()
        actual[table_name] = {
            str(model_version): int(row_count)
            for model_version, row_count in rows
        }
    return actual


def validate_loaded_counts(
    expected: dict[str, dict[str, int]],
    actual: dict[str, dict[str, int]],
) -> None:
    if actual != expected:
        issues: dict[str, dict[str, dict[str, int]]] = {}
        for table_name in sorted(set(expected) | set(actual)):
            expected_counts = expected.get(table_name, {})
            actual_counts = actual.get(table_name, {})
            if actual_counts != expected_counts:
                issues[table_name] = {
                    "expected": expected_counts,
                    "actual": actual_counts,
                }
        raise RuntimeError(
            "전체 적재 후 버전별 행 수 검증에 실패했습니다: "
            + json.dumps(issues, ensure_ascii=False)
        )


def validate_reference_counts(connection, bundle: YelpDataBundle) -> None:
    playbook_count = int(
        connection.exec_driver_sql(
            "SELECT COUNT(*) FROM retention_playbooks"
        ).scalar_one()
    )
    action_count = int(
        connection.exec_driver_sql(
            "SELECT COUNT(*) FROM retention_playbook_risk_actions"
        ).scalar_one()
    )
    operator_decision_count = int(
        connection.exec_driver_sql(
            "SELECT COUNT(*) FROM operator_decisions"
        ).scalar_one()
    )
    actual = {
        "retention_playbooks": playbook_count,
        "retention_playbook_risk_actions": action_count,
        "operator_decisions": operator_decision_count,
    }
    expected = {
        "retention_playbooks": len(bundle.parent_rows),
        "retention_playbook_risk_actions": len(bundle.risk_action_rows),
        "operator_decisions": 0,
    }
    if actual != expected:
        raise RuntimeError(
            "전체 적재 후 운영 기준정보 행 수 검증에 실패했습니다: "
            + json.dumps(
                {"expected": expected, "actual": actual},
                ensure_ascii=False,
            )
        )


def assert_target_database(connection, confirm_database: str) -> None:
    actual_database = database_name(connection)
    if confirm_database != TARGET_DATABASE:
        raise RuntimeError(
            f"--confirm-database에는 {TARGET_DATABASE}를 정확히 입력해야 합니다."
        )
    if actual_database != TARGET_DATABASE:
        raise RuntimeError(
            f"연결 DB({actual_database})가 전체 적재 대상({TARGET_DATABASE})과 다릅니다."
        )


def load_mysql(
    bundle: YelpDataBundle,
    confirm_database: str,
    chunk_size: int,
) -> None:
    if not confirm_database:
        raise RuntimeError(
            "오적재 방지를 위해 --confirm-database yelp_data가 필요합니다."
        )
    if chunk_size <= 0:
        raise ValueError("--chunk-size는 1 이상이어야 합니다.")

    engine = create_engine_from_env(bundle.project_root)
    try:
        with engine.begin() as connection:
            assert_target_database(connection, confirm_database)
            assert_empty_target(connection, bundle)
            apply_schema(connection, bundle.project_root)

        with engine.begin() as connection:
            assert_target_database(connection, confirm_database)
            assert_empty_target(connection, bundle)

            for table_name, frame in bundle.frames:
                nullable(frame).to_sql(
                    table_name,
                    con=connection,
                    if_exists="append",
                    index=False,
                    chunksize=chunk_size,
                    method="multi",
                )
                versions = ",".join(
                    sorted(frame["model_version"].astype(str).unique())
                )
                print(
                    f"loaded: {table_name} "
                    f"(model_version={versions}, {len(frame):,} rows)"
                )

            seed_reference_data(
                connection,
                bundle.parent_rows,
                bundle.risk_action_rows,
            )
            print(
                "loaded: retention_playbooks "
                f"({len(bundle.parent_rows):,} rows)"
            )
            print(
                "loaded: retention_playbook_risk_actions "
                f"({len(bundle.risk_action_rows):,} rows)"
            )

            actual_counts = actual_version_counts(
                connection,
                sorted(bundle.expected_version_counts),
            )
            validate_loaded_counts(
                bundle.expected_version_counts,
                actual_counts,
            )
            validate_reference_counts(connection, bundle)
    finally:
        engine.dispose()


def main() -> int:
    args = parse_args()
    try:
        bundle = build_bundle(args.project_root)
        print(json.dumps(bundle_summary(bundle), ensure_ascii=False, indent=2))
        if args.dry_run:
            print("dry-run complete: DB 변경 없음")
            return 0
        load_mysql(
            bundle,
            confirm_database=args.confirm_database,
            chunk_size=args.chunk_size,
        )
        print("yelp_data complete load and verification successful")
        return 0
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
