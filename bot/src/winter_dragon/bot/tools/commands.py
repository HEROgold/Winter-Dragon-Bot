"""Module that contains utility tools for commands."""

from discord import app_commands
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.log import LoggerMixin


class Commands(LoggerMixin):
    """Utility tools for commands."""

    @staticmethod
    def _get_cmd_mention(bot: WinterDragon, command: app_commands.Command | str) -> str:
        name = command if isinstance(command, str) else command.qualified_name

        if cmd := bot.get_app_command(name):
            return cmd.mention
        msg = f"Can't find {name}"
        Commands.logger.exception(msg)
        raise ValueError(msg)

    @staticmethod
    def _validate_command(command: app_commands.Command | str) -> None:
        """Validate the command type."""
        if not isinstance(command, (app_commands.Command, str)):  # type:ignore[reportUnnecessaryIsInstance]
            msg = f"Expected `app_commands.commands.Command` or `str` but got {type(command)}"
            raise TypeError(msg)

    @staticmethod
    def get_command_mention(bot: WinterDragon, command: app_commands.Command | str) -> str:
        """Return a command string from a given functiontype. (Decorated with app_commands.command)."""
        Commands._validate_command(command)
        return Commands._get_cmd_mention(bot, command)
