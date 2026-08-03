"""Run fixed-MLP OOF feature-set ablation for v05_04_01."""

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


VERSION = "v05_04_01_dl"
REPORT_DIR = common.REPORT_ROOT / VERSION


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    summary_path = REPORT_DIR / "feature_set_comparison.csv"
    if summary_path.exists() and not args.overwrite:
        raise FileExistsError(f"{summary_path} exists; use --overwrite")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    frame, feature_sets, config, build_metadata = common.load_static_contract()
    device = common.configure_runtime()
    candidate = common.candidate_from_dict(config["fixed_mlp"])
    requested_sets = list(config["screen_feature_sets"])
    missing = [name for name in requested_sets if name not in feature_sets]
    if missing:
        raise ValueError(f"Unknown screen feature sets: {missing}")
    print(
        f"version={VERSION}, device={device}, feature_sets={requested_sets}, "
        f"torch={torch.__version__}",
        flush=True,
    )

    oof_parts = []
    threshold_parts = []
    summary_rows = []
    for index, feature_set in enumerate(requested_sets, start=1):
        columns = feature_sets[feature_set]
        print(
            f"[{index}/{len(requested_sets)}] fixed MLP OOF: "
            f"{feature_set} ({len(columns)} features)",
            flush=True,
        )
        oof = base.run_candidate_oof(frame, columns, candidate, device)
        oof.insert(0, "feature_set", feature_set)
        oof_parts.append(oof)
        threshold_grid, selected = common.selected_threshold_row(candidate, oof)
        threshold_grid.insert(0, "feature_count", len(columns))
        threshold_grid.insert(0, "feature_set", feature_set)
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

    oof_all = pd.concat(oof_parts, ignore_index=True)
    thresholds = pd.concat(threshold_parts, ignore_index=True)
    summary = common.sort_summary(pd.DataFrame(summary_rows))
    summary.insert(0, "selection_rank", np.arange(1, len(summary) + 1))
    summary["selected"] = summary["selection_rank"].eq(1)
    selected = summary.iloc[0]

    oof_all.to_parquet(REPORT_DIR / "oof_predictions.parquet", index=False)
    thresholds.to_csv(
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
            "selected_config": common.candidate_to_dict(candidate),
            "weakened_threshold": selected["weakened_threshold"],
            "stopped_threshold": selected["stopped_threshold"],
            "oof_macro_f1": selected["oof_macro_f1"],
            "oof_macro_pr_auc": selected["oof_macro_pr_auc"],
            "feature_dataset_sha256": build_metadata["output_sha256"],
            "elapsed_seconds": time.perf_counter() - started,
        },
    )
    print(
        f"selected={selected['feature_set']}, "
        f"OOF Macro F1={selected['oof_macro_f1']:.4f}, "
        f"elapsed={time.perf_counter() - started:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
