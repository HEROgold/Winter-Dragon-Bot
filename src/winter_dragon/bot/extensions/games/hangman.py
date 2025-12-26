"""Module to contain the Hangman game."""

import random
from textwrap import dedent
from typing import Unpack, override

import aiohttp
import discord
from discord import app_commands
from sqlmodel import select

from winter_dragon.bot.core.cogs import BotArgs, GroupCog
from winter_dragon.bot.ui.button import Button
from winter_dragon.bot.ui.modal import Modal
from winter_dragon.database.constants import SessionMixin
from winter_dragon.database.tables import AssociationUserHangman as AUH  # noqa: N817
from winter_dragon.database.tables import Games
from winter_dragon.database.tables import Hangmen as HangmanDb
from winter_dragon.database.tables import ResultMassiveMultiplayer as ResultMM


HANGMAN = "hangman"
# Hang Man Stages
HANGMEN = [
    """
 ------
|        |
|
|
|
|
|
|
----------
""",
    """
 ------
|       |
|       0
|
|
|
|
|
----------
""",
    """
 ------
|        |
|        0
|        +
|
|
|
|
----------
""",
    """
 ------
|        |
|        0
|       -+
|
|
|
|
----------
""",
    """
 ------
|        |
|        0
|       -+-
|
|
|
|
----------
""",
    """
 ------
|        |
|        0
|      /-+-
|
|
|
|
----------
""",
    """
 ------
|        |
|        0
|      /-+-/
|
|
|
|
----------
""",
    """
 ------
|        |
|        0
|      /-+-/
|        |
|
|
|
----------
""",
    """
 ------
|        |
|        0
|      /-+-/
|        |
|        |
|
|
----------
""",
    """
 ------
|        |
|        0
|      /-+-/
|        |
|        |
|       |
|       |
----------
""",
    """
 ------
|        |
|        0
|      /-+-/
|        |
|        |
|       | |
|       | |
----------
""",
]


def get_hangman(guess_amount: int) -> str:
    """Get a hangman text-image based on the amount of guesses."""
    return HANGMEN[guess_amount]


class HangmanButton(Button):
    """A button to start a hangman game."""

    async def callback(self, interaction: discord.Interaction) -> None:
        """Start a hangman game."""
        try:
            await interaction.response.send_modal(SubmitLetter())
        except Exception:
            self.logger.exception("Error creating hangman SubmitLetter modal")


