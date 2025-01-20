import datetime
import logging
from textwrap import dedent

import discord
from discord import app_commands
from discord.ext import commands

from bot.core import WinterDragon
from bot.base.mixins import LoggerMixin
from bot.config import config
from bot.core.tasks import loop
from bot.errors.aliases import AllErrors


type ReturnOriginal = (
    commands.errors.MessageNotFound |
    commands.errors.MemberNotFound |
    commands.errors.UserNotFound |
    commands.errors.ChannelNotFound |
    commands.errors.RoleNotFound |
    commands.errors.EmojiNotFound |
    commands.errors.ChannelNotReadable |
    commands.errors.BadColourArgument |
    commands.errors.BadInviteArgument |
    commands.errors.BadBoolArgument |
    commands.errors.BadUnionArgument |
    commands.errors.NSFWChannelRequired |
    commands.errors.ArgumentParsingError |
    commands.errors.UserInputError |
    commands.errors.ExtensionError |
    commands.errors.ExtensionAlreadyLoaded |
    commands.errors.ExtensionNotLoaded |
    commands.errors.ExtensionFailed |
    commands.errors.ExtensionNotFound |
    commands.errors.CheckAnyFailure |
    commands.errors.ConversionError |
    commands.errors.NoEntryPointError |
    commands.errors.UnexpectedQuoteError |
    commands.errors.ExpectedClosingQuoteError |
    commands.errors.InvalidEndOfQuotedStringError |
    commands.errors.CommandRegistrationError |
    commands.errors.PartialEmojiConversionFailure |
    commands.errors.MaxConcurrencyReached |
    app_commands.errors.CommandSyncFailure |
    commands.errors.CommandOnCooldown |
    app_commands.errors.CommandOnCooldown |
    commands.errors.DisabledCommand
)


class ErrorHandler(LoggerMixin):
    """ErrorHandler is a class that handles errors encountered during command execution in the WinterDragon bot.

    Args:
    ----
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
        self.time_code = datetime.datetime.now(datetime.UTC).timestamp()

        self._async_init.start()


    @loop(count=1)
    async def _async_init(self) -> None:
        self.invite_command = self.bot.get_app_command("invite")
        if self.invite_command is None:
            self.server_invite = self.bot.get_bot_invite()
        else:
            self.server_invite = f"</{self.invite_command} server:{self.invite_command.id}>"

        await self.handle_error()


    @_async_init.before_loop
    async def before_async_init(self) -> None:
        self.logger.debug("Setting up error handler")
        await self.bot.wait_until_ready()


    def _get_message_from_error(self) -> str | AllErrors:
        error = self.error

        if isinstance(error, discord.errors.NotFound):
            self.logger.error(f"NotfoundError: CODE: {self.time_code=}")
            return error
        if isinstance(
            error,
            commands.errors.CommandInvokeError | app_commands.errors.CommandInvokeError,
        ):
            self.logger.error(f"CommandInvokeError: {self.time_code=}")

        original = getattr(error, "original", error)
        self.logger.debug(f"{original=}, {error=}")
        error_msg = self.get_error_message(original)
        return error_msg or "An unexpected error occurred."

    def get_error_message(self, error: AllErrors) -> str | AllErrors:  # noqa: C901, PLR0912
        error_msg = ""
        match type(error):
            case commands.errors.MissingRequiredArgument:
                error_msg = f"Missing a required argument, {error.param}."
            case commands.errors.BotMissingPermissions | app_commands.errors.BotMissingPermissions:
                error_msg = f"I do not have enough permissions to use this command! {error.missing_permissions}"
            case commands.errors.MissingPermissions | app_commands.errors.MissingPermissions:
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
            case commands.errors.MissingRole | app_commands.errors.MissingRole:
                error_msg = f"You are missing a required role, {error.missing_role}"
            case commands.errors.BotMissingRole | commands.errors.BotMissingAnyRole:
                error_msg = f"This bot is missing a required role, {error.missing_role}"
            case app_commands.errors.MissingAnyRole | commands.errors.MissingAnyRole:
                error_msg = f"You are missing the required Role, {error.missing_roles}"
            # Errors below need reviewing, might not want to show to users
            case commands.errors.CommandInvokeError | app_commands.errors.CommandInvokeError:
                if "403 Forbidden" in error.args:
                    error_msg = error
            case commands.errors.CheckFailure:
                error_msg = f"{error}"
            case discord.errors.Forbidden:
                error_msg = "I do not have enough permissions to do that."
            case _:
                error_msg = dedent(f"""
                    Unexpected error {error}, try {self.help_msg} for help.
                    Or contact the bot creator with the following code `{self.time_code}`.
                    Use {self.server_invite} to join the official bot guild, and submit the error code in the forums channel.
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
            self.logger.exception(error, exc_info=True)
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
                await original.edit(content=message)
        else:
            dm = await self.get_dm(interface)

            try:
                await interface.message.delete()
                await interface.send(message)
            except discord.Forbidden:
                self.logger.warning("Not allowed to remove message")
                await dm.send(message)
