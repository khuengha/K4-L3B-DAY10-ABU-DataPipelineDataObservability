# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `ABU`
- **Mã Nhóm / Lớp:** `K4-L3B-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3B-DAY10-ABU-DataPipelineDataObservability`

---

## Thành viên

| STT | Họ và tên | MSSV | Vai trò & Phân công công việc | Checkpoint | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Nguyễn Hà Khuê | 2A202602938 | Trưởng nhóm / Pipeline Integrator — Ingestion, Cleaning & Baseline (`crossref.py`, `cleaning.py`, `phase1.py`) | CP0, CP1, CP3 | `report/2A202602938_NguyenHaKhue.md` |
| 2 | Nguyễn Hoàng Anh | 2A202602811 | Corruption & Recovery — 6 kịch bản làm bẩn dữ liệu, Idempotent Repair (`corruption.py`, `corruption_flow.py`, QA Agent) | CP4, CP5 | `report/2A202602811_NguyenHoangAnh.md` |
| 3 | Nguyễn Huy Hoàng | 2A202602738 | Observability & Evaluation — GX 1.x Quality Gate, Test Set, báo cáo (`quality.py`, `testset.py`, `reporting.py`) | CP2, quality/freshness CP1 | `report/2A202602738_NguyenHuyHoang.md` |

---

## Cá nhân

### Nguyễn Hà Khuê - 2A202602938
- **Vai trò:** Trưởng nhóm & Điều phối Pipeline — **CP0, CP1, CP3**.
- **Công việc chi tiết đã hoàn thành:**
  - Implement Ingestion Crossref trong `src/ingestion/crossref.py`: parse payload, retry 429/503, fallback snapshot local.
  - Implement `src/ingestion/cleaning.py`: strip JATS XML, khử trùng lặp, tính `age_days`, ghép `text_for_embedding` 5 phần.
  - Kết nối luồng thực thi Baseline trong `src/pipelines/phase1.py` và chạy artifacts `baseline_metrics.json`.
- **Điều học được / Đóng góp chính:**
  - Data Lineage: bảo toàn raw snapshot trước khi biến đổi, retry/fallback khi API lỗi.
  - Thiết kế luồng pipeline end-to-end Ingestion → Cleaning → Indexing → Evaluation.

### Nguyễn Hoàng Anh - 2A202602811
- **Vai trò:** Phụ trách Corruption, Repair & RAG Agent — **CP4, CP5**.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng 6 kịch bản Synthetic Data Corruption trong `src/ingestion/corruption.py` + `corruption_log.json`.
  - Thực thi cơ chế Idempotent Repair trong `src/pipelines/corruption_flow.py` phục hồi dữ liệu từ raw snapshot.
  - Hiểu và bảo trì QA Agent & vector index (`src/retrieval/`) phục vụ demo.
- **Điều học được / Đóng góp chính:**
  - Kỹ thuật Idempotent Repair và chứng minh Silent Failure qua 3 trạng thái dữ liệu.

### Nguyễn Huy Hoàng - 2A202602738
- **Vai trò:** Phụ trách Data Observability & Benchmark Evaluation — **CP2, phần quality/freshness CP1**.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập Quality Gate theo chuẩn **Great Expectations 1.x** và giám sát Freshness SLA trong `src/observability/quality.py`.
  - Xây dựng bộ câu hỏi đánh giá 4 nhóm nghiệp vụ trong `src/evaluation/testset.py`.
  - Viết báo cáo đối chiếu (`src/observability/reporting.py`) và đo lường hiệu năng evaluation.
- **Điều học được / Đóng góp chính:**
  - Cách thiết lập hệ thống cảnh báo sớm chặn đứng hiện tượng Silent Failure trước khi dữ liệu vào serving layer.
