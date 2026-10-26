"""wd-discord is the transport layer: it imports nothing from the packages built on it."""

lazy from pathlib import Path

lazy import pytest


SOURCE = Path(__file__).resolve().parents[1] / "src" / "wd_discord"


@pytest.mark.parametrize("package", ["wd_core", "wd_db", "wd_bot", "winter_dragon"])
def test_wd_discord_imports_nothing_above_it(package: str) -> None:
    offenders = [
        path.relative_to(SOURCE).as_posix()
        for path in sorted(SOURCE.rglob("*.py*"))
        if path.suffix in {".py", ".pyi"}
        and any(f"{verb} {package}" in path.read_text(encoding="utf-8") for verb in ("from", "import"))
    ]
    assert offenders == []
