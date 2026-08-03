"""Select one DL candidate by OOF, then evaluate that candidate on final test."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import confusion_matrix

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.v05_04_dl import common
from pipeline.v05_01_dl import train as base
from pipeline.v05_03_dl import train as hybrid


VERSION = "v05_04_04_dl"
STAGE01_DIR = common.REPORT_ROOT / "v05_04_01_dl"
STAGE02_DIR = common.REPORT_ROOT / "v05_04_02_dl"
STAGE03_DIR = common.REPORT_ROOT / "v05_04_03_dl"
REPORT_DIR = common.REPORT_ROOT / VERSION
MODEL_DIR = common.MODEL_ROOT / VERSION
PROFILE_PATH = common.PROFILE_ROOT / "final_test_retention_profiles_v05_04_04_dl.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def seed_oof_f1(
    oof: pd.DataFrame,
    weakened_threshold: float,
    stopped_threshold: float,
) -> tuple[float, float]:
    values = []
    for seed in base.SEEDS:
        part = oof.loc[oof["record_type"].eq("seed") & oof["seed"].eq(seed)]
        scores = part[common.SCORE_COLUMNS].to_numpy()
        predictions = base.threshold_predictions(
            scores,
            weakened_threshold,
            stopped_threshold,
        )
        values.append(
            base.evaluate(part["retention_state"].to_numpy(), predictions, scores)[
                "macro_f1"
            ]
        )
    return float(np.mean(values)), float(np.std(values, ddof=1))


def metadata_candidate(version: str) -> tuple[dict, pd.DataFrame]:
    metadata = common.load_json(common.MODEL_ROOT / version / "metadata.json")
    oof = pd.read_parquet(common.REPORT_ROOT / version / "selected_oof_predictions.parquet")
    thresholds = metadata["decision_thresholds"]
    weakened = float(thresholds["weakened_score"])
    stopped = float(thresholds["stopped_score"])
    mean_f1, std_f1 = seed_oof_f1(oof, weakened, stopped)
    feature_set = metadata.get("feature_set", "core43")
    feature_count = metadata.get(
        "static_feature_count",
        metadata.get("feature_count", 43),
    )
    row = {
        "candidate_id": version,
        "source": version,
        "model_family": metadata["model_type"],
        "feature_set": feature_set,
        "feature_count": feature_count,
        "candidate_name": version,
        "config_json": json.dumps(
            metadata.get("model_config", metadata.get("selected_config", {})),
            sort_keys=True,
        ),
        "weakened_threshold": weakened,
        "stopped_threshold": stopped,
        "seed_macro_f1_mean": mean_f1,
        "seed_macro_f1_std": std_f1,
    }
    row.update({f"oof_{key}": value for key, value in metadata["oof_metrics"].items()})
    return row, oof


def load_static_finalist() -> tuple[dict, pd.DataFrame, dict]:
    selected = common.load_json(STAGE02_DIR / "selected.json")
    feature_set = selected["selected_feature_set"]
    candidate_name = selected["selected_config"]["name"]
    source_stage = selected["source_stage"]
    if source_stage == "v05_04_01_dl":
        oof = pd.read_parquet(STAGE01_DIR / "oof_predictions.parquet")
        oof = oof.loc[oof["feature_set"].eq(feature_set)].copy()
    else:
        oof = pd.read_parquet(STAGE02_DIR / "oof_predictions.parquet")
        oof = oof.loc[
            oof["feature_set"].eq(feature_set)
            & oof["candidate_name"].eq(candidate_name)
        ].copy()
    metrics = selected["oof_metrics"]
    mean_f1, std_f1 = seed_oof_f1(
        oof,
        selected["weakened_threshold"],
        selected["stopped_threshold"],
    )
    row = {
        "candidate_id": "v05_04_static",
        "source": source_stage,
        "model_family": "PyTorch TabularMLP",
        "feature_set": feature_set,
        "feature_count": selected["selected_feature_count"],
        "candidate_name": candidate_name,
        "config_json": json.dumps(selected["selected_config"], sort_keys=True),
        "weakened_threshold": selected["weakened_threshold"],
        "stopped_threshold": selected["stopped_threshold"],
        "seed_macro_f1_mean": mean_f1,
        "seed_macro_f1_std": std_f1,
    }
    row.update({f"oof_{key}": value for key, value in metrics.items()})
    return row, oof, selected


def load_fusion_finalist() -> tuple[dict, pd.DataFrame, dict]:
    selected = common.load_json(STAGE03_DIR / "selected.json")
    oof = pd.read_parquet(STAGE03_DIR / "oof_predictions.parquet")
    metrics = selected["oof_metrics"]
    mean_f1, std_f1 = seed_oof_f1(
        oof,
        selected["weakened_threshold"],
        selected["stopped_threshold"],
    )
    row = {
        "candidate_id": "v05_04_fusion",
        "source": "v05_04_03_dl",
        "model_family": "PyTorch HybridGRU",
        "feature_set": selected["new_fusion_feature_set"],
        "feature_count": selected["new_fusion_feature_count"],
        "candidate_name": "hybrid_gru_fixed_v05_03",
        "config_json": json.dumps(selected["hybrid_config"], sort_keys=True),
        "weakened_threshold": selected["weakened_threshold"],
        "stopped_threshold": selected["stopped_threshold"],
        "seed_macro_f1_mean": mean_f1,
        "seed_macro_f1_std": std_f1,
    }
    row.update({f"oof_{key}": value for key, value in metrics.items()})
    return row, oof, selected


def train_static_final(
    frame: pd.DataFrame,
    columns: list[str],
    selected: dict,
    device: torch.device,
) -> tuple[np.ndarray, dict, dict]:
    config = common.candidate_from_dict(selected["selected_config"])
    train_mask = frame["selection_year"].between(2010, 2017).to_numpy()
    test_mask = frame["selection_year"].eq(2018).to_numpy()
    train = frame.loc[train_mask]
    test = frame.loc[test_mask]
    preprocessor = base.build_preprocessor()
    x_train = preprocessor.fit_transform(train[columns]).astype(np.float32)
    x_test = preprocessor.transform(test[columns]).astype(np.float32)
    preprocessing_path = MODEL_DIR / "preprocessing.joblib"
    joblib.dump({"static_preprocessor": preprocessor}, preprocessing_path)
    labels = train["retention_state"].to_numpy(dtype=np.int64)
    scores_by_seed = []
    checksums = {}
    for seed in base.SEEDS:
        print(f"final static training seed {seed}", flush=True)
        model = base.train_model(x_train, labels, config, seed, device)
        scores = base.predict_scores(model, x_test, device)
        weight_path = MODEL_DIR / f"seed_{seed}_state_dict.pt"
        torch.save(
            {key: value.detach().cpu() for key, value in model.state_dict().items()},
            weight_path,
        )
        reloaded = base.TabularMLP(
            input_dim=x_train.shape[1],
            hidden_dims=config.hidden_dims,
            dropout=config.dropout,
        ).to(device)
        reloaded.load_state_dict(
            torch.load(weight_path, map_location=device, weights_only=True)
        )
        reloaded_scores = base.predict_scores(reloaded, x_test, device)
        if not np.allclose(scores, reloaded_scores, rtol=0, atol=1e-7):
            raise ValueError("Reloaded static scores changed")
        checksums[str(seed)] = common.sha256(weight_path)
        scores_by_seed.append(scores)
    return (
        np.mean(scores_by_seed, axis=0),
        {
            "preprocessing_sha256": common.sha256(preprocessing_path),
            "weight_sha256": checksums,
        },
        {
            "input_dim_after_imputation": int(x_train.shape[1]),
            "model_config": common.candidate_to_dict(config),
        },
    )


def train_fusion_final(
    frame: pd.DataFrame,
    columns: list[str],
    selected: dict,
    device: torch.device,
) -> tuple[np.ndarray, dict, dict]:
    config = selected["hybrid_config"]
    raw_sequence = common.load_raw_sequence(frame, config["sequence_channels"])
    train_mask = frame["selection_year"].between(2010, 2017).to_numpy()
    test_mask = frame["selection_year"].eq(2018).to_numpy()
    train = frame.loc[train_mask]
    test = frame.loc[test_mask]
    preprocessor = base.build_preprocessor()
    x_static_train = preprocessor.fit_transform(train[columns]).astype(np.float32)
    x_static_test = preprocessor.transform(test[columns]).astype(np.float32)
    x_sequence_train, x_sequence_test, sequence_scaler = hybrid.transform_sequence(
        raw_sequence[train_mask],
        raw_sequence[test_mask],
    )
    preprocessing_path = MODEL_DIR / "preprocessing.joblib"
    joblib.dump(
        {
            "static_preprocessor": preprocessor,
            "sequence_scaler": sequence_scaler,
            "sequence_transform": "log1p first two channels, then StandardScaler",
        },
        preprocessing_path,
    )
    labels = train["retention_state"].to_numpy(dtype=np.int64)
    scores_by_seed = []
    checksums = {}
    for seed in base.SEEDS:
        print(f"final fusion training seed {seed}", flush=True)
        model = hybrid.train_model(
            x_static_train,
            x_sequence_train,
            labels,
            config,
            seed,
            device,
        )
        scores = hybrid.predict_scores(
            model,
            x_static_test,
            x_sequence_test,
            device,
        )
        weight_path = MODEL_DIR / f"seed_{seed}_state_dict.pt"
        torch.save(
            {key: value.detach().cpu() for key, value in model.state_dict().items()},
            weight_path,
        )
        reloaded = hybrid.make_model(x_static_train.shape[1], config, device)
        reloaded.load_state_dict(
            torch.load(weight_path, map_location=device, weights_only=True)
        )
        reloaded_scores = hybrid.predict_scores(
            reloaded,
            x_static_test,
            x_sequence_test,
            device,
        )
        if not np.allclose(scores, reloaded_scores, rtol=0, atol=1e-7):
            raise ValueError("Reloaded fusion scores changed")
        checksums[str(seed)] = common.sha256(weight_path)
        scores_by_seed.append(scores)
    return (
        np.mean(scores_by_seed, axis=0),
        {
            "preprocessing_sha256": common.sha256(preprocessing_path),
            "sequence_sha256": common.sha256(common.SEQUENCE_PATH),
            "weight_sha256": checksums,
        },
        {
            "static_input_dim_after_imputation": int(x_static_train.shape[1]),
            "sequence_length": 24,
            "sequence_channels": config["sequence_channels"],
            "model_config": config["model"],
        },
    )


def reference_comparison_row(version: str) -> dict:
    metadata = common.load_json(common.MODEL_ROOT / version / "metadata.json")
    top20 = metadata["top20_policy"]
    return {
        "candidate": version,
        "selected_by_v05_04_oof": False,
        "oof_macro_f1": metadata["oof_metrics"]["macro_f1"],
        "oof_macro_pr_auc": metadata["oof_metrics"]["macro_pr_auc"],
        "test_macro_f1": metadata["test_metrics"]["macro_f1"],
        "test_macro_pr_auc": metadata["test_metrics"]["macro_pr_auc"],
        "test_weakened_recall": metadata["test_metrics"]["weakened_recall"],
        "test_stopped_recall": metadata["test_metrics"]["stopped_recall"],
        "top20_precision": top20["status_loss_precision"],
        "top20_recall": top20["status_loss_recall"],
        "top20_lift": top20["status_loss_lift"],
    }


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    selected_path = REPORT_DIR / "selected_candidate.json"
    if selected_path.exists() and not args.overwrite:
        raise FileExistsError(f"{selected_path} exists; use --overwrite")
    required = [
        STAGE02_DIR / "selected.json",
        STAGE03_DIR / "selected.json",
        common.MODEL_ROOT / "v05_03_dl" / "metadata.json",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing finalist inputs:\n- " + "\n- ".join(missing))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    frame, feature_sets, config, build_metadata = common.load_static_contract()
    device = common.configure_runtime()
    existing_row, existing_oof = metadata_candidate("v05_03_dl")
    static_row, static_oof, static_selected = load_static_finalist()
    fusion_row, fusion_oof, fusion_selected = load_fusion_finalist()
    finalist_table = common.sort_summary(
        pd.DataFrame([existing_row, static_row, fusion_row])
    )
    finalist_table.insert(0, "selection_rank", np.arange(1, len(finalist_table) + 1))
    finalist_table["selected"] = finalist_table["selection_rank"].eq(1)
    winner = finalist_table.iloc[0]
    winner_id = str(winner["candidate_id"])
    print(
        f"OOF-selected final candidate={winner_id}, "
        f"Macro F1={winner['oof_macro_f1']:.4f}",
        flush=True,
    )
    finalist_table.to_csv(
        REPORT_DIR / "oof_finalist_comparison.csv",
        index=False,
        encoding="utf-8-sig",
    )

    if winner_id == "v05_03_dl":
        selected_oof = existing_oof
        existing_metadata = common.load_json(
            common.MODEL_ROOT / "v05_03_dl" / "metadata.json"
        )
        test_metrics = existing_metadata["test_metrics"]
        top20_policy = existing_metadata["top20_policy"]
        artifact_metadata = existing_metadata["artifacts"]
        model_details = {
            "reuse_existing_model": True,
            "existing_model_version": "v05_03_dl",
        }
        profile_path = common.PROFILE_ROOT / "final_test_retention_profiles_v05_03_dl.parquet"
    else:
        columns = feature_sets[str(winner["feature_set"])]
        if winner_id == "v05_04_static":
            selected_oof = static_oof
            test_scores, artifact_metadata, model_details = train_static_final(
                frame,
                columns,
                static_selected,
                device,
            )
            selected_detail = static_selected
        else:
            selected_oof = fusion_oof
            test_scores, artifact_metadata, model_details = train_fusion_final(
                frame,
                columns,
                fusion_selected,
                device,
            )
            selected_detail = fusion_selected
        test = frame.loc[frame["selection_year"].eq(2018)].copy()
        labels = test["retention_state"].to_numpy()
        predictions = base.threshold_predictions(
            test_scores,
            float(winner["weakened_threshold"]),
            float(winner["stopped_threshold"]),
        )
        test_metrics = base.evaluate(labels, predictions, test_scores)
        top_k = pd.DataFrame(base.top_k_records("final_test", labels, test_scores))
        top_k.to_csv(REPORT_DIR / "top_k.csv", index=False, encoding="utf-8-sig")
        top20 = top_k.loc[top_k["target_rate"].eq(base.PRIMARY_TARGET_RATE)].iloc[0]
        top20_policy = {
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
        }
        matrix = confusion_matrix(labels, predictions, labels=base.CLASS_CODES)
        pd.DataFrame(
            matrix,
            index=[f"actual_{name}" for name in base.CLASS_NAMES],
            columns=[f"predicted_{name}" for name in base.CLASS_NAMES],
        ).to_csv(REPORT_DIR / "confusion.csv", encoding="utf-8-sig")
        test[common.SCORE_COLUMNS] = test_scores
        test["priority_score"] = test["weakened_score"] + test["stopped_score"]
        test["predicted_state"] = predictions
        test["priority_rank"] = test["priority_score"].rank(
            method="first", ascending=False
        ).astype(int)
        test["priority_top_percent"] = test["priority_rank"].div(len(test)).mul(100)
        test["selected_for_crm"] = test["priority_rank"].le(
            int(np.ceil(len(test) * base.PRIMARY_TARGET_RATE))
        ).astype("int8")
        test.sort_values(["priority_rank", "sample_id"]).reset_index(drop=True).to_parquet(
            PROFILE_PATH,
            index=False,
        )
        profile_path = PROFILE_PATH

    selected_oof.to_parquet(
        REPORT_DIR / "selected_oof_predictions.parquet",
        index=False,
    )
    comparison_rows = [
        reference_comparison_row("v05_01_dl"),
        reference_comparison_row("v05_02_dl"),
        reference_comparison_row("v05_03_dl"),
    ]
    if winner_id != "v05_03_dl":
        comparison_rows.append(
            {
                "candidate": winner_id,
                "selected_by_v05_04_oof": True,
                "oof_macro_f1": winner["oof_macro_f1"],
                "oof_macro_pr_auc": winner["oof_macro_pr_auc"],
                "test_macro_f1": test_metrics["macro_f1"],
                "test_macro_pr_auc": test_metrics["macro_pr_auc"],
                "test_weakened_recall": test_metrics["weakened_recall"],
                "test_stopped_recall": test_metrics["stopped_recall"],
                "top20_precision": top20_policy["status_loss_precision"],
                "top20_recall": top20_policy["status_loss_recall"],
                "top20_lift": top20_policy["status_loss_lift"],
            }
        )
    comparison = pd.DataFrame(comparison_rows)
    comparison.loc[
        comparison["candidate"].eq(winner_id), "selected_by_v05_04_oof"
    ] = True
    comparison.to_csv(
        REPORT_DIR / "dl_model_comparison.csv",
        index=False,
        encoding="utf-8-sig",
    )

    metadata = {
        "version": VERSION,
        "status": "dl_development_complete",
        "selection_basis": "pooled expanding-time OOF only",
        "selected_candidate": winner_id,
        "selected_model_family": winner["model_family"],
        "selected_feature_set": winner["feature_set"],
        "selected_feature_count": winner["feature_count"],
        "decision_thresholds": {
            "weakened_score": winner["weakened_threshold"],
            "stopped_score": winner["stopped_threshold"],
        },
        "oof_metrics": {
            column.removeprefix("oof_"): winner[column]
            for column in winner.index
            if column.startswith("oof_")
        },
        "test_metrics": test_metrics,
        "top20_policy": top20_policy,
        "model_details": model_details,
        "artifacts": artifact_metadata,
        "profile_path": str(profile_path),
        "feature_dataset_sha256": build_metadata["output_sha256"],
        "runtime": {
            "device": str(device),
            "torch_version": torch.__version__,
            "python_version": sys.version.split()[0],
            "sklearn_version": sklearn.__version__,
            "pandas_version": pd.__version__,
            "elapsed_seconds": time.perf_counter() - started,
        },
        "scope_boundary": (
            "ML comparison and ML-DL ensemble are intentionally deferred to "
            "v05_04_05 and v05_04_06 with teammate inputs."
        ),
    }
    common.save_json(MODEL_DIR / "metadata.json", metadata)
    common.save_json(selected_path, metadata)
    report = f"""# v05_04_04 DL model development result

