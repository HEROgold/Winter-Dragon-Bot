"""Derive a stable signature string for a command's callable, used to detect definition drift.

TODO: generic enough to belong in ``herogold`` rather than here - tracked upstream at
https://github.com/HEROgold/HeroPy/issues/33. Drop this module in favor of herogold's version
once that lands.
"""

from __future__ import annotations

lazy import annotationlib
lazy from inspect import signature
lazy from typing import TYPE_CHECKING


if TYPE_CHECKING:
    lazy from collections.abc import Callable


def command_signature(func: Callable[..., object]) -> str:
    """Return a stable string form of ``func``'s signature, used to detect when it has changed.

    Annotations are rendered as source strings and never evaluated, so the result is the same with or
    without ``from __future__ import annotations`` and doesn't depend on what is importable.
    """
    return str(signature(func, annotation_format=annotationlib.Format.STRING))
