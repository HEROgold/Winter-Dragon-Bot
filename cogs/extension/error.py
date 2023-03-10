import datetime
import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import Error as CE
from config import Main as CM
from tools import app_command_tools


class Error(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot:commands.Bot = bot
        self.help_msg = ""
        self.logger = logging.getLogger(f"{CM.BOT_NAME}.error")

    # -> Option 1 --- Change on_error to self.on_error on load
    def cog_load(self) -> None: # type: ignore
        tree = self.bot.tree
        tree.on_error = self.on_app_command_error

    # -> Option 1 --- Change back to default on_error on unload
    def cog_unload(self) -> None: # type: ignore
        tree = self.bot.tree
        tree.on_error = tree.__class__.on_error

    async def on_app_command_error(self, interaction:discord.Interaction, error:app_commands.AppCommandError) -> None:
        if type(error) != app_commands.errors.CommandNotFound:
            self.logger.debug(f"Error from interaction: {interaction.command.name}")
        await self.error_check(interaction, error)

    @commands.Cog.listener()
    async def on_command_error(self, ctx:commands.Context, error:commands.CommandError) -> None:
        if type(error) != commands.errors.CommandNotFound:
            self.logger.debug(f"Error from ctx: {ctx.command.name}")
        await self.error_check(ctx, error)

    async def get_dm(self, i:discord.Interaction|commands.Context) -> discord.DMChannel:
        if isinstance(i, commands.Context):
            ctx:commands.Context = i
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                self.logger.warning("Not allowed to remove message from dm")
            dm = await ctx.message.author.create_dm()
            self.help_msg = f"`help {ctx.command}`" if ctx else "`help`"
        else:
            interaction:discord.Interaction = i
            dm = await interaction.user.create_dm()
            act = app_command_tools.Converter(bot=self.bot)
            app_command, custom_mention = await act.get_sub_app_command(interaction.command)
            try:
                self.help_msg = f"{custom_mention or app_command.mention}"
            except AttributeError:
                help_command = await act.get_app_command(self.bot.tree.get_command("help"))
                self.logger.debug(f"{help_command} {help_command.options}")
                for sub in help_command.options:
                    self.logger.debug(f"{sub}")
                    if type(sub) == app_commands.Argument and sub.name == "command":
                        # TODO: pre fill with the command argument
                        self.help_msg = f"</{help_command.name} command:{help_command.id}>"
                        break
        self.logger.debug(f"Returning dm channel {dm.recipient}, with message {self.help_msg}")
        return dm

    async def error_check(self, x:commands.Context|discord.Interaction, error:app_commands.AppCommandError|commands.CommandError) -> None:
        # sourcery skip: low-code-quality
        dm = await self.get_dm(x)
        code = datetime.datetime.now(datetime.timezone.utc).timestamp()
        if CE.ALWAYS_LOG_ERRORS == True:
            self.logger.exception(error)
        if CE.IGNORE_ERRORS == True:
            return
        invite_command = await app_command_tools.Converter(bot=self.bot).get_app_command(self.bot.tree.get_command("invite"))
        server_invite = f"</{invite_command} server:{invite_command.id}>"        
        self.logger.debug(f"ErrorType: {type(error)}")
        match type(error):
            case commands.errors.MissingRequiredArgument:
                await dm.send(f"Missing a required argument, use {self.help_msg} for more information.")
            case commands.errors.BotMissingPermissions | app_commands.errors.BotMissingPermissions:
                await dm.send("I do not have enough permissions to use this command!")
            case commands.errors.MissingPermissions | app_commands.errors.MissingPermissions:
                await dm.send("You do not have enough permission to use this command.")
            case commands.errors.TooManyArguments:
                await dm.send(f"Too many arguments given. use {self.help_msg} for more information")
            case commands.errors.PrivateMessageOnly:
                await dm.send("This command may only be used in a private messages.")
            case commands.errors.NoPrivateMessage | app_commands.errors.NoPrivateMessage:
                await dm.send("This command does not work in private messages.")
            case discord.HTTPException:
                await dm.send("There is a HTTPException")
            case commands.errors.CommandOnCooldown | app_commands.errors.CommandOnCooldown | commands.errors.DisabledCommand:
                await dm.send(error)
            case commands.errors.MissingRole | app_commands.errors.MissingRole:
                await dm.send("You are missing a required role")
            case commands.errors.BotMissingRole | commands.errors.BotMissingAnyRole:
                await dm.send("This bot is missing a required role")
            case app_commands.errors.MissingAnyRole | commands.errors.MissingAnyRole:
                await dm.send("You are missing the required Role")
            case commands.errors.CommandNotFound | app_commands.errors.CommandNotFound:
                await dm.send("Command not found, try `help` to find all available commands")
            case discord.errors.NotFound:
                self.logger.error(f"NotfoundError: CODE: {code}")
            # case commands.errors.MessageNotFound:
            #     await dm.send(error)
            # case commands.errors.MemberNotFound | commands.errors.UserNotFound:
            #     await dm.send(error)
            # case commands.errors.ChannelNotFound:
            #     await dm.send(error)
            # case commands.errors.RoleNotFound:
            #     await dm.send(error)
            # case commands.errors.EmojiNotFound:
            #     await dm.send(error)
            # case commands.errors.CheckAnyFailure:
            #     await dm.send(error)
            # case commands.errors.PartialEmojiConversionFailure:
            #     await dm.send(error)
            # case commands.errors.MaxConcurrencyReached:
            #     await dm.send(error)
            # case commands.errors.ChannelNotReadable:
            #     await dm.send(error)
            # case commands.errors.BadColourArgument:
            #     await dm.send(error)
            # case commands.errors.BadInviteArgument:
            #     await dm.send(error)
            # case commands.errors.BadBoolArgument:
            #     await dm.send(error)
            # case commands.errors.NSFWChannelRequired:
            #     await dm.send(error)
            # case commands.errors.BadUnionArgument:
            #     await dm.send(error)
            # case commands.errors.ArgumentParsingError:
            #     await dm.send(error)
            # case commands.errors.UnexpectedQuoteError:
            #     await dm.send(error)
            # case commands.errors.ConversionError:
            #     await dm.send(error)
            # case commands.errors.InvalidEndOfQuotedStringError:
            #     await dm.send(error)
            # case commands.errors.ExpectedClosingQuoteError:
            #     await dm.send(error)
            # case commands.errors.NoEntryPointError:
            #     await dm.send(error)
            # case commands.errors.CommandRegistrationError:
            #     await dm.send(error)
            # case commands.errors.UserInputError:
            #     await dm.send(error)
            # case commands.errors.ExtensionError:
            #     await dm.send(error)
            # case commands.errors.ExtensionAlreadyLoaded:
            #     await dm.send(error)
            # case commands.errors.ExtensionNotLoaded:
            #     await dm.send(error)
            # case commands.errors.ExtensionFailed:
            #     await dm.send(error)
            # case commands.errors.ExtensionNotFound:
            #     await dm.send(error)
            case commands.errors.CommandInvokeError | app_commands.errors.CommandInvokeError:
                self.logger.error(f"Args: {error.args}")
                for arg in error.args:
                    if "NotOwner" in arg:
                        await dm.send("Only the bot owner(s) may use this command!")
                    else:
                        self.logger.error(f"Error executing command, CODE: {code}")
                        await dm.send(f"Error executing command, please contact the bot creator with the following code `{code}`.\nTry {self.help_msg}, Or Use {server_invite} to join the official bot server")
            case _:
                self.logger.error(f"Unexpected error, CODE: {code}")
                await dm.send(f"Unexpected error, try {self.help_msg} for more help, or contact the bot creator with the following code `{code}`.\nuse {server_invite} to join the official bot server")

async def setup(bot:commands.Bot) -> None:
    # sourcery skip: instance-method-first-arg-name
	await bot.add_cog(Error(bot))
