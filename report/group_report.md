# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
|---|---|
| Khóa/Lớp | K4-L3B |
| Tên nhóm | ABU |
| Repository | [K4-L3B-DAY10-ABU-DataPipelineDataObservability](https://github.com/khuengha/K4-L3B-DAY10-ABU-DataPipelineDataObservability) |
| Ngày hoàn thành | 2026-09-26 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Hà Khuê | 2A202602938 | Trưởng nhóm / Pipeline Integrator — CP0, CP1, CP3 | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/pipelines/phase1.py`, `src/observability/reporting.py`, artifacts raw/clean/baseline |
| 2 | Nguyễn Hoàng Anh | 2A202602811 | Corruption & Recovery — CP4, CP5 | `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py`, artifacts corrupted/repaired |
| 3 | Nguyễn Huy Hoàng | 2A202602738 | Observability & Evaluation — CP2, quality CP1 | `src/evaluation/testset.py`, `src/observability/quality.py`, artifacts eval/quality |

## 2. Tóm tắt kết quả

Nhóm hoàn thành đầy đủ 7 checkpoint (CP0–CP6): pipeline ingestion → cleaning → GX 1.x quality gate → ChromaDB indexing → evaluation baseline chạy end-to-end, sau đó là chuỗi corruption 6 kịch bản, đo lường suy giảm và repair idempotent từ raw snapshot. Baseline pipeline sinh đủ artifacts: 24 raw records (`data/raw/`), 24 dòng sạch (`data/clean/`), test set 10 câu thuộc 4 nhóm nghiệp vụ (`data/eval/test_set.json`), collection `papers-baseline` với 24 documents, `baseline_metrics.json` (hit_rate 1.00, token_f1 1.00) và `phase1_report.md`. Corruption ảnh hưởng rõ nhất là `drop_latest_records`: xóa 4/24 bài mới nhất làm `retrieval_hit_rate` sụt từ 1.00 xuống 0.80 (mất vĩnh viễn 2 ground-truth docs); `blank_summary` kéo `mean_token_f1` xuống 0.885. Quality gate phát hiện đúng 4/7 expectations vi phạm và freshness rơi xuống `is_fresh=False` (45.45% stale) — chứng minh hiện tượng Silent Failure. Repair rebuild sạch từ `data/raw/crossref_records.json`, cho metrics quay về đúng 100% baseline (1.00/1.00/1.00). Blocker lớn nhất nhóm gặp là môi trường: console Windows cp1252 crash khi print Unicode, đã xử lý bằng ASCII-safe output; giới hạn còn lại là chưa có pytest CI (bonus B3) và Ragas bị tắt mặc định.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API / local snapshot (data/raw/)          [CP0 - Khuê]
    -> parse_crossref_payload -> PaperRecord (24)
    -> build_clean_dataframe (strip JATS, dedupe, age_days,
       text_for_embedding 5 phần)                    [CP1 - Khuê]
    -> GX 1.x quality gate + freshness SLA           [CP1 quality - Huy Hoàng]
    -> build_test_set (10 câu, 4 types)              [CP2 - Huy Hoàng]
    -> MiniLM embeddings -> ChromaDB papers-baseline [CP2/CP3]
    -> evaluate_pipeline -> baseline_metrics.json    [CP3 - Khuê]
    -> corrupt_clean_dataframe (6 kịch bản)          [CP4 - Hoàng Anh]
    -> corrupted quality/freshness -> corrupted index -> corrupted_metrics
    -> repair_from_raw_snapshot (idempotent)         [CP5 - Hoàng Anh]
    -> repaired quality/freshness -> repaired index -> repaired_metrics
    -> corruption_report.md (3 trạng thái)
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
|---|---|---|---|---|
| Ingestion | Crossref API / snapshot | Fetch + retry 429/503 exponential backoff, fallback local, parse payload | `data/raw/crossref_response.json`, `crossref_records.json` | Khuê |
| Cleaning | `list[PaperRecord]` + run_date | Strip JATS XML, dedupe `paper_id`, `age_days`, `text_for_embedding` | `data/clean/papers_clean.csv.json`| Khuê
| Embedding/index | Clean df | `all-MiniLM-L6-v2`, ChromaDB cosine, 3 collections | `data/chroma/`, `data/embeddings/*.json` | (scaffold sẵn) cả nhóm review |
| Evaluation | Test set + index | Hit rate, token F1, LLM judge, Ragas tùy chọn | `data/results/*_metrics.json`, `*_answers.json` | Huy Hoàng |
| Observability | Clean df (mỗi trạng thái) | GX 1.x ephemeral, 7 expectations, freshness SLA 25% | `data/quality/*_quality_report.json`, `*_freshness_report.json` | Huy Hoàng |
| Corruption/repair | Clean df / raw snapshot | 6 kịch bản + log; rebuild idempotent + kiểm chứng nhất quán | `corruption_log.json`, `*_corrupted/repaired_clean.*`, metrics | Hoàng Anh |
| Orchestration | Settings | `phase1.py` (baseline), `corruption_flow.py` (3 trạng thái) | `phase1_report.md`, `corruption_report.md` | Khuê + Hoàng Anh |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
|---|---|
| `LLM_PROVIDER` | `openai` |
| `LLM_MODEL` | `gpt-4o-mini` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 (`max_results`) |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày, stale ratio tối đa 25% |
| Random seed, nếu có | Không dùng randomness — pipeline deterministic (test set sinh theo thứ tự ngày xuất bản) |

### Lệnh cài đặt

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # điền OPENAI_API_KEY
```

### Lệnh chạy

```bash
cd src
python ..\script\run_phase1.py
python ..\script\run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
|---|---|---|---|
| Baseline pipeline | Thành công (exit 0) | 2026-09-26 | `baseline_metrics.json` (hit_rate 1.00), `phase1_report.md` |
| Corruption flow | Thành công (exit 0) | 2026-09-26 | `corrupted_metrics.json` (0.80/0.885), `repaired_metrics.json` (1.00/1.00), `corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
|---|---|
| Source | Crossref REST API `https://api.crossref.org/works` (fallback snapshot `data/raw/crossref_response.json`) |
| Query/filter | `query="agentic retrieval augmented generation large language model"`, `filter=from-pub-date:<run_date-180d>,has-abstract:true`, `rows=24` |
| Thời điểm lấy dữ liệu | Snapshot gốc kèm repo; lần fetch lại gần nhất 2026-09-26 |
| Số record nhận được | 24 (24 record hợp lệ sau parse) |
| Cơ chế retry/backoff | 4 lần, exponential backoff 2s/4s/8s cho HTTP 429/503 và lỗi network; sau đó fallback snapshot local |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
|---|---|---|---|---|
| `paper_id` | string (slug của DOI) | Có | Định danh document, dedupe key | Bỏ record nếu thiếu DOI |
| `title` | string | Có | Tiêu đề paper | Bỏ record nếu rỗng |
| `summary` | string | Có (raw giữ nguyên; clean strip JATS) | Abstract dùng cho embedding/QA | Bỏ record nếu rỗng sau strip |
| `published` | string `YYYY-MM-DD` | Có | Ngày xuất bản, gốc tính `age_days` | Bỏ record nếu parse fail |
| `authors_joined` | string "A, B" | Không | Metadata phục vụ QA type authors | Chuỗi rỗng nếu không có tác giả |
| `categories_joined` | string | Không | Metadata phục vụ QA type categories | Chuỗi rỗng |
| `age_days` | int | Có (clean) | Tuổi bài so với run_date | Clamp >= 0 |
| `text_for_embedding` | string 5 phần | Có (clean) | Nội dung được embed | Bắt buộc non-empty trước khi index |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
|---|---|---:|---|
| Strip `<jats:...>` tags + normalize whitespace khỏi abstract | Validity | 24 (tất cả abstract đều bọc JATS) | `papers_clean.json` — summary không còn `<jats:` |
| Dedupe theo `paper_id` (keep first) | Uniqueness | 0 ở baseline (corruption sẽ tạo dup → repaired về 0) | GX `expect_column_values_to_be_unique` |
| Bỏ record thiếu DOI/title/summary/published | Completeness | 0 ở baseline | Row count = 24 |
| Clamp `age_days >= 0` | Validity | 0 | GX + freshness report `invalid_age_rows=0` |

`text_for_embedding` được tạo theo cấu trúc 5 phần cố định: `Title: ... / Authors: ... / Categories: ... / Published: ... / Summary: ...` — title đứng đầu để semantic search trúng câu hỏi có tên paper. `paper_id` = `safe_slug(DOI)` để làm document ID ổn định, tất cả so sánh doc id trong evaluation đều dùng chuỗi này (lowercase bên phía index).

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
|---|---|
| Số câu hỏi | 10 |
| Các `question_type` | `summary`, `authors`, `date`, `categories` (luân vòng: 3/3/2/2) |
| Ground-truth document ID | `paper_id` (slug DOI) của paper sinh câu hỏi, ghi trong `ground_truth_doc_ids` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | ChromaDB persist tại `data/chroma/`, collections: `papers-baseline`, `papers-corrupted`, `papers-repaired` (cosine) |
| Retrieval `top_k` | 4 |
| LLM provider/model | `openai` / `gpt-4o-mini` (judge; fallback heuristic nếu LLM unavailable) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` — cùng 1 file cho baseline/corrupted/repaired |

Câu hỏi được thiết kế khớp pattern trong `qa.py` ("Who authored...", "When was ... published?", "What categories...") và câu summary/authors/date/categories chứa title nguyên văn trong ngoặc kép để agent exact-lookup đúng paper. Test set được giữ nguyên cho cả 3 trạng thái để biến độc lập duy nhất là chất lượng dữ liệu: nếu đổi test set thì không tách được hiệu ứng corrupt/repair khỏi hiệu ứng câu hỏi.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
|---|---|---|---|
| Raw response/records | `data/raw/` | Có | 24 records, bất biến (lineage) |
| Cleaned dataset | `data/clean/` | Có | `papers_clean.csv` + `.json`, 24 dòng |
| Embedding manifest/index | `data/embeddings/`, `data/chroma/` | Có | Manifest 3 trạng thái + ChromaDB persist |
| Evaluation set | `data/eval/` | Có | `test_set.json`, 10 câu |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Kèm `baseline_answers.json` chi tiết từng câu |
| Quality/freshness | `data/quality/` | Có | baseline/corrupted/repaired quality + freshness + GX suite JSON |
| Baseline report | `data/reports/phase1_report.md` | Có | Sinh tự động từ `reporting.py` |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
|---|---:|---|
| `retrieval_hit_rate` | 1.00 | 10/10 câu retrieve đúng paper ground truth trong top-4 |
| `mean_token_f1` | 1.00 | Đáp án trích xuất khớp chính xác ground truth (dữ liệu sạch) |
| `judge_accuracy` | 1.00 | LLM judge xác nhận 10/10 câu đúng |
| `mean_judge_score` | 5.0 | Điểm tối đa |
| Ragas | N/A | Không bật (`RUN_RAGAS` unset) để giữ thời gian chạy demo — có thể bật bằng env |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Kết quả corrupted | Bằng chứng |
|---|---|---|---|---|---|
| `expect_table_row_count_to_be_between` | Completeness | 24 (min=max=24) | PASS (24) | FAIL (22) | `data/quality/{baseline,corrupted}_quality_report.json` |
| `expect_column_values_to_not_be_null(paper_id)` | Validity | 0 null | PASS | PASS | như trên |
| `expect_column_values_to_be_unique(paper_id)` | Uniqueness | 0 duplicate | PASS | FAIL (4 dòng dup) | như trên |
| `expect_column_values_to_not_be_null(title)` | Completeness | 0 null | PASS | PASS | như trên |
| `expect_column_value_lengths_to_be_between(title, min 8)` | Validity | >= 8 ký tự | PASS | FAIL (2 title bị truncate) | như trên |
| `expect_column_values_to_not_be_null(summary)` | Completeness | 0 null | PASS | PASS (rỗng ≠ null, bắt bởi length) | như trên |
| `expect_column_value_lengths_to_be_between(summary, min 1)` | Validity | >= 1 ký tự | PASS | FAIL (2 summary rỗng) | như trên |

Baseline: **7/7 PASS**. Corrupted: **3/7 PASS, 4 vi phạm** → quality gate báo động đúng kỳ vọng.

### Freshness

| Thuộc tính | Giá trị |
|---|---|
| Freshness được đo tại | Clean dataframe của từng trạng thái (baseline/corrupted/repaired), trường `age_days` |
| Timestamp mới nhất / cũ nhất | 2026-07-22 / 2026-03-28 (baseline) |
| Ngưỡng freshness | `age_days > 180` tính là stale; `is_fresh=False` nếu stale ratio > 25% |
| Trạng thái baseline | **Fresh** (1/24 stale = 4.17%) |
| Lý do | Dữ liệu có filter `from-pub-date:<run_date - 180d>` nên gần như toàn bộ còn tươi; đúng 1 bài biên trên ngưỡng |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
|---|---|---:|---|---|---|
| `drop_latest_records` | Xóa 20% bài mới nhất (4 bài) | 4 | Row count FAIL | hit_rate 1.00→0.80 (2 câu mất ground-truth doc) | Rebuild từ raw snapshot |
| `blank_summary` | Gán summary = "" | 2 | summary length FAIL | token_f1 giảm (agent trả "I don't know" cho câu summary) | Rebuild từ raw snapshot |
| `inject_noise` | Chèn chuỗi rác `[CORRUPTED_NOISE_TEXT_XYZ_999]` vào summary | 2 | (chưa có max-length check → lọt gate) | Ảnh hưởng không đáng kể token_f1 (noise cuối summary) | Rebuild từ raw snapshot |
| `truncate_title` | Cắt title còn 5 ký tự | 2 | title length < 8 FAIL | Exact-lookup theo title fail cho bài đó | Rebuild từ raw snapshot |
| `stale_date` | Lùi `published` 365 ngày | 7 | Freshness: stale 1/24 → 10/22 (45.45%), `is_fresh=False` | Age questions trả ngày sai | Rebuild từ raw snapshot |
| `duplicate_rows` | Nhân bản 2 dòng | +2 dòng | paper_id unique FAIL | Làm sai lệch phân bố retrieval | Rebuild từ raw snapshot |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log đủ cả 6 loại, ghi rõ từng `affected_paper_ids`, tham số (drop_ratio 0.2, shift_days -365, max_chars 5, noise string) và giá trị trước/sau cho stale_date — đủ truy vết từng lỗi.

Repair đảm bảo phục hồi từ nguồn đáng tin cậy thay vì che lỗi: `repair_from_raw_snapshot()` đọc lại `data/raw/crossref_records.json` (raw artifact bất biến của CP0), chạy lại toàn bộ `build_clean_dataframe` (quy trình cleaning chuẩn, không có bước nào "vá riêng cho corruption"), rồi kiểm chứng logic nhất quán trước khi đánh giá: số dòng và tập `paper_id` của repaired phải trùng khớp baseline, nếu không pipeline raise. Đây là tính **idempotent**: repair có chạy nhiều lần trên dữ liệu raw cho cùng kết quả, không phụ thuộc trạng thái corrupted.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
|---|---:|---:|---:|---:|---:|---|
| `retrieval_hit_rate` | 1.00 | 0.80 | 1.00 | -0.20 | 100% | Mất 2/10 ground-truth docs do drop_latest_records |
| `mean_token_f1` | 1.00 | 0.885 | 1.00 | -0.115 | 100% | blank_summary là nguyên nhân chính |
| `judge_accuracy` | 1.00 | 0.80 | 1.00 | -0.20 | 100% | 2/10 câu judge đánh sai trên corrupted |
| `mean_judge_score` | 5.0 | 4.4 | 5.0 | -0.6 | 100% | — |
| Quality checks pass/fail | PASS (7/7) | FAIL (3/7) | PASS (7/7) | 4 vi phạm | 100% | Gate phát hiện đủ row count/unique/title/summary |
| Freshness status | Fresh (4.17%) | Stale (45.45%, is_fresh=False) | Fresh (4.17%) | +41.28 điểm phần trăm stale | 100% | stale_date + drop bài mới đẩy ratio vượt SLA 25% |

Kết luận nhân quả:

1. **Corruption → quality signal → agent metric:** `drop_latest_records` (4 bài) + `blank_summary` (2 bài) → index thiếu ground-truth documents → `retrieval_hit_rate` 1.00→0.80, `mean_token_f1` 1.00→0.885, `judge_accuracy` 1.00→0.80; song song `duplicate_rows`/`truncate_title`/`stale_date` → GX gate FAIL 4/7 + `is_fresh=False`. Pipeline vẫn exit 0 — Silent Failure được chất lượng chứng minh bằng artifacts, không bằng lời.
2. **Repair → quality recovery → agent recovery:** rebuild từ raw snapshot → quality gate PASS 7/7, freshness 4.17% → toàn bộ metrics về đúng 1.00/1.00/1.00. Self-healing thành công và được xác minh bằng so sánh tập `paper_id` repaired vs baseline trong `corruption_flow.py`.

Kết quả khác kỳ vọng: nhóm dự đoán `inject_noise` làm token_f1 giảm mạnh nhất, thực tế gần như không ảnh hưởng (noise nằm cuối summary, đáp án type summary lấy câu đầu tiên). Đã kiểm chứng bằng cách đọc `corrupted_answers.json` đối chiếu từng câu miss — 2 câu miss đều do paper bị drop hoặc blank summary.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** `run_phase1.py` crash giữa chừng với `UnicodeEncodeError: 'charmap' codec can't encode character '\u1ea1'` (console Windows cp1252), dù logic pipeline đúng.
- **Nguyên nhân:** print tiếng Việt có dấu trên stdout Windows không cấu hình UTF-8; lỗi chỉ xuất hiện khi redirect output, gây khó debug.
- **Cách xử lý:** chuẩn hóa toàn bộ output console của pipeline sang ASCII thuần (giữ nội dung tiếng Việt đầy đủ trong markdown reports, vốn ghi file UTF-8).
- **Cách xác minh:** chạy lại `python script/run_phase1.py` và `python script/run_corruption_flow.py` → cả hai exit 0, đủ artifacts (log chạy 2026-09-26).

Vấn đề tích hợp thứ hai: `quality.py` bản cải tiến trả key `results` (GX `to_json_dict`) trong khi `reporting.py` đọc `checks` → report hiện "0 expectations". Đã fix `reporting.py` đọc fallback `results` trước `checks`, xác minh qua `phase1_report.md` hiển thị đúng 7 expectations.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
|---|---|---|
| Chưa có max-length expectation cho `summary` | Kịch bản `inject_noise` lọt quality gate | Thêm `ExpectColumnValueLengthsToBeBetween(summary, max_value=4000)` → gate phải FAIL trên corrupted (đo được ngay bằng corruption_log) |
| Exact-lookup theo title fail khi title chứa nháy đơn | 1 loại câu hỏi có thể miss trên corpus thật | Fallback tìm title sau khi strip dấu nháy; đo bằng hit_rate trên test set mở rộng |
| Chưa có pytest CI (bonus B3) | Không tự phát hiện regression | Thêm test cho parsing/cleaning/quality + GitHub Actions, mục tiêu coverage `ingestion/` > 80% |
| Ragas tắt mặc định | Thiếu các chỉ số faithfulness/context precision | Bật `RUN_RAGAS=1` cho lần chạy chính thức, lưu vào metrics JSON |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set (`data/eval/test_set.json`).
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
