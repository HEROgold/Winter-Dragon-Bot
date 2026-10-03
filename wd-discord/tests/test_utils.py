"""Unit tests: xor helper."""

from __future__ import annotations

lazy import pytest


# NOTE: this module imports from herogold (with_known_exception),
# which can fail to import on Python 3.15 (herogold 3.3.0). Skip the whole module
# cleanly until that upstream issue is resolved.
try:
    from wd_discord.utils.xor import XORError, xor
except (ImportError, TypeError) as exc:  # pragma: no cover - environment-dependent
    pytest.skip(f"wd_discord.utils is unimportable: {exc}", allow_module_level=True)


def test_xor_returns_truthy_side() -> None:
    assert xor(True, False) is True
    assert xor(False, True) is True


def test_xor_coerces_non_bool() -> None:
    assert xor("value", "") is True  # type: ignore[arg-type]
    assert xor(0, 5) is True  # type: ignore[arg-type]


def test_xor_rejects_both_truthy() -> None:
    with pytest.raises(XORError):
        raise xor(True, True)


def test_xor_rejects_both_falsy() -> None:
    with pytest.raises(XORError):
        raise xor(False, False)
