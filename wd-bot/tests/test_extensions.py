"""Unit tests: ExtensionDiscovery finds modules at any depth, named relative to the package."""

from __future__ import annotations

lazy import importlib
lazy import sys
lazy import types
lazy from typing import TYPE_CHECKING

lazy import pytest
lazy from wd_bot.extensions import ExtensionDiscovery


if TYPE_CHECKING:
    lazy from pathlib import Path


def test_yields_nested_modules_relative_to_the_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    package = tmp_path / "fake_cogs"
    (package / "admin").mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "heartbeat.py").write_text("")
    (package / "admin" / "__init__.py").write_text("")
    (package / "admin" / "sync.py").write_text("")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(sys, "modules", dict(sys.modules))

    modules = sorted(ExtensionDiscovery(importlib.import_module("fake_cogs")).modules())

    assert modules == ["admin.sync", "heartbeat"]


def test_raises_for_a_module_that_is_not_a_package() -> None:
    with pytest.raises(AttributeError):
        list(ExtensionDiscovery(types.ModuleType("not_a_package")).modules())
