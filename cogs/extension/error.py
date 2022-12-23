import logging
import discord
from discord.ext import commands
from config import error as CE

class Error(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx:commands.Context, error):
        # sourcery skip: low-code-quality
        dm = await ctx.message.author.create_dm()
        help_msg = f"`help {ctx.command}`" if ctx else "`help`"
        if CE.always_send_errors == True:
            await dm.send(f"Always_send_errors is set to true, skipping error handling and giving error directly.\n{error}")
        elif CE.ignore_errors == True:
            logging.info(f"Ignoring error {error}")
        elif isinstance(error, commands.MissingRequiredArgument) and CE.log_MissingRequiredArgument == True:
            await ctx.send(f"Missing a required argument, use {help_msg} for more information.")
        elif isinstance(error, commands.BotMissingPermissions) and CE.log_BotMissingPermissions == True:
            await ctx.send("I do not have enough permissions to use this command!")
        elif isinstance(error, commands.MissingPermissions) and CE.log_MissingPermissions == True:
            await ctx.send("You do not have enough permission to use this command.")
        elif isinstance(error, commands.CommandNotFound) and CE.log_CommandNotFound == True:
            await ctx.message.delete()
            await dm.send("Command not found, try `help` to find all available commands")
        elif isinstance(error, commands.TooManyArguments) and CE.log_TooManyArguments == True:
            await ctx.send(f"Too many arguments given. use {help_msg} for more information")
        elif isinstance(error, commands.PrivateMessageOnly) and CE.log_PrivateMessageOnly == True:
            await ctx.send("This command may only be used in a private messages.")
        elif isinstance(error, commands.NoPrivateMessage) and CE.log_NoPrivateMessage == True:
            await ctx.send("This command does not work in private messages.")
        elif isinstance(error, discord.HTTPException) and CE.log_HTTPException == True:
            logging.error(error)
            await ctx.send(f"There is a HTTPException, {error}")
        elif isinstance(error, commands.errors.CommandOnCooldown) and CE.log_CooldownError == True:
            await ctx.message.delete()
            await dm.send(error)
        elif isinstance(error, commands.errors.CommandNotFound) and CE.log_CommandNotFound == True:
            await dm.send(error)
        elif isinstance(error, commands.errors.DisabledCommand) and CE.log_DisabledCommand == True:
            await ctx.message.delete()
            await dm.send(error)
        elif isinstance(error, commands.errors.MissingRole) and CE.log_UserMissingRole == True:
            await dm.send("You are missing a required role")
        elif isinstance(error, commands.errors.BotMissingRole) and CE.log_UserMissingRole == True:
            await dm.send("This bot is missing a required role")
        else:
            logging.error(f"Unexpected error: {error}")
            await dm.send(f"Unexpected error, try {help_msg} for help with commands, or contact bot creator.")

async def setup(bot:commands.Bot):
	await bot.add_cog(Error(bot))

# TODO add remaining error types
# USE commands.errors TO AUTOFILL  ERRORS TOO
#    'CheckAnyFailure',
#    'CommandInvokeError',
#    'UserInputError',
#    'MaxConcurrencyReached',
#    'NotOwner',
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