"""Contains a class which represents a 'lobby'.

This 'lobby' will be a message and have a join and leave button
"""

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
from textwrap import dedent

import discord
from discord import Interaction, User
from discord.ui import Button, View
from sqlmodel import select
from winter_dragon.database.constants import SessionMixin
from winter_dragon.database.tables import AssociationUserLobby as AUL  # noqa: N817
from winter_dragon.database.tables import Lobbies as DbLobby
from winter_dragon.database.tables.game import Games
from winter_dragon.database.tables.lobbystatus import LobbyStatus


class Lobby(View, SessionMixin):
    """A class that represents a lobby in text form with buttons."""

    join_button = Button["Lobby"](
        style=discord.ButtonStyle.green,
        custom_id=None,
        url=None,
        disabled=False,
        label="Join button",
        emoji=None,
        row=None,
    )
    leave_button = Button["Lobby"](
        style=discord.ButtonStyle.red,
        custom_id=None,
        url=None,
        disabled=False,
        label="Leave button",
        emoji=None,
        row=None,
    )
    start_button = Button["Lobby"](
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
        start_function: Callable[...],
        game: Games,
        max_players: int = 0,
        timeout: int = 300,
    ) -> None:
        """Initialize the lobby.

        with a given message, max_players, start_function, timeout, and game type.
        """
        game = self.validate_game(game)
        super().__init__(timeout=timeout)
        self.message = message
        self.start_function = start_function
        self.max_players = max_players
        self.timeout_timestamp = datetime.now() + timedelta(seconds=timeout)  # noqa: DTZ005
        self.players: list[User] = []

        self.session.add(DbLobby(
            id=message.id,
            game_id=game.id or 0,
            status=LobbyStatus.CREATED,
        ))

        self.join_button.callback = self.join_callback
        self.leave_button.callback = self.leave_callback
        self.start_button.callback = self.start_callback
        self.add_item(self.start_button)
        self.add_item(self.join_button)
        self.add_item(self.leave_button)
        self.update_message()

    def validate_game(self, game: Games) -> Games:
        """Validate that the game exists in the database."""
        if game.id is None:
            game = Games.fetch_game_by_name(game.name)
            if game is None:
                msg = "Game must be in the database before creating a lobby."
                raise ValueError(msg)
        return game


    def __del__(self) -> None:
        """Close the session when the lobby is deleted."""
        self.session.close()


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
            view=self,
        ))

    async def join_callback(self, interaction: Interaction) -> None:
        """Add a user to the lobby. Then updates the message. calls `update_message()`."""
        self.session.add(AUL(
            lobby_id=self.message.id,
            user_id=interaction.user.id,
        ))
        self.session.commit()
        self.update_message()


    async def leave_callback(self, interaction: Interaction) -> None:
        """Remove a user from the lobby. Then updates the message. calls `update_message()`."""
        self.session.delete(
            self.session.exec(
                select(AUL)
                .where(AUL.lobby_id == self.message, AUL.user_id == interaction.user.id),
            ).first(),
        )
        self.session.commit()
        self.update_message()


    async def start_callback(self, interaction: Interaction) -> None:  # noqa: ARG002
        """Start the game. Close the session and call the start function."""
        # if coroutine run asyncio, otherwise just run it
        # Should always have arguments ready by using partial
        self.session.close()
        self.start_function()


    async def on_timeout(self) -> None:
        """Remove the lobby instance on timeout."""
        del self
