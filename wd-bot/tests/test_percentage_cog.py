"""Unit tests: the percentage command's calculation is deterministic and its embed matches the legacy love meter."""

lazy import random
lazy from typing import TYPE_CHECKING

lazy from hypothesis import given
lazy from hypothesis import strategies as st
from wd_bot.testing import detached_cog
lazy from wd_discord import User as BoundUser
lazy from wd_discord.gateway.events import InteractionDataOption, ResolvedData
lazy from wd_discord.resources.user import User
lazy from wd_discord.testing import RecordingClient

lazy from winter_dragon.cogs.percentage import Love, build_love_embed, calculate_percentage


if TYPE_CHECKING:
    lazy from conftest import InteractionFactory
    lazy from wd_discord import CommandInteraction


MAX_PERCENT = 100
LOVE_COLOR = 0xFF0000


def _bound(user: User) -> BoundUser:
    return BoundUser(RecordingClient(), user)


USER_IDS = st.integers(min_value=0, max_value=2**64 - 1)


@given(USER_IDS, USER_IDS)
def test_percentage_is_a_fixed_percentage_for_each_pair_in_either_order(a: int, b: int) -> None:
    value = calculate_percentage(a, b)
    assert 0 <= value <= MAX_PERCENT
    assert calculate_percentage(a, b) == value
    assert calculate_percentage(b, a) == value


def test_percentage_matches_manual_seed() -> None:
    expected = random.Random(1 + 2).randint(0, 100)  # noqa: S311 - mirrors the implementation
    assert calculate_percentage(1, 2) == expected


def test_love_embed_uses_global_name() -> None:
    target = _bound(User(id=2, username="bob", discriminator="0", global_name="Bobby"))
    embed = build_love_embed(target, 42)
    assert embed.title == "Love Meter"
    assert embed.description == " "
    assert embed.color == LOVE_COLOR
    assert embed.fields is not None
    assert len(embed.fields) == 1
    field = embed.fields[0]
    assert field.name == "Bobby"
    assert field.value == "Your compatibility with Bobby is 42%"
    assert field.inline is True


def test_love_embed_falls_back_to_username() -> None:
    target = _bound(User(id=2, username="bob", discriminator="0"))
    embed = build_love_embed(target, 7)
    assert embed.fields is not None
    assert embed.fields[0].name == "bob"
    assert embed.fields[0].value == "Your compatibility with bob is 7%"


def _interaction(make_interaction: InteractionFactory, asker: User | None) -> CommandInteraction:
    """Build a /percentage interaction targeting user 2, optionally invoked by ``asker``."""
    target = User(id=2, username="bob", discriminator="0", global_name="Bobby")
    return make_interaction(
        "percentage",
        options=[InteractionDataOption(name="user", type=6, value="2")],
        resolved=ResolvedData(users={"2": target}),
        user=asker,
    )


def _cog() -> Love:
    """Build a Love cog without running Cog.__init__; the handler only talks to its interaction."""
    return detached_cog(Love)


async def test_handler_replies_with_love_embed(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    asker = User(id=1, username="alice", discriminator="0")
    interaction = _interaction(make_interaction, asker)
    await Love.love.invoke(_cog(), interaction)
    target = _bound(User(id=2, username="bob", discriminator="0", global_name="Bobby"))
    expected = build_love_embed(target, calculate_percentage(1, 2))
    assert discord_client.interaction_responses() == [
        {"type": 4, "data": {"embeds": [expected.model_dump(mode="json", exclude_none=True)]}},
    ]


async def test_handler_without_asker_replies_content_only(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    interaction = _interaction(make_interaction, None)
    await Love.love.invoke(_cog(), interaction)
    (response,) = discord_client.interaction_responses()
    assert "embeds" not in response["data"]
    assert response["data"]["content"]
