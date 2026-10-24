"""Container health checks, run by compose: ``python -m winter_dragon.health bot`` or ``... web``.

Each exits 0 when healthy and 1 otherwise. ``bot`` is healthy while :class:`~winter_dragon.cogs.health.Health` keeps
:data:`ALIVE_FILE` fresh, which it does only while every gateway shard gets its heartbeats acknowledged. ``web`` is
healthy when the landing page, which reads the database, answers 200.
"""

lazy import sys
lazy import tempfile
lazy import time
lazy import urllib.request
lazy from pathlib import Path


ALIVE_FILE = Path(tempfile.gettempdir()) / "winter-dragon-alive"
"""Touched by :class:`~winter_dragon.cogs.health.Health` while the bot is connected to Discord."""
ALIVE_MAX_AGE = 90.0
"""Seconds :data:`ALIVE_FILE` may go untouched before the bot counts as unhealthy."""
WEB_TIMEOUT = 5.0
"""Seconds the landing page may take to answer."""


def bot_healthy() -> bool:
    """Return whether :data:`ALIVE_FILE` was touched within :data:`ALIVE_MAX_AGE` seconds."""
    try:
        age = time.time() - ALIVE_FILE.stat().st_mtime
    except FileNotFoundError:
        return False
    return age < ALIVE_MAX_AGE


def web_healthy() -> bool:
    """Return whether the dashboard's landing page answers 200 on this host."""
    from winter_dragon.web.settings import DashboardSettings  # noqa: PLC0415 - only the web check reads dashboard.ini

    url = f"http://127.0.0.1:{DashboardSettings.port}/"
    try:
        with urllib.request.urlopen(url, timeout=WEB_TIMEOUT) as response:  # noqa: S310 - fixed http URL on localhost
            return response.status == 200  # noqa: PLR2004 - HTTP OK
    except OSError:
        return False


CHECKS = {"bot": bot_healthy, "web": web_healthy}


def main(argv: list[str]) -> int:
    """Run the check named by ``argv[0]`` and return the exit code."""
    if len(argv) != 1 or argv[0] not in CHECKS:
        print(f"usage: python -m winter_dragon.health {{{','.join(CHECKS)}}}", file=sys.stderr)
        return 2
    return 0 if CHECKS[argv[0]]() else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
