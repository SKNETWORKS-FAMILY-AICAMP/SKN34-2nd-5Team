"""Tune MLP architecture on the top v05_04_01 feature sets using OOF only."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.v05_04_dl import common
from pipeline.v05_01_dl import train as base


VERSION = "v05_04_02_dl"
STAGE01_DIR = common.REPORT_ROOT / "v05_04_01_dl"
REPORT_DIR = common.REPORT_ROOT / VERSION


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    summary_path = REPORT_DIR / "candidate_comparison.csv"
    if summary_path.exists() and not args.overwrite:
        raise FileExistsError(f"{summary_path} exists; use --overwrite")
    stage01_summary_path = STAGE01_DIR / "feature_set_comparison.csv"
    if not stage01_summary_path.is_file():
        raise FileNotFoundError(stage01_summary_path)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    frame, feature_sets, config, build_metadata = common.load_static_contract()
    device = common.configure_runtime()
    stage01 = pd.read_csv(stage01_summary_path)
    top_count = int(config["tune_top_feature_sets"])
    top_feature_sets = stage01.head(top_count)["feature_set"].tolist()
    tuning_candidates = [
        common.candidate_from_dict(value)
        for value in config["tuning_candidates"]
    ]
    print(
        f"version={VERSION}, device={device}, feature_sets={top_feature_sets}, "
        f"candidates={[candidate.name for candidate in tuning_candidates]}, "
        f"torch={torch.__version__}",
        flush=True,
    )

    oof_parts = []
    threshold_parts = []
    reference_columns_to_drop = [
        column for column in ["selection_rank", "selected"] if column in stage01
    ]
    summary_rows = (
        stage01.loc[stage01["feature_set"].isin(top_feature_sets)]
        .drop(columns=reference_columns_to_drop)
        .to_dict("records")
    )
    total = len(top_feature_sets) * len(tuning_candidates)
    run_index = 0
    for feature_set in top_feature_sets:
        columns = feature_sets[feature_set]
        for candidate in tuning_candidates:
            run_index += 1
            print(
                f"[{run_index}/{total}] MLP tuning OOF: {feature_set} + "
                f"{candidate.name}",
                flush=True,
            )
            checkpoint_stem = f"checkpoint_{feature_set}_{candidate.name}"
            checkpoint_oof = REPORT_DIR / f"{checkpoint_stem}_oof.parquet"
            checkpoint_thresholds = REPORT_DIR / f"{checkpoint_stem}_thresholds.csv"
            if checkpoint_oof.exists() and checkpoint_thresholds.exists() and not args.overwrite:
                print(f"reuse {checkpoint_stem}", flush=True)
                oof = pd.read_parquet(checkpoint_oof)
                threshold_grid = pd.read_csv(checkpoint_thresholds)
                selected = threshold_grid.loc[threshold_grid["selected"]].iloc[0]
            else:
                oof = base.run_candidate_oof(frame, columns, candidate, device)
                oof.insert(0, "candidate_name", candidate.name)
                oof.insert(0, "feature_set", feature_set)
                threshold_grid, selected = common.selected_threshold_row(candidate, oof)
                threshold_grid.insert(0, "feature_count", len(columns))
                threshold_grid.insert(0, "feature_set", feature_set)
                oof.to_parquet(checkpoint_oof, index=False)
                threshold_grid.to_csv(
                    checkpoint_thresholds,
                    index=False,
                    encoding="utf-8-sig",
                )
            oof_parts.append(oof)
            threshold_parts.append(threshold_grid)
            selected = selected.copy()
            selected["feature_count"] = len(columns)
            summary_rows.append(
                common.summary_from_selected(
                    VERSION,
                    "TabularMLP",
                    feature_set,
                    candidate,
                    selected,
                )
            )

    summary = common.sort_summary(pd.DataFrame(summary_rows))
    summary.insert(0, "selection_rank", np.arange(1, len(summary) + 1))
    summary["selected"] = summary["selection_rank"].eq(1)
    selected = summary.iloc[0]
    selected_config = json.loads(selected["config_json"])

    pd.concat(oof_parts, ignore_index=True).to_parquet(
        REPORT_DIR / "oof_predictions.parquet",
        index=False,
    )
    pd.concat(threshold_parts, ignore_index=True).to_csv(
        REPORT_DIR / "threshold_candidates.csv",
        index=False,
        encoding="utf-8-sig",
    )
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    common.save_json(
        REPORT_DIR / "selected.json",
        {
            "version": VERSION,
            "selection_basis": "pooled expanding-time OOF only",
            "selected_feature_set": selected["feature_set"],
            "selected_feature_count": selected["feature_count"],
            "selected_config": selected_config,
            "source_stage": selected["stage"],
            "weakened_threshold": selected["weakened_threshold"],
            "stopped_threshold": selected["stopped_threshold"],
            "oof_metrics": {
                column.removeprefix("oof_"): selected[column]
                for column in selected.index
                if column.startswith("oof_")
            },
            "feature_dataset_sha256": build_metadata["output_sha256"],
            "elapsed_seconds": time.perf_counter() - started,
        },
    )
    print(
        f"selected={selected['feature_set']} + {selected['candidate_name']}, "
        f"OOF Macro F1={selected['oof_macro_f1']:.4f}, "
        f"elapsed={time.perf_counter() - started:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
