"""Unit tests: xor helper and the LimitedString descriptor."""
from __future__ import annotations

lazy import pytest


# NOTE: these modules import from herogold (DataDescriptor / with_known_exception),
# which can fail to import on Python 3.15 (herogold 3.3.0). Skip the whole module
# cleanly until that upstream issue is resolved.
try:
    from wd_discord.utils.strings import LimitedString
    from wd_discord.utils.xor import XORError, xor
    from wd_errors.size import TooLongError
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
        xor(True, True)


def test_xor_rejects_both_falsy() -> None:
    with pytest.raises(XORError):
        xor(False, False)


class _Host:
    name = LimitedString(5)


def test_limited_string_round_trip() -> None:
    host = _Host()
    host.name = "abc"
    assert host.name == "abc"


def test_limited_string_rejects_non_str() -> None:
    host = _Host()
    with pytest.raises(TypeError):
        host.name = 123  # type: ignore[assignment]


def test_limited_string_rejects_too_long() -> None:
    host = _Host()
    with pytest.raises(TooLongError):
        host.name = "way too long"


def test_limited_string_get_before_set() -> None:
    descriptor = LimitedString(5)

    class Fresh:
        value = descriptor

    with pytest.raises(AttributeError):
        _ = Fresh().value


def test_limited_string_delete() -> None:
    descriptor = LimitedString(5)

    class Fresh:
        value = descriptor

    Fresh().value = "ok"
    del Fresh().value
    with pytest.raises(AttributeError):
        _ = Fresh().value
