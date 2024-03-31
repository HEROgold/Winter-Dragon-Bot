import datetime
import logging
from textwrap import dedent

import discord
from discord import app_commands
from discord.ext import commands, tasks

from _types.bot import WinterDragon
from _types.errors import AllErrors
from tools.config_reader import config


class ErrorHandler:
    """
    ErrorHandler is a class that handles errors encountered during command execution in the WinterDragon bot.

    Args:
        bot (WinterDragon): The instance of the WinterDragon bot.
        interface (commands.Context | discord.Interaction): The context or interaction where the error occurred.
        error (app_commands.AppCommandError | commands.CommandError): The error that occurred.
    """

    interface: commands.Context | discord.Interaction
    error: AllErrors
    logger: logging.Logger
    time_code: float

    def __init__(
        self,
        bot: WinterDragon,
        interface: commands.Context | discord.Interaction,
        error: AllErrors | Exception,
    ) -> None:
        self.bot = bot
        self.interface = interface
        self.error = error
        self.help_msg = "`help`"
        self.logger = logging.getLogger(
            f"{config['Main']['bot_name']}.{self.__class__.__name__}",
        )
        self.time_code = datetime.datetime.now(datetime.UTC).timestamp()

        self._async_init.start()

    @tasks.loop(count=1)
    async def _async_init(self) -> None:
        # self.help_command = self.bot.get_app_command("help")
        self.invite_command = self.bot.get_app_command("invite")
        self.server_invite = f"</{self.invite_command} server:{self.invite_command.id}>"

        await self.handle_error()

    @_async_init.before_loop
    async def before_async_init(self) -> None:
        self.logger.debug("Setting up error handler")
        await self.bot.wait_until_ready()

    def _get_message_from_error(self) -> str | AllErrors:  # noqa: PLR0915
        error = self.error

        if isinstance(error, discord.errors.NotFound):
            self.logger.error(f"NotfoundError: CODE: {self.time_code=}")
            return error
        if isinstance(
            error,
            commands.errors.CommandInvokeError | app_commands.errors.CommandInvokeError,
        ):
            self.logger.error(f"CommandInvokeError: {self.time_code=}")

        match type(error):
            case commands.errors.MissingRequiredArgument:
                error_msg = f"Missing a required argument, {error.param}."
            case commands.errors.BotMissingPermissions:
                error_msg = f"I do not have enough permissions to use this command! {error.missing_permissions}"
            case app_commands.errors.BotMissingPermissions:
                error_msg = f"I do not have enough permissions to use this command! {error.missing_permissions}"
            case commands.errors.MissingPermissions:
                error_msg = f"You do not have enough permission to use this command! {error.missing_permissions}"
            case app_commands.errors.MissingPermissions:
                error_msg = f"You do not have enough permission to use this command! {error.missing_permissions}"
            case commands.errors.TooManyArguments:
                error_msg = f"Too many arguments given. use {self.help_msg} for more information"
            case commands.errors.PrivateMessageOnly:
                error_msg = "This command may only be used in a private messages."
            case commands.errors.NoPrivateMessage:
                error_msg = "This command does not work in private messages."
            case app_commands.errors.NoPrivateMessage:
                error_msg = "This command does not work in private messages."
            case discord.HTTPException:
                error_msg = f"There is a HTTPException {error.status, error.code, error.text}"
            case commands.errors.CommandOnCooldown:
                error_msg = error
            case app_commands.errors.CommandOnCooldown:
                error_msg = error
            case commands.errors.DisabledCommand:
                error_msg = error
            case commands.errors.MissingRole:
                error_msg = f"You are missing a required role, {error.missing_role}"
            case app_commands.errors.MissingRole:
                error_msg = f"You are missing a required role, {error.missing_role}"
            case commands.errors.BotMissingRole:
                error_msg = f"This bot is missing a required role, {error.missing_role}"
            case commands.errors.BotMissingAnyRole:
                error_msg = f"This bot is missing a required role, {error.missing_roles}"
            case app_commands.errors.MissingAnyRole:
                error_msg = f"You are missing the required Role, {error.missing_roles}"
            case commands.errors.MissingAnyRole:
                error_msg = f"You are missing the required Role, {error.missing_roles}"
            # case commands.errors.CommandNotFound: error_msg = f"Command not found, try {self.help_command.mention} to find all available commands",
            # case app_commands.errors.CommandNotFound: error_msg = f"Command not found, try {self.help_command.mention} to find all available commands",
            case commands.errors.MessageNotFound:
                error_msg = error
            case commands.errors.MemberNotFound:
                error_msg = error
            case commands.errors.UserNotFound:
                error_msg = error
            case commands.errors.ChannelNotFound:
                error_msg = error
            case commands.errors.RoleNotFound:
                error_msg = error
            case commands.errors.EmojiNotFound:
                error_msg = error
            case commands.errors.ChannelNotReadable:
                error_msg = error
            case commands.errors.BadColourArgument:
                error_msg = error
            case commands.errors.BadInviteArgument:
                error_msg = error
            case commands.errors.BadBoolArgument:
                error_msg = error
            case commands.errors.BadUnionArgument:
                error_msg = error
            case commands.errors.NSFWChannelRequired:
                error_msg = error
            case commands.errors.ArgumentParsingError:
                error_msg = error
            case commands.errors.UserInputError:
                error_msg = error
            case commands.errors.ExtensionError:
                error_msg = error
            case commands.errors.ExtensionAlreadyLoaded:
                error_msg = error
            case commands.errors.ExtensionNotLoaded:
                error_msg = error
            case commands.errors.ExtensionFailed:
                error_msg = error
            case commands.errors.ExtensionNotFound:
                error_msg = error
            # Errors below need reviewing, might not want to show to users
            case commands.errors.CheckAnyFailure:
                error_msg = error
            case commands.errors.ConversionError:
                error_msg = error
            case commands.errors.NoEntryPointError:
                error_msg = error
            case commands.errors.UnexpectedQuoteError:
                error_msg = error
            case commands.errors.ExpectedClosingQuoteError:
                error_msg = error
            case commands.errors.InvalidEndOfQuotedStringError:
                error_msg = error
            case commands.errors.CommandRegistrationError:
                error_msg = error
            case commands.errors.PartialEmojiConversionFailure:
                error_msg = error
            case commands.errors.MaxConcurrencyReached:
                error_msg = error
            case commands.errors.CommandInvokeError | app_commands.errors.CommandInvokeError:
                # TODO: Add invoke error handling
                if "403 Forbidden" in error.args:
                    pass
            case _:
                error_msg = dedent(f"""
                    Unexpected error {error.type}, try {self.help_msg} for help, or contact the bot creator with the following code `{self.time_code}`.
                    Use {self.server_invite} to join the official bot server, and submit the error code in the forums channel.
                    """)
        return error_msg

    async def get_dm(self, ctx: commands.Context) -> discord.DMChannel:
        self.help_msg = f"`help {ctx.command}`" if ctx else "`help`"
        return ctx.author.dm_channel or await ctx.message.author.create_dm()

    async def handle_error(self) -> None:
        error = self.error
        self.logger.debug(f"{type(error)=}, {error.args=}")

        if config.getboolean("Error", "always_log_errors"):
            self.logger.error(f"Always log error: {self.time_code}")
            self.logger.exception(error)
        if config.getboolean("Error", "ignore_errors"):
            return

        message = self._get_message_from_error()
        self.logger.debug(f"{message=}")
        await self.send_message(f"{message}")

    async def send_message(self, message: str) -> None:
        interface = self.interface

        if isinstance(interface, discord.Interaction):
            try:
                await interface.response.send_message(message, ephemeral=True)
            except discord.errors.InteractionResponded:
                original = await interface.original_response()
                await original.edit(content="Unexpected Error...", delete_after=10)
                dm = interface.user.dm_channel or await interface.user.create_dm()
                await dm.send(message)
        else:
            dm = await self.get_dm(interface)
            self.logger.debug(f"Sending {message=} to {dm=}")

            try:
                await interface.message.delete()
            except discord.Forbidden:
                self.logger.warning("Not allowed to remove message from dm")

            await interface.send(message)
