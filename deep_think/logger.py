"""Ghi nhận toàn văn luồng lập luận, không cắt ngắn nội dung."""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

__all__ = [
    "DEFAULT_LOG_PATH",
    "DeepThinkError",
    "DeepThinkLogger",
    "DeepThinkSession",
    "LogEntry",
    "deep_think",
]

DEFAULT_LOG_PATH = "deep_think_detailed.log"
ENTRY_BEGIN = "===== BEGIN DEEP_THINK ====="
ENTRY_END = "===== END DEEP_THINK ====="
LEGACY_SEPARATOR = "=" * 60
CONTENT_HEADER = "NỘI DUNG LẬP LUẬN TOÀN VĂN:"
SUPPORTED_FORMATS = frozenset({"text", "jsonl"})

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()
_default_logger: DeepThinkLogger | None = None
_default_logger_guard = threading.Lock()


class DeepThinkError(ValueError):
    """Dữ liệu đầu vào hoặc định dạng log không hợp lệ."""


@dataclass(slots=True)
class LogEntry:
    """Một bản ghi suy luận đã được chuẩn hoá."""

    entry_id: str
    timestamp: str
    thought_content: str
    stage: str | None = None
    steps: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    session_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_text(self) -> str:
        meta: dict[str, Any] = {}
        for key, value in self.to_dict().items():
            if key == "thought_content" or value in (None, [], {}):
                continue
            meta[key] = value
        meta["content_chars"] = len(self.thought_content)

        lines = [
            ENTRY_BEGIN,
            f"META      : {json.dumps(meta, ensure_ascii=False, separators=(',', ':'))}",
            f"ENTRY_ID  : {self.entry_id}",
            f"TIMESTAMP : {self.timestamp}",
        ]
        if self.session_id:
            lines.append(f"SESSION   : {self.session_id}")
        if self.stage:
            lines.append(f"GIAI ĐOẠN : {self.stage}")
        if self.tags:
            lines.append(f"TAGS      : {', '.join(self.tags)}")
        lines.append(CONTENT_HEADER)
        lines.append(self.thought_content)
        if self.steps:
            lines.append("")
            lines.append("CÁC BƯỚC LOGIC TUẦN TỰ:")
            for index, step in enumerate(self.steps, 1):
                lines.append(f"  {index}. {step}")
        if self.evidence:
            lines.append("")
            lines.append("DỮ LIỆU KIỂM CHỨNG:")
            for key, value in self.evidence.items():
                lines.append(f"  - {key}: {_render_value(value)}")
        if self.extra:
            lines.append("")
            lines.append("THÔNG TIN BỔ SUNG:")
            for key, value in self.extra.items():
                lines.append(f"  - {key}: {_render_value(value)}")
        lines.append(ENTRY_END)
        lines.append("")
        return "\n".join(lines)


def _render_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _clean_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_items(items: Sequence[str] | None) -> list[str]:
    if not items:
        return []
    return [str(item).strip() for item in items if str(item).strip()]


def _normalize_tags(tags: Sequence[str] | None) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for tag in _normalize_items(tags):
        if tag not in seen:
            seen.add(tag)
            unique.append(tag)
    return unique


def _normalize_evidence(
    evidence: Mapping[str, Any] | Sequence[Any] | None,
) -> dict[str, Any]:
    if evidence is None:
        return {}
    if isinstance(evidence, Mapping):
        return {str(key): value for key, value in evidence.items()}
    return {str(index): item for index, item in enumerate(evidence, 1)}