- Selection basis: pooled expanding-time OOF only
- Selected candidate: {winner_id}
- Selected feature set: {winner['feature_set']} ({int(winner['feature_count'])} features)
- OOF Macro F1: {float(winner['oof_macro_f1']):.4f}
- OOF Macro PR-AUC: {float(winner['oof_macro_pr_auc']):.4f}
- Final Test Macro F1: {float(test_metrics['macro_f1']):.4f}
- Final Test Macro PR-AUC: {float(test_metrics['macro_pr_auc']):.4f}
- Final Test weakened Recall: {float(test_metrics['weakened_recall']):.2%}
- Final Test stopped Recall: {float(test_metrics['stopped_recall']):.2%}
- Top 20% Precision / Recall / Lift:
  {float(top20_policy['status_loss_precision']):.2%} /
  {float(top20_policy['status_loss_recall']):.2%} /
  {float(top20_policy['status_loss_lift']):.2f}x

The class scores are ranking scores, not calibrated churn probabilities.
ML comparison and ML-DL ensembling are outside this stage.
"""
    (REPORT_DIR / "performance.md").write_text(report, encoding="utf-8")
    print(
        f"selected={winner_id}, OOF Macro F1={winner['oof_macro_f1']:.4f}, "
        f"Test Macro F1={test_metrics['macro_f1']:.4f}, "
        f"elapsed={time.perf_counter() - started:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
