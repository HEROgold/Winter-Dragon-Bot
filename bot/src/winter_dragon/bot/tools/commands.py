"""Module that contains utility tools for commands."""

from discord import app_commands
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.log import LoggerMixin


class Commands(LoggerMixin):
    """Utility tools for commands."""

    @staticmethod
    def get_command_mention(bot: WinterDragon, command: app_commands.Command) -> str:
        """Return a command string from a given functiontype. (Decorated with app_commands.command)."""
        if not isinstance(command, app_commands.Command):  # type:ignore[reportUnnecessaryIsInstance]
            msg = f"Expected app_commands.commands.Command but got {type(command)}"
            raise TypeError(msg)

        if cmd := bot.get_app_command(command.qualified_name):
            return cmd.mention
        msg = f"Can't find {command.qualified_name}"
        Commands.logger.exception(msg)
        raise ValueError(msg)
