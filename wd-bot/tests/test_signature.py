"""Unit tests: command_signature's stable string form of a callable's signature."""
# Annotations are rendered with annotationlib.Format.STRING, so they always read as quoted source
# strings ("a: 'int'") whether or not the module uses `from __future__ import annotations`.

from __future__ import annotations

from wd_bot.signature import command_signature


def sample(a: int, b: str = "x") -> None:
    pass


def test_signature_is_stable_string() -> None:
    assert command_signature(sample) == "(a: 'int', b: 'str' = 'x') -> 'None'"


def test_signature_changes_when_params_change() -> None:
    def other(a: int, b: str, c: float) -> None:
        pass

    assert command_signature(sample) != command_signature(other)


def test_signature_never_evaluates_annotations() -> None:
    def unresolvable(a: NotImportedAnywhere) -> None:  # noqa: F821
        pass

    assert command_signature(unresolvable) == "(a: 'NotImportedAnywhere') -> 'None'"
