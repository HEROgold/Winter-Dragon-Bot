import datetime
import logging
from logging.handlers import RotatingFileHandler
from typing import List, Optional, Self

import sqlalchemy
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, BigInteger
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship
)

try:
    import config
except ModuleNotFoundError:
    pass


logger: logging.Logger = logging.getLogger("sqlalchemy.engine")
if "config" in locals():
    logger.setLevel(config.Main.LOG_LEVEL)
else:
    logger.setLevel("DEBUG")


# handler = logging.FileHandler(filename='sqlalchemy.log', encoding='utf-8', mode='w')
handler = RotatingFileHandler(filename='sqlalchemy.log', backupCount=7, encoding="utf-8")
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
# logger.addHandler(logging.StreamHandler())


db_name = "db" # Defined in docker-compose.yml
match config.Database.db:
    case "postgres":
        username = config.Database.username
        password = config.Database.password
        logger.info(f"Connecting to postgres {db_name=}, as {username=}")
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
    type: Mapped[str] = mapped_column(String(15))
    guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID)) # , unique=True, nullable=False
    guild: Mapped["Guild"] = relationship(back_populates="channels", foreign_keys=[guild_id])
    messages: Mapped[List["Message"]] = relationship(back_populates="channel")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, unique=True)
    messages: Mapped[List["Message"]] = relationship(back_populates="user")
    reminders: Mapped[List["Reminder"]] = relationship(back_populates="user")

    @staticmethod
    def fetch_user(id: int) -> Self:
        """Find existing or create new user, and return it

        Args:
            id (int): Identifier for the user.
        """
        with Session(engine) as session:
            logger.debug(f"Looking for user {id=}")
            user = session.query(User).where(User.id == id).first()
            if user is None:
                logger.debug(f"Creating user {id=}")
                session.add(User(id=id))
                session.commit()
                user = session.query(User).where(User.id == id).first()
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
    user_id: Mapped["User"] = mapped_column(ForeignKey(USERS_ID))


# Should work for any player count.
class ResultMassiveMultiplayer(Base):
    __tablename__ = "results_mp"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    game: Mapped["Game"] = mapped_column(ForeignKey(GAMES_ID))
    user_id: Mapped["User"] = mapped_column(ForeignKey(USERS_ID))
    placement: Mapped[Optional[int]] = mapped_column()


# This only works for 1v1 games.
class ResultDuels(Base):
    __tablename__ = "results_1v1"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    game: Mapped[str] = mapped_column(ForeignKey(GAMES_ID))
    player_1: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    player_2: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    winner: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID))
    loser: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID))


class Steam(Base):
    __tablename__ = "steam"

    # id: Mapped[int] = mapped_column( unique=True)
    id: Mapped["User"] = mapped_column(ForeignKey(USERS_ID), primary_key=True, unique=True)


class Suggestion(Base):
    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    type: Mapped[str] = mapped_column(String(50))
    is_verified: Mapped[bool] = mapped_column(Boolean)
    content: Mapped[str] = mapped_column(String(2048))


# TODO: look at lobby database, create association table to map votes to users and polls.
# TODO: restructure
class Poll(Base):
    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey(CHANNELS_ID))
    message_id: Mapped[int] = mapped_column(ForeignKey(MESSAGES_ID))
    # guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID))
    content: Mapped[str] = mapped_column(String(2048))
    end_date: Mapped[datetime.datetime] = mapped_column(DateTime)
    votes: Mapped[list[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    values: Mapped[list[int]] = mapped_column(Integer, nullable=True)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    # members: Mapped[list["User"]] = mapped_column(ForeignKey(USERS_ID))


class AssociationUserTeam(Base):
    __tablename__ = "association_users_teams"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    team_id: Mapped["Lobby"] = mapped_column(ForeignKey(TEAMS_ID))
    user_id: Mapped["User"] = mapped_column(ForeignKey(USERS_ID))
    voted: Mapped[bool] = mapped_column(Boolean)


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
    user_id: Mapped["User"] = mapped_column(ForeignKey(USERS_ID))
    score: Mapped[int] = mapped_column(Integer, default=0)


class LookingForGroup(Base):
    __tablename__ = "looking_for_groups"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    user_id: Mapped["User"] = mapped_column(ForeignKey(USERS_ID))
    game_id: Mapped["Game"] = mapped_column(ForeignKey(GAMES_ID))


class Presence(Base):
    __tablename__ = "presence"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    user_id: Mapped["User"] = mapped_column(ForeignKey(USERS_ID))
    status: Mapped[str] = mapped_column(String(15))
    date_time: Mapped[datetime.datetime] = mapped_column(DateTime)


all_tables = Base.__subclasses__()

try:
    with Session(engine) as session:
        for i in all_tables:
            logger.debug(f"Checking for existing database table: {i}")
            session.query(i).all()
except Exception as e:
    logger.exception(f"Error getting all tables: {e}")
    """Should only run max once per startup, creating missing tables"""
    Base().metadata.create_all(engine)
