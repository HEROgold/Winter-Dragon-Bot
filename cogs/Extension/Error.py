import discord
from discord.ext import commands

class Error(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        print(self, error, ctx)
        dm = await ctx.message.author.create_dm()
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing a required argument, use the Help command for more information.")
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send("I do not have enough permissions to use this command!")
        if isinstance(error, commands.CommandNotFound):
            await ctx.messagedelete()
            await dm.send(error)
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have enough permission to use this command.")
        if isinstance(error, commands.TooManyArguments):
            await ctx.send("Too many arguments given. use the Help command for more information")
        if isinstance(error, commands.PrivateMessageOnly):
            await ctx.send("This command may only be used in a private messages.")
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send("This command does not work in private messages.")
def setup(bot):
	bot.add_cog(Error(bot))

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