class SubmitLetter(Modal, SessionMixin, title="Submit Letter"):
    """A modal to submit a letter for the hangman game."""

    letter = discord.ui.TextInput(label="Letter", min_length=1, max_length=1)

    def __del__(self) -> None:
        """Delete the modal."""
        self.session.close()

    @override
    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Submit a letter for the hangman game."""
        self.logger.debug(f"Submitting {self.letter.value=}")
        self.interaction = interaction
        await self.get_hangman_game()
        await self.notify_chosen_letter()
        player = self.get_player_record()
        self.track_wrong_guesses()

        hangman = get_hangman(guess_amount=len(self.wrong_after))
        self.add_player_score(player, 2 if self.is_wrong else -1)
        hidden_word = self.get_hidden_word()

        wrong_max = 10
        if len(self.wrong_after) >= wrong_max:
            await interaction.response.edit_message(
                content=dedent(
                    f"""Game Lost...
                    Guesses: {hidden_word}
                    Word: {self.hangman_db.word}
                    {hangman}`
                    Letters: {self.hangman_db.letters}""",
                ),
                view=None,
            )
            return

        checks = self.validate_guessed_letters()

        if not all(checks):
            await interaction.response.edit_message(
                content=f"Word: {hidden_word}\n{hangman}\nLetters: {self.hangman_db.letters}",
            )
            self.session.commit()
            return

        # Fetch all players that played,
        # Push results to results table
        # then delete association table data for that player.
        hangman_players = self.fetch_hangman_players()
        self.rank_hangman_players(hangman_players)

        for player in hangman_players:
            placement = self.calculate_placement(hangman_players, player)
            game = Games.fetch_game_by_name(HANGMAN)
            self.session.add(
                ResultMM(
                    game_id=game.id,
                    player=player.user_id,
                    placement=placement,
                ),
            )

        for i in hangman_players:
            self.session.delete(i)

        # Edit message, change status and end game
        await interaction.response.edit_message(
            content=f"Game Won!\nWord: {self.hangman_db.word}\n{hangman}\nLetters: {self.hangman_db.letters}",
            view=None,
        )
        self.session.commit()

    def get_hidden_word(self) -> str:
        """Get the hidden word."""
        return "".join(i if i in self.hangman_db.letters else "-" for i in self.hangman_db.word)

    def track_wrong_guesses(self) -> None:
        """Track wrong guesses. Return the wrong guesses and if the guess was wrong."""
        self.wrong_before = [i for i in self.hangman_db.letters if i not in self.hangman_db.word]
        self.add_chosen_letter()
        self.wrong_after = [i for i in self.hangman_db.letters if i not in self.hangman_db.word]
        self.is_wrong = len(self.wrong_before) > len(self.wrong_after)

    def add_chosen_letter(self) -> None:
        """Add the chosen letter to the hangman game."""
        self.logger.debug(f"Adding {self.letter.value=}")
        self.hangman_db.letters += self.letter.value

    async def notify_chosen_letter(self) -> None:
        """Notify the user about the chosen letter."""
        if self.letter.value in self.hangman_db.letters:
            self.logger.debug(f"Already chosen: {self.letter.value=}, {self.interaction.user=}")
            await self.interaction.response.send_message("Letter already chosen.", ephemeral=True)
        else:
            await self.interaction.response.send_message(f"Chosen letter: {self.letter.value}", ephemeral=True)

    async def get_hangman_game(self) -> None:
        """Get the hangman game. Creates a new one if it doesn't exist."""
        if not self.interaction.message:
            msg = "No message found."
            self.logger.warning(msg)
            raise ValueError(msg)

        self.hangman_db = (
            self.session.exec(
                select(HangmanDb).where(HangmanDb.message_id == self.interaction.message.id),
            ).first()
            or await self.new_hangman_game()
        )

    def calculate_placement(self, hangman_players: list[AUH], player: AUH) -> int:
        """Calculate the placement of the player."""
        return hangman_players.index(player)

    def rank_hangman_players(self, hangman_players: list[AUH]) -> None:
        """Rank the hangman players."""
        try:

            def sort_key(x: AUH) -> int:
                return x.score

            hangman_players.sort(key=sort_key)
        except AttributeError:
            self.logger.exception("Error sorting hangman players")

    def fetch_hangman_players(self) -> list[AUH]:
        """Fetch all players that played."""
        if not self.interaction.message:
            msg = "No message found."
            self.logger.warning(msg)
            raise ValueError(msg)

        hangman_players = self.session.exec(
            select(AUH).where(AUH.hangman_id == self.interaction.message.id),
        ).all()
        self.logger.debug(f"{hangman_players=}")
        return list(hangman_players)

    def add_player_score(self, player: AUH, score: int) -> None:
        """Add score to player."""
        try:
            player.score += score
        except TypeError:
            self.logger.exception(f"Error adding score: {player=}")
            player.score = score

    def validate_guessed_letters(self) -> list[bool]:
        """Validate guessed letters."""
        checks: list[bool] = [truthy for letter in self.hangman_db.word if (truthy := letter in self.hangman_db.letters)]
        self.logger.debug(f"{checks=}")
        return checks

    def get_player_record(self) -> AUH:
        """Get the player record. Create if it doesn't exist."""
        if not self.interaction.message:
            msg = "No message found."
            self.logger.warning(msg)
            raise ValueError(msg)

        player = self.session.exec(
            select(AUH).where(
                AUH.hangman_id == self.interaction.message.id,
                AUH.user_id == self.interaction.user.id,
            ),
        ).first()
        return player or self.create_player_record()

    def create_player_record(self) -> AUH:
        """Create a new player record."""
        if not self.interaction.message:
            msg = "No message found."
            self.logger.warning(msg)
            raise ValueError(msg)

        player = AUH(
            hangman_id=self.interaction.message.id,
            user_id=self.interaction.user.id,
            score=0,
        )
        self.session.add(player)
        return player

    async def new_hangman_game(self) -> HangmanDb:
        """Create a new hangman game."""
        self.logger.debug("Hangman is empty, creating new one.")
        async with aiohttp.ClientSession().get("https://www.mit.edu/~ecprice/wordlist.10000") as res:
            t = await res.text()
            r_word = random.choice(t.splitlines())  # noqa: S311
        self.logger.debug(f"{r_word=}")

        if not self.interaction.message:
            msg = "No message found."
            self.logger.warning(msg)
            raise ValueError(msg)

        hangman_db = HangmanDb(
            message_id=self.interaction.message.id,
            word=r_word,
            letters="",
        )
        self.session.add(hangman_db)
        return hangman_db


class Hangman(GroupCog, auto_load=True):
    """A cog that plays the hangman game in a discord chat message."""

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the Hangman cog."""
        super().__init__(**kwargs)
        self.game = Games.fetch_game_by_name(HANGMAN)

    @app_commands.command(name="start", description="Hangman")
    async def slash_hangman(self, interaction: discord.Interaction) -> None:
        """Start a hangman game."""
        view = discord.ui.View()
        btn = HangmanButton(label="Add Letter", style=discord.ButtonStyle.primary)
        view.add_item(btn)
        await interaction.response.send_message(f"{HANGMEN[0]}", view=view)
