"""The database package for the Winter Dragon project."""
from __future__ import annotations

from wd_db.tables import (
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
from wd_db.tables.associations.auto_assign_role import AutoAssignRole
from wd_db.tables.associations.channel_audit import ChannelAudit
from wd_db.tables.associations.channel_lobby import ChannelLobby
from wd_db.tables.associations.channel_tags import ChannelTag
from wd_db.tables.associations.user_command import AssociationUserCommand
from wd_db.tables.associations.user_hangman import AssociationUserHangman
from wd_db.tables.associations.user_lobby import AssociationUserLobby
from wd_db.tables.audit_log import AuditLog
from wd_db.tables.auto_reassign import AutoReAssign
from wd_db.tables.autochannel import AutoChannels
from wd_db.tables.autochannel_settings import AutoChannelSettings
from wd_db.tables.car_fuel import CarFuels
from wd_db.tables.channel import Channels
from wd_db.tables.command import Commands
from wd_db.tables.commandgroup import CommandGroups
from wd_db.tables.disabled_commands import DisabledCommands
from wd_db.tables.game import Games
from wd_db.tables.incremental import Players, UserMoney
from wd_db.tables.incremental.generators import Generators
from wd_db.tables.incremental.rates import GeneratorRates
from wd_db.tables.incremental.user_generator import AssociationUserGenerator

# Matchmaking system tables
from wd_db.tables.matchmaking.game_match import GameMatch
from wd_db.tables.matchmaking.match_player import MatchPlayer
from wd_db.tables.matchmaking.match_team import MatchTeam
from wd_db.tables.matchmaking.player_game_stats import PlayerGameStats
from wd_db.tables.matchmaking.player_synergy import PlayerSynergy
from wd_db.tables.matchmaking.team_composition import TeamComposition
from wd_db.tables.matchmaking.team_composition_player import TeamCompositionPlayer
from wd_db.tables.reminder import TimedReminder
from wd_db.tables.steamsale import SteamSaleProperties
from wd_db.tables.sync_ban.sync_ban_banned_by import SyncBanBannedBy

from .constants import SessionMixin, session
from .extension.model import SQLModel


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
