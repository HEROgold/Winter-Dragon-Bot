import datetime
from pathlib import Path
from typing import Optional, Self

from discord import AuditLogAction, AuditLogActionCategory, AuditLogEntry
from flask_login import UserMixin
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
)

from _types.enums import ChannelTypes as EChannelTypes
from _types.enums import Generators
from tools.main_log import sql_logger as logger


engine = create_engine("sqlite:///database/db.sqlite", echo=False)

# DB string refs
CASCADE = "CASCADE"

# DB reference constants
USERS_ID = "users.id"
GUILDS_ID = "guilds.id"
CHANNELS_ID = "channels.id"
MESSAGES_ID = "messages.id"
GAMES_NAME = "games.name"
LOBBIES_ID = "lobbies.id"
TEAMS_ID = "teams.id"
HANGMAN_ID = "hangman.id"
ROLE_ID = "roles.id"
INCREMENTAL_ID = "incremental_data.id"
AUTOCHANNEL_ID = "autochannels.id"
POLLS_ID = "polls.id"
TICKETS_ID = "tickets.id"
COMMANDS_ID = "commands.id"
COMMAND_GROUPS_ID = "command_groups.id"
ROLES_ID = "roles.id"
LOBBY_STATUS = "lobby_status.status"
CHANNEL_TYPES = "channel_types.type"
SUGGESTIONS_TYPES = "suggestions_types.type"


class Base(DeclarativeBase):
    "Subclass of DeclarativeBase with customizations."

    def __repr__(self) -> str:
        return str(self.__dict__)


class Guild(Base):
    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)
    channels: Mapped[list["Channel"]] = relationship(back_populates="guild")


class ChannelTypes(Base):
    __tablename__ = "channel_types"

    type: Mapped[str] = mapped_column(Enum(EChannelTypes), primary_key=True)


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)
    name: Mapped[str] = mapped_column(String(50))
    type: Mapped[str] = mapped_column(ForeignKey(CHANNEL_TYPES), nullable=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID))

    messages: Mapped[list["Message"]] = relationship(back_populates="channel")
    guild: Mapped["Guild"] = relationship(back_populates="channels", foreign_keys=[guild_id])


    @classmethod
    def update(cls, channel: Self) -> None:
        # TODO: Update whenever the bot hears a discord channel update event > on_channel_update listener
        with Session(engine) as session:
            if db_channel := session.query(Channel).where(Channel.id == channel.id).first():
                db_channel.id = channel.id
                db_channel.name = channel.name
                db_channel.type = channel.type
                db_channel.guild_id = channel.guild_id
            else:
                session.add(channel)
            session.commit()


class User(Base, UserMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)

    messages: Mapped[list["Message"]] = relationship(back_populates="user")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="user")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="user")

    @classmethod
    def fetch_user(cls, id: int) -> Self:
        """Find existing or create new user, and return it

        Args:
            id (int): Identifier for the user.
        """
        with Session(engine) as session:
            logger.debug(f"Looking for user {id=}")

            if user := session.query(cls).where(cls.id == id).first():
                logger.debug(f"Returning user {id=}")
                return user

            logger.debug(f"Creating user {id=}")
            session.add(cls(id=id))
            session.commit()
            return session.query(cls).where(cls.id == id).first() # type: ignore


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)
    content: Mapped[str] = mapped_column(String(2000))
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    channel_id: Mapped[int] = mapped_column(ForeignKey(CHANNELS_ID), nullable=True)

    user: Mapped["User"] = relationship(back_populates="messages", foreign_keys=[user_id])
    channel: Mapped["Channel"] = relationship(back_populates="messages", foreign_keys=[channel_id])


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    content: Mapped[str] = mapped_column(String(2000))
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="reminders", foreign_keys=[user_id])


class Welcome(Base):
    __tablename__ = "welcome"

    guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID), primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey(CHANNELS_ID))
    message: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean)


class NhieQuestion(Base):
    __tablename__ = "nhie_questions"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    value: Mapped[str] = mapped_column(String())


class WyrQuestion(Base):
    __tablename__ = "wyr_questions"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    value: Mapped[str] = mapped_column(String())


class Game(Base):
    __tablename__ = "games"

    name: Mapped[str] = mapped_column(String(15), primary_key=True, unique=True)

    @classmethod
    def fetch_game_by_name(cls, name: str) -> Self:
        """Find existing or create new game, and return it

        Args:
            name (str): Name for the game
        """
        with Session(engine) as session:
            logger.debug(f"Looking for game {name=}")
            if game := session.query(cls).where(cls.name == name).first():
                logger.debug(f"Returning game {name=}")
                return game

            logger.debug(f"Creating game {name=}")
            session.add(cls(name=name))
            session.commit()
            return session.query(cls).where(cls.name == name).first() # type: ignore


