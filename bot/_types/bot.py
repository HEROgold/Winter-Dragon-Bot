from __future__ import annotations

import datetime
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord
from discord import Intents, app_commands
from discord.ext.commands import AutoShardedBot, CommandError
from discord.ext.commands.help import DefaultHelpCommand, HelpCommand

from bot.config import config
from bot.constants import BOT_PERMISSIONS, BOT_SCOPE, DISCORD_AUTHORIZE, EXTENSIONS


if TYPE_CHECKING:
    from asyncio import Task
    from collections.abc import Coroutine, Sequence

    from discord.abc import Snowflake
    from discord.ext.commands.context import Context

    from bot._types.aliases import AppCommandStore, BotT, MaybeGroupedAppCommand, PrefixType


class WinterDragon(AutoShardedBot):
    """WinterDragon is a subclass of AutoShardedBot.

    this represents a bot with additional attributes and methods specific to the Winter Dragon bot.
    """

    launch_time: datetime.datetime
    logger: logging.Logger
    has_app_command_mentions: bool = False
    log_saver: Task[Coroutine[Any, Any, None]] | None = None
    _global_app_commands: AppCommandStore
    _guild_app_commands: dict[int, AppCommandStore]
    default_intents: Intents

    def __init__(  # noqa: PLR0913
        self,
        command_prefix: PrefixType[WinterDragon],
        *,
        help_command: HelpCommand | None = None,
        tree_cls: type[app_commands.CommandTree[Any]] = app_commands.CommandTree,
        description: str | None = None,
        intents: discord.Intents,
        **options,
    ) -> None:
        self._global_app_commands = {}
        self._guild_app_commands = {}
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}")
        self.launch_time = datetime.datetime.now(datetime.UTC)

        if help_command is None:
            help_command = DefaultHelpCommand()

        super().__init__(
            command_prefix,
            help_command=help_command,
            tree_cls=tree_cls,
            description=description,
            intents=intents,
            **options,
        )

    def get_bot_invite(self) -> str:
        return (
            DISCORD_AUTHORIZE
            + f"?client_id={self.application_id}"
            + f"&permissions={BOT_PERMISSIONS}"
            + f"&scope={"+".join(BOT_SCOPE)}"
        )

    async def on_error(self, event_method: str, /, *args, **kwargs) -> None:
        self.logger.exception(f"error in: {event_method}")
        return await super().on_error(event_method, *args, **kwargs)

    async def on_command_error(self, context: Context[BotT], exception: CommandError) -> None:
        self.logger.exception(f"error in command: {context}", exc_info=exception)
        return await super().on_command_error(context, exception)


    # Credits to https://gist.github.com/Soheab/fed903c25b1aae1f11a8ca8c33243131#file-bot_subclass
    def get_app_command(
        self,
        value: str | int,
        guild: Snowflake | int | None = None,
        fallback_to_global: bool = True,  # noqa: FBT001, FBT002
    ) -> MaybeGroupedAppCommand:
        def search_dict(d: AppCommandStore) -> MaybeGroupedAppCommand:
            for cmd_name, cmd in d.items():
                if value == cmd_name or (str(value).isdigit() and int(value) == cmd.id):
                    return cmd
            return None

        if guild:
            guild_id = guild if isinstance(guild, int) else guild.id
            guild_commands = self._guild_app_commands.get(guild_id, {})
            if not fallback_to_global:
                return search_dict(guild_commands)
            return search_dict(guild_commands) or search_dict(self._global_app_commands)
        return search_dict(self._global_app_commands)


    async def update_app_commands_cache(
        self,
        commands: list[app_commands.AppCommand] | None = None,
        guild: Snowflake | int | None = None,
    ) -> None:
        def unpack_app_commands(commands: list[app_commands.AppCommand]) -> AppCommandStore:
            ret: AppCommandStore = {}

            def unpack_options(
                options: Sequence[app_commands.AppCommand | app_commands.AppCommandGroup | app_commands.Argument],
            ) -> None:
                for option in options:
                    if isinstance(option, app_commands.AppCommandGroup):
                        ret[option.qualified_name] = option
                        unpack_options(option.options)

            for command in commands:
                ret[command.name] = command
                unpack_options(command.options)

            return ret

        # because we support both int and Snowflake
        # we need to convert it to a Snowflake like object if it's an int
        _guild: Snowflake | None = None
        if guild is not None:
            _guild = discord.Object(guild) if isinstance(guild, int) else guild

        tree: app_commands.CommandTree = self.tree
        # commands.Bot has a built-in tree
        # this should be point to your tree if using discord.Client
        if not commands:
            commands = await tree.fetch_commands(guild=_guild)

        if _guild:
            self._guild_app_commands[_guild.id] = unpack_app_commands(commands)
        else:
            self._global_app_commands = unpack_app_commands(commands)


    async def get_extensions(self) -> list[str]:
        extensions = []
        for root, _, files in os.walk(EXTENSIONS):
            for file in files:
                if file.endswith(".py"):
                    extension = Path(root) / file
                    extensions.append(self.normalize_extension_path(extension.as_posix()))
        return extensions

    @staticmethod
    def normalize_extension_path(extension: str) -> str:
            idx = len(os.getcwd())  # noqa: PTH109
            if os.name == "nt":
                idx += 1 # +1 to avoid a leading slash after replacing.
            return extension[idx:].replace(os.sep, ".")

    async def load_extensions(self) -> None:
        if not (os.listdir(EXTENSIONS)):
            self.logger.critical("No extensions Directory To Load!")
            return
        for extension in await self.get_extensions():
            self.logger.info(f"Loading {extension}")
            try:
                await self.load_extension(extension)
            except Exception:
                self.logger.exception("")
            else:
                self.logger.info(f"Loaded {extension}")
