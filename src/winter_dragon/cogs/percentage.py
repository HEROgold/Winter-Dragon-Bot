"""A cog with a single command: a random compatibility percentage between two users."""

from __future__ import annotations

lazy import random
lazy from typing import TYPE_CHECKING

lazy from wd_bot.cogs import Cog

# Command resolves option annotations from module globals at runtime, so User must be available here.
lazy from wd_discord import User  # noqa: TC002
lazy from wd_discord.embed import Embed, EmbedField


if TYPE_CHECKING:
    lazy from wd_discord import CommandInteraction


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
        color=0xFF0000,
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
    async def love(self, interaction: CommandInteraction, user: User) -> None:
        """Reply with a random compatibility love between the invoking user and ``user``."""
        asker = interaction.user
        if asker is None:
            await interaction.respond("I couldn't work out who invoked this command.")
            return
        percent = calculate_percentage(int(asker.id), int(user.id))
        await interaction.respond(embeds=[build_love_embed(user, percent)])
