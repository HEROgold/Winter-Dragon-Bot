from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database.tables import CASCADE, Base, session
from database.tables.definitions import COMMANDS_ID, GUILDS_ID, HANGMEN_ID, LOBBIES_ID, POLLS_ID, ROLES_ID, USERS_ID


if TYPE_CHECKING:
    from database.tables.games import Hangman, Lobby
else:
    Hangman = "hangmen"
    Lobby = "lobbies"


class AssociationUserHangman(Base):
    __tablename__ = "association_users_hangman"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    hangman_id: Mapped["Hangman"] = mapped_column(ForeignKey(HANGMEN_ID))
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    score: Mapped[int] = mapped_column(Integer, default=0)


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
        with session:
            data = session.query(cls).all()
            seen_users = []
            for row in data:
                seen_users.append(row.user_id)
                if seen_users.count(row.user_id) >= track_amount:
                    # get first findable row, then delete it
                    session.delete(session.query(cls).where(cls.user_id == row.user_id).first())
                    seen_users.remove(row.user_id)
            session.commit()


class GuildCommands(Base):
    __tablename__ = "guild_commands"

    guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID), primary_key=True)
    command_id: Mapped[int] = mapped_column(ForeignKey(COMMANDS_ID))


class GuildRoles(Base):
    __tablename__ = "guild_roles"

    guild_id: Mapped[int] = mapped_column(ForeignKey(GUILDS_ID), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey(ROLES_ID), primary_key=True)


class AssociationUserPoll(Base):
    __tablename__ = "association_users_polls"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, autoincrement=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey(POLLS_ID))
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID))
    voted_value: Mapped[int] = mapped_column(Integer)


class AssociationUserLobby(Base):
    __tablename__ = "association_users_lobbies"

    lobby_id: Mapped["Lobby"] = mapped_column(ForeignKey(LOBBIES_ID, ondelete=CASCADE), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), primary_key=True)
