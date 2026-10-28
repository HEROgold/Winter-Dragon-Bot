"""Cogs for the winter_dragon example bot (see run_test_bot.py)."""

lazy import importlib
lazy import sys

lazy from wd_bot.extensions import ExtensionDiscovery


def import_cogs() -> None:
    """Import every module the bot loads as an extension, so each feature and table the cogs define is known.

    The modules come from the same :class:`~wd_bot.extensions.ExtensionDiscovery` the bot's extension loader uses.
    """
    for module in ExtensionDiscovery(sys.modules[__name__]).modules():
        importlib.import_module(f"{__name__}.{module}")
