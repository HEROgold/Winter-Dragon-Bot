import discord
from discord.ext import commands
from config import error as CE

class Error(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        print(self, error, ctx)
        dm = await ctx.message.author.create_dm()
        if isinstance(error, commands.MissingRequiredArgument) and CE.log_MissingRequiredArgument == True:
            await ctx.send("Missing a required argument, use the Help command for more information.")
        if isinstance(error, commands.BotMissingPermissions) and CE.log_BotMissingPermissions == True:
            await ctx.send("I do not have enough permissions to use this command!")
        if isinstance(error, commands.CommandNotFound) and CE.log_CommandNotFound == True:
            await ctx.message.delete()
            await dm.send(error)
        if isinstance(error, commands.MissingPermissions) and CE.log_MissingPermissions == True:
            await ctx.send("You do not have enough permission to use this command.")
        if isinstance(error, commands.TooManyArguments) and CE.log_TooManyArguments == True:
            await ctx.send("Too many arguments given. use the Help command for more information")
        if isinstance(error, commands.PrivateMessageOnly) and CE.log_PrivateMessageOnly == True:
            await ctx.send("This command may only be used in a private messages.")
        if isinstance(error, commands.NoPrivateMessage) and CE.log_NoPrivateMessage == True:
            await ctx.send("This command does not work in private messages.")
        if isinstance(error, discord.HTTPException) and CE.log_HTTPException == True:
            print(error)
            await ctx.send("There is a HTTPException")
        if isinstance(error, commands.errors.CommandOnCooldown) and CE.log_CommandError == True:
            await ctx.send(error)
        elif CE.ignore_errors == True:
            print (error)
def setup(bot):
	bot.add_cog(Error(bot))


# USE commands.errors TO AUTOFILL  ERRORS TOO
#    'CheckFailure',
#    'CheckAnyFailure',
#    'CommandNotFound',
#    'DisabledCommand',
#    'CommandInvokeError',
#    'UserInputError',
#    'CommandOnCooldown',
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
#    'MissingRole',
#    'BotMissingRole',
#    'MissingAnyRole',
#    'BotMissingAnyRole',
#    'MissingPermissions',
#    'BotMissingPermissions',
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