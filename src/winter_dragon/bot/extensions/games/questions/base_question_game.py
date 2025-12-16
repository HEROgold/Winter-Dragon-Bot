"""Module for an Abstract class, for questionnaire like games."""

from abc import abstractmethod
from collections.abc import Sequence
from typing import Any, Generic, TypeVar, Unpack

import discord
from sqlalchemy import func
from sqlmodel import SQLModel, select

from winter_dragon.bot.core.cogs import BotArgs, GroupCog
from winter_dragon.database.tables import Games, Suggestions


MISSING: Any = object()
T = TypeVar("T", bound=SQLModel)


class BaseQuestionGame(Generic[T], GroupCog, auto_load=False):
    """Base class for question-based games like Never Have I Ever and Would You Rather."""

    # Constants to be overridden by subclasses
    GAME_NAME: str = MISSING
    GAME_DISPLAY_NAME: str = MISSING
    QUESTION_MODEL: type[T] = MISSING
    BASE_QUESTIONS: list[str] = MISSING

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the game with a session and set default data."""
        if self.__class__ is BaseQuestionGame:
            return
        super().__init__(**kwargs)
        self._validate_game_constants()
        self.game = Games.fetch_game_by_name(self.GAME_NAME)
        self.set_default_data()

    def _validate_game_constants(self) -> None:
        """Validate that required game constants are properly defined."""
        if self.GAME_NAME is MISSING:
            msg = "GAME_NAME must be defined as a string in the subclass."
            raise TypeError(msg)
        if self.GAME_DISPLAY_NAME is MISSING:
            msg = "GAME_DISPLAY_NAME must be defined as a string in the subclass."
            raise TypeError(msg)
        if self.QUESTION_MODEL is MISSING:
            msg = "QUESTION_MODEL must be defined as a subclass of SQLModel in the subclass."
            raise TypeError(msg)
        if self.BASE_QUESTIONS is MISSING:
            msg = "BASE_QUESTIONS must be defined as a list of strings in the subclass."
            raise TypeError(msg)

    def set_default_data(self) -> None:
        """Set default data to the database if it doesn't exist."""
        questions = self.session.exec(select(self.QUESTION_MODEL)).all()
        if len(questions) > 0:
            self.logger.debug("Questions already present in table.")
            return
        for question_id, _ in enumerate(self.BASE_QUESTIONS):
            self.logger.debug(f"adding question to database {question_id=}, value={self.BASE_QUESTIONS[question_id]}")
            self.session.add(self.QUESTION_MODEL(id=question_id, value=self.BASE_QUESTIONS[question_id]))
        self.session.commit()

    def get_questions(self) -> tuple[int, Sequence[T]]:
        """Get all questions from the database."""
        questions = self.session.exec(select(self.QUESTION_MODEL)).all()
        game_id = 0
        return game_id, questions

    def get_random_question(self) -> T | None:
        """Get a random question from the database."""
        return self.session.exec(select(self.QUESTION_MODEL).order_by(func.random)).first()

    @abstractmethod
    def create_embed(self, question: T) -> discord.Embed:
        """Create a game-specific embed. To be overridden by subclasses."""

    @abstractmethod
    async def add_reactions(self, message: discord.Message) -> None:
        """Add game-specific reactions. To be overridden by subclasses."""

    async def show(self, interaction: discord.Interaction) -> None:
        """Send a randomized question to the channel.

        Intended to be called by subclasses.
        """
        if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This command can only be used in a channel", ephemeral=True)
            return
        question = self.get_random_question()
        if question is None:
            # Should not happen, since we have default questions.
            self.logger.warning(f"No questions available for {self.GAME_NAME}")
            await interaction.response.send_message("No questions available", ephemeral=True)
            return
        emb = self.create_embed(question)
        send_msg = await interaction.channel.send(embed=emb)
        await self.add_reactions(send_msg)
        await interaction.response.send_message("Question send", ephemeral=True, delete_after=2)

    async def add(self, interaction: discord.Interaction, question: str) -> None:
        """Add a new question to the game."""
        self.session.add(
            Suggestions(
                id=None,
                type=self.GAME_NAME,
                content=question,
            ),
        )
        self.session.commit()
        await interaction.response.send_message(
            f"The question ```{question}``` is added, it will be verified later.",
            ephemeral=True,
        )

    async def add_verified(self, interaction: discord.Interaction) -> None:
        """Add all verified questions to the game."""
        result = self.session.exec(
            select(Suggestions).where(
                Suggestions.type == self.GAME_NAME,
                Suggestions.verified_at is not None,
            ),
        )
        questions = result.all()
        if not questions:
            await interaction.response.send_message("No questions to add", ephemeral=True)
            return

        for question in questions:
            self.session.add(self.QUESTION_MODEL(value=question.content))
        self.session.commit()
        await interaction.response.send_message("Added all verified questions", ephemeral=True)
