"""
Module deep_think: Ghi nhận chi tiết toàn bộ luồng lập luận, phân tích đa bước và dữ liệu kiểm chứng dưới dạng văn bản.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, List


class DeepThinkLogger:
    def __init__(self, log_path: str = "deep_think_detailed.log"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        thought_content: str,
        stage: Optional[str] = None,
        steps: Optional[List[str]] = None,
    ) -> str:
        """
        Ghi toàn bộ nội dung phân tích chi tiết vào log mà không cắt ngắn.
        
        :param thought_content: Toàn văn luồng phân tích/suy luận.
        :param stage: Giai đoạn xử lý (ví dụ: Khởi tạo, Phân tích dữ liệu, Đánh giá rủi ro, Kết luận).
        :param steps: Danh sách các bước logic tuần tự.
        :return: Đường dẫn tệp log.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        lines = [
            f"============================================================",
            f"TIMESTAMP : {timestamp}",
        ]
        
        if stage:
            lines.append(f"GIAI ĐOẠN : {stage}")
            
        lines.append("NỘI DUNG LẬP LUẬN TOÀN VĂN:")
        lines.append(thought_content.strip())
        
        if steps:
            lines.append("\nCÁC BƯỚC LOGIC TUẦN TỰ:")
            for idx, step in enumerate(steps, 1):
                lines.append(f"  {idx}. {step}")
                
        lines.append("============================================================\n\n")
        
        output_text = "\n".join(lines)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(output_text)
            
        return str(self.log_path.resolve())


# Khởi tạo instance mặc định
logger = DeepThinkLogger()


def deep_think(
    thought_content: str,
    stage: Optional[str] = None,
    steps: Optional[List[str]] = None,
    log_file: Optional[str] = None,
) -> str:
    """
    Hàm gọi nhanh để ghi toàn bộ nội dung phân tích chi tiết.
    """
    target_logger = DeepThinkLogger(log_file) if log_file else logger
    path = target_logger.log(thought_content, stage=stage, steps=steps)
    return f"Đã lưu toàn bộ luồng suy nghĩ vào: {path}"


if __name__ == "__main__":
    sample_content = (
        "Phân tích toàn diện: Cần đọc toàn bộ danh mục tài liệu EMG, xác định các trường "
        "dữ liệu cần thiết, kiểm tra tính toàn vẹn của file trước khi chuyển đổi định dạng."
    )
    sample_steps = [
        "Quét thư mục gốc để lấy danh sách đường dẫn",
        "Phân loại tài liệu theo từng nhóm chuyên ngành",
        "Kiểm tra tính hợp lệ của định dạng và quyền truy cập",
        "Thực thi chuyển đổi và lưu trữ log chi tiết"
    ]
    print(deep_think(sample_content, stage="Phân tích & Lập kế hoạch", steps=sample_steps))
