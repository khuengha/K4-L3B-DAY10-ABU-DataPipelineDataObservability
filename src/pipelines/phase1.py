from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

from core.config import load_settings, require_llm_credentials
from core.utils import read_json, write_json, write_csv
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


@dataclass(frozen=True)
class SourceSummary:
    source_api: str
    source_query: str
    total_records: int
    clean_records: int
    embedding_model: str
    collection_name: str
    top_k: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_api": self.source_api,
            "source_query": self.source_query,
            "total_records": self.total_records,
            "clean_records": self.clean_records,
            "embedding_model": self.embedding_model,
            "collection_name": self.collection_name,
            "top_k": self.top_k,
        }


def main() -> None:
    """TODO(student): xay dung baseline pipeline end-to-end."""
    settings = load_settings()
    try:
        require_llm_credentials(settings)
    except RuntimeError as exc:
        print(f"CANH BAO: {exc} Dung provider 'mock' cho lan chay nay.")
        settings = replace(settings, llm_provider="mock", model_name="mock")

    print("=== PHASE 1: BASELINE PIPELINE ===")

    records = fetch_source_records(settings)
    print(f"Ingestion: {len(records)} raw records")

    run_date = datetime.now(timezone.utc)
    df = build_clean_dataframe(records, run_date)
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))
    print(f"Cleaning: {len(df)} dong sach")

    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    if not quality["success"]:
        print("CANH BAO: Data Quality Gate that bai tren du lieu baseline!")

    test_set_path = settings.paths.eval_testset
    if settings.refresh_test_set or not test_set_path.exists():
        test_set = build_test_set(df, test_set_path)
    else:
        test_set = read_json(test_set_path)
    print(f"Test set: {len(test_set)} cau hoi")

    index = LocalEmbeddingIndex.build(df, settings)
    print(f"Index: collection '{index.collection_name}' voi {len(index.documents)} documents")

    print("Dang evaluate baseline (co the mat vai phut)...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=test_set_path,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    summary = bundle.summary
    print(
        f"Baseline: hit_rate={summary['retrieval_hit_rate']:.2f}, "
        f"token_f1={summary['mean_token_f1']:.2f}, judge_acc={summary['judge_accuracy']:.2f}"
    )

    demo_questions = [
        "Who authored 'Agentic Retrieval-Augmented Generation for Knowledge-Intensive Tasks'?",
        test_set[0]["question"],
    ]
    demo_answers: list[dict[str, Any]] = []
    for question in demo_questions:
        result = answer_question(question, settings=settings, index=index)
        demo_answers.append(
            {
                "question": question,
                "answer": result.answer,
                "retrieved_doc_ids": result.retrieved_doc_ids,
            }
        )
        print(f"Demo Q: {question}\n  -> {result.answer}")
    write_json(settings.paths.demo_answers, demo_answers)

    source_summary = SourceSummary(
        source_api=settings.source_api,
        source_query=settings.source_query,
        total_records=len(records),
        clean_records=len(df),
        embedding_model=settings.embedding_model,
        collection_name=index.collection_name,
        top_k=settings.top_k,
    ).to_dict()

    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=summary,
        quality=quality,
        freshness=freshness,
    )
    print(f"Bao cao phase 1: {settings.paths.baseline_report}")
    print("=== PHASE 1 HOAN TAT ===")
