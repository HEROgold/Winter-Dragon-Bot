"""Unit tests: module-level loggers are the same object per name and reach their own log file."""

from __future__ import annotations

lazy from pathlib import Path

lazy from herogold.log import LoggerMixin
lazy from wd_discord.log import get_logger


def test_the_same_name_is_the_same_logger() -> None:
    assert get_logger("SameName") is get_logger("SameName")


def test_a_record_reaches_the_names_log_file(tmp_path: Path) -> None:
    LoggerMixin.set_log_directory(str(tmp_path))
    try:
        logger = get_logger("FileTarget")
        logger.warning(t"unknown fields on {'Channel'}")
        for handler in logger.handlers:
            handler.flush()
    finally:
        LoggerMixin.set_log_directory("logs")

    assert "unknown fields on Channel" in (tmp_path / "FileTarget.log").read_text(encoding="utf-8")
