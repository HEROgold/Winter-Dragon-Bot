"""A cog with a single command: a random compatibility percentage between two users."""

from typing import TYPE_CHECKING, Annotated
lazy import random

from confkit.data_types import Hex
from wd_bot.cogs import Cog
from wd_bot.commands import Describe

# Command resolves option annotations from module globals at runtime, so User must be available here.
lazy from wd_discord import User
lazy from wd_discord.embed import Embed, EmbedField

from winter_dragon.config import CogConfig


if TYPE_CHECKING:
    lazy from wd_discord import CommandInteraction


class PercentageSettings:
    """Settings for /love, in its ``cogs.ini`` section."""

    love_color = CogConfig(Hex(0xFF0000))
    """The color of the Love Meter embed."""


def calculate_percentage(user_id_a: int, user_id_b: int) -> int:
    """Compute a random 0-100 percentage, seeded by both user IDs (order-independent)."""
    rng = random.Random(user_id_a + user_id_b)  # noqa: S311 - not security-sensitive: a novelty percentage
    return rng.randint(0, 100)


def build_love_embed(target: User, percent: int) -> Embed:
    """Build the "Love Meter" embed for ``target`` with the given compatibility ``percent``."""
    name = target.display_name
    return Embed(
        title="Love Meter",
        description=" ",
        color=PercentageSettings.love_color,
        fields=[
            EmbedField(
                name=name,
                value=f"Your compatibility with {name} is {percent}%",
                inline=True,
            ),
        ],
    )


class Love(Cog):
    """Cog for the /love command."""

    @Cog.command(name="love", description="Calculate compatibility with another user")  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUntypedFunctionDecorator]
    async def love(
        self,
        interaction: CommandInteraction,
        user: Annotated[User, Describe("The user to calculate compatibility with")],
    ) -> None:
        """Reply with a random compatibility love between the invoking user and ``user``."""
        asker = interaction.user
        if asker is None:
            await interaction.respond("I couldn't work out who invoked this command.")
            return
        percent = calculate_percentage(int(asker.id), int(user.id))
        await interaction.respond(embeds=[build_love_embed(user, percent)])
