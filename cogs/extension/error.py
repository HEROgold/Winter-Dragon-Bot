import datetime
import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import error as CE


class Error(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot
        self.help_msg = ""
        self.logger = logging.getLogger("winter_dragon.error")


    # -> Option 1 --- Change on_error to self.on_error on load
    def cog_load(self):
        tree = self.bot.tree
        tree.on_error = self.on_app_command_error

    # -> Option 1 --- Change back to default on_error on unload
    def cog_unload(self):
        tree = self.bot.tree
        tree.on_error = tree.__class__.on_error

    async def on_app_command_error(self, interaction:discord.Interaction, error:app_commands.AppCommandError):
        self.logger.debug(f"Error from: {interaction.command.name}")
        await self.error_check(interaction, error)

    @commands.Cog.listener()
    async def on_command_error(self, ctx:commands.Context, error:commands.CommandError):
        self.logger.debug(f"Error from: {ctx.command.name}")
        await self.error_check(ctx, error)

    async def get_dm(self, x:discord.Interaction|commands.Context) -> discord.DMChannel:
        if isinstance(x, commands.Context):
            ctx:commands.Context = x
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                self.logger.warning("Not allowed to remove message from dm")
            dm = await ctx.message.author.create_dm()
            self.help_msg = f"`help {ctx.command}`" if ctx else "`help`"
        elif isinstance(x, discord.Interaction):
            interaction:discord.Interaction = x
            dm = await interaction.user.create_dm()
            self.help_msg = f"`help {interaction.command.name}`" if interaction else "`help`"
        self.logger.debug(f"Returning dm channel {dm.recipient}")
        return dm

    async def error_check(self, x:commands.Context|discord.Interaction, error:app_commands.AppCommandError|commands.CommandError):
        # sourcery skip: low-code-quality
        dm = await self.get_dm(x)
        if CE.always_log_errors == True:
            self.logger.exception(error)
        if CE.ignore_errors == True:
            return
        elif isinstance(error, commands.MissingRequiredArgument) and CE.MissingRequiredArgument == True:
            await dm.send(f"Missing a required argument, use {self.help_msg} for more information.")
        elif isinstance(error, commands.BotMissingPermissions | app_commands.errors.BotMissingPermissions) and CE.BotMissingPermissions == True:
            await dm.send("I do not have enough permissions to use this command!")
        elif isinstance(error, commands.MissingPermissions | app_commands.errors.MissingPermissions) and CE.MissingPermissions == True:
            await dm.send("You do not have enough permission to use this command.")
        elif isinstance(error, commands.CommandNotFound | app_commands.errors.CommandNotFound) and CE.CommandNotFound == True:
            await dm.send("Command not found, try `help` to find all available commands")
        elif isinstance(error, commands.TooManyArguments) and CE.TooManyArguments == True:
            await dm.send(f"Too many arguments given. use {self.help_msg} for more information")
        elif isinstance(error, commands.PrivateMessageOnly) and CE.PrivateMessageOnly == True:
            await dm.send("This command may only be used in a private messages.")
        elif isinstance(error, commands.NoPrivateMessage | app_commands.errors.NoPrivateMessage) and CE.NoPrivateMessage == True:
            await dm.send("This command does not work in private messages.")
        elif isinstance(error, discord.HTTPException) and CE.HTTPException == True:
            await dm.send(f"There is a HTTPException, {error}")
        elif isinstance(error, commands.errors.CommandOnCooldown | app_commands.errors.CommandOnCooldown) and CE.CooldownError == True:
            await dm.send(error)
        elif isinstance(error, commands.errors.DisabledCommand) and CE.DisabledCommand == True:
            await dm.send(error)
        elif isinstance(error, commands.errors.MissingRole | app_commands.errors.MissingRole) and CE.UserMissingRole == True:
            await dm.send("You are missing a required role")
        elif isinstance(error, commands.errors.BotMissingRole) and CE.UserMissingRole == True:
            await dm.send("This bot is missing a required role")
        elif isinstance(error, commands.errors.CommandInvokeError | app_commands.errors.CommandInvokeError) and CE.CommandInvokeError == True:
            for arg in error.args:
                if "NotOwner" in arg and CE.NotOwner == True:
                    await dm.send("Only the bot owner(s) may use this command!")
                else:
                    await dm.send(f"Error during command execution: {error}")
        else:
            code = datetime.datetime.now(datetime.timezone.utc).timestamp()
            self.logger.error(f"Unexpected error, CODE: {code}, Error: {error}")
            await dm.send(f"Unexpected error, try {self.help_msg} for more help, or contact bot creator with the following code `{code}`")

async def setup(bot:commands.Bot):
	await bot.add_cog(Error(bot))

# TODO add remaining error types
# REMINDER: app_commands.errors
# Add app commands checks
# USE commands.errors TO AUTOFILL  ERRORS TOO
#    'CheckAnyFailure',
#    'UserInputError',
#    'MaxConcurrencyReached',
#    'MessageNotFound',
#    'MemberNotFound',
#    'UserNotFound',
#    'ChannelNotFound',
#    'ChannelNotReadable',
#    'BadColourArgument',
#    'RoleNotFound',
#    'BadInviteArgument',
#    'EmojiNotFound',
#    'PartialEmojiConversionFailure',
#    'BadBoolArgument',
#    'MissingAnyRole',
#    'BotMissingAnyRole',
#    'NSFWChannelRequired',
#    'ConversionError',
#    'BadUnionArgument',
#    'ArgumentParsingError',
#    'UnexpectedQuoteError',
#    'InvalidEndOfQuotedStringError',
#    'ExpectedClosingQuoteError',
#    'ExtensionError',
#    'ExtensionAlreadyLoaded',
#    'ExtensionNotLoaded',
#    'NoEntryPointError',
#    'ExtensionFailed',
#    'ExtensionNotFound',
#    'CommandRegistrationError