class LobbyStatus(Base):
    __tablename__ = "lobby_status"

    status: Mapped[str] = mapped_column(String(10), primary_key=True)

    @classmethod
    def create_default_values(cls) -> None:
        with Session(engine) as session:
            for status in [
                "waiting",
                "running",
            ]:
                if session.query(cls.status).where(cls.status == status).first():
                    continue
                session.add(cls(
                    status=status,
                ))
            session.commit()


class Lobby(Base):
    __tablename__ = "lobbies"

    id: Mapped[int] = mapped_column(ForeignKey(MESSAGES_ID, ondelete=CASCADE), primary_key=True, unique=True)
    game: Mapped[str] = mapped_column(ForeignKey(GAMES_NAME))
    status: Mapped[str] = mapped_column(ForeignKey(LOBBY_STATUS))


class AssociationUserLobby(Base):
    __tablename__ = "association_users_lobbies"

    lobby_id: Mapped["Lobby"] = mapped_column(ForeignKey(LOBBIES_ID, ondelete=CASCADE), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), primary_key=True)


# Should work for any player count.
class ResultMassiveMultiplayer(Base):
    __tablename__ = "results_mp"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    game: Mapped["Game"] = mapped_column(ForeignKey(GAMES_NAME))
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    placement: Mapped[Optional[int]] = mapped_column(nullable=True)


# This only works for 1v1 games.
class ResultDuels(Base):
    __tablename__ = "results_1v1"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    game: Mapped["Game"] = mapped_column(ForeignKey(GAMES_NAME))
    player_1: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    player_2: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    winner: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID))
    loser: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID))


class SteamUser(Base):
    __tablename__ = "steam_users"

    id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), primary_key=True, unique=True)


class SteamSale(Base):
    __tablename__ = "steam_sales"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    title: Mapped[str] = mapped_column(String(50))
    url: Mapped[str] = mapped_column(String(200))
    sale_percent: Mapped[int] = mapped_column(Integer)
    final_price: Mapped[int] = mapped_column(Float) # (5, True, 2)
    is_dlc: Mapped[bool] = mapped_column(Boolean)
    is_bundle: Mapped[bool] = mapped_column(Boolean)
    update_datetime: Mapped[datetime.datetime] = mapped_column(DateTime)


class SuggestionTypes(Base):
    __tablename__ = "suggestions_types"

    type: Mapped[str] = mapped_column(String(50), primary_key=True)

class Suggestion(Base):
    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    type: Mapped[str] = mapped_column(ForeignKey(SUGGESTIONS_TYPES))
    is_verified: Mapped[bool] = mapped_column(Boolean)
    content: Mapped[str] = mapped_column(String(2048))


class Poll(Base):
    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey(CHANNELS_ID))
    message_id: Mapped[int] = mapped_column(ForeignKey(MESSAGES_ID))
    content: Mapped[str] = mapped_column(Text)
    end_date: Mapped[datetime.datetime] = mapped_column(DateTime)


class AssociationUserPoll(Base):
    __tablename__ = "association_users_polls"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey(POLLS_ID))
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    voted_value: Mapped[int] = mapped_column(Integer)


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    process_id: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(15))
    run_path: Mapped[str] = mapped_column(String(255))


class Hangman(Base):
    __tablename__ = "hangman"

    id: Mapped[int] = mapped_column(ForeignKey(MESSAGES_ID), primary_key=True, unique=True)
    word: Mapped[str] = mapped_column(String(24))
    letters: Mapped[str] = mapped_column(String(24), nullable=True)


class AssociationUserHangman(Base):
    __tablename__ = "association_users_hangman"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    hangman_id: Mapped["Hangman"] = mapped_column(ForeignKey(HANGMAN_ID))
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    score: Mapped[int] = mapped_column(Integer, default=0)


class LookingForGroup(Base):
    __tablename__ = "looking_for_groups"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    game_id: Mapped["Game"] = mapped_column(ForeignKey(GAMES_NAME))


class Presence(Base):
    __tablename__ = "presence"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    status: Mapped[str] = mapped_column(String(15))
    date_time: Mapped[datetime.datetime] = mapped_column(DateTime)


    @staticmethod
    def remove_old_presences(member_id: int, days: int = 265) -> None:
        """
        Removes old presences present in the database, if they are older then a year

        Parameters
        -----------
        :param:`member`: :class:`int`
            The Member_id to clean

        :param:`days`: :class:`int`
            The amount of days ago to remove, defaults to (256)
        """
        with Session(engine) as session:
            db_presences = session.query(Presence).where(Presence.user_id == member_id).all()
            for presence in db_presences:
                if (presence.date_time + datetime.timedelta(days=days)) >= datetime.datetime.now():
                    session.delete(presence)
            session.commit()


