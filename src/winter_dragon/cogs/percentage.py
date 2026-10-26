"""A cog with a single command: a random compatibility percentage between two users."""

from datetime import datetime
from typing import Annotated
lazy import random
lazy from typing import TYPE_CHECKING, ClassVar, override

from sqlalchemy import BigInteger
from sqlmodel import Field, Session
from wd_bot.commands import Describe
from wd_db.extension.columns import AwareDateTime
from wd_db.extension.lifecycle import LifecycleModel, Ownership, upsert
from wd_types.clock import utc_now
lazy from confkit.data_types import Hex
lazy from wd_bot.cogs import Cog

# Command resolves option annotations from module globals at runtime, so User must be available here.
lazy from wd_discord import User  # noqa: TC002
lazy from wd_discord.embed import Embed, EmbedField
lazy from wd_errors import Refused

lazy from winter_dragon.config import CogConfig


if TYPE_CHECKING:
    lazy from wd_discord import CommandInteraction


class PercentageSettings:
    """Settings for /love, in its ``cogs.ini`` section."""

    love_color = CogConfig(Hex(0xFF0000))
    """The color of the Love Meter embed."""


class CompatibilityCheck(LifecycleModel, table=True):
    """A member's check of their compatibility with another user; ``user_id`` is the member who asked, and they own it.

    The percentage is fixed for each pair, so it is not stored. The checked user has no record of it.
    """

    ownership: ClassVar[Ownership] = Ownership(member="user_id")
    natural_key: ClassVar[tuple[str, ...]] = ("user_id", "target_id")

    user_id: int = Field(sa_type=BigInteger, index=True)
    target_id: int = Field(sa_type=BigInteger)
    target_name: str
    """The checked user's display name when the check was made."""
    checked_at: datetime = Field(default_factory=utc_now, sa_type=AwareDateTime)
    """When the member last checked this user."""


def record_check(session: Session, user_id: int, target_id: int, target_name: str) -> CompatibilityCheck:
    """Store that ``user_id`` checked ``target_id``, or refresh the earlier check of the same pair; the caller commits."""
    return upsert(session, CompatibilityCheck(user_id=user_id, target_id=target_id, target_name=target_name))


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

    @override
    async def load(self) -> None:
        """Create the compatibility check table if missing."""
        self.create_tables(CompatibilityCheck)

    @Cog.command(name="love", description="Calculate compatibility with another user")  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUntypedFunctionDecorator]
    async def love(
        self,
        interaction: CommandInteraction,
        user: Annotated[User, Describe("The user to calculate compatibility with")],
    ) -> None:
        """Reply with a random compatibility love between the invoking user and ``user``."""
        asker = interaction.user
        if asker is None:
            msg = "I couldn't work out who invoked this command."
            raise Refused(msg)
        percent = calculate_percentage(int(asker.id), int(user.id))
        with Session(self.bind) as session:
            record_check(session, int(asker.id), int(user.id), user.display_name)
            session.commit()
        await interaction.respond(embeds=[build_love_embed(user, percent)])
