"""Module to implement the Would You Rather game."""
import random
from typing import override

import discord
from discord import app_commands
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.tools import rainbow
from winter_dragon.database.tables import NhieQuestion

from .base_question_game import BaseQuestionGame


class NeverHaveIEver(BaseQuestionGame[NhieQuestion]):
    """Never Have I Ever game implementation."""

    GAME_NAME = "NEVER_HAVE_I_EVER"
    GAME_DISPLAY_NAME = "Never Have I Ever"
    QUESTION_MODEL = NhieQuestion
    BASE_QUESTIONS = [  # noqa: RUF012
"Never have I ever gone skinny dipping.",
"Never have I ever gone on a blind date.",
"Never have I ever creeped an ex on social media.",
"Never have I ever been hungover.",
"Never have I ever kissed my best friend.",
"Never have I ever ghosted someone.",
"Never have I ever gotten a speeding ticket.",
"Never have I ever slid into someone's DMs.",
"Never have I ever dined and dashed.",
"Never have I ever used a fake ID.",
"Never have I ever had a crush on a teacher.",
"Never have I ever been in love.",
"Never have I ever made out in a public place.",
"Never have I ever gotten into a physical fight.",
"Never have I ever had an alcoholic drink.",
"Never have I ever played spin the bottle.",
"Never have I ever snooped through someone's phone.",
"Never have I ever snuck into a movie theater.",
"Never have I ever kissed a friend's ex.",
'Never have I ever told someone "I love you" without meaning it.',
"Never have I ever been called a player.",
"Never have I ever smoked a cigarette.",
"Never have I ever given a lap dance.",
"Never have I ever gotten a lap dance.",
"Never have I ever cheated on a test.",
"Never have I ever used a dating app.",
"Never have I ever kissed more than one person in 24 hours.",
"Never have I ever cheated on someone.",
"Never have I ever been cheated on.",
"Never have I ever sent a racy text to the wrong person.",
"Never have I ever had a negative bank account balance.",
"Never have I ever played strip poker.",
"Never have I ever been arrested.",
"Never have I ever been expelled.",
"Never have I ever stolen anything.",
"Never have I ever gotten a hickey.",
"Never have I ever been fired.",
"Never have I ever made out in a movie theater.",
"Never have I ever dated someone older than me.",
"Never have I ever dated someone younger than me.",
"Never have I ever broken the law.",
"Never have I ever been to a nude beach.",
"Never have I stood a date up.",
"Never have I ever stayed in a relationship that I really wasn`t feeling.",
"Never have I ever given someone a fake phone number.",
"Never have I ever lied to someone in this room.",
"Never have I ever broken up with someone over text.",
"Never have I ever had a crush on an SO`s best friend.",
"Never have I ever shoplifted.",
"Never have I ever seen a ghost.",
"Never have I told a secret I wasn`t supposed to share.",
"Never have I ever had a friend with benefits.",
"Never have I ever intentionally started a fight between other people.",
"Never have I ever dated more than one person at once.",
"Never have I ever spent money that wasn`t mine to spend.",
"Never have I ever had a relationship last less than a month.",
"Never have I ever had a relationship last longer than a year.",
"Never have I ever gotten an unexpected piercing.",
"Never have I ever found a dumb excuse to text an ex.",
"Never have I ever fallen in love at first sight.",
"Never have I ever kissed someone I just met.",
"Never have I ever kept a crush secret from people in this room.",
"Never have I ever been in love with someone without them knowing.",
"Never have I ever been in an open relationship.",
"Never have I ever fantasized about getting back with an ex.",
"Never have I ever helped a friend lie by being their alibi.",
"Never have I ever seriously thought about marrying someone.",
"Never have I ever had a totally online relationship.",
"Never have I ever flirted just to get something I wanted.",
"Never have I ever tried guessing someone`s password.",
"Never have I ever been caught lying.",
]


    @override
    def create_embed(self, question: NhieQuestion) -> discord.Embed:
        emb = discord.Embed(
            title="Never Have I Ever",
            description=question.value,
            color=random.choice(rainbow.RAINBOW),  # noqa: S311
        )
        emb.add_field(name="I Have", value="✅")
        emb.add_field(name="Never", value="⛔")
        return emb

    async def add_reactions(self, message: discord.Message) -> None:
        """Add reactions to the message."""
        await message.add_reaction("✅")
        await message.add_reaction("⛔")

    # Use more specific command names to avoid conflicts
    @app_commands.command(
        name="show",
        description="Use this to get a never have i ever question, that you can reply to",
    )
    @app_commands.checks.cooldown(1, 10)
    async def slash_nhie_show(self, interaction: discord.Interaction) -> None:
        """Send a random Would You Rather question to the channel."""
        await self.show(interaction)

    @app_commands.command(
        name="add",
        description="Lets you add a Never Have I Ever question",
    )
    async def slash_nhie_add(self, interaction: discord.Interaction, nhie_question: str) -> None:
        """Add a Would You Rather question to the game. The question requires verification first."""
        await self.add(interaction, nhie_question)

    @app_commands.command(
        name="add_verified",
        description="Add all questions stored in the NHIE database file, to the questions data section.",
    )
    async def slash_nhie_add_verified(self, interaction: discord.Interaction) -> None:
        """Add all verified questions to the game."""
        await self.add_verified(interaction)


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(NeverHaveIEver(bot=bot))