class AutoChannel(Base):
    __tablename__ = "autochannels"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=False)
    channel_id: Mapped[int] = mapped_column(ForeignKey(CHANNELS_ID))


class AutoChannelSettings(Base):
    __tablename__ = "autochannel_settings"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=False)
    channel_name: Mapped[str] = mapped_column(Text)
    channel_limit: Mapped[int] = mapped_column(Integer)


ticket_helpers = Table("ticket_helpers", Base.metadata,
    Column("ticket_id", Integer, ForeignKey(TICKETS_ID), primary_key=True),
    Column("user_id", Integer, ForeignKey(USERS_ID), primary_key=True),
)

class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)

    opened_at: Mapped[DateTime] = mapped_column(DateTime)
    closed_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    is_closed: Mapped[bool] = mapped_column(Boolean)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(USERS_ID))
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(CHANNELS_ID))

    user: Mapped[User] = relationship("User")
    channel: Mapped["Channel"] = relationship("Channel")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="ticket")
    helpers: Mapped[list["User"]] = relationship(back_populates="tickets", secondary=ticket_helpers)

    @classmethod
    def close(cls) -> None:
        with Session(engine) as session:
            cls.is_closed = True
            cls.closed_at = datetime.datetime.now()
            session.commit()


class Transaction(Base):
    __tablename__ = "ticket_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[DateTime] = mapped_column(DateTime)
    action: Mapped[str] = mapped_column(String)
    details: Mapped[str] = mapped_column(String)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickets.id"))
    responder_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))

    ticket: Mapped["Ticket"] = relationship(back_populates="transactions")
    responder: Mapped["User"] = relationship()


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    name: Mapped[str] = mapped_column(String)

class UserRoles(Base):
    __tablename__ = "user_roles"

    role_id: Mapped["Role"] = mapped_column(ForeignKey(ROLES_ID), primary_key=True)
    guild_id: Mapped["Guild"] = mapped_column(ForeignKey(GUILDS_ID), primary_key=True)
    user_id: Mapped["User"] = mapped_column(ForeignKey(USERS_ID), primary_key=True)

class AutoAssignRole(Base):
    __tablename__ = "auto_assign"

    role_id: Mapped["Role"] = mapped_column(ForeignKey(ROLE_ID), primary_key=True)
    guild_id: Mapped["Guild"] = mapped_column(ForeignKey(GUILDS_ID), primary_key=True)


class Incremental(Base):
    __tablename__ = "incremental_data"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    balance: Mapped[int] = mapped_column(BigInteger)
    last_update: Mapped[datetime.datetime] = mapped_column(DateTime)

    generators: Mapped[list["IncrementalGen"]] = relationship(back_populates="incremental")

    @classmethod
    def fetch_user(cls, user_id: int) -> Self:
        """Find existing or create new incremental, and return it

        Args:
            user_id (int): Identifier for the incremental.
        """
        with Session(engine) as session:
            logger.debug(f"Looking for incremental {user_id=}")
            incremental = session.query(cls).where(cls.user_id == user_id).first()
            if incremental is None:
                logger.debug(f"Creating incremental {user_id=}")
                incremental = cls(
                    user_id = user_id,
                    balance = 0,
                    last_update = datetime.datetime.now(),
                )
                session.add(incremental)

                gen = Generators(0)

                session.add(IncrementalGen(
                    user_id = user_id,
                    incremental_id = incremental.id,
                    generator_id = gen.value,
                    name = gen.name,
                    price = gen.value << 2,
                    generating = gen.generation_rate,
                ))
            session.commit()
            logger.debug(f"Returning incremental {user_id=}")
            return incremental


class IncrementalGen(Base):
    __tablename__ = "incremental_gens"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    incremental_id: Mapped[int] = mapped_column(ForeignKey(INCREMENTAL_ID))
    generator_id: Mapped[int] = mapped_column(Integer)
    name : Mapped[str] = mapped_column(String(15))
    price : Mapped[str] = mapped_column(Integer)
    generating : Mapped[float] = mapped_column(Float)

    incremental: Mapped["Incremental"] = relationship(back_populates="generators", foreign_keys=[incremental_id])


class Command(Base):
    __tablename__ = "commands"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    qual_name: Mapped[str] = mapped_column(String(30))
    call_count: Mapped[int] = mapped_column(Integer, default=0)
    parent_id: Mapped[int] = mapped_column(ForeignKey(COMMAND_GROUPS_ID), nullable=True)

    parent: Mapped["CommandGroup"] = relationship(back_populates="commands", foreign_keys=[parent_id])


class CommandGroup(Base):
    __tablename__ = "command_groups"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30))

    commands: Mapped[list["Command"]] = relationship(back_populates="parent")


class AssociationUserCommand(Base):
    __tablename__ = "association_user_command"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    command_id: Mapped[int] = mapped_column(ForeignKey(COMMANDS_ID))

    @classmethod
    def cleanup(cls) -> None:
        """
        cleanup this database to keep track of (at most)
        1k commands for each user
        TODO: test
        """
        track_amount = 1000
        with Session(engine) as session:
            data = session.query(cls).all()
            seen_users = []
            for row in data:
                seen_users.append(row.user_id)
                if seen_users.count(row.user_id) >= track_amount:
                    # get first findable row, then delete it
                    session.delete(session.query(cls).where(cls.user_id == row.user_id).first())
                    seen_users.remove(row.user_id)
            session.commit()


class SyncBan(Base):
    __tablename__ = "synced_bans"

    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), primary_key=True)


class SyncBanGuild(Base):
    __tablename__ = "sync_ban_guilds"

    guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID), primary_key=True)


class DisabledCommands(Base):
    __tablename__ = "disabled_commands"

    command_id: Mapped[int] = mapped_column(ForeignKey(COMMANDS_ID), primary_key=True)
    _user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    _channel_id: Mapped[int] = mapped_column(ForeignKey(CHANNELS_ID), nullable=True)
    _guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID), nullable=True)

    def __init__(self, **kw: int) -> None:
        # TODO: needs testing
        id_limit = 2
        if len(kw) > id_limit:
            msg = f"Only 2 arguments expected, got {len(kw)}!"
            raise ValueError(msg)
        super().__init__(**kw)

    @property
    def target_id(self) -> int:
        return self._user_id or self._channel_id or self._guild_id

class GuildCommands(Base):
    __tablename__ = "guild_commands"

    guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID), primary_key=True)
    command_id: Mapped[int] = mapped_column(ForeignKey(COMMANDS_ID))
    # group_id: Mapped[int] = mapped_column(ForeignKey(COMMAND_GROUPS_ID))
    # commands: Mapped[list["Command", "CommandGroup"]] = relationship(foreign_keys=[command_id, group_id])


class GuildRoles(Base):
    __tablename__ = "guild_roles"

    guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey(ROLES_ID), primary_key=True)


class Infractions(Base):
    __tablename__ = "infractions"

    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), primary_key=True)
    infraction_count: Mapped[int] = mapped_column(Integer, default=0)

    @classmethod
    def add_infraction_count(cls, user_id: int, amount: int) -> None:
        """Add an infraction to a user, if it isn't in this table add it"""
        with Session(engine) as session:
            infraction = session.query(cls).where(cls.user_id == user_id).first()

            if infraction is None:
                infraction = cls(user_id=user_id, infraction_count=0)
                session.add(infraction)

            infraction.infraction_count += amount
            session.commit()


    @classmethod
    def fetch_user(cls, id: int) -> Self:
        """Find existing or create new user, and return it

        Args:
            id (int): Identifier for the user.
        """
        with Session(engine) as session:
            logger.debug(f"Looking for user {id=}")

            if user := session.query(cls).where(cls.id == id).first():
                logger.debug(f"Returning user {id=}")
                return user

            logger.debug(f"Creating user {id=}")
            session.add(cls(id=id))
            session.commit()
            return session.query(cls).where(cls.id == id).first() # type: ignore

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, unique=True, autoincrement=True)
    action: Mapped[AuditLogAction] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)
    target_id: Mapped[int] = mapped_column(Integer, nullable=True)
    category: Mapped[AuditLogActionCategory] = mapped_column(Integer, nullable=True)
    # # changes: Mapped[AuditLogChanges] = mapped_column(, nullable=True)
    # before: Mapped[AuditLogDiff] = mapped_column(String, nullable=True)
    # after: Mapped[AuditLogDiff] = mapped_column(String, nullable=True)

    @classmethod
    def from_audit_log(cls, entry: AuditLogEntry) -> Self:
        with Session(engine) as session:
            audit = cls(
                id = entry.id,
                action = entry.action,
                reason = entry.reason,
                created_at = entry.created_at,
                target = entry.target,
                category = entry.category,
                # changes = entry.changes,
                # before = entry.before,
                # after = entry.after,
            )
            session.add(audit)
            session.commit()
        return audit


all_tables = Base.__subclasses__()

try:
    with Session(engine) as session:
        for i in all_tables:
            logger.debug(f"Checking for existing database table: {i}")
            session.query(i).first()
except Exception:
    logger.exception("Error getting all tables")
    """Should only run max once per startup, creating missing tables"""
    Base().metadata.create_all(engine)
    LobbyStatus.create_default_values()

# Test using Hypothesis
# https://youtu.be/dsBitCcWWf4

# TODO: Use knowledge from databases lessons for update this file
