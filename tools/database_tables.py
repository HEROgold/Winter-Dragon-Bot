import datetime
import logging
from logging.handlers import RotatingFileHandler
from typing import List, Optional, Self

import sqlalchemy
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    BigInteger,
    Text,
    Table,
    Column
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship
)

from tools.config_reader import config


logger: logging.Logger = logging.getLogger("sqlalchemy.engine")

if "config" in locals():
    logger.setLevel(config["Main"]["log_level"])
else:
    logger.setLevel("DEBUG")


handler = RotatingFileHandler(filename='sqlalchemy.log', backupCount=7, encoding="utf-8")
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
# logger.addHandler(logging.StreamHandler())


db_name = "db" # Defined in docker-compose.yml
match config["Database"]["db"]:
    case "postgres":
        username = config["Database"]["username"]
        password = config["Database"]["password"]
        logger.info(f"Connecting to postgres {db_name=}, as {username=}")
        # Add +asyncpg to postgres?
        engine: sqlalchemy.Engine = sqlalchemy.create_engine(f"postgresql://{username}:{password}@{db_name}:5432", echo=False)
    case "sqlite":
        logger.info(f"Connecting to sqlite {db_name=}")
        engine: sqlalchemy.Engine = sqlalchemy.create_engine(f"sqlite:///database/{db_name}", echo=False)
    case _:
        logger.critical("No database selected to use!")
        raise AttributeError("No database selected")


# DB reference constants
USERS_ID = "users.id"
GUILDS_ID = "guilds.id"
CHANNELS_ID = "channels.id"
MESSAGES_ID = "messages.id"
GAMES_ID = "games.id"
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


class Base(DeclarativeBase):
    "Subclass of DeclarativeBase with customizations."

    def __repr__(self) -> str:
        return str(self.__dict__)


class Guild(Base):
    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)
    channels: Mapped[List["Channel"]] = relationship(back_populates="guild")


class Channel(Base):
    __tablename__ = "channels"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)
    name: Mapped[str] = mapped_column(String(50))
    type: Mapped[str] = mapped_column(String(15), nullable=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID))
    messages: Mapped[List["Message"]] = relationship(back_populates="channel")
    guild: Mapped["Guild"] = relationship(back_populates="channels", foreign_keys=[guild_id])


    @classmethod
    def update(cls, channel: Self):
        with Session(engine) as session:
            if db_channel := session.query(Channel).where(Channel.id == channel.id).first():
                db_channel.id = channel.id
                db_channel.name = channel.name
                db_channel.type = channel.type
                db_channel.guild_id = channel.guild_id
            else:
                session.add(channel)
            session.commit()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)
    messages: Mapped[List["Message"]] = relationship(back_populates="user")
    reminders: Mapped[List["Reminder"]] = relationship(back_populates="user")
    tickets: Mapped[List["Ticket"]] = relationship(back_populates="user")

    @classmethod
    def fetch_user(cls, id: int) -> Self:
        """Find existing or create new user, and return it

        Args:
            id (int): Identifier for the user.
        """
        with Session(engine) as session:
            logger.debug(f"Looking for user {id=}")
            user = session.query(cls).where(cls.id == id).first()
            if user is None:
                logger.debug(f"Creating user {id=}")
                session.add(cls(id=id))
                session.commit()
                user = session.query(cls).where(cls.id == id).first()
            logger.debug(f"Returning user {id=}")
            return user


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)
    content: Mapped[str] = mapped_column(String(2000))
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    user: Mapped["User"] = relationship(back_populates="messages", foreign_keys=[user_id])
    channel_id: Mapped[int] = mapped_column(ForeignKey(CHANNELS_ID), nullable=True)
    channel: Mapped["Channel"] = relationship(back_populates="messages", foreign_keys=[channel_id])
    guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID), nullable=True) # actually should reference to the guild from channel.guild
    guild: Mapped["Guild"] = relationship(foreign_keys=[guild_id]) # back_populates="messages"


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    content: Mapped[str] = mapped_column(String(2000))
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    user: Mapped["User"] = relationship(back_populates="reminders", foreign_keys=[user_id])
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime)


class Welcome(Base):
    __tablename__ = "welcome"

    guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID), primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey(CHANNELS_ID))
    message: Mapped[Optional[str]] = mapped_column(String(2048))
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

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    name: Mapped[str] = mapped_column(String(15))

    @classmethod
    def fetch_game_by_name(cls, name: str = None) -> Self:
        """Find existing or create new game, and return it

        Args:
            id (int): Identifier for the game.
            name (str): Name for the game
        """
        if not name:
            raise AttributeError("Missing name.")
        with Session(engine) as session:
            logger.debug(f"Looking for game {name=}")
            game = session.query(cls).where(cls.name == name).first()
            if game is None:
                logger.debug(f"Creating game {name=}")
                session.add(cls(name=name))
                session.commit()
                game = session.query(cls).where(cls.name == name).first()
            logger.debug(f"Returning game {name=}")
            return game


class Lobby(Base):
    __tablename__ = "lobbies"

    id: Mapped[int] = mapped_column(ForeignKey(MESSAGES_ID), primary_key=True, unique=True)
    game: Mapped[str] = mapped_column(ForeignKey(GAMES_ID))
    status: Mapped[str] = mapped_column(String(10))
    # players: Mapped[List["User"]] = relationship(back_populates="lobby")


class AssociationUserLobby(Base):
    __tablename__ = "association_users_lobbies"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    lobby_id: Mapped["Lobby"] = mapped_column(ForeignKey(LOBBIES_ID))
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))


# Should work for any player count.
class ResultMassiveMultiplayer(Base):
    __tablename__ = "results_mp"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    game: Mapped["Game"] = mapped_column(ForeignKey(GAMES_ID))
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    placement: Mapped[Optional[int]] = mapped_column()


# This only works for 1v1 games.
class ResultDuels(Base):
    __tablename__ = "results_1v1"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    game: Mapped["Game"] = mapped_column(ForeignKey(GAMES_ID))
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


class Suggestion(Base):
    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    type: Mapped[str] = mapped_column(String(50))
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
    game_id: Mapped["Game"] = mapped_column(ForeignKey(GAMES_ID))


class Presence(Base):
    __tablename__ = "presence"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    status: Mapped[str] = mapped_column(String(15))
    date_time: Mapped[datetime.datetime] = mapped_column(DateTime)


    def remove_old_presences(self, member_id: int, days: int = 265) -> None:
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
                if (presence.date_time + datetime.timedelta(days=days)) >= datetime.datetime.now(datetime.timezone.utc):
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


# TODO: Change association tables to the following format:
team_users = Table("ticket_helpers", Base.metadata,
    Column("ticket_id", Integer, ForeignKey(TICKETS_ID), primary_key=True),
    Column("user_id", Integer, ForeignKey(USERS_ID), primary_key=True)
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
    user: Mapped[User] = relationship("User")
    
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(CHANNELS_ID))
    channel: Mapped["Channel"] = relationship("Channel")

    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="ticket")
    helpers: Mapped[list["User"]] = relationship("User", secondary=team_users, back_populates="tickets")

    @classmethod    
    def close(cls) -> None:
        with Session(engine) as session:
            cls.is_closed = True
            cls.closed_at = datetime.datetime.now()
            session.commit()

# # TODO: Change association tables to the following format:
# team_users = Table("team_users", Base.metadata,
#     Column("team_id", Integer, ForeignKey(TEAMS_ID), primary_key=True),
#     Column("user_id", Integer, ForeignKey(USERS_ID), primary_key=True)
# )

# team_channels = Table("team_channels", Base.metadata,
#     Column("team_id", Integer, ForeignKey(TEAMS_ID), primary_key=True),
#     Column("channel_id", Integer, ForeignKey(CHANNELS_ID), primary_key=True)
# )

# class Team(Base):
#     __tablename__ = "teams"

#     id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
#     members: Mapped[list["User"]] = relationship("User", secondary=team_users, back_populates="teams")
#     channel: Mapped[Channel] = relationship("Channel", secondary=team_channels, back_populates="team")


class Transaction(Base):
    __tablename__ = "ticket_transactions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[DateTime] = mapped_column(DateTime)
    action: Mapped[str] = mapped_column(String)
    details: Mapped[str] = mapped_column(String)
    
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickets.id"))
    ticket: Mapped[Ticket] = relationship("Ticket", back_populates="transactions")
    
    responder_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    responder: Mapped[User] = relationship("User")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)


class AutoAssignRole(Base):
    __tablename__ = "auto_assign"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    role_id: Mapped["Role"] = mapped_column(ForeignKey(ROLE_ID))
    guild_id: Mapped["Guild"] = mapped_column(ForeignKey(GUILDS_ID))


class Incremental(Base):
    __tablename__ = "incremental_data"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    balance: Mapped[int] = mapped_column(BigInteger)
    last_update: Mapped[datetime.datetime] = mapped_column(DateTime)
    generators: Mapped[List["IncrementalGen"]] = relationship(back_populates="incremental")

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
                from enums.incremental import Generators
                logger.debug(f"Creating incremental {user_id=}")
                incremental = cls(
                    user_id = user_id,
                    balance = 0,
                    last_update = datetime.datetime.now()
                )
                session.add(incremental)

                gen = Generators(0)

                session.add(IncrementalGen(
                    user_id = user_id,
                    incremental_id = incremental.id,
                    generator_id = gen.value,
                    name = gen.name,
                    price = gen.value << 2,
                    generating = gen.generation_rate
                ))
            session.commit()
            logger.debug(f"Returning incremental {user_id=}")
            return incremental


class IncrementalGen(Base):
    __tablename__ = "incremental_gens"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    incremental_id: Mapped[int] = mapped_column(ForeignKey(INCREMENTAL_ID))
    incremental: Mapped["Incremental"] = relationship(back_populates="generators", foreign_keys=[incremental_id])
    generator_id: Mapped[int] = mapped_column(Integer)
    name : Mapped[str] = mapped_column(String(15))
    price : Mapped[str] = mapped_column(Integer)
    generating : Mapped[float] = mapped_column(Float)


class Command(Base):
    __tablename__ = "commands"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(15))
    call_count: Mapped[int] = mapped_column(Integer, default=0)
    parent_id = mapped_column(ForeignKey(COMMAND_GROUPS_ID), nullable=True)
    parent: Mapped["CommandGroup"] = relationship(back_populates="commands", foreign_keys=[parent_id])


class CommandGroup(Base):
    __tablename__ = "command_groups"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(15))
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


class GuildCommands(Base):
    __tablename__ = "guild_commands"

    guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID), primary_key=True)
    command_id: Mapped[int] = mapped_column(ForeignKey(COMMANDS_ID))
    # group_id: Mapped[int] = mapped_column(ForeignKey(COMMAND_GROUPS_ID))
    # commands: Mapped[list["Command", "CommandGroup"]] = relationship(foreign_keys=[command_id, group_id])


all_tables = Base.__subclasses__()

try:
    with Session(engine) as session:
        for i in all_tables:
            logger.debug(f"Checking for existing database table: {i}")
            session.query(i).first()
except Exception as e:
    logger.exception(f"Error getting all tables: {e}")
    """Should only run max once per startup, creating missing tables"""
    Base().metadata.create_all(engine)

# Test using Hypothesis
# https://youtu.be/dsBitCcWWf4

# TODO: Use more joins etc.