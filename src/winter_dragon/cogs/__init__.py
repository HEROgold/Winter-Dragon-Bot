"""Cogs for the winter_dragon example bot (see run_test_bot.py)."""

lazy import importlib
lazy import pkgutil


def import_cogs() -> None:
    """Import every module of this package, so each feature and table the cogs define is known."""
    for module in pkgutil.walk_packages(__path__, f"{__name__}."):
        importlib.import_module(module.name)
