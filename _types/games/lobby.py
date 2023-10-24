"""
This file contains a class which represents a 'lobby'
This 'lobby' will be a message and have a join and leave button
# TODO: expand on this
"""

import asyncio
from datetime import datetime, timedelta
from types import FunctionType
from typing import TYPE_CHECKING, Optional
from discord import Interaction, User
from discord.ui import Button

from tools.database_tables import (
    Session, engine,
    Lobby as DbLobby,
    AssociationUserLobby as AUL
)

class Lobby:
    if TYPE_CHECKING:
        message_id: int
        players: list[User]
        join_button: Button
        leave_button: Button
        lobby_msg: str
        start_function: FunctionType
        start_button: Optional[Button]
        max_players: Optional[int]
        timeout_timestamp: int


    join_button = Button(
        style=None,
        custom_id=None,
        url=None,
        disabled=None,
        label=None,
        emoji=None,
        row=None
    )
    leave_button = Button(
        style=None,
        custom_id=None,
        url=None,
        disabled=None,
        label=None,
        emoji=None,
        row=None
    )
    start_button = Button(
        style=None,
        custom_id=None,
        url=None,
        disabled=None,
        label=None,
        emoji=None,
        row=None
    )

    def __init__(
        self,
        message_id: int,
        start_function: Optional[FunctionType],
        max_players: Optional[int],
        timeout: Optional[int] = 300,
        game: Optional[str] = None
    ) -> None:
        self.message_id = message_id
        self.start_function = start_function
        self.max_players = max_players
        self._session = Session(engine)
        self.timeout_timestamp = datetime.now() + timedelta(seconds=timeout)

        self._session.add(DbLobby(
            id=message_id,
            game=game,
            status="waiting",
        ))


    def update_message(self, interaction: Interaction, reason: str):
        asyncio.run(asyncio.ensure_future(interaction.message.edit(self.lobby_msg)))


    def join_callback(self, interaction: Interaction) -> None:
        self._session.add(AUL(
            lobby_id=self.message_id,
            user_id=interaction.user.id
        ))
        self._session.commit()
        self.update_message(reason=f"player joined lobby {interaction.user.mention}")


    def leave_callback(self, interaction: Interaction) -> None:
        self._session.delete(
                self._session.query(AUL)
                .where(
                    AUL.lobby_id == self.message_id,
                    AUL.user_id == interaction.user.id
                ))
        self._session.commit()
        self.update_message(reason=f"player left lobby {interaction.user.mention}")


    def start_callback(self, interaction: Interaction) -> None:
        # if coroutine run asyncio, otherwise jut run it
        # Should always have arguments ready by using partial
        self._session.close()
        self.start_function()

    def on_timeout(self, interaction: Interaction) -> None:
        self._session.close()


    join_button.callback = join_callback
    leave_button.callback = leave_callback
    start_button.callback = start_callback
