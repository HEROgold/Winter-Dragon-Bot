"""Unit tests: module-level loggers are the same object per name and reach their own log file."""

from __future__ import annotations

lazy from pathlib import Path

lazy from herogold import log
lazy from wd_discord.log import get_logger


def test_the_same_name_is_the_same_logger() -> None:
    assert get_logger("SameName") is get_logger("SameName")


def test_a_record_reaches_the_names_log_file(tmp_path: Path) -> None:
    log.setup(tmp_path, stream=False)
    try:
        logger = get_logger("FileTarget")
        logger.warning(t"unknown fields on {'Channel'}")
    finally:
        log.teardown()

    assert "unknown fields on Channel" in (tmp_path / f"{logger.name}.log").read_text(encoding="utf-8")
