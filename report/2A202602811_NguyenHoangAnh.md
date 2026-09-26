# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | [Nguyễn Hoàng Anh]             |
| MSSV               | [2A202602811]                     |
| Khóa/Lớp         | [K4]              |
| Tên nhóm         | [ABU]     |
| Vai trò chính    | [Corruption & Recovery — 6 kịch bản làm bẩn dữ liệu, Idempotent Repair CP4 CP5]                 |
| Repository         | [https://github.com/khuengha/K4-L3B-DAY10-ABU-DataPipelineDataObservability/tree/hoanganh] |
| Ngày hoàn thành | [2026-09-26]               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| [Synthetic Data Corruption]      | [src/ingestion/corruption.py — corrupt_clean_dataframe()]           | [Clean dataset từ Phase 1]          | [Corrupted dataset + corruption_log.json] | [Hoàn thành] |
| [Idempotent Repair & Impact Analysis]      | [src/pipelines/corruption_flow.py — repair_from_raw_snapshot(), run_corruption_flow_pipeline()]           | [Raw snapshot, clean dataset, test set]          | [Corrupted/Repaired datasets, metrics, quality reports, 3-state report] | [Hoàn thành] |

Chỉ nhận ownership cho phần bạn trực tiếp thực hiện. Liên hệ rõ phần việc của bạn với đầu vào, đầu ra và các thành viên phụ thuộc vào phần đó.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| [Tích hợp và kiểm tra flow CP5 với evaluation và vector index] | [evaluation/metrics.py, retrieval/index.py, observability/quality.py] | [Xác minh pipeline có thể chạy từ corruption → evaluation → repair → evaluation và sinh đầy đủ artifact] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| [Xây dựng bộ 6 kịch bản corruption] | [src/ingestion/corruption.py] | [data/results/corruption_log.json] | [Chạy corrupt_clean_dataframe()] |
| [Xây dựng pipeline repair từ raw snapshot] | [src/pipelines/corruption_flow.py] | [papers_clean_repaired.csv/json] | [Chạy python -m pipelines.corruption_flow] |
| [Đánh giá tác động của corruption lên RAG] | [src/pipelines/corruption_flow.py, evaluation/metrics.py] | [corrupted_metrics.json, corrupted_answers.json] | [Evaluation trên cùng test set] |
| [Đánh giá khả năng phục hồi] | [src/pipelines/corruption_flow.py] | [repaired_metrics.json, repaired_answers.json] | [So sánh với baseline] |
| [Tạo báo cáo 3 trạng thái] | [data/reports/corruption_report.md] | [Baseline / Corrupted / Repaired comparison] | [Kiểm tra report và metrics thực tế] |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

[corruption làm retrieval_hit_rate giảm từ 100% xuống 80%, mean_token_f1 từ 100% xuống 88.5%, judge_accuracy từ 100% xuống 90%; sau repair, các metric phục hồi về 100%.]

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

[Phần của tôi tập trung vào việc mô phỏng các lỗi dữ liệu có thể xảy ra trong pipeline và kiểm tra ảnh hưởng của chúng đến hệ thống RAG. Sau đó xây dựng cơ chế khôi phục dữ liệu từ raw snapshot thay vì sửa trực tiếp dataset đã bị corruption.

Clean Data -> Corruption -> Quality / Freshness degradation -> RAG performance degradation -> Repair from Raw Snapshot -> Quality recovery + RAG recovery]

### Cách triển khai

[Bộ corruption gồm 6 nhóm:
- Drop latest records
- Blank summary
- Inject noise
- Truncate title
- Stale date
- Duplicate rows
Các thay đổi được ghi lại trong corruption_log.json để có thể audit và tái kiểm tra.

Đối với repair, pipeline không sửa trực tiếp corrupted dataset. Thay vào đó, đọc lại raw snapshot bằng load_raw_records(), sau đó chạy lại quy trình build_clean_dataframe() để tạo dataset sạch mới.
Pipeline CP5 thực hiện:Baseline Load -> Corruption -> Quality & Freshness -> Corrupted Index + Evaluation -> Repair from Raw Snapshot -> Repaired Quality & Freshness -> Repaired Index + Evaluation -> 3-State Report]

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | [Clean dataset, raw snapshot data/raw/crossref_records.json, evaluation test set và baseline metrics]           |
| Output                         | [Corrupted/Repaired datasets, corruption log, metrics, quality/freshness reports và comparison report] |
| Module phụ thuộc             | [ingestion.crossref, ingestion.cleaning, ingestion.corruption, evaluation.metrics, retrieval.index, observability.quality, observability.reporting]                    |
| Module sử dụng output        | [Evaluation, observability và báo cáo tổng hợp]                    |
| Điều kiện lỗi cần xử lý | [Thiếu raw snapshot, thiếu baseline artifacts, repaired dataset không khớp baseline về số lượng hoặc paper_id]                   |

### Cách xác minh

```bash
[python -m pipelines.corruption_flow]
```

- **Kết quả mong đợi:** [Pipeline hoàn thành toàn bộ Baseline → Corrupted → Repaired và sinh comparison report.]
- **Kết quả thực tế:** [Pipeline hoàn thành và tạo đầy đủ corrupted/repaired artifacts.]
- **Artifact/log:** [data/results/corruption_log.json, data/results/corrupted_metrics.json, data/results/repaired_metrics.json, data/reports/corruption_report.md]

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** [Sau khi dữ liệu bị corruption, có hai hướng: sửa trực tiếp từng lỗi trên corrupted dataset hoặc tạo lại dataset sạch từ raw snapshot.]
- **Các phương án đã cân nhắc:** [
    1. Sửa trực tiếp từng record bị corruption.
    2. Xây dựng lại dataset từ raw snapshot và chạy lại cleaning pipeline.]
- **Phương án đã chọn:** [Xây dựng lại từ raw snapshot.]
- **Lý do:** [Raw snapshot là nguồn dữ liệu gốc, giúp giảm phụ thuộc vào trạng thái corrupted hiện tại và phù hợp với yêu cầu Idempotent Repair. Cách này cũng dễ kiểm chứng hơn bằng cách so sánh paper_id và metrics với baseline.]
- **Bằng chứng quyết định phù hợp:** [Dataset repaired khôi phục từ 22 record corrupted về 24 record và các metrics RAG trở lại mức baseline: 100% / 100% / 100%]

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** [Ban đầu src/ingestion/corruption.py và src/pipelines/corruption_flow.py chưa có implementation hoàn chỉnh.]
- **Lệnh hoặc bước tái hiện:** [Kiểm tra source và chạy pipeline trước khi implementation.]
- **Nguyên nhân gốc:** [Các module CP4/CP5 mới chỉ có skeleton/TODO.]
- **Cách xử lý:** [Implement bộ corruption trong corruption.py và xây dựng end-to-end corruption → evaluation → repair → evaluation trong corruption_flow.py.]
- **Cách xác minh sau khi sửa:** [
python -m py_compile src/pipelines/corruption_flow.py
python -m pipelines.corruption_flow
]
- **Điều học được:** [Với data pipeline, cần kiểm tra cả artifact dữ liệu và downstream metrics; việc pipeline chạy không lỗi chưa đảm bảo chất lượng dữ liệu và chất lượng RAG vẫn đúng.]

Nếu chưa xử lý xong:

- **Phạm vi bị ảnh hưởng:** [Module/artifact.]
- **Những gì đã loại trừ:** [Các giả thuyết đã kiểm tra.]
- **Bước tiếp theo:** [Hành động có thể kiểm chứng.]

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

[
1. Dữ liệu đi từ Crossref đến vector index như thế nào?

Dữ liệu được lấy từ Crossref và lưu thành raw snapshot. Sau đó pipeline cleaning chuẩn hóa dữ liệu thành clean dataset. Dataset sạch được dùng để tạo embedding và xây dựng vector index. Retrieval sử dụng vector index để tìm các document liên quan đến câu hỏi của evaluation set.

2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?

Evaluation set chứa các câu hỏi cùng document ID được xem là ground truth. Retrieval được đánh giá bằng việc kiểm tra document được truy xuất có chứa ground-truth document hay không. Sau đó câu trả lời được đánh giá thêm bằng token F1 và LLM judge.

3. Quality checks khác freshness monitoring ở điểm nào?

Quality checks kiểm tra các thuộc tính về tính hợp lệ và chất lượng của dữ liệu, chẳng hạn missing values, duplicate hoặc các điều kiện schema/content.

Freshness monitoring tập trung vào độ mới của dữ liệu, dựa trên thông tin thời gian và ngưỡng freshness được cấu hình.

4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?

Dùng cùng test set giúp giữ nguyên điều kiện đánh giá giữa ba trạng thái. Vì vậy sự thay đổi của metrics có thể được đối chiếu trực tiếp với trạng thái dữ liệu thay vì do test set khác nhau.

5. Repair được xem là thành công dựa trên artifact và metric nào?

Repair được kiểm tra bằng:

Dataset repaired có số lượng record và tập paper_id phù hợp với baseline.
Repaired Quality Gate đạt PASS.
Freshness được phục hồi.
repaired_metrics.json được tạo từ evaluation thực tế.
Các metrics repaired phục hồi về mức baseline trong lần chạy hiện tại.
]

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      [100%] |       [80%] |      [100%] | [Corruption làm giảm khả năng truy xuất đúng document, sau repair phục hồi về baseline.]              |
| `mean_token_f1`      |      [100%] |       [88.5%] |      [100%] | [Chất lượng câu trả lời giảm khi dữ liệu bị biến đổi và phục hồi sau repair.]              |
| `judge_accuracy`     |      [100%] |       [90%] |      [100%] | [LLM judge ghi nhận chất lượng answer giảm trên corrupted data.]              |
| `mean_judge_score`   |      [5.0] |       [4.4] |      [5.0] | [Điểm đánh giá trung bình giảm trên corrupted data và phục hồi sau repair.]              |
| Quality checks         |      [PASS] |       [FAIL] |      [PASS] | [Corrupted dataset có các vi phạm quality, repaired dataset đạt lại quality gate.]              |
| Freshness status       |      [—] |       [False] |      [True] | [Corrupted data có stale records; repaired data phục hồi freshness theo ngưỡng kiểm tra.]              |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. [Corruption] → [Quality Gate FAIL + is_fresh=False] → [retrieval_hit_rate 100% → 80%] → [mean_token_f1 100% → 88.5%] → [judge_accuracy 100% → 90%].
2. [Repair from raw snapshot] → [Quality Gate PASS + is_fresh=True] → [retrieval_hit_rate 80% → 100%] → [mean_token_f1 88.5% → 100%] → [judge_accuracy 90% → 100%].

Corruption nào ảnh hưởng rõ nhất và vì sao?

[Corruption ảnh hưởng rõ nhất đến retrieval hit rate, giảm 20 điểm phần trăm so với baseline. Điều này cho thấy việc thay đổi hoặc loại bỏ thông tin trong corpus có thể trực tiếp làm giảm khả năng truy xuất đúng tài liệu.]

Kết quả nào khác với kỳ vọng ban đầu?

[Kết quả thực tế cho thấy corrupted dataset không làm toàn bộ pipeline dừng hoặc crash. Thay vào đó, pipeline vẫn tạo index và trả lời câu hỏi nhưng các metrics giảm. Đây là minh họa rõ cho hiện tượng silent failure trong data pipeline.]

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. [Dữ liệu cần được kiểm soát từ raw snapshot đến serving; việc pipeline chạy thành công không đồng nghĩa dữ liệu đầu vào luôn đúng.]
2. [Quality và freshness cần được kiểm tra độc lập để phát hiện các loại lỗi dữ liệu khác nhau.]
3. [Những thay đổi nhỏ trong corpus như missing summary, truncate title hoặc duplicate có thể ảnh hưởng đến retrieval và answer quality.]

### Nếu có thêm thời gian

[Có thể mở rộng repair flow thành cơ chế tự động:

Quality Gate FAIL → Trigger Repair → Rebuild Index → Re-evaluate → Compare với Baseline

Sau đó đo thêm thời gian repair, số lượng record được phục hồi và mức chênh lệch metrics trước/sau repair.]

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Nguyễn Hoàng Anh]
**Ngày xác nhận:** [2026-09-26]
