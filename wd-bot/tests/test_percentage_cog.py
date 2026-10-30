"""Unit tests: the percentage command's calculation is deterministic and its embed matches the legacy love meter."""

lazy import random
lazy from typing import TYPE_CHECKING

from sqlmodel import Session, select
from wd_bot.testing import detached_cog
from wd_db.extension.lifecycle import alive, soft_delete
lazy from hypothesis import given
lazy from hypothesis import strategies as st
lazy from wd_discord import User as BoundUser
lazy from wd_discord.gateway.events import InteractionDataOption, ResolvedData
lazy from wd_discord.resources.user import User
lazy from wd_discord.testing import RecordingClient

lazy from winter_dragon.cogs.percentage import CompatibilityCheck, Love, build_love_embed, calculate_percentage, record_check


if TYPE_CHECKING:
    lazy from conftest import InteractionFactory
    lazy from sqlalchemy import Engine
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


def _cog(engine: Engine) -> Love:
    """Build a Love cog without running Cog.__init__; the handler talks to its interaction and the database."""
    return detached_cog(Love, engine=engine)


async def test_handler_replies_with_love_embed(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    asker = User(id=1, username="alice", discriminator="0")
    interaction = _interaction(make_interaction, asker)
    await Love.love.invoke(_cog(engine), interaction)
    target = _bound(User(id=2, username="bob", discriminator="0", global_name="Bobby"))
    expected = build_love_embed(target, calculate_percentage(1, 2))
    assert discord_client.interaction_responses() == [
        {"type": 4, "data": {"embeds": [expected.model_dump(mode="json", exclude_none=True)]}},
    ]


async def test_handler_without_asker_refuses_privately(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    interaction = _interaction(make_interaction, None)
    await Love.love.invoke(_cog(engine), interaction)
    (response,) = discord_client.interaction_responses()
    assert response["data"] == {"content": "I couldn't work out who invoked this command.", "flags": 64}


async def test_handler_records_a_check_owned_by_the_asker(engine: Engine, make_interaction: InteractionFactory) -> None:
    asker = User(id=1, username="alice", discriminator="0")
    await Love.love.invoke(_cog(engine), _interaction(make_interaction, asker))
    with Session(engine) as session:
        (check,) = session.exec(alive(CompatibilityCheck)).all()
    assert (check.user_id, check.target_id, check.target_name) == (1, 2, "Bobby")


async def test_handler_without_asker_records_nothing(engine: Engine, make_interaction: InteractionFactory) -> None:
    await Love.love.invoke(_cog(engine), _interaction(make_interaction, None))
    with Session(engine) as session:
        assert session.exec(select(CompatibilityCheck)).all() == []


async def test_the_checked_user_has_no_record(engine: Engine, make_interaction: InteractionFactory) -> None:
    asker = User(id=1, username="alice", discriminator="0")
    await Love.love.invoke(_cog(engine), _interaction(make_interaction, asker))
    with Session(engine) as session:
        assert [check.user_id for check in session.exec(select(CompatibilityCheck)).all()] == [1]


def test_a_repeat_check_updates_the_row_instead_of_adding_one(engine: Engine) -> None:
    with Session(engine) as session:
        first = record_check(session, 1, 2, "Bobby")
        session.commit()
        first_time, first_id = first.checked_at, first.id
    with Session(engine) as session:
        record_check(session, 1, 2, "Bob")
        session.commit()
    with Session(engine) as session:
        (check,) = session.exec(select(CompatibilityCheck)).all()
    assert (check.id, check.target_name) == (first_id, "Bob")
    assert check.checked_at >= first_time


def test_a_check_of_a_deleted_entry_brings_it_back(engine: Engine) -> None:
    with Session(engine) as session:
        check = record_check(session, 1, 2, "Bobby")
        session.commit()
        soft_delete(session, check)
        session.commit()
    with Session(engine) as session:
        record_check(session, 1, 2, "Bobby")
        session.commit()
    with Session(engine) as session:
        assert len(session.exec(alive(CompatibilityCheck)).all()) == 1


def test_different_askers_each_get_their_own_check(engine: Engine) -> None:
    with Session(engine) as session:
        record_check(session, 1, 2, "Bobby")
        record_check(session, 3, 2, "Bobby")
        session.commit()
        assert len(session.exec(select(CompatibilityCheck)).all()) == 2  # noqa: PLR2004


def test_a_check_is_member_data_the_member_can_delete(engine: Engine) -> None:
    from wd_db.extension.lifecycle import lifecycle_models, owned_by  # noqa: PLC0415

    assert CompatibilityCheck in set(lifecycle_models())
    assert CompatibilityCheck.ownership.member == "user_id"
    with Session(engine) as session:
        check = record_check(session, 1, 2, "Bobby")
        session.commit()
        (owned,) = session.exec(owned_by(CompatibilityCheck, member=1)).all()
        assert owned.id == check.id
        assert session.exec(owned_by(CompatibilityCheck, member=2)).all() == []
        soft_delete(session, owned)
        session.commit()
        assert session.exec(alive(CompatibilityCheck)).all() == []
