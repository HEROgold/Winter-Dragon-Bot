import datetime
from typing import Any

import discord
from discord import app_commands
from discord.ext.commands import AutoShardedBot
from discord.ext.commands.help import HelpCommand


class WinterDragon(AutoShardedBot):
    launch_time: datetime.datetime

    def __init__(
        self,
        command_prefix,
        *,
        help_command: HelpCommand | None = None,
        tree_cls: type[app_commands.CommandTree[Any]] = app_commands.CommandTree,
        description: str | None = None,
        intents: discord.Intents,
        **options: Any
    ) -> None:
        super().__init__(command_prefix, help_command=help_command, tree_cls=tree_cls, description=description, intents=intents, **options)
