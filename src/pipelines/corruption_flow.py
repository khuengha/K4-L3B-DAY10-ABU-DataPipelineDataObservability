from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pandas as pd

from core.config import Settings, load_settings, require_llm_credentials
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def repair_from_raw_snapshot(settings: Settings) -> pd.DataFrame:
    """Rebuild clean dataframe idempotently from raw snapshot file."""
    if not settings.paths.raw_records_json.exists():
        raise FileNotFoundError(f"Raw snapshot not found at {settings.paths.raw_records_json}")

    records = load_raw_records(settings.paths.raw_records_json)
    run_date = datetime.now(timezone.utc)
    repaired_df = build_clean_dataframe(records, run_date=run_date)

    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    return repaired_df


def run_corruption_flow_pipeline(settings: Settings) -> None:
    """Execute end-to-end Baseline -> Corrupted -> Repaired evaluation pipeline."""
    try:
        require_llm_credentials(settings)
    except RuntimeError as exc:
        print(f"CANH BAO: {exc} Dung provider 'mock' cho lan chay nay.")
        settings = replace(settings, llm_provider="mock", model_name="mock")

    print("=== CORRUPTION, REPAIR & IMPACT ANALYSIS PIPELINE ===")

    # 1. Baseline Load
    print("Step 1: Loading baseline clean dataset and baseline metrics...")
    if not settings.paths.clean_json.exists() or not settings.paths.baseline_metrics.exists():
        raise FileNotFoundError("Baseline artifacts missing. Please run Phase 1 baseline pipeline first.")

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = pd.read_json(settings.paths.clean_json)
    print(f"  -> Baseline dataset loaded: {len(clean_df)} clean records")

    # 2. Corrupted Data Generation
    print("Step 2: Generating synthetic corrupted dataset (CP4)...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    print(f"  -> Corrupted dataset created: {len(corrupted_df)} records (Log: {settings.paths.corruption_log})")

    # 3. Corrupted Observability (Quality & Freshness)
    print("Step 3: Running Data Quality Gate & Freshness check on Corrupted Data...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = corrupted_quality.get("freshness") or build_freshness_report(
        corrupted_df, settings, settings.paths.quality_dir / "corrupted_freshness_report.json"
    )
    print(f"  -> Corrupted Quality Gate status: {'PASS' if corrupted_quality.get('success') else 'FAIL (Expected failure)'}")

    # 4. Corrupted Indexing & Evaluation
    print("Step 4: Indexing and Evaluating Corrupted Data...")
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, embeddings_output_path=settings.paths.corrupted_embeddings_json
    )
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_bundle.summary
    print(
        f"  -> Corrupted metrics: hit_rate={corrupted_metrics.get('retrieval_hit_rate', 0.0):.2f}, "
        f"token_f1={corrupted_metrics.get('mean_token_f1', 0.0):.2f}, "
        f"judge_acc={corrupted_metrics.get('judge_accuracy', 0.0):.2f}"
    )

    # 5. Idempotent Repair from Raw Snapshot
    print("Step 5: Repairing dataset from raw snapshot...")
    repaired_df = repair_from_raw_snapshot(settings)
    print(f"  -> Repaired dataset created: {len(repaired_df)} records")

    # Verification of logical consistency with baseline
    if len(repaired_df) != len(clean_df) or set(repaired_df["paper_id"]) != set(clean_df["paper_id"]):
        raise RuntimeError(
            f"Repaired dataset logical inconsistency: {len(repaired_df)} records vs baseline {len(clean_df)} records."
        )

    # 6. Repaired Observability (Quality & Freshness)
    print("Step 6: Running Data Quality Gate & Freshness check on Repaired Data...")
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = repaired_quality.get("freshness") or build_freshness_report(
        repaired_df, settings, settings.paths.quality_dir / "repaired_freshness_report.json"
    )
    print(f"  -> Repaired Quality Gate status: {'PASS' if repaired_quality.get('success') else 'FAIL'}")

    # 7. Repaired Indexing & Evaluation
    print("Step 7: Indexing and Evaluating Repaired Data...")
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, embeddings_output_path=settings.paths.repaired_embeddings_json
    )
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = repaired_bundle.summary
    print(
        f"  -> Repaired metrics: hit_rate={repaired_metrics.get('retrieval_hit_rate', 0.0):.2f}, "
        f"token_f1={repaired_metrics.get('mean_token_f1', 0.0):.2f}, "
        f"judge_acc={repaired_metrics.get('judge_accuracy', 0.0):.2f}"
    )

    # 8. Report Generation
    print("Step 8: Generating 3-State Comparison Report...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"Bao cao CP5 hoan tat: {settings.paths.comparison_report}")
    print("=== CP5 PIPELINE HOAN TAT ===")


def main() -> None:
    settings = load_settings()
    run_corruption_flow_pipeline(settings)


if __name__ == "__main__":
    main()

