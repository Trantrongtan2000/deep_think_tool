"""
deep_think: ghi nhận chi tiết toàn bộ luồng lập luận, phân tích đa bước
và dữ liệu kiểm chứng dưới dạng văn bản, không cắt ngắn nội dung.
"""

from .cli import main
from .logger import (
    DEFAULT_LOG_PATH,
    DeepThinkError,
    DeepThinkLogger,
    DeepThinkSession,
    LogEntry,
    deep_think,
)

__version__ = "0.2.0"
__all__ = [
    "DEFAULT_LOG_PATH",
    "DeepThinkError",
    "DeepThinkLogger",
    "DeepThinkSession",
    "LogEntry",
    "deep_think",
    "main",
]
