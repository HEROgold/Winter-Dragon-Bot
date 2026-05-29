from __future__ import annotations

lazy from .associations import (
    AssociationUserCommand,
    AssociationUserHangman,
    AssociationUserLobby,
    ChannelTag,
    GuildCommands,
    GuildRoles,
)
lazy from .associations.auto_assign_role import AutoAssignRole
lazy from .associations.channel_lobby import ChannelLobby
lazy from .associations.guild_audit_log import GuildAuditLog
lazy from .associations.user_roles import UserRoles
lazy from .audit_log import AuditLog
lazy from .auto_reassign import AutoReAssign
lazy from .autochannel import AutoChannels
lazy from .autochannel_settings import AutoChannelSettings
lazy from .car_fuel import CarFuels
lazy from .channel import Channels
lazy from .command import Commands
lazy from .commandgroup import CommandGroups
lazy from .disabled_commands import DisabledCommands
lazy from .game import Games
lazy from .guild import Guilds
lazy from .hangman import Hangmen
lazy from .infractions import Infractions
lazy from .lobby import Lobbies
lazy from .lobbystatus import LobbyStatus
lazy from .lookingforgroup import LookingForGroup
lazy from .message import Messages
lazy from .nhiequestion import NhieQuestion
lazy from .presence import Presence
lazy from .reminder import Reminder
lazy from .result_multiplayer import ResultMassiveMultiplayer
lazy from .role import Roles
lazy from .steamsale import SteamSale
lazy from .steamuser import SteamUsers
lazy from .suggestion import Suggestions
lazy from .sync_ban import SyncBanGuild, SyncBanUser
lazy from .tournament_signup import (
    TournamentSignupConfig,
    TournamentSignupEvent,
    TournamentSignupParticipant,
)
lazy from .user import Users
lazy from .welcome import Welcome
lazy from .wyr_question import WyrQuestion


__all__ = [
    "AssociationUserCommand",
    "AssociationUserHangman",
    "AssociationUserLobby",
    "AuditLog",
    "AutoAssignRole",
    "AutoChannelSettings",
    "AutoChannels",
    "AutoReAssign",
    "CarFuels",
    "ChannelLobby",
    "ChannelTag",
    "Channels",
    "CommandGroups",
    "Commands",
    "DisabledCommands",
    "Games",
    "GuildAuditLog",
    "GuildCommands",
    "GuildRoles",
    "Guilds",
    "Hangmen",
    "Infractions",
    "Lobbies",
    "LobbyStatus",
    "LookingForGroup",
    "Messages",
    "NhieQuestion",
    "Presence",
    "Reminder",
    "ResultMassiveMultiplayer",
    "Roles",
    "SteamSale",
    "SteamUsers",
    "Suggestions",
    "SyncBanGuild",
    "SyncBanUser",
    "TournamentSignupConfig",
    "TournamentSignupEvent",
    "TournamentSignupParticipant",
    "UserRoles",
    "Users",
    "Welcome",
    "WyrQuestion",
]
