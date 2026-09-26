# Phase 1 Report — Baseline Pipeline

## 1. Nguồn dữ liệu (Data Lineage)

| Thông số | Giá trị |
|---|---|
| Source API | Crossref REST API |
| Query | `agentic retrieval augmented generation large language model` |
| Raw records | 24 |
| Clean records | 24 |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| ChromaDB collection | `papers-baseline` |
| Top-K retrieval | 4 |

## 2. Chỉ số hiệu năng Baseline

| Chỉ số | Giá trị |
|---|---|
| `samples` | 10 |
| `retrieval_hit_rate` | 100.00% |
| `mean_token_f1` | 100.00% |
| `judge_accuracy` | 100.00% |
| `mean_judge_score` | 5 |

## 3. Data Quality Gate (Great Expectations 1.x)

- **Status:** ✅ PASS
- Số expectation: 7

## 4. Freshness SLA

- **is_fresh:** ✅ True
- Tỷ lệ stale (> 180 ngày): 4.17% (1/24 bài)
- Ngày xuất bản: 2026-03-28 → 2026-07-22

## 5. Kết luận

Pipeline baseline chạy end-to-end trên dữ liệu sạch: ingestion → cleaning → quality gate → indexing → evaluation. Các chỉ số này làm mốc so sánh (baseline) cho giai đoạn corruption & repair.