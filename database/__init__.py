from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .constants import DATABASE_URL
from .tables import (
    AssociationUserCommand,
    AssociationUserHangman,
    AssociationUserLobby,
    AuditLog,
    AutoAssignRole,
    AutoChannel,
    AutoChannelSettings,
    AutoReAssign,
    CarFuel,
    Channel,
    Command,
    CommandGroup,
    DisabledCommands,
    Game,
    Guild,
    GuildCommands,
    GuildRoles,
    Hangman,
    Infractions,
    Lobby,
    LobbyStatus,
    LookingForGroup,
    Message,
    NhieQuestion,
    Presence,
    Reminder,
    ResultDuels,
    ResultMassiveMultiplayer,
    Role,
    SteamSale,
    SteamUser,
    Suggestion,
    SyncBan,
    SyncBanGuild,
    User,
    UserRoles,
    Welcome,
    WyrQuestion,
)
from .tables.base import Base


engine = create_engine(DATABASE_URL, echo=False)


Base().metadata.create_all(engine)
session = Session(engine)


__all__ = [
    "AssociationUserCommand",
    "AssociationUserHangman",
    "AssociationUserLobby",
    "AuditLog",
    "AutoAssignRole",
    "AutoChannel",
    "AutoChannelSettings",
    "AutoReAssign",
    "CarFuel",
    "Channel",
    "Command",
    "CommandGroup",
    "DisabledCommands",
    "Game",
    "Guild",
    "GuildCommands",
    "GuildRoles",
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
