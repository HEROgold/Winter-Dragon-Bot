from discord import (
    ClientException,
    DiscordException,
    DiscordServerError,
    HTTPException,
    app_commands,
)
from discord.ext import commands


type CommandErrors = (
    commands.errors.MissingRequiredArgument
    | commands.errors.BotMissingPermissions
    | commands.errors.MissingPermissions
    | commands.errors.TooManyArguments
    | commands.errors.PrivateMessageOnly
    | commands.errors.NoPrivateMessage
    | commands.errors.CommandOnCooldown
    | commands.errors.DisabledCommand
    | commands.errors.MissingRole
    | commands.errors.BotMissingRole
    | commands.errors.BotMissingAnyRole
    | commands.errors.MissingAnyRole
    | commands.errors.CommandNotFound
    | commands.errors.MessageNotFound
    | commands.errors.MemberNotFound
    | commands.errors.UserNotFound
    | commands.errors.ChannelNotFound
    | commands.errors.RoleNotFound
    | commands.errors.EmojiNotFound
    | commands.errors.ChannelNotReadable
    | commands.errors.BadColourArgument
    | commands.errors.BadInviteArgument
    | commands.errors.BadBoolArgument
    | commands.errors.BadUnionArgument
    | commands.errors.NSFWChannelRequired
    | commands.errors.ArgumentParsingError
    | commands.errors.UserInputError
    | commands.errors.ExtensionError
    | commands.errors.ExtensionAlreadyLoaded
    | commands.errors.ExtensionNotLoaded
    | commands.errors.ExtensionFailed
    | commands.errors.ExtensionNotFound
    | commands.errors.CheckAnyFailure
    | commands.errors.ConversionError
    | commands.errors.NoEntryPointError
    | commands.errors.UnexpectedQuoteError
    | commands.errors.ExpectedClosingQuoteError
    | commands.errors.InvalidEndOfQuotedStringError
    | commands.errors.CommandRegistrationError
    | commands.errors.PartialEmojiConversionFailure
    | commands.errors.MaxConcurrencyReached
)

type AppCommandErrors = (
    app_commands.errors.BotMissingPermissions
    | app_commands.errors.MissingPermissions
    | app_commands.errors.NoPrivateMessage
    | app_commands.errors.CommandOnCooldown
    | app_commands.errors.MissingRole
    | app_commands.errors.MissingAnyRole
    | app_commands.errors.CommandNotFound
)

type AllErrors = CommandErrors | AppCommandErrors | HTTPException | DiscordException | ClientException | DiscordServerError
