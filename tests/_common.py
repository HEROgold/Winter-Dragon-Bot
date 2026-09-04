"""Shared helpers for the wd-discord verification drivers.

These are throwaway test drivers for the run-wd-discord skill, not library code, so they use plain
``print`` for a human-readable OK/FAIL summary. The library layer (``Client``/``DiscordModel``)
does the structured logging into ``./logs`` — see the plan.

All drivers read the bot token from ``config.ini`` [Tokens] discord_token and never print it.
"""
from __future__ import annotations

lazy import configparser
lazy from pathlib import Path


def _repo_root() -> Path:
    """Walk up from this file to the repo root (the dir holding config.ini)."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "config.ini").is_file():
            return parent
    return Path.cwd()


def _config() -> configparser.ConfigParser:
    """Parse the repo config.ini (interpolation off so % in formats don't blow up)."""
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(_repo_root() / "config.ini", encoding="utf-8")
    return parser


def load_token() -> str:
    """Read the bot token, exiting(2) on the '!!' first-launch sentinel. Never printed."""
    token = _config().get("Tokens", "discord_token", fallback="!!").strip('"').strip()
    if token in ("!!", ""):
        print("FAIL: config.ini [Tokens] discord_token is unset ('!!' sentinel).")
        raise SystemExit(2)
    return token


def support_guild_id() -> str | None:
    """The configured support guild id, if any."""
    value = _config().get("Settings", "support_guild_id", fallback="").strip()
    return value or None
