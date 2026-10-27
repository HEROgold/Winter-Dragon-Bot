"""The /hangman command: start a game, and guess at it with a button and a modal."""

lazy from random import Random
lazy from typing import TYPE_CHECKING, override

from sqlmodel import Session
lazy from wd_bot.cogs import Cog
lazy from wd_db.extension.lifecycle import alive
lazy from wd_discord import GuildCommandInteraction  # noqa: TC002 - wd_bot reads the handler's interaction type at runtime
lazy from wd_discord.components import Label, Modal, TextInput
lazy from wd_discord.interactions import InteractionContextType
lazy from wd_errors import Refused

lazy from .cards import game_message, guess_buttons
lazy from .models import HANGMAN_TABLES, HangmanGame, HangmanStatus
lazy from .service import guess, participants_of, start_game


if TYPE_CHECKING:
    lazy from wd_discord import ComponentInteraction, ModalSubmitInteraction

MODAL_INPUT = "guess"
"""The ``custom_id`` of the text input in the Guess modal."""


class Hangman(Cog):
    """Plays hangman in a channel: each game is one message, anyone may guess, and a channel can hold several."""

    rng = Random()  # noqa: S311 - drawing a word isn't cryptography
    """Draws the words; tests replace it with a seeded one."""

    @override
    async def load(self) -> None:
        """Create the hangman tables if missing."""
        self.create_tables(*HANGMAN_TABLES)

    @Cog.command(
        name="hangman",
        description="Start a game of hangman in this channel",
        contexts=[InteractionContextType.GUILD],
    )
    async def hangman(self, interaction: GuildCommandInteraction) -> None:
        """Start a game: a message with a Guess button that anyone in the channel may use."""
        with Session(self.bind) as session:
            game = start_game(
                session,
                guild_id=interaction.guild_id,
                channel_id=interaction.channel.id,
                rng=self.rng,
            )
            session.commit()
            session.refresh(game)
            content, buttons = game_message(game), guess_buttons(self.guess_button, game)
        await interaction.respond(content, components=buttons)

    @Cog.component("hangman-guess")
    async def guess_button(self, interaction: ComponentInteraction, game_id: str) -> None:
        """Open the modal for guessing a letter or the whole word."""
        with Session(self.bind) as session:
            game = self._active(session, game_id)
            title = f"Guess the {len(game.word)}-letter word"
        modal = Modal(
            custom_id=self.guess_modal.custom_id(game_id),
            title=title,
            components=[
                Label(
                    label="One letter, or the whole word",
                    component=TextInput(custom_id=MODAL_INPUT, min_length=1, max_length=30, placeholder="e, or the word"),
                ),
            ],
        )
        await interaction.show_modal(modal)

    @Cog.modal("hangman-guess")
    async def guess_modal(self, interaction: ModalSubmitInteraction, game_id: str) -> None:
        """Apply the submitted guess to the game and update its message."""
        user = interaction.user
        if user is None:
            return
        with Session(self.bind) as session:
            game = self._active(session, game_id)
            guess(session, game, user.id, interaction.values.get(MODAL_INPUT, ""))
            session.commit()
            session.refresh(game)
            content = game_message(game, participants_of(session, game))
            buttons = guess_buttons(self.guess_button, game)
        await interaction.update(content, components=buttons)

    @staticmethod
    def _active(session: Session, game_id: str) -> HangmanGame:
        """Return the stored game ``game_id``; refuse when it is gone or over."""
        game = session.exec(alive(HangmanGame).where(HangmanGame.id == int(game_id)).with_for_update()).first()
        if game is None:
            msg = "This game is gone."
            raise Refused(msg)
        if game.status is not HangmanStatus.ACTIVE:
            msg = "This game is over."
            raise Refused(msg)
        return game
