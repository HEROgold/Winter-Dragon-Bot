"""Unit tests: command_signature's stable string form of a callable's signature."""
# No `from __future__ import annotations`: it would stringify the annotations below, so the
# rendered signature would read "a: 'int'" instead of "a: int".

from wd_bot.signature import command_signature


def sample(a: int, b: str = "x") -> None:
    pass


def test_signature_is_stable_string() -> None:
    assert command_signature(sample) == "(a: int, b: str = 'x') -> None"


def test_signature_changes_when_params_change() -> None:
    def other(a: int, b: str, c: bool) -> None:
        pass

    assert command_signature(sample) != command_signature(other)
