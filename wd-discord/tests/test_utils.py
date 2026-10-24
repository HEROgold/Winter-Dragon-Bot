"""Unit tests: xor helper."""

lazy import pytest
lazy from hypothesis import assume, given
lazy from hypothesis import strategies as st


# NOTE: this module imports from herogold (with_known_exception),
# which can fail to import on Python 3.15 (herogold 3.3.0). Skip the whole module
# cleanly until that upstream issue is resolved.
try:
    from wd_discord.utils.xor import XORError, xor
except (ImportError, TypeError) as exc:  # pragma: no cover - environment-dependent
    pytest.skip(f"wd_discord.utils is unimportable: {exc}", allow_module_level=True)


VALUES = st.booleans() | st.integers() | st.text()


@given(VALUES, VALUES)
def test_xor_is_true_when_exactly_one_side_is_truthy(a: object, b: object) -> None:
    assume(bool(a) != bool(b))
    assert xor(a, b) is True  # type: ignore[arg-type]


@given(VALUES, VALUES)
def test_xor_rejects_two_truthy_or_two_falsy_sides(a: object, b: object) -> None:
    assume(bool(a) == bool(b))
    assert isinstance(xor(a, b), XORError)  # type: ignore[arg-type]
