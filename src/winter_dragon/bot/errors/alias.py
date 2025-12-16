"""Type aliases shared by the bot's error handling helpers."""

from discord.app_commands.errors import AppCommandError
from discord.ext.commands.errors import CommandError


type DiscordCommandError = CommandError | AppCommandError
