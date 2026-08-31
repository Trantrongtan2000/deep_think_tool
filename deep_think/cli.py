"""Giao diện dòng lệnh cho deep_think."""

from __future__ import annotations

import argparse
import sys

from .logger import DEFAULT_LOG_PATH, DeepThinkError, DeepThinkLogger, deep_think

DEMO_CONTENT = (
    "Phân tích toàn diện: Cần đọc toàn bộ danh mục tài liệu EMG, xác định các trường "
    "dữ liệu cần thiết, kiểm tra tính toàn vẹn của file trước khi chuyển đổi định dạng."
)
DEMO_STEPS = [
    "Quét thư mục gốc để lấy danh sách đường dẫn",
    "Phân loại tài liệu theo từng nhóm chuyên ngành",
    "Kiểm tra tính hợp lệ của định dạng và quyền truy cập",
    "Thực thi chuyển đổi và lưu trữ log chi tiết",
]


def _parse_evidence(items: list[str] | None) -> dict[str, str]:
    evidence: dict[str, str] = {}
    for item in items or []:
        if "=" not in item:
            raise DeepThinkError(
                f"evidence phải có dạng key=value, nhận được: {item!r}"
            )
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise DeepThinkError("evidence key không được để trống.")
        evidence[key] = value
    return evidence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deep-think",
        description="Ghi và đọc toàn văn luồng lập luận, không cắt ngắn nội dung.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="deep-think 0.2.0",
    )
    sub = parser.add_subparsers(dest="command")

    log_cmd = sub.add_parser("log", help="Ghi một bản ghi suy luận.")
    log_cmd.add_argument("content", help="Toàn văn luồng phân tích.")
    log_cmd.add_argument("--stage", "-s", help="Giai đoạn xử lý.")
    log_cmd.add_argument("--step", action="append", dest="steps", default=None)
    log_cmd.add_argument("--tag", action="append", dest="tags", default=None)
    log_cmd.add_argument(
        "--evidence",
        action="append",
        default=None,
        help="Dữ liệu kiểm chứng dạng key=value; có thể lặp lại.",
    )
    log_cmd.add_argument("--session", dest="session_id", help="Mã phiên.")
    log_cmd.add_argument("--file", "-f", dest="log_file", default=DEFAULT_LOG_PATH)
    log_cmd.add_argument(
        "--jsonl",
        action="store_true",
        help="Ghi dưới dạng JSON Lines thay vì văn bản.",
    )

    show_cmd = sub.add_parser("show", help="In các bản ghi đã lưu.")
    show_cmd.add_argument("--file", "-f", dest="log_file", default=DEFAULT_LOG_PATH)
    show_cmd.add_argument("--last", type=int, default=0, help="Chỉ in N bản ghi cuối.")
    show_cmd.add_argument("--session", dest="session_id", help="Lọc theo session_id.")

    demo_cmd = sub.add_parser("demo", help="Ghi bản ghi mẫu.")
    demo_cmd.add_argument("--file", "-f", dest="log_file", default=DEFAULT_LOG_PATH)
    demo_cmd.add_argument("--jsonl", action="store_true")

    return parser


def _cmd_log(args: argparse.Namespace) -> int:
    fmt = "jsonl" if args.jsonl else "text"
    message = deep_think(
        args.content,
        stage=args.stage,
        steps=args.steps,
        log_file=args.log_file,
        evidence=_parse_evidence(args.evidence) or None,
        tags=args.tags,
        session_id=args.session_id,
        fmt=fmt,
    )
    print(message)
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    logger = DeepThinkLogger(args.log_file)
    entries = logger.read()
    if args.session_id:
        entries = [entry for entry in entries if entry.session_id == args.session_id]
    if args.last > 0:
        entries = entries[-args.last :]
    if not entries:
        print("Không có bản ghi nào.")
        return 0
    for entry in entries:
        print(entry.to_text(), end="")
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    fmt = "jsonl" if args.jsonl else "text"
    message = deep_think(
        DEMO_CONTENT,
        stage="Phân tích & Lập kế hoạch",
        steps=DEMO_STEPS,
        log_file=args.log_file,
        evidence={
            "nguon": "danh_muc_emg",
            "yeu_cau": "khong_cat_ngan_noi_dung",
        },
        tags=["demo", "planning"],
        fmt=fmt,
    )
    print(message)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    if not argv_list:
        argv_list = ["demo"]
    parser = build_parser()
    try:
        args = parser.parse_args(argv_list)
        if args.command == "log":
            return _cmd_log(args)
        if args.command == "show":
            return _cmd_show(args)
        if args.command == "demo":
            return _cmd_demo(args)
        parser.print_help()
        return 0
    except DeepThinkError as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"Lỗi hệ thống: {exc}", file=sys.stderr)
        return 1
