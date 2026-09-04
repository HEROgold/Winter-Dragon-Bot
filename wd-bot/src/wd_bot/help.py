"""Module for defining the help command."""
from __future__ import annotations

from wd_core.command import Command
from wd_core.ui import View


class HelpCommand(View, Command):
    """The help command."""

class DefaultHelpCommand(HelpCommand):
    """Default implementation for a simple help command.

    Displays all available commands, with their description
    """

default_help = DefaultHelpCommand()