def _normalize_mapping(data: Mapping[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    return dict(data)


def _lock_for(path: Path) -> threading.Lock:
    key = str(path.expanduser().resolve())
    with _locks_guard:
        lock = _locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _locks[key] = lock
        return lock


def _entry_from_dict(data: Mapping[str, Any]) -> LogEntry:
    return LogEntry(
        entry_id=str(data.get("entry_id") or ""),
        timestamp=str(data.get("timestamp") or ""),
        thought_content=str(data.get("thought_content") or ""),
        stage=_clean_optional_str(data.get("stage")),
        steps=[str(step) for step in (data.get("steps") or [])],
        evidence=dict(data.get("evidence") or {}),
        tags=[str(tag) for tag in (data.get("tags") or [])],
        session_id=_clean_optional_str(data.get("session_id")),
        extra=dict(data.get("extra") or {}),
    )


def _parse_jsonl(text: str) -> list[LogEntry]:
    entries: list[LogEntry] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or not line.startswith("{"):
            continue
        entries.append(_entry_from_dict(json.loads(line)))
    return entries


def _meta_from_header(header: str) -> dict[str, Any]:
    for line in header.splitlines():
        if line.startswith("META") and ":" in line:
            payload = line.split(":", 1)[1].strip()
            try:
                loaded = json.loads(payload)
            except json.JSONDecodeError:
                return {}
            return loaded if isinstance(loaded, dict) else {}
    return {}


def _parse_legacy_headers(header: str, content: str) -> dict[str, Any]:
    fields: dict[str, Any] = {"thought_content": content}
    for line in header.splitlines():
        if ":" not in line or line.startswith("META"):
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key == "TIMESTAMP":
            fields["timestamp"] = value
        elif key in {"GIAI ĐOẠN", "STAGE"}:
            fields["stage"] = value
        elif key in {"SESSION", "SESSION_ID"}:
            fields["session_id"] = value
        elif key == "ENTRY_ID":
            fields["entry_id"] = value
        elif key == "TAGS":
            fields["tags"] = [item.strip() for item in value.split(",") if item.strip()]
    fields.setdefault("entry_id", "")
    fields.setdefault("timestamp", "")
    return fields


def _parse_text(text: str) -> list[LogEntry]:
    """Parse text logs using META content_chars so body delimiters cannot truncate."""
    entries: list[LogEntry] = []
    cursor = 0
    while True:
        begin = text.find(ENTRY_BEGIN, cursor)
        if begin < 0:
            break
        after_begin = begin + len(ENTRY_BEGIN)
        if text.startswith("\n", after_begin):
            after_begin += 1

        header_end = text.find(CONTENT_HEADER, after_begin)
        if header_end < 0:
            break
        header = text[after_begin:header_end]
        meta = _meta_from_header(header)

        content_start = header_end + len(CONTENT_HEADER)
        if text.startswith("\n", content_start):
            content_start += 1

        content_chars = meta.get("content_chars")
        if isinstance(content_chars, int) and content_chars >= 0:
            content = text[content_start : content_start + content_chars]
            cursor = content_start + content_chars
        else:
            end = text.find(ENTRY_END, content_start)
            content = text[content_start:end].rstrip("\n") if end >= 0 else text[content_start:]
            cursor = end + len(ENTRY_END) if end >= 0 else len(text)

        meta.pop("content_chars", None)
        meta["thought_content"] = content
        if not meta.get("entry_id"):
            meta.update(_parse_legacy_headers(header, content))
        entries.append(_entry_from_dict(meta))

        end_pos = text.find(ENTRY_END, cursor)
        next_begin = text.find(ENTRY_BEGIN, cursor)
        if end_pos >= 0 and (next_begin < 0 or end_pos < next_begin):
            cursor = end_pos + len(ENTRY_END)
    return entries


def _parse_legacy(text: str) -> list[LogEntry]:
    entries: list[LogEntry] = []
    blocks = [block.strip("\n") for block in text.split(LEGACY_SEPARATOR)]
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        timestamp = ""
        stage = None
        steps: list[str] = []
        content_lines: list[str] = []
        in_content = False
        in_steps = False
        for line in block.splitlines():
            if line.startswith("TIMESTAMP"):
                timestamp = line.split(":", 1)[1].strip() if ":" in line else ""
                in_content = False
                in_steps = False
            elif line.startswith("GIAI ĐOẠN"):
                stage = line.split(":", 1)[1].strip() if ":" in line else None
                in_content = False
                in_steps = False
            elif line.startswith(CONTENT_HEADER):
                in_content = True
                in_steps = False
            elif "CÁC BƯỚC LOGIC" in line:
                in_content = False
                in_steps = True
            elif in_steps:
                stripped = line.strip()
                if stripped:
                    steps.append(stripped.split(".", 1)[1].strip() if "." in stripped[:4] else stripped)
            elif in_content:
                content_lines.append(line)
        content = "\n".join(content_lines).strip()
        if not content and not timestamp:
            continue
        entries.append(
            LogEntry(
                entry_id="",
                timestamp=timestamp,
                thought_content=content,
                stage=stage,
                steps=steps,
            )
        )
    return entries


def parse_log_text(text: str) -> list[LogEntry]:
    """Tự nhận diện JSONL, định dạng text mới, hoặc log kiểu cũ."""
    stripped = text.lstrip()
    if not stripped:
        return []
    if stripped.startswith("{"):
        return _parse_jsonl(text)
    if ENTRY_BEGIN in text:
        return _parse_text(text)
    if LEGACY_SEPARATOR in text:
        return _parse_legacy(text)
    return _parse_jsonl(text)


class DeepThinkLogger:
    """Ghi và đọc nhật ký suy luận theo đường dẫn cụ thể."""

    def __init__(
        self,
        log_path: str | Path = DEFAULT_LOG_PATH,
        *,
        fmt: str = "text",
    ) -> None:
        if fmt not in SUPPORTED_FORMATS:
            raise DeepThinkError(
                f"Định dạng không hỗ trợ: {fmt!r}. Dùng 'text' hoặc 'jsonl'."
            )
        self.log_path = Path(log_path).expanduser()
        self.fmt = fmt

    def log(
        self,
        thought_content: str,
        stage: str | None = None,
        steps: Sequence[str] | None = None,
        *,
        evidence: Mapping[str, Any] | Sequence[Any] | None = None,
        tags: Sequence[str] | None = None,
        session_id: str | None = None,
        extra: Mapping[str, Any] | None = None,
        entry_id: str | None = None,
    ) -> LogEntry:
        """
        Ghi toàn bộ nội dung phân tích chi tiết vào log mà không cắt ngắn.

        :param thought_content: Toàn văn luồng phân tích/suy luận.
        :param stage: Giai đoạn xử lý (ví dụ: Khởi tạo, Phân tích dữ liệu, Kết luận).
        :param steps: Danh sách các bước logic tuần tự.
        :param evidence: Dữ liệu kiểm chứng (dict hoặc danh sách).
        :param tags: Nhãn phân loại bản ghi.
        :param session_id: Mã phiên để nhóm các bước liên quan.
        :param extra: Trường bổ sung tuỳ ý.
        :param entry_id: Ghi đè mã bản ghi; mặc định tạo UUID.
        :return: Bản ghi đã lưu.
        """
        if thought_content is None:
            raise DeepThinkError("thought_content không được để trống.")
        content = str(thought_content).strip()
        if not content:
            raise DeepThinkError("thought_content không được để trống.")

        entry = LogEntry(
            entry_id=entry_id or uuid.uuid4().hex,
            timestamp=_utc_timestamp(),
            thought_content=content,
            stage=_clean_optional_str(stage),
            steps=_normalize_items(steps),
            evidence=_normalize_evidence(evidence),
            tags=_normalize_tags(tags),
            session_id=_clean_optional_str(session_id),
            extra=_normalize_mapping(extra),
        )
        self._write(entry)
        return entry

    def _write(self, entry: LogEntry) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = (
            entry.to_text()
            if self.fmt == "text"
            else json.dumps(entry.to_dict(), ensure_ascii=False) + "\n"
        )
        lock = _lock_for(self.log_path)
        with lock:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()

    def read(self) -> list[LogEntry]:
        if not self.log_path.is_file():
            return []
        return parse_log_text(self.log_path.read_text(encoding="utf-8"))

    def session(
        self,
        session_id: str | None = None,
        *,
        stage: str | None = None,
        tags: Sequence[str] | None = None,
    ) -> DeepThinkSession:
        return DeepThinkSession(self, session_id=session_id, stage=stage, tags=tags)


class DeepThinkSession:
    """Nhóm nhiều bước suy luận dưới cùng một session_id."""

    def __init__(
        self,
        logger: DeepThinkLogger,
        session_id: str | None = None,
        *,
        stage: str | None = None,
        tags: Sequence[str] | None = None,
    ) -> None:
        self.logger = logger
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.stage = stage
        self.tags = _normalize_tags(tags)

    def log(
        self,
        thought_content: str,
        stage: str | None = None,
        steps: Sequence[str] | None = None,
        *,
        evidence: Mapping[str, Any] | Sequence[Any] | None = None,
        tags: Sequence[str] | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> LogEntry:
        merged_tags = list(self.tags)
        for tag in _normalize_tags(tags):
            if tag not in merged_tags:
                merged_tags.append(tag)
        return self.logger.log(
            thought_content,
            stage=stage if stage is not None else self.stage,
            steps=steps,
            evidence=evidence,
            tags=merged_tags,
            session_id=self.session_id,
            extra=extra,
        )

    think = log

    def __enter__(self) -> DeepThinkSession:
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        return False


def get_default_logger() -> DeepThinkLogger:
    global _default_logger
    with _default_logger_guard:
        if _default_logger is None:
            _default_logger = DeepThinkLogger()
        return _default_logger


def deep_think(
    thought_content: str,
    stage: str | None = None,
    steps: Sequence[str] | None = None,
    log_file: str | Path | None = None,
    *,
    evidence: Mapping[str, Any] | Sequence[Any] | None = None,
    tags: Sequence[str] | None = None,
    session_id: str | None = None,
    extra: Mapping[str, Any] | None = None,
    fmt: str = "text",
) -> str:
    """
    Hàm gọi nhanh để ghi toàn bộ nội dung phân tích chi tiết.

    Giữ tương thích với API ban đầu: trả về thông báo kèm đường dẫn tệp.
    """
    if log_file is None and fmt == "text":
        target = get_default_logger()
    else:
        target = DeepThinkLogger(log_file or DEFAULT_LOG_PATH, fmt=fmt)
    entry = target.log(
        thought_content,
        stage=stage,
        steps=steps,
        evidence=evidence,
        tags=tags,
        session_id=session_id,
        extra=extra,
    )
    path = str(target.log_path.resolve())
    return f"Đã lưu toàn bộ luồng suy nghĩ vào: {path} (entry_id={entry.entry_id})"
