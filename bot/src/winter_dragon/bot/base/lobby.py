"""Contains a class which represents a 'lobby'.

This 'lobby' will be a message and have a join and leave button
"""

import asyncio
from datetime import datetime, timedelta
from textwrap import dedent
from typing import TYPE_CHECKING, ClassVar

import discord
from discord import Interaction, User
from discord.ui import Button
from sqlmodel import select
from winter_dragon.database import Session, engine
from winter_dragon.database.tables import AssociationUserLobby as AUL  # noqa: N817
from winter_dragon.database.tables import Lobby as DbLobby


def _f() -> None:  ...
type FunctionType = type[_f]


class Lobby:
    """A class that represents a lobby in text form with buttons."""

    if TYPE_CHECKING:
        message: discord.Message
        join_button: Button
        leave_button: Button
        lobby_msg: str
        start_function: FunctionType
        start_button: Button
        timeout_timestamp: int
        view: discord.ui.View
    max_players: int = 0
    players: ClassVar[list[User]] = []


    join_button = Button(
        style=discord.ButtonStyle.green,
        custom_id=None,
        url=None,
        disabled=False,
        label="Join button",
        emoji=None,
        row=None,
    )
    leave_button = Button(
        style=discord.ButtonStyle.red,
        custom_id=None,
        url=None,
        disabled=False,
        label="Leave button",
        emoji=None,
        row=None,
    )
    start_button = Button(
        style=discord.ButtonStyle.primary,
        custom_id=None,
        url=None,
        disabled=False,
        label="Start Game",
        emoji=None,
        row=None,
    )


    def __init__(
        self,
        message: discord.Message,
        max_players: int = 0,
        start_function: FunctionType | None = None,
        timeout: int = 300,
        game: str | None = None,
    ) -> None:
        """Initialize the lobby.

        with a given message, max_players, start_function, timeout, and game type.
        """
        self.message = message
        self.start_function = start_function
        self.max_players = max_players
        self._session = Session(engine, autoflush=False)
        self.timeout_timestamp = datetime.now() + timedelta(seconds=timeout)  # noqa: DTZ005

        self._session.add(DbLobby(
            id=message.id,
            game=game,
            status="waiting",
        ))

        self.join_button.callback = self.join_callback
        self.leave_button.callback = self.leave_callback
        self.start_button.callback = self.start_callback
        self.view = discord.ui.View()
        self.view.add_item(self.start_button)
        self.view.add_item(self.join_button)
        self.view.add_item(self.leave_button)
        self.update_message()


    def __del__(self) -> None:
        """Close the session when the lobby is deleted."""
        self._session.close()


    def update_msg_text(self) -> None:
        """Update the message with total player count and display names of joined players."""
        if len(self.players) != 0:
            self.message.content = dedent(f"""Join here to start playing!
            Total: {100*self.max_players/len(self.players)}% {len(self.players)}/{self.max_players},
            Players: {','.join(player.display_name for player in self.players)}
            """)


    def update_message(self) -> None:
        """Update and edit the message. Calls `update_msg_text()`."""
        self.update_msg_text()
        loop = asyncio.get_event_loop()
        loop.create_task(self.message.edit(  # noqa: RUF006
            content=self.message.content,
            view=self.view,
        ))

    def join_callback(self, interaction: Interaction) -> None:
        """Add a user to the lobby. Then updates the message. calls `update_message()`."""
        self._session.add(AUL(
            lobby_id=self.message.id,
            user_id=interaction.user.id,
        ))
        self._session.commit()
        self.update_message()


    def leave_callback(self, interaction: Interaction) -> None:
        """Remove a user from the lobby. Then updates the message. calls `update_message()`."""
        self._session.delete(
            self._session.exec(
                select(AUL)
                .where(AUL.lobby_id == self.message, AUL.user_id == interaction.user.id),
            ).first(),
        )
        self._session.commit()
        self.update_message()


    def start_callback(self, interaction: Interaction) -> None:  # noqa: ARG002
        """Start the game. Close the session and call the start function."""
        # if coroutine run asyncio, otherwise jut run it
        # Should always have arguments ready by using partial
        self._session.close()
        self.start_function()


    def on_timeout(self, interaction: Interaction) -> None:  # noqa: ARG002
        """Remove the lobby instance on timeout."""
        del self
