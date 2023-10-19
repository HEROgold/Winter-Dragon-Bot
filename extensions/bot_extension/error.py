import datetime
import logging
from textwrap import dedent
from typing import Any, Coroutine

import discord
from discord import app_commands
from discord.ext import commands, tasks

from tools import app_command_tools
from tools.config_reader import config
from _types.cogs import Cog
from _types.bot import WinterDragon


class ErrorHandler:
    bot: WinterDragon
    interface: commands.Context | discord.Interaction
    error: app_commands.AppCommandError | commands.CommandError
    logger: logging.Logger
    act: app_command_tools.Converter
    time_code: float


    def __init__(
        self,
        bot: WinterDragon,
        interface: commands.Context | discord.Interaction,
        error: app_commands.AppCommandError | commands.CommandError
    ) -> None:
        self.bot = bot
        self.interface = interface
        self.error = error
        self.help_msg = ""
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")
        self.act = app_command_tools.Converter(bot=self.bot)
        self.time_code = datetime.datetime.now(datetime.timezone.utc).timestamp()
        
        self._async_init.start()


    @tasks.loop(count = 1)
    async def _async_init(self) -> Coroutine[Any, Any, None]:
        self.help_command = await self.act.get_app_command(self.bot.tree.get_command("help"))
        self.invite_command = await self.act.get_app_command(self.bot.tree.get_command("invite"))
        self.server_invite = f"</{self.invite_command} server:{self.invite_command.id}>"

        await self.handle_error()


    @_async_init.before_loop
    async def before_async_init(self) -> None:
        self.logger.debug("Setting up error handler")
        await self.bot.wait_until_ready()


    def _get_message_from_error(self) -> str | app_commands.AppCommandError | commands.CommandError:
        error = self.error

        if isinstance(error, discord.errors.NotFound):
            self.logger.error(f"NotfoundError: CODE: {self.time_code=}")
            return error
        elif isinstance(error, (commands.errors.CommandInvokeError, app_commands.errors.CommandInvokeError)):
            self.logger.error(f"CommandInvokeError: {self.time_code=}")

        error_messages = {
            commands.errors.MissingRequiredArgument: f"Missing a required argument, use {self.help_msg} for more information.",
            commands.errors.BotMissingPermissions: "I do not have enough permissions to use this command!",
            app_commands.errors.BotMissingPermissions: "I do not have enough permissions to use this command!",
            commands.errors.MissingPermissions: "You do not have enough permission to use this command.",
            app_commands.errors.MissingPermissions: "You do not have enough permission to use this command.",
            commands.errors.TooManyArguments: f"Too many arguments given. use {self.help_msg} for more information",
            commands.errors.PrivateMessageOnly: "This command may only be used in a private messages.",
            commands.errors.NoPrivateMessage: "This command does not work in private messages.",
            app_commands.errors.NoPrivateMessage: "This command does not work in private messages.",
            discord.HTTPException: "There is a HTTPException",
            commands.errors.CommandOnCooldown: error,
            app_commands.errors.CommandOnCooldown: error,
            commands.errors.DisabledCommand: error,
            commands.errors.MissingRole: "You are missing a required role",
            app_commands.errors.MissingRole: "You are missing a required role",
            commands.errors.BotMissingRole: "This bot is missing a required role",
            commands.errors.BotMissingAnyRole: "This bot is missing a required role",
            app_commands.errors.MissingAnyRole: "You are missing the required Role",
            commands.errors.MissingAnyRole: "You are missing the required Role",
            commands.errors.CommandNotFound: f"Command not found, try {self.help_command.mention} to find all available commands",
            app_commands.errors.CommandNotFound: f"Command not found, try {self.help_command.mention} to find all available commands",
            commands.errors.MessageNotFound: error,
            commands.errors.MemberNotFound: error,
            commands.errors.UserNotFound: error,
            commands.errors.ChannelNotFound: error,
            commands.errors.RoleNotFound: error,
            commands.errors.EmojiNotFound: error,
            commands.errors.ChannelNotReadable: error,
            commands.errors.BadColourArgument: error,
            commands.errors.BadInviteArgument: error,
            commands.errors.BadBoolArgument: error,
            commands.errors.BadUnionArgument: error,
            commands.errors.NSFWChannelRequired: error,
            commands.errors.ArgumentParsingError: error,
            commands.errors.UserInputError: error,
            commands.errors.ExtensionError: error,
            commands.errors.ExtensionAlreadyLoaded: error,
            commands.errors.ExtensionNotLoaded: error,
            commands.errors.ExtensionFailed: error,
            commands.errors.ExtensionNotFound: error,
            # Errors below need reviewing, might not want to show to users
            commands.errors.CheckAnyFailure: error,
            commands.errors.ConversionError: error,
            commands.errors.NoEntryPointError: error,
            commands.errors.UnexpectedQuoteError: error,
            commands.errors.ExpectedClosingQuoteError: error,
            commands.errors.InvalidEndOfQuotedStringError: error,
            commands.errors.CommandRegistrationError: error,
            commands.errors.PartialEmojiConversionFailure: error,
            commands.errors.MaxConcurrencyReached: error,
        }

        default_message = f"""
            Unexpected error, try {self.help_msg} for help, or contact the bot creator with the following code `{self.time_code}`.
            Use {self.server_invite} to join the official bot server, and submit the error code in the forums channel.
            """

        return error_messages.get(
            type(error),
            dedent(default_message)
        )


    async def get_dm(self, ctx: commands.Context) -> discord.DMChannel:
        self.help_msg = f"`help {ctx.command}`" if ctx else "`help`"
        return ctx.author.dm_channel or await ctx.message.author.create_dm()


    async def handle_error(self) -> None:
        error = self.error
        self.logger.debug(f"{type(error)=}, {error.args=}")
        
        if config.getboolean("Error", "always_log_errors"):
            self.logger.error("Always log error:")
            self.logger.exception(error)
        if config.getboolean("Error", "ignore_errors"):
            return

        message = self._get_message_from_error()
        self.logger.debug(f"{message=}")
        await self.send_message(message)


    async def send_message(
        self,
        message: str
    ) -> Coroutine[Any, Any, None]:
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


# TODO: Might needs to be removed, since in _types.cogs it adds ErrorHandler directly
# Fixable by adding a piece of code too all listeners
# preferably in a wrapper from this module/file
class Error(Cog):
    help_msg: str

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.help_msg = ""


    # -> --- Change on_error to self.on_error on load
    def cog_load(self) -> None: # type: ignore
        tree = self.bot.tree
        tree.on_error = self.on_app_command_error


    # -> --- Change back to default on_error on unload
    def cog_unload(self) -> None: # type: ignore
        tree = self.bot.tree
        tree.on_error = tree.__class__.on_error


    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ) -> None:
        if not interaction:
            self.logger.critical(f"No interaction on interaction: {error=}")
            return
        # Issue with typing /command and spamming dm about cmd not found.
        # Leave handle_error inside if
        if type(error) != app_commands.errors.CommandNotFound and interaction.command.name == "shutdown":
            self.logger.exception(error)
            return
        ErrorHandler(self.bot, interaction, error)


    @Cog.listener()
    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError
    ) -> None:
        if type(error) != app_commands.errors.CommandNotFound:
            self.logger.debug(f"Error from ctx: {ctx.command.name}")
        ErrorHandler(self.bot, ctx, error)


async def setup(bot: WinterDragon) -> None:
    return # Return early to stop using cog.
    if config["Main"]["log_level"] == "DEBUG":
        return
    await bot.add_cog(Error(bot))