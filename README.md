# deep_think_tool

Ghi **toàn văn** luồng lập luận, các bước phân tích và dữ liệu kiểm chứng ra tệp log — không cắt ngắn nội dung.

Công cụ này dùng khi cần lưu vết suy luận để đối chiếu, kiểm thử hoặc kiểm toán sau này.

## Cài đặt

Python 3.10 trở lên.

```bash
pip install -e ".[dev]"
```

Sau khi cài, lệnh `deep-think` có sẵn trong môi trường.

Chạy trực tiếp từ mã nguồn:

```bash
python -m deep_think demo
```

## Dùng nhanh (Python)

```python
from deep_think import deep_think, DeepThinkLogger

deep_think(
    "Cần đọc toàn bộ danh mục, kiểm tra tính toàn vẹn, rồi mới chuyển đổi.",
    stage="Phân tích & Lập kế hoạch",
    steps=[
        "Quét thư mục gốc",
        "Phân loại tài liệu",
        "Kiểm tra định dạng và quyền truy cập",
    ],
    evidence={"nguon": "danh_muc_emg", "so_file": 128},
    tags=["planning"],
)
```

Nhóm nhiều bước trong một phiên:

```python
logger = DeepThinkLogger("session.jsonl", fmt="jsonl")

with logger.session(stage="Chuyển đổi", tags=["emg"]) as session:
    session.log("Bắt đầu quét thư mục gốc")
    session.log(
        "Đã lọc 12 file lỗi encoding",
        evidence={"invalid_files": 12},
        stage="Đánh giá rủi ro",
    )
```

Đọc lại log:

```python
for entry in logger.read():
    print(entry.entry_id, entry.stage, entry.thought_content[:80])
```

## Dùng nhanh (CLI)

```bash
deep-think log "Toàn văn phân tích..." \
  --stage "Kết luận" \
  --step "Đối chiếu checksum" \
  --step "Ghi báo cáo" \
  --tag audit \
  --evidence checksum=abc123 \
  --file deep_think_detailed.log

deep-think show --file deep_think_detailed.log --last 3
deep-think demo --jsonl --file demo.jsonl
```

Không truyền lệnh con thì `python -m deep_think` chạy `demo` (giữ hành vi mẫu như bản đầu).

## Định dạng log

- **text** (mặc định): văn bản UTF-8, có tiêu đề tiếng Việt, phù hợp đọc trực tiếp.
- **jsonl**: một object JSON mỗi dòng, phù hợp xử lý máy và grep.

Cả hai đều giữ nguyên toàn bộ nội dung (kể cả dấu phân cách, xuống dòng, Unicode). Hàm `read()` tự nhận diện text mới, JSONL, và log kiểu cũ (`TIMESTAMP : ...`).

Mỗi bản ghi có `entry_id`, mốc thời gian UTC, tuỳ chọn `session_id`, `stage`, `steps`, `evidence`, `tags`.

## Phát triển

```bash
pip install -e ".[dev]"
pytest
```

CI chạy pytest trên Python 3.10 và 3.12.
