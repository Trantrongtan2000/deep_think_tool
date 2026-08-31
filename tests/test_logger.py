from __future__ import annotations

import threading
from pathlib import Path

import pytest

from deep_think import (
    DeepThinkError,
    DeepThinkLogger,
    deep_think,
)
from deep_think.logger import LEGACY_SEPARATOR, parse_log_text


def test_writes_full_untruncated_unicode(tmp_path: Path) -> None:
    log_path = tmp_path / "think.log"
    logger = DeepThinkLogger(log_path)
    content = ("Phân tích " * 2000) + "漢字 emoji 🧠 " + ("X" * 10_000)
    entry = logger.log(
        content,
        stage="Phân tích dữ liệu",
        steps=["Đọc nguồn", "Đối chiếu", "Kết luận"],
        evidence={"checksum": "abc123", "records": 42},
        tags=["emg", "emg"],
        session_id="sess-1",
        extra={"operator": "qa"},
    )
    stored = log_path.read_text(encoding="utf-8")
    assert content in stored
    assert "GIAI ĐOẠN : Phân tích dữ liệu" in stored
    assert "DỮ LIỆU KIỂM CHỨNG:" in stored
    assert entry.tags == ["emg"]

    loaded = logger.read()
    assert len(loaded) == 1
    assert loaded[0].thought_content == content
    assert loaded[0].stage == "Phân tích dữ liệu"
    assert loaded[0].steps == ["Đọc nguồn", "Đối chiếu", "Kết luận"]
    assert loaded[0].evidence["records"] == 42
    assert loaded[0].session_id == "sess-1"
    assert loaded[0].extra["operator"] == "qa"


def test_empty_content_is_rejected(tmp_path: Path) -> None:
    logger = DeepThinkLogger(tmp_path / "empty.log")
    with pytest.raises(DeepThinkError):
        logger.log("   ")
    with pytest.raises(DeepThinkError):
        logger.log(None)  # type: ignore[arg-type]


def test_jsonl_roundtrip(tmp_path: Path) -> None:
    log_path = tmp_path / "think.jsonl"
    logger = DeepThinkLogger(log_path, fmt="jsonl")
    logger.log("bước một", stage="A", steps=["1"])
    logger.log("bước hai\nnhiều dòng", stage="B", evidence=["file-a", "file-b"])
    entries = logger.read()
    assert [item.thought_content for item in entries] == [
        "bước một",
        "bước hai\nnhiều dòng",
    ]
    assert entries[1].evidence == {"1": "file-a", "2": "file-b"}
    raw = log_path.read_text(encoding="utf-8")
    assert raw.count("\n") == 2
    assert "bước hai" in raw


def test_session_groups_entries(tmp_path: Path) -> None:
    logger = DeepThinkLogger(tmp_path / "session.log")
    with logger.session(stage="Khởi tạo", tags=["pipeline"]) as session:
        session.log("Bắt đầu quét")
        session.log("Hoàn tất", stage="Kết luận", tags=["done"])
    entries = logger.read()
    assert len(entries) == 2
    assert entries[0].session_id == entries[1].session_id
    assert entries[0].stage == "Khởi tạo"
    assert entries[1].stage == "Kết luận"
    assert entries[0].tags == ["pipeline"]
    assert entries[1].tags == ["pipeline", "done"]


def test_thread_safe_appends(tmp_path: Path) -> None:
    logger = DeepThinkLogger(tmp_path / "concurrent.log")
    count = 24

    def worker(index: int) -> None:
        logger.log(f"thread-{index} " + ("body " * 50), stage=str(index))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    entries = logger.read()
    assert len(entries) == count
    bodies = {entry.thought_content.split()[0] for entry in entries}
    assert bodies == {f"thread-{i}" for i in range(count)}


def test_deep_think_helper_returns_path(tmp_path: Path) -> None:
    log_file = tmp_path / "helper.log"
    message = deep_think(
        "Nội dung ngắn",
        stage="Test",
        log_file=log_file,
        tags=["unit"],
    )
    assert str(log_file.resolve()) in message
    assert "entry_id=" in message
    assert log_file.read_text(encoding="utf-8").count("Nội dung ngắn") == 1


def test_content_containing_delimiters_roundtrips(tmp_path: Path) -> None:
    logger = DeepThinkLogger(tmp_path / "delim.log")
    content = (
        "===== BEGIN DEEP_THINK =====\n"
        "META      : not-real\n"
        "===== END DEEP_THINK =====\n"
        + ("=" * 60)
    )
    logger.log(content, stage="Trap")
    loaded = logger.read()
    assert loaded[0].thought_content == content


def test_legacy_format_is_readable() -> None:
    legacy = f"""
{LEGACY_SEPARATOR}
TIMESTAMP : 2026-08-31 14:50:11.123
GIAI ĐOẠN : Phân tích & Lập kế hoạch
NỘI DUNG LẬP LUẬN TOÀN VĂN:
Phân tích toàn diện EMG
CÁC BƯỚC LOGIC TUẦN TỰ:
  1. Quét thư mục gốc
  2. Phân loại tài liệu
{LEGACY_SEPARATOR}
"""
    entries = parse_log_text(legacy)
    assert len(entries) == 1
    assert entries[0].stage == "Phân tích & Lập kế hoạch"
    assert "Phân tích toàn diện EMG" in entries[0].thought_content
    assert entries[0].steps == ["Quét thư mục gốc", "Phân loại tài liệu"]


def test_invalid_format_rejected(tmp_path: Path) -> None:
    with pytest.raises(DeepThinkError):
        DeepThinkLogger(tmp_path / "x.log", fmt="xml")


def test_read_missing_file(tmp_path: Path) -> None:
    logger = DeepThinkLogger(tmp_path / "missing.log")
    assert logger.read() == []
