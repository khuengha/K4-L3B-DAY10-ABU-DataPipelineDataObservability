# Corruption & Repair Report — Đối chiếu 3 trạng thái

## 1. Bảng đối chiếu hiệu năng: Baseline vs Corrupted vs Repaired

| Chỉ số | Baseline | Corrupted | Repaired | Δ Corrupted | Δ Repaired |
|---|---|---|---|---|---|
| `retrieval_hit_rate` | 100.00% | 80.00% | 100.00% | -0.2000 | +0.0000 |
| `mean_token_f1` | 100.00% | 88.50% | 100.00% | -0.1150 | +0.0000 |
| `judge_accuracy` | 100.00% | 90.00% | 100.00% | -0.1000 | +0.0000 |
| `mean_judge_score` | 5 | 4.4000 | 5 | -0.6000 | +0.0000 |

## 2. Data Quality Gate & Freshness

- Corrupted quality gate: ❌ FAIL (phát hiện lỗi — đúng kỳ vọng) (7 expectations)
- Repaired quality gate: ✅ PASS

- Corrupted is_fresh: ❌ False (stale 10/22)
- Repaired is_fresh: ✅ True (stale 1/24)

## 3. Phân tích hiện tượng Silent Failure

- **Corrupted:** các kịch bản làm bẩn (mất bản ghi mới, blank summary, noise, truncate title, stale date, duplicate rows) làm chỉ số retrieval/answer sụt giảm so với baseline trong khi hệ thống vẫn có vẻ vận hành bình thường — đây chính là **Silent Failure**.
- **Quality Gate:** Great Expectations 1.x phát hiện vi phạm trên dữ liệu corrupted, chứng minh data observability chặn lỗi trước khi dữ liệu tới serving layer.
- **Repaired:** pipeline repair idempotent tái tạo dữ liệu sạch từ raw snapshot (`data/raw/crossref_records.json`), chỉ số quay về ngang baseline — chứng minh năng lực self-healing.

## 4. Kết luận

Dữ liệu chất lượng kém làm RAG suy giảm nghiêm trọng nhưng quality gate phát hiện được và repair khôi phục đầy đủ. Data observability là lớp phòng thủ thiết yếu của pipeline AI production.