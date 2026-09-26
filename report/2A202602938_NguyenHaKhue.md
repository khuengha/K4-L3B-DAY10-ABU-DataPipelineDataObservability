# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Nguyễn Hà Khuê |
| MSSV | 2A202602938 |
| Khóa/Lớp | K4 |
| Tên nhóm | ABU |
| Vai trò chính | Trưởng nhóm / Pipeline Integrator (Ingestion, Cleaning, Baseline Pipeline) |
| Repository | [Branch Khue](https://github.com/khuengha/K4-L3B-DAY10-ABU-DataPipelineDataObservability/tree/Khue) |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|---|---|---|---|---|
| CP0 — Ingestion | `src/ingestion/crossref.py` (`parse_crossref_payload`, `fetch_source_records`, `load_raw_records`) | Crossref API response / local snapshot | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` (24 records) | Hoàn thành |
| CP1 — Cleaning | `src/ingestion/cleaning.py` (`build_clean_dataframe`) | List `PaperRecord` + run_date | `data/clean/papers_clean.csv`, `papers_clean.json` (24 dòng) | Hoàn thành |
| CP3 — Baseline pipeline | `src/pipelines/phase1.py` (`main`) | Clean dataframe, test set | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md`, ChromaDB `papers-baseline` | Hoàn thành |
| Report generator | `src/observability/reporting.py` (`generate_phase1_report`, `generate_corruption_report`) | Metrics + quality + freshness | Markdown report 3 trạng thái | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|---|---|---|
| Phân lại Team assignment, xóa template thừa trong `docs/TEAM.md` | Cả nhóm | Phân công đều 3–3–3 theo checkpoint (CP0/1/3 — CP4/5 — CP2) |
| Fix reporting đọc sai key (`checks` vs `results`) sau khi bản GX quality gate mới được merge | Nguyễn Huy Hoàng (`quality.py`) | `phase1_report.md` hiển thị đúng số expectation = 7 |
| Review `testset.py` (contract với `qa.py` pattern matching) | Nguyễn Huy Hoàng | 10 câu khớp 100% pattern, signal CP2 đạt |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Parse Crossref payload, retry 429/503, fallback snapshot local | `crossref.py` | 24 `PaperRecord` + 2 raw JSON | Lệnh tín hiệu CP0 in "Đã tải 24 bài báo" |
| Clean: strip JATS XML, dedupe `paper_id`, `age_days`, `text_for_embedding` 5 phần | `cleaning.py` | 24 dòng sạch | Lệnh tín hiệu CP1 in "Clean thành công 24 dòng" |
| Orchestrate end-to-end baseline | `phase1.py` | `baseline_metrics.json`, `phase1_report.md` | `python script/run_phase1.py` exit 0 |

Output cụ thể: `data/results/baseline_metrics.json` với `retrieval_hit_rate = 1.0`, `mean_token_f1 = 1.0`, `judge_accuracy = 1.0` trên 10 câu hỏi; `phase1_report.md` tổng hợp lineage, quality gate (PASS, 7 expectations), freshness (is_fresh=True, 1/24 stale).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Biến dữ liệu thô từ Crossref thành nguồn dữ liệu sạch, có truy vết (lineage), sẵn sàng cho embedding và đánh giá RAG; đồng thời chạy được cả khi mất mạng — vì demo trước lớp không được phụ thuộc network.

### Cách triển khai

- `parse_crossref_payload`: duyệt `payload["message"]["items"]`, trích DOI (slug thành `paper_id` qua `safe_slug`), title, abstract (chỉ normalize whitespace ở bước raw — JATS XML để cleaning strip), author `given`+`family`, subject, `published.date-parts` (đệm [1,1] cho thiếu ngày/tháng). Bỏ record thiếu DOI/title/ngày.
- `fetch_source_records`: nếu `REFRESH_SOURCE` không bật và `crossref_records.json` tồn tại → dùng snapshot (lineage bất biến). Ngược lại gọi `api.crossref.org/works` với retry 4 lần exponential backoff (2s/4s/8s) cho 429/503; nếu hết retry → fallback đọc `crossref_response.json` local. Luôn ghi cả 2 raw artifacts.
- `build_clean_dataframe`: strip `<jats:...>` bằng regex, dedupe theo `paper_id` (keep first), `age_days = (run_date - published).days`, `text_for_embedding` ghép 5 phần: Title / Authors / Categories / Published / Summary. Sort theo `published, paper_id` để chạy reproducer.
- `phase1.py`: nối chuỗi fetch → clean → quality gate → test set (reuse nếu đã có trừ khi `REFRESH_TEST_SET=1`) → `LocalEmbeddingIndex.build` → `evaluate_pipeline` → demo agent → report.

### Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input | Crossref payload dict / snapshot JSON; `Settings` từ `core/config.py` (không hardcode path) |
| Output | `PaperRecord(paper_id, title, summary, authors, categories, primary_category, published, updated, abs_url, pdf_url, comment)`; clean df 24 dòng với schema mà `index.py` yêu cầu |
| Module phụ thuộc | `core/config.py`, `core/utils.py`, `requests`, `pandas` |
| Module sử dụng output | `observability/quality.py`, `evaluation/testset.py`, `retrieval/index.py`, `evaluation/metrics.py` |
| Điều kiện lỗi cần xử lý | 429/503 API, mất mạng, record thiếu DOI/title/date, Unicode cp1252 console |

### Cách xác minh

```bash
cd src
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Đã tải {len(r)} bài báo')"
python ..\script\run_phase1.py
```

- **Kết quả mong đợi:** 24 records; pipeline exit 0; baseline metrics + report sinh ra.
- **Kết quả thực tế:** `Đã tải 24 bài báo`; `Baseline: hit_rate=1.00, token_f1=1.00, judge_acc=1.00`; exit 0.
- **Artifact/log:** `data/results/baseline_metrics.json`, `data/reports/phase1_report.md`, `data/results/agent_demo_answers.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Phải quyết định `fetch_source_records` ưu tiên API hay snapshot local.
- **Các phương án đã cân nhắc:** (a) Luôn gọi API trước, lỗi mới fallback; (b) Ưu tiên snapshot nếu tồn tại, chỉ gọi API khi `REFRESH_SOURCE` bật.
- **Phương án đã chọn:** (b).
- **Lý do:** Reproducibility — mọi lần chạy (của tôi, của giám khảo, của repair trong CP5) đều cùng một nguồn dữ liệu bất biến; tránh bị 429 khi cả lớp chạy cùng lúc; data lineage giữ nguyên raw ban đầu.
- **Bằng chứng quyết định phù hợp:** 2 lần chạy `run_phase1.py` cho kết quả metrics và report giống hệt nhau; CP5 repair cũng đọc từ cùng snapshot.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `UnicodeEncodeError: 'charmap' codec can't encode character '\u1ea1'` khi chạy `run_phase1.py` (print tiếng Việt có dấu trên console Windows cp1252).
- **Lệnh hoặc bước tái hiện:** `python ..\script\run_phase1.py` trên Windows không đặt `PYTHONIOENCODING`.
- **Nguyên nhân gốc:** Windows console mặc định cp1252; các print có ký tự Unicode tiếng Việt crash ở bước ghi stdout, không phải lỗi logic pipeline.
- **Cách xử lý:** Chuyển toàn bộ print trong `phase1.py` sang ASCII thuần ("dong sach", "CANH BAO"...).
- **Cách xác minh sau khi sửa:** Chạy lại `python script/run_phase1.py` → exit 0, đủ artifacts.
- **Điều học được:** Mã phải chạy được trên môi trường giám khảo (Windows mặc định), không chỉ trên máy mình — mọi output console cần ASCII-safe.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref → vector index:** API/snapshot → `PaperRecord` (raw JSON, lineage) → cleaning (strip JATS, dedupe, `text_for_embedding` 5 phần) → `MiniLMEmbeddings` biến mỗi `text_for_embedding` thành vector 384 chiều → ChromaDB collection `papers-baseline` lưu vector + metadata (paper_id, published, authors...).
2. **Evaluation set:** `testset.py` sinh 10 câu từ chính clean df, mỗi câu có `ground_truth` và `ground_truth_doc_ids`. Khi đánh giá: agent retrieve top-k từ Chroma, `retrieval_hit_rate` đo việc paper đúng có nằm trong top-k không; `token_f1` so token đáp án với ground truth; LLM judge chấm 1–5.
3. **Quality checks vs freshness:** Quality checks (GX) xác thực *schema/nội dung tại thời điểm chạy* (row count, not-null, unique, độ dài); freshness monitoring theo dõi *sự lỗi thời theo thời gian* (tỷ lệ `age_days > 180` vượt 25% → `is_fresh=False`) — cái là gate, cái là SLA thời gian.
4. **Cùng test set cho 3 trạng thái:** để so sánh công bằng — biến độc lập duy nhất là *chất lượng dữ liệu*, không phải bộ câu hỏi. Đổi test set sẽ không tách được hiệu ứng corrupt/repair khỏi hiệu ứng câu hỏi.
5. **Repair thành công khi:** quality gate trên dữ liệu repaired PASS (`repaired_quality_report.json` success=true), `is_fresh` trở về True, và `repaired_metrics.json` quay về ngang `baseline_metrics.json` (hit_rate/token_f1 ≈ baseline).

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
|---|---:|---:|---:|---|
| `retrieval_hit_rate` | 1.00 | 0.80 | 1.00 | Sụt 20% do `drop_latest_records` xóa 4/24 paper — 2 câu trong test set mất hẳn ground-truth doc khỏi index |
| `mean_token_f1` | 1.00 | 0.885 | 1.00 | Giảm do câu hỏi summary trúng paper bị `blank_summary` → agent trả "I don't know" |
| `judge_accuracy` | 1.00 | 0.80 | 1.00 | 2/10 câu bị đánh sai, khớp với 2 câu mất docs/summary |
| `mean_judge_score` | 5 | 4.4 | 5 | — |
| Quality checks | PASS (7/7) | FAIL (3/7, 4 vi phạm) | PASS (7/7) | Gate bắt được: row count 22≠24, `paper_id` duplicate ×4, title length < 8 ×2, summary rỗng ×2 |
| Freshness status | True (1/24 stale = 4.17%) | False (10/22 stale = 45.45%) | True (1/24 stale) | `stale_date` lùi 7 bài 365 ngày + drop 4 bài mới → ratio vượt ngưỡng SLA 25% |

### Kết luận từ số liệu

1. **Corruption → signal → agent:** `drop_latest_records` (xóa 4 bài mới nhất) + `blank_summary` (2 bài) làm agent mất ground-truth document hoặc mất nội dung trả lời → `retrieval_hit_rate` 1.00→0.80, `mean_token_f1` 1.00→0.885, `judge_accuracy` 1.00→0.80; đồng thời `duplicate_rows`/`truncate_title`/`stale_date` khiến GX gate FAIL 4/7 expectations và `is_fresh` False (45.45% stale > 25% SLA). Hệ thống vẫn chạy exit 0 nhưng chất lượng đã sụp — **Silent Failure đúng nghĩa**.
2. **Repair → signal phục hồi → agent phục hồi:** repair idempotent đọc lại `data/raw/crossref_records.json` (nguồn bất biến của CP0), rebuild clean df → quality gate PASS 7/7, freshness trở về 1/24 stale (4.17%), và toàn bộ metrics quay về đúng giá trị baseline (1.00/1.00/1.00) — chứng minh repair thành công và pipeline có khả năng self-healing.

**Corruption ảnh hưởng rõ nhất:** `drop_latest_records` — vì nó là lỗi duy nhất không thể "sống chung": paper đã mất khỏi index thì câu hỏi về nó không bao giờ hit được nữa (mất vĩnh viễn 20% hit rate), trong khi noise/duplicate chủ yếu làm giảm chất lượng context còn summary blank chỉ ảnh hưởng câu hỏi trúng bài đó.

Kết quả khác kỳ vọng: ban đầu tôi dự đoán `inject_noise` sẽ kéo `token_f1` xuống mạnh nhất, nhưng thực tế chỉ `blank_summary` và `drop_latest_records` mới làm giảm metrics (noise text nằm cuối summary, câu trả lời type summary lấy câu đầu nên gần như không bị ảnh hưởng); token_f1 giảm 0.115 thay vì dự đoán ~0.3. Tôi đã kiểm tra bằng cách đọc từng `*_answers.json` đối chiếu câu nào miss — xác nhận 2 câu miss đều do paper bị drop hoặc blank summary, không phải do noise. Baseline đạt 1.0 tuyệt đối không phải pipeline sai: bài báo là dữ liệu mô phỏng sạch, câu hỏi có title trích nguyên văn nên exact-match lookup luôn đúng, đáp án là trích xuất trực tiếp.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** raw data phải bất biến (lineage) — mọi biến đổi để tái tạo được; idempotency bắt đầu từ khâu ingestion, không chỉ repair.
2. **Data quality/observability:** quality gate có giá trị thật khi expectations được thiết kế để *bắt đúng kịch bản lỗi* (title ≥ 8 ký tự bắt truncate, not-null summary bắt blank), không chỉ để "pass cho có".
3. **Data → RAG:** chất lượng corpus quyết định trực tiếp retrieval/answer metrics; lỗi dữ liệu nhỏ (truncate title, noise) đủ làm hệ thống suy giảm mà console vẫn "bình thường" — Silent Failure.

### Nếu có thêm thời gian

Thêm unit test pytest cho `parse_crossref_payload` (payload thiếu field, date-parts không đầy đủ) và retry logic (mock 429) — đo bằng coverage > 80% cho module `ingestion/`, đồng thời phục vụ bonus B3.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Hà Khuê
**Ngày xác nhận:** 2026-09-26
