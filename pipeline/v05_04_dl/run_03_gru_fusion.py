"""Evaluate the best new static feature set with the protected GRU branch."""

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
from pipeline.v05_03_dl import train as hybrid


VERSION = "v05_04_03_dl"
STAGE02_DIR = common.REPORT_ROOT / "v05_04_02_dl"
EXISTING_VERSION = "v05_03_dl"
EXISTING_METADATA_PATH = common.MODEL_ROOT / EXISTING_VERSION / "metadata.json"
EXISTING_OOF_PATH = common.REPORT_ROOT / EXISTING_VERSION / "selected_oof_predictions.parquet"
REPORT_DIR = common.REPORT_ROOT / VERSION


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def existing_gru_summary() -> dict:
    metadata = common.load_json(EXISTING_METADATA_PATH)
    oof = pd.read_parquet(EXISTING_OOF_PATH)
    thresholds = metadata["decision_thresholds"]
    seed_f1 = []
    for seed in base.SEEDS:
        part = oof.loc[oof["record_type"].eq("seed") & oof["seed"].eq(seed)]
        scores = part[common.SCORE_COLUMNS].to_numpy()
        predictions = base.threshold_predictions(
            scores,
            thresholds["weakened_score"],
            thresholds["stopped_score"],
        )
        seed_f1.append(
            base.evaluate(part["retention_state"].to_numpy(), predictions, scores)[
                "macro_f1"
            ]
        )
    row = {
        "stage": EXISTING_VERSION,
        "model_family": "HybridGRU",
        "feature_set": "core43",
        "feature_count": 43,
        "candidate_name": EXISTING_VERSION,
        "config_json": json.dumps(metadata["model_config"], sort_keys=True),
        "weakened_threshold": thresholds["weakened_score"],
        "stopped_threshold": thresholds["stopped_score"],
        "seed_macro_f1_mean": float(np.mean(seed_f1)),
        "seed_macro_f1_std": float(np.std(seed_f1, ddof=1)),
    }
    row.update({f"oof_{key}": value for key, value in metadata["oof_metrics"].items()})
    return row


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    comparison_path = REPORT_DIR / "fusion_comparison.csv"
    if comparison_path.exists() and not args.overwrite:
        raise FileExistsError(f"{comparison_path} exists; use --overwrite")
    stage02_summary_path = STAGE02_DIR / "candidate_comparison.csv"
    required = [stage02_summary_path, EXISTING_METADATA_PATH, EXISTING_OOF_PATH]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing stage inputs:\n- " + "\n- ".join(missing))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    frame, feature_sets, config, build_metadata = common.load_static_contract()
    device = common.configure_runtime()
    stage02 = pd.read_csv(stage02_summary_path)
    new_candidates = stage02.loc[stage02["feature_set"].ne("core43")]
    selected_static = (
        new_candidates.iloc[0] if len(new_candidates) else stage02.iloc[0]
    )
    feature_set = str(selected_static["feature_set"])
    columns = feature_sets[feature_set]
    hybrid_config = dict(config["hybrid"])
    hybrid_config["model"] = dict(hybrid_config["model"])
    hybrid_config["model"]["name"] = "hybrid_gru_fixed_v05_03"
    raw_sequence = common.load_raw_sequence(
        frame,
        hybrid_config["sequence_channels"],
    )
    print(
        f"version={VERSION}, device={device}, feature_set={feature_set}, "
        f"features={len(columns)}, torch={torch.__version__}",
        flush=True,
    )

    oof = hybrid.run_oof(
        frame,
        raw_sequence,
        columns,
        hybrid_config,
        device,
    )
    oof.insert(0, "feature_set", feature_set)
    thresholds, selected = hybrid.select_thresholds(oof)
    selected = selected.copy()
    selected["feature_count"] = len(columns)
    new_summary = common.summary_from_selected(
        VERSION,
        "HybridGRU",
        feature_set,
        {"name": "hybrid_gru_fixed_v05_03", **hybrid_config["model"]},
        selected,
    )
    comparison = common.sort_summary(
        pd.DataFrame([existing_gru_summary(), new_summary])
    )
    comparison.insert(0, "selection_rank", np.arange(1, len(comparison) + 1))
    comparison["selected"] = comparison["selection_rank"].eq(1)

    oof.to_parquet(REPORT_DIR / "oof_predictions.parquet", index=False)
    thresholds.insert(0, "feature_count", len(columns))
    thresholds.insert(0, "feature_set", feature_set)
    thresholds.to_csv(
        REPORT_DIR / "threshold_candidates.csv",
        index=False,
        encoding="utf-8-sig",
    )
    comparison.to_csv(comparison_path, index=False, encoding="utf-8-sig")
    common.save_json(
        REPORT_DIR / "selected.json",
        {
            "version": VERSION,
            "selection_basis": "pooled expanding-time OOF only",
            "new_fusion_feature_set": feature_set,
            "new_fusion_feature_count": len(columns),
            "hybrid_config": hybrid_config,
            "weakened_threshold": selected["weakened_threshold"],
            "stopped_threshold": selected["stopped_threshold"],
            "oof_metrics": {
                column.removeprefix("oof_"): selected[column]
                for column in selected.index
                if column.startswith("oof_")
            },
            "comparison_winner": comparison.iloc[0]["candidate_name"],
            "feature_dataset_sha256": build_metadata["output_sha256"],
            "sequence_sha256": common.sha256(common.SEQUENCE_PATH),
            "elapsed_seconds": time.perf_counter() - started,
        },
    )
    print(
        f"new_fusion={feature_set}, OOF Macro F1={selected['oof_macro_f1']:.4f}, "
        f"comparison_winner={comparison.iloc[0]['candidate_name']}, "
        f"elapsed={time.perf_counter() - started:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
