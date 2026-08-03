"""v05_05_dl의 Trust Center용 상세 지표(model_validation_metrics/
model_confusion_matrix/model_topk_metrics)를 계산해 MySQL에 적재한다.

`load_v05_05_dl.py`가 이미 넣은 model_predictions/validation_outcomes만으로는
Trust Center(api/services/trust_service.py의 _multiclass_block)가 요구하는
클래스별 ROC-AUC·혼동행렬·Top-K 표가 없다. v05_05_dl의 평가 코드
(pipeline/v05_05_dl/evaluate_test.py)는 클래스별 ROC-AUC를 계산하지 않아
DDL의 NOT NULL 컬럼과 맞지 않기 때문이다.

이 스크립트는 pipeline/v04/modeling.py의 evaluate()/confusion_records()/
top_k_records()를 그대로 재사용해 v04와 완전히 같은 방식·같은 컬럼으로
v05_05_dl의 Test 프로필(test_retention_profiles_v05_05_dl.parquet)에서
지표를 다시 계산한다 — v04와의 비교가 같은 산식이어야 의미가 있어서다.
feature_importance/feature_group_importance는 다루지 않는다(순열 중요도
산출물이 아직 없음) — Trust Center에서 v05_05_dl의 해당 패널은 빈 채로
남는다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.v04.modeling import (  # noqa: E402
    CLASS_CODES,
    CLASS_NAMES,
    confusion_records,
    evaluate,
    top_k_records,
)
from database.load.load_v05_05_dl import (  # noqa: E402
    apply_schema,
    create_engine_from_env,
    database_name,
    nullable,
)

MODEL_VERSION = "v05_05_dl"
EXPECTED_TEST_ROWS = 6_533
PROFILE_PATH = (
    ROOT / "data" / "processed" / "predictions" / "test_retention_profiles_v05_05_dl.parquet"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply-schema", action="store_true")
    parser.add_argument("--confirm-database")
    return parser.parse_args()


def compute_frames() -> dict[str, pd.DataFrame]:
    profile = pd.read_parquet(PROFILE_PATH)
    if len(profile) != EXPECTED_TEST_ROWS:
        raise ValueError(f"Test 프로필 행 수가 {EXPECTED_TEST_ROWS:,}이 아닙니다.")

    y_true = profile["retention_state"].to_numpy(dtype=np.int64)
    predictions = profile["predicted_state"].to_numpy(dtype=np.int64)
    scores = profile[["retained_score", "weakened_score", "stopped_score"]].to_numpy(
        dtype=np.float64
    )

    metrics = evaluate(y_true, predictions, scores)
    validation_row = {
        "model_version": MODEL_VERSION,
        "record_type": "final_test",
        "split": "selection_2018_target_2019",
        "train_selection_years": "2010~2017",
        "validation_selection_year": 2018,
        "train_samples": None,
        "validation_samples": len(profile),
        **metrics,
    }
    validation_metrics = pd.DataFrame([validation_row])

    confusion_rows = confusion_records("final_test", y_true, predictions)
    confusion_matrix = pd.DataFrame(confusion_rows)
    confusion_matrix.insert(0, "model_version", MODEL_VERSION)

    topk_rows = top_k_records("final_test", y_true, scores)
    topk_metrics = pd.DataFrame(topk_rows)
    topk_metrics.insert(0, "model_version", MODEL_VERSION)

    if int(confusion_matrix["users"].sum()) != len(profile):
        raise ValueError("혼동행렬 인원 합이 Test 표본 수와 다릅니다.")
    if len(confusion_matrix) != len(CLASS_CODES) ** 2:
        raise ValueError("혼동행렬 행 수가 9행이 아닙니다.")
    if set(CLASS_NAMES) != {"retained", "weakened", "stopped"}:
        raise ValueError("CLASS_NAMES가 예상과 다릅니다.")

    return {
        "model_validation_metrics": validation_metrics,
        "model_confusion_matrix": confusion_matrix,
        "model_topk_metrics": topk_metrics,
    }


def assert_clean_target(connection, model_version: str) -> None:
    tables = ["model_validation_metrics", "model_confusion_matrix", "model_topk_metrics"]
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
            "이미 v05_05_dl 상세 지표가 있어 안전상 중단합니다: "
            + json.dumps(occupied, ensure_ascii=False)
        )


def load_mysql(frames: dict[str, pd.DataFrame], args: argparse.Namespace) -> None:
    if not args.confirm_database:
        raise RuntimeError(
            "오적재 방지를 위해 --confirm-database에 대상 DB 이름을 입력해야 합니다."
        )
    engine = create_engine_from_env(ROOT)
    try:
        if args.apply_schema:
            with engine.begin() as connection:
                actual_database = database_name(connection)
                if actual_database != args.confirm_database:
                    raise RuntimeError(
                        f"연결 DB({actual_database})와 확인값"
                        f"({args.confirm_database})이 다릅니다."
                    )
                apply_schema(connection, ROOT)

        with engine.begin() as connection:
            actual_database = database_name(connection)
            if actual_database != args.confirm_database:
                raise RuntimeError(
                    f"연결 DB({actual_database})와 확인값"
                    f"({args.confirm_database})이 다릅니다."
                )
            assert_clean_target(connection, MODEL_VERSION)
            for table_name, frame in frames.items():
                nullable(frame).to_sql(
                    table_name, con=connection, if_exists="append", index=False
                )
                print(f"loaded: {table_name} ({len(frame):,} rows)")
    finally:
        engine.dispose()


def main() -> int:
    args = parse_args()
    try:
        frames = compute_frames()
        summary = {
            name: len(frame) for name, frame in frames.items()
        }
        summary["test_macro_f1"] = float(
            frames["model_validation_metrics"].iloc[0]["macro_f1"]
        )
        summary["test_macro_ovr_roc_auc"] = float(
            frames["model_validation_metrics"].iloc[0]["macro_ovr_roc_auc"]
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if args.dry_run:
            print("dry-run complete: DB 변경 없음")
            return 0
        load_mysql(frames, args)
        print("v05_05_dl trust metrics load complete")
        return 0
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
