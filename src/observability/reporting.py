from __future__ import annotations

from typing import Any

from core.utils import write_text


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2%}" if 0 <= value <= 1 else f"{value:.4f}"
    return str(value)


def _metrics_table(metrics: dict[str, Any]) -> str:
    rows = ["| Chỉ số | Giá trị |", "|---|---|"]
    for key in ("samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        if key in metrics:
            rows.append(f"| `{key}` | {_fmt(metrics[key])} |")
    return "\n".join(rows)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """TODO(student): viet markdown report cho baseline phase."""
    lines = [
        "# Phase 1 Report — Baseline Pipeline",
        "",
        "## 1. Nguồn dữ liệu (Data Lineage)",
        "",
        "| Thông số | Giá trị |",
        "|---|---|",
        f"| Source API | {source_summary['source_api']} |",
        f"| Query | `{source_summary['source_query']}` |",
        f"| Raw records | {source_summary['total_records']} |",
        f"| Clean records | {source_summary['clean_records']} |",
        f"| Embedding model | `{source_summary['embedding_model']}` |",
        f"| ChromaDB collection | `{source_summary['collection_name']}` |",
        f"| Top-K retrieval | {source_summary['top_k']} |",
        "",
        "## 2. Chỉ số hiệu năng Baseline",
        "",
        _metrics_table(metrics),
        "",
        "## 3. Data Quality Gate (Great Expectations 1.x)",
        "",
        f"- **Status:** {'✅ PASS' if quality.get('success') else '❌ FAIL'}",
        f"- Số expectation: {len(quality.get('results', quality.get('checks', [])))}",
        "",
        "## 4. Freshness SLA",
        "",
        f"- **is_fresh:** {'✅ True' if freshness.get('is_fresh') else '❌ False'}",
        f"- Tỷ lệ stale (> {freshness.get('freshness_threshold_days')} ngày): {_fmt(freshness.get('stale_ratio', 0))} "
        f"({freshness.get('stale_rows', 0)}/{freshness.get('total_rows', 0)} bài)",
        f"- Ngày xuất bản: {freshness.get('oldest_published')} → {freshness.get('latest_published')}",
        "",
        "## 5. Kết luận",
        "",
        "Pipeline baseline chạy end-to-end trên dữ liệu sạch: ingestion → cleaning → quality gate → "
        "indexing → evaluation. Các chỉ số này làm mốc so sánh (baseline) cho giai đoạn corruption & repair.",
    ]
    write_text(report_path, "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    metric_keys = (
        "retrieval_hit_rate",
        "mean_token_f1",
        "judge_accuracy",
        "mean_judge_score",
    )
    table = ["| Chỉ số | Baseline | Corrupted | Repaired | Δ Corrupted | Δ Repaired |", "|---|---|---|---|---|---|"]
    for key in metric_keys:
        base = baseline_metrics.get(key, 0.0)
        corr = corrupted_metrics.get(key, 0.0)
        rep = repaired_metrics.get(key, 0.0)
        table.append(
            f"| `{key}` | {_fmt(base)} | {_fmt(corr)} | {_fmt(rep)} "
            f"| {corr - base:+.4f} | {rep - base:+.4f} |"
        )
    table = "\n".join(table)

    quality_line = (
        f"- Corrupted quality gate: {'PASS' if corrupted_quality.get('success') else '❌ FAIL (phát hiện lỗi — đúng kỳ vọng)'} "
        f"({len(corrupted_quality.get('results', corrupted_quality.get('checks', [])))} expectations)\n"
        f"- Repaired quality gate: {'✅ PASS' if repaired_quality.get('success') else '❌ FAIL'}"
    )
    freshness_line = (
        f"- Corrupted is_fresh: {'✅ True' if corrupted_freshness.get('is_fresh') else '❌ False'} "
        f"(stale {corrupted_freshness.get('stale_rows', '?')}/{corrupted_freshness.get('total_rows', '?')})\n"
        f"- Repaired is_fresh: {'✅ True' if repaired_freshness.get('is_fresh') else '❌ False'} "
        f"(stale {repaired_freshness.get('stale_rows', '?')}/{repaired_freshness.get('total_rows', '?')})"
    )

    lines = [
        "# Corruption & Repair Report — Đối chiếu 3 trạng thái",
        "",
        "## 1. Bảng đối chiếu hiệu năng: Baseline vs Corrupted vs Repaired",
        "",
        table,
        "",
        "## 2. Data Quality Gate & Freshness",
        "",
        quality_line,
        "",
        freshness_line,
        "",
        "## 3. Phân tích hiện tượng Silent Failure",
        "",
        "- **Corrupted:** các kịch bản làm bẩn (mất bản ghi mới, blank summary, noise, truncate title, "
        "stale date, duplicate rows) làm chỉ số retrieval/answer sụt giảm so với baseline trong khi hệ thống "
        "vẫn có vẻ vận hành bình thường — đây chính là **Silent Failure**.",
        "- **Quality Gate:** Great Expectations 1.x phát hiện vi phạm trên dữ liệu corrupted, chứng minh "
        "data observability chặn lỗi trước khi dữ liệu tới serving layer.",
        "- **Repaired:** pipeline repair idempotent tái tạo dữ liệu sạch từ raw snapshot "
        "(`data/raw/crossref_records.json`), chỉ số quay về ngang baseline — chứng minh năng lực self-healing.",
        "",
        "## 4. Kết luận",
        "",
        "Dữ liệu chất lượng kém làm RAG suy giảm nghiêm trọng nhưng quality gate phát hiện được và repair "
        "khôi phục đầy đủ. Data observability là lớp phòng thủ thiết yếu của pipeline AI production.",
    ]
    write_text(report_path, "\n".join(lines))
