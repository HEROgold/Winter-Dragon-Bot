"""A cache for storing application commands, both globally and per guild."""

from typing import TYPE_CHECKING, ClassVar

import discord
from discord.app_commands import AppCommand, AppCommandGroup, Argument, Command


if TYPE_CHECKING:
    from collections.abc import Sequence

    from discord.abc import Snowflake
    from discord.ext.commands.bot import BotBase


type AppCommandStore = dict[str, AppCommand | AppCommandGroup]
type MentionableCommand = AppCommand | AppCommandGroup


class AppCommandCache:
    """A cache for storing application commands, both globally and per guild."""

    _global_app_commands: ClassVar[AppCommandStore] = {}
    _guild_app_commands: ClassVar[dict[int, AppCommandStore]] = {}

    def __repr__(self) -> str:
        return f"AppCommandCache(global={self._global_app_commands}, guilds={self._guild_app_commands})"

    # Credits to https://gist.github.com/Soheab/fed903c25b1aae1f11a8ca8c33243131#file-bot_subclass
    def get_app_command(
        self,
        value: str,
        guild: Snowflake | int | None = None,
        *,
        fallback_to_global: bool = True,
    ) -> MentionableCommand | None:
        """Get an app command from the cache.

        This app command may be a group or app_command or None
        """

        def search_dict(d: AppCommandStore) -> MentionableCommand | None:
            return d.get(value, None)

        if guild:
            guild_id = guild if isinstance(guild, int) else guild.id
            guild_commands = self._guild_app_commands.get(guild_id, {})
            if not fallback_to_global:
                return search_dict(guild_commands)
            return search_dict(guild_commands) or search_dict(self._global_app_commands)
        return search_dict(self._global_app_commands)

    def _unpack_app_commands(self, commands: list[AppCommand]) -> AppCommandStore:
        """Unpack the app commands from the store into a typed dictionary."""
        ret: AppCommandStore = {}

        def unpack_options(
            options: Sequence[AppCommand | AppCommandGroup | Argument],
        ) -> None:
            for option in options:
                if isinstance(option, AppCommandGroup):
                    ret[option.qualified_name] = option
                    unpack_options(option.options)

        for command in commands:
            ret[command.name] = command
            unpack_options(command.options)

        return ret

    async def update_app_commands_cache(
        self,
        bot: BotBase,
        commands: list[AppCommand] | None = None,
        guild: Snowflake | int | None = None,
    ) -> None:
        """Update the app commands cache with the provided commands for a given guild."""
        # because we support both int and Snowflake
        # we need to convert it to a Snowflake like object if it's an int
        _guild: Snowflake | None = None
        if guild is not None:
            _guild = discord.Object(guild) if isinstance(guild, int) else guild

        # commands.Bot has a built-in tree
        # this should be point to your tree if using discord.Client
        if not commands:
            commands = await bot.tree.fetch_commands(guild=_guild)

        if _guild:
            self._guild_app_commands[_guild.id].update(self._unpack_app_commands(commands))
        else:
            self._global_app_commands.update(self._unpack_app_commands(commands))

    def _get_cmd_mention(self, command: Command | str) -> str:
        full_name = command if isinstance(command, str) else command.qualified_name

        if cmd := self.get_app_command(full_name):
            return cmd.mention
        msg = f"Can't find {full_name}"
        raise ValueError(msg)

    def get_command_mention(self, command: Command | str) -> str:
        """Return a command string from a given functiontype. (Decorated with app_commands.command)."""
        return self._get_cmd_mention(command)
