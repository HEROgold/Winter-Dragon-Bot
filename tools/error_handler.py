import datetime
import logging
from textwrap import dedent

import discord
from discord import app_commands
from discord.ext import commands, tasks

from _types.bot import WinterDragon
from _types.error_types import AllErrors
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
        error: AllErrors
    ) -> None:
        self.bot = bot
        self.interface = interface
        self.error = error
        self.help_msg = "`help`"
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")
        self.time_code = datetime.datetime.now(datetime.timezone.utc).timestamp()
        
        self._async_init.start()


    @tasks.loop(count = 1)
    async def _async_init(self) -> None:
        # self.help_command = self.bot.get_app_command("help")
        self.invite_command = self.bot.get_app_command("invite")
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
        elif isinstance(error, (commands.errors.CommandInvokeError, app_commands.errors.CommandInvokeError)):
            self.logger.error(f"CommandInvokeError: {self.time_code=}")

        match type(error):
            case commands.errors.MissingRequiredArgument: return f"Missing a required argument, {error.param}.", 
            case commands.errors.BotMissingPermissions: return f"I do not have enough permissions to use this command! {error.missing_permissions}",
            case app_commands.errors.BotMissingPermissions: return f"I do not have enough permissions to use this command! {error.missing_permissions}",
            case commands.errors.MissingPermissions: return f"You do not have enough permission to use this command! {error.missing_permissions}",
            case app_commands.errors.MissingPermissions: return f"You do not have enough permission to use this command! {error.missing_permissions}",
            case commands.errors.TooManyArguments: return f"Too many arguments given. use {self.help_msg} for more information",
            case commands.errors.PrivateMessageOnly: return "This command may only be used in a private messages.",
            case commands.errors.NoPrivateMessage: return "This command does not work in private messages.",
            case app_commands.errors.NoPrivateMessage: return "This command does not work in private messages.",
            case discord.HTTPException: return f"There is a HTTPException {error.status, error.code, error.text}",
            case commands.errors.CommandOnCooldown: return error,
            case app_commands.errors.CommandOnCooldown: return error,
            case commands.errors.DisabledCommand: return error,
            case commands.errors.MissingRole: return f"You are missing a required role, {error.missing_role}",
            case app_commands.errors.MissingRole: return f"You are missing a required role, {error.missing_role}",
            case commands.errors.BotMissingRole: return f"This bot is missing a required role, {error.missing_role}",
            case commands.errors.BotMissingAnyRole: return f"This bot is missing a required role, {error.missing_roles}",
            case app_commands.errors.MissingAnyRole: return f"You are missing the required Role, {error.missing_roles}",
            case commands.errors.MissingAnyRole: return f"You are missing the required Role, {error.missing_roles}",
            # case commands.errors.CommandNotFound: return f"Command not found, try {self.help_command.mention} to find all available commands",
            # case app_commands.errors.CommandNotFound: return f"Command not found, try {self.help_command.mention} to find all available commands",
            case commands.errors.MessageNotFound: return error,
            case commands.errors.MemberNotFound: return error,
            case commands.errors.UserNotFound: return error,
            case commands.errors.ChannelNotFound: return error,
            case commands.errors.RoleNotFound: return error,
            case commands.errors.EmojiNotFound: return error,
            case commands.errors.ChannelNotReadable: return error,
            case commands.errors.BadColourArgument: return error,
            case commands.errors.BadInviteArgument: return error,
            case commands.errors.BadBoolArgument: return error,
            case commands.errors.BadUnionArgument: return error,
            case commands.errors.NSFWChannelRequired: return error,
            case commands.errors.ArgumentParsingError: return error,
            case commands.errors.UserInputError: return error,
            case commands.errors.ExtensionError: return error,
            case commands.errors.ExtensionAlreadyLoaded: return error,
            case commands.errors.ExtensionNotLoaded: return error,
            case commands.errors.ExtensionFailed: return error,
            case commands.errors.ExtensionNotFound: return error,
            # Errors below need reviewing, might not want to show to users
            case commands.errors.CheckAnyFailure: return error,
            case commands.errors.ConversionError: return error,
            case commands.errors.NoEntryPointError: return error,
            case commands.errors.UnexpectedQuoteError: return error,
            case commands.errors.ExpectedClosingQuoteError: return error,
            case commands.errors.InvalidEndOfQuotedStringError: return error,
            case commands.errors.CommandRegistrationError: return error,
            case commands.errors.PartialEmojiConversionFailure: return error,
            case commands.errors.MaxConcurrencyReached: return error,
            case _: return dedent(f"""
                Unexpected error, try {self.help_msg} for help, or contact the bot creator with the following code `{self.time_code}`.
                Use {self.server_invite} to join the official bot server, and submit the error code in the forums channel.
            """)


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
        await self.send_message(message)


    async def send_message(
        self,
        message: str
    ) -> None:
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
