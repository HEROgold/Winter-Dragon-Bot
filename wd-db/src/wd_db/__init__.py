"""The database package for the Winter Dragon project."""
from __future__ import annotations

lazy from wd_db.tables import (
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
lazy from wd_db.tables.associations.auto_assign_role import AutoAssignRole
lazy from wd_db.tables.associations.channel_audit import ChannelAudit
lazy from wd_db.tables.associations.channel_lobby import ChannelLobby
lazy from wd_db.tables.associations.channel_tags import ChannelTag
lazy from wd_db.tables.associations.user_command import AssociationUserCommand
lazy from wd_db.tables.associations.user_hangman import AssociationUserHangman
lazy from wd_db.tables.associations.user_lobby import AssociationUserLobby
lazy from wd_db.tables.audit_log import AuditLog
lazy from wd_db.tables.auto_reassign import AutoReAssign
lazy from wd_db.tables.autochannel import AutoChannels
lazy from wd_db.tables.autochannel_settings import AutoChannelSettings
lazy from wd_db.tables.car_fuel import CarFuels
lazy from wd_db.tables.channel import Channels
lazy from wd_db.tables.command import Commands
lazy from wd_db.tables.commandgroup import CommandGroups
lazy from wd_db.tables.disabled_commands import DisabledCommands
lazy from wd_db.tables.game import Games
lazy from wd_db.tables.incremental import Players, UserMoney
lazy from wd_db.tables.incremental.generators import Generators
lazy from wd_db.tables.incremental.rates import GeneratorRates
lazy from wd_db.tables.incremental.user_generator import AssociationUserGenerator

# Matchmaking system tables
lazy from wd_db.tables.matchmaking.game_match import GameMatch
lazy from wd_db.tables.matchmaking.match_player import MatchPlayer
lazy from wd_db.tables.matchmaking.match_team import MatchTeam
lazy from wd_db.tables.matchmaking.player_game_stats import PlayerGameStats
lazy from wd_db.tables.matchmaking.player_synergy import PlayerSynergy
lazy from wd_db.tables.matchmaking.team_composition import TeamComposition
lazy from wd_db.tables.matchmaking.team_composition_player import TeamCompositionPlayer
lazy from wd_db.tables.reminder import TimedReminder
lazy from wd_db.tables.steamsale import SteamSaleProperties
lazy from wd_db.tables.sync_ban.sync_ban_banned_by import SyncBanBannedBy

lazy from .constants import SessionMixin, session
lazy from .extension.model import SQLModel


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
    "GameMatch",
    "Games",
    "GeneratorRates",
    "Generators",
    "GuildAuditLog",
    "GuildCommands",
    "GuildRoles",
    "Guilds",
    "Hangmen",
    "Lobbies",
    "LookingForGroup",
    "MatchPlayer",
    "MatchTeam",
    "Messages",
    "NhieQuestion",
    "PlayerGameStats",
    "PlayerSynergy",
    "Players",
    "Presence",
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
    "TeamComposition",
    "TeamCompositionPlayer",
    "TimedReminder",
    "UserMoney",
    "UserRoles",
    "Users",
    "WyrQuestion",
    "session",
]
