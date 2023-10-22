"""
This file contains a class which represents a 'lobby'
This 'lobby' will be a message and have a join and leave button
# TODO: expand on this
"""

import asyncio
from types import FunctionType
from typing import TYPE_CHECKING, Optional
from discord import Interaction, User
from discord.ui import Button


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


    def update_message(self, interaction: Interaction):
        asyncio.run(asyncio.ensure_future(interaction.message.edit(self.lobby_msg)))


    def join_callback(self, interaction: Interaction) -> None:
        self.update_message()


    def leave_callback(self, interaction: Interaction) -> None:
        self.update_message()

    def start_callback(self, interaction: Interaction) -> None:
        # if coroutine run asyncio, otherwise jut run it
        # Should always have arguments ready by using partial
        self.start_function()


    join_button.callback = join_callback
    leave_button.callback = leave_callback
    start_button.callback = start_callback
