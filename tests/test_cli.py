from __future__ import annotations

from pathlib import Path

import pytest

from deep_think.cli import main


def test_cli_log_and_show(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log_file = tmp_path / "cli.log"
    code = main(
        [
            "log",
            "Luồng lập luận CLI",
            "--stage",
            "Kiểm thử",
            "--step",
            "Ghi",
            "--step",
            "Đọc",
            "--tag",
            "cli",
            "--evidence",
            "source=unit-test",
            "--file",
            str(log_file),
        ]
    )
    assert code == 0
    logged = capsys.readouterr().out
    assert "Đã lưu toàn bộ luồng suy nghĩ vào" in logged
    assert log_file.is_file()

    code = main(["show", "--file", str(log_file)])
    assert code == 0
    shown = capsys.readouterr().out
    assert "Luồng lập luận CLI" in shown
    assert "GIAI ĐOẠN : Kiểm thử" in shown
    assert "source: unit-test" in shown


def test_cli_demo_jsonl(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log_file = tmp_path / "demo.jsonl"
    assert main(["demo", "--file", str(log_file), "--jsonl"]) == 0
    capsys.readouterr()
    raw = log_file.read_text(encoding="utf-8")
    assert raw.startswith("{")
    assert "danh_muc_emg" in raw
    assert main(["show", "--file", str(log_file), "--last", "1"]) == 0
    shown = capsys.readouterr().out
    assert "Phân tích toàn diện" in shown


def test_cli_rejects_bad_evidence(tmp_path: Path) -> None:
    code = main(
        [
            "log",
            "x",
            "--evidence",
            "missing-equals",
            "--file",
            str(tmp_path / "bad.log"),
        ]
    )
    assert code == 2


def test_cli_show_empty(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["show", "--file", str(tmp_path / "none.log")]) == 0
    assert "Không có bản ghi nào." in capsys.readouterr().out
