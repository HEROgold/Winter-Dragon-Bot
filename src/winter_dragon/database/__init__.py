"""The database package for the Winter Dragon project."""

from sqlmodel import SQLModel

from winter_dragon.bot.extensions.server.infractions import Infractions
from winter_dragon.bot.extensions.server.welcome import Welcome
from winter_dragon.bot.extensions.user.reminder import Reminder
from winter_dragon.database.tables import (
    GuildAuditLog,
    GuildCommands,
    GuildRoles,
    Guilds,
    Hangmen,
    Lobbies,
    LookingForGroup,
    Messages,
    NhieQuestion,
    Presence,
    ResultMassiveMultiplayer,
    Roles,
    SteamSale,
    SteamUsers,
    Suggestions,
    SyncBanGuild,
    SyncBanUser,
    UserRoles,
    Users,
    WyrQuestion,
)
from winter_dragon.database.tables.associations.auto_assign_role import AutoAssignRole
from winter_dragon.database.tables.associations.channel_audit import ChannelAudit
from winter_dragon.database.tables.associations.channel_lobby import ChannelLobby
from winter_dragon.database.tables.associations.channel_tags import ChannelTag
from winter_dragon.database.tables.associations.user_command import AssociationUserCommand
from winter_dragon.database.tables.associations.user_hangman import AssociationUserHangman
from winter_dragon.database.tables.associations.user_lobby import AssociationUserLobby
from winter_dragon.database.tables.audit_log import AuditLog
from winter_dragon.database.tables.auto_reassign import AutoReAssign
from winter_dragon.database.tables.autochannel import AutoChannels
from winter_dragon.database.tables.autochannel_settings import AutoChannelSettings
from winter_dragon.database.tables.car_fuel import CarFuels
from winter_dragon.database.tables.channel import Channels
from winter_dragon.database.tables.command import Commands
from winter_dragon.database.tables.commandgroup import CommandGroups
from winter_dragon.database.tables.disabled_commands import DisabledCommands
from winter_dragon.database.tables.game import Games
from winter_dragon.database.tables.incremental import Players, UserMoney
from winter_dragon.database.tables.incremental.generators import Generators
from winter_dragon.database.tables.incremental.rates import GeneratorRates
from winter_dragon.database.tables.incremental.user_generator import AssociationUserGenerator
from winter_dragon.database.tables.reminder import TimedReminder
from winter_dragon.database.tables.steamsale import SteamSaleProperties
from winter_dragon.database.tables.sync_ban.sync_ban_banned_by import SyncBanBannedBy

from .constants import SessionMixin, session


__all__ = [
    "AssociationUserCommand",
    "AssociationUserGenerator",
    "AssociationUserHangman",
    "AssociationUserLobby",
    "AuditLog",
    "AutoAssignRole",
    "AutoChannelSettings",
    "AutoChannels",
    "AutoReAssign",
    "CarFuels",
    "ChannelAudit",
    "ChannelLobby",
    "ChannelTag",
    "Channels",
    "CommandGroups",
    "Commands",
    "DisabledCommands",
    "Games",
    "GeneratorRates",
    "Generators",
    "GuildAuditLog",
    "GuildCommands",
    "GuildRoles",
    "Guilds",
    "Hangmen",
    "Infractions",
    "Lobbies",
    "LookingForGroup",
    "Messages",
    "NhieQuestion",
    "Players",
    "Presence",
    "Reminder",
    "ResultMassiveMultiplayer",
    "Roles",
    "SQLModel",
    "SessionMixin",
    "SteamSale",
    "SteamSaleProperties",
    "SteamUsers",
    "Suggestions",
    "SyncBanBannedBy",
    "SyncBanGuild",
    "SyncBanUser",
    "TimedReminder",
    "UserMoney",
    "UserRoles",
    "Users",
    "Welcome",
    "WyrQuestion",
    "session",
]
