from .associations import (
    AssociationUserCommand,
    AssociationUserHangman,
    AssociationUserLobby,
    GuildCommands,
    GuildRoles,
)
from .auditlog import AuditLog
from .autoassignrole import AutoAssignRole
from .autochannel import AutoChannel
from .autochannelsettings import AutoChannelSettings
from .autoreassign import AutoReAssign
from .car_fuel import CarFuel
from .channel import Channel
from .command import Command
from .commandgroup import CommandGroup
from .disabledcommands import DisabledCommands
from .game import Game
from .guild import Guild
from .hangman import Hangman
from .infractions import Infractions
from .lobby import Lobby
from .lobbystatus import LobbyStatus
from .lookingforgroup import LookingForGroup
from .message import Message
from .nhiequestion import NhieQuestion
from .presence import Presence
from .reminder import Reminder
from .resultduels import ResultDuels
from .resultmassivemultiplayer import ResultMassiveMultiplayer
from .role import Role
from .steamsale import SteamSale
from .steamuser import SteamUser
from .suggestion import Suggestion
from .syncban import SyncBan
from .syncbanguild import SyncBanGuild
from .user import User
from .userroles import UserRoles
from .welcome import Welcome
from .wyrquestion import WyrQuestion


__all__ = [
    "AssociationUserCommand",
    "AssociationUserHangman",
    "AssociationUserLobby",
    "AutoReAssign",
    "CarFuel",
    "GuildCommands",
    "GuildRoles",
    "AuditLog",
    "AutoAssignRole",
    "AutoChannel",
    "AutoChannelSettings",
    "Channel",
    "Command",
    "CommandGroup",
    "DisabledCommands",
    "Game",
    "Guild",
    "Hangman",
    "Infractions",
    "Lobby",
    "LobbyStatus",
    "LookingForGroup",
    "Message",
    "NhieQuestion",
    "Presence",
    "Reminder",
    "ResultDuels",
    "ResultMassiveMultiplayer",
    "Role",
    "SteamSale",
    "SteamUser",
    "Suggestion",
    "SyncBan",
    "SyncBanGuild",
    "User",
    "UserRoles",
    "Welcome",
    "WyrQuestion",
]


# TODO @HEROgold: Test using Hypothesis
# https://youtu.be/dsBitCcWWf4
