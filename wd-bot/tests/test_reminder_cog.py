"""Unit tests: the /reminder commands, their autocomplete, and sending due reminders (no network)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session, select
from wd_bot.registry import CommandRegistry
from wd_discord import AutocompleteInteraction
from wd_discord.errors.api import ApiResponseError
from wd_discord.gateway.events import AutocompleteInteraction as AutocompleteInteractionModel
from wd_discord.gateway.events import InteractionData, InteractionDataOption, InteractionType
from wd_discord.resources.user import User
from wd_discord.testing import RecordingClient

import winter_dragon.cogs.reminder as module
from winter_dragon.cogs.reminder import Reminder, Reminders, TimedReminder, delay_from, next_occurrence


if TYPE_CHECKING:
    from conftest import InteractionFactory
    from sqlalchemy import Engine


NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
ASKER_ID = 3
OPEN_DM = "/users/@me/channels"
SEND_DM = "/channels/6/messages"
MESSAGE_JSON = {
    "id": "5",
    "channel_id": "6",
    "author": {"id": "2", "username": "bot", "discriminator": "0"},
    "content": "",
    "timestamp": "2026-10-08T12:00:00+00:00",
    "tts": False,
    "mention_everyone": False,
}


@pytest.fixture(autouse=True)
def frozen_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "utc_now", lambda: NOW)


def _cog(engine: Engine) -> tuple[Reminders, RecordingClient]:
    """Build a Reminders cog on ``engine`` without running Cog.__init__, on a client that accepts DMs."""
    client = RecordingClient()
    client.reply("POST", OPEN_DM, {"id": "6", "type": 1})
    client.reply("POST", SEND_DM, MESSAGE_JSON)
    cog = Reminders.__new__(Reminders)
    cog.bot = SimpleNamespace(client=client, registry=CommandRegistry())  # pyright: ignore[reportAttributeAccessIssue]
    cog.session = Session(engine)
    return cog, client


def _options(**values: str | int) -> list[InteractionDataOption]:
    return [
        InteractionDataOption(name=name, type=3 if isinstance(value, str) else 4, value=value) for name, value in values.items()
    ]


def _reply(discord_client: RecordingClient) -> str:
    return discord_client.interaction_responses()[-1]["data"]["content"]


def _seed(engine: Engine, *reminders: Reminder | TimedReminder) -> list[int]:
    with Session(engine) as session:
        session.add_all(reminders)
        session.commit()
        return [reminder.id for reminder in reminders if reminder.id is not None]


def _autocomplete(client: RecordingClient, current: str) -> AutocompleteInteraction:
    model = AutocompleteInteractionModel(
        id="1",
        application_id="2",
        type=InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE,
        token="tok",  # noqa: S106
        version=1,
        user=User.model_validate({"id": str(ASKER_ID), "username": "asker", "discriminator": "0"}),
        data=InteractionData(id="10", name="reminder", type=1),
    )
    return AutocompleteInteraction(client, model)


def test_delay_from_adds_every_unit() -> None:
    assert delay_from(minutes=30, hours=1, days=1, weeks=1) == timedelta(weeks=1, days=1, hours=1, minutes=30)


@pytest.mark.parametrize("amounts", [{}, {"minutes": 0}, {"minutes": -5}, {"days": 10**15}, {"weeks": 600}])
def test_delay_from_refuses_no_negative_or_absurd_delays(amounts: dict[str, int]) -> None:
    assert delay_from(**amounts) is None


def test_next_occurrence_is_one_interval_on_when_just_due() -> None:
    assert next_occurrence(NOW, timedelta(hours=1), NOW) == NOW + timedelta(hours=1)


def test_next_occurrence_skips_missed_occurrences() -> None:
    due = NOW - timedelta(hours=5, minutes=30)
    assert next_occurrence(due, timedelta(hours=1), NOW) == NOW + timedelta(minutes=30)


async def test_add_stores_a_one_off_reminder(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    cog, _ = _cog(engine)
    await Reminders.add.invoke(cog, make_interaction("reminder"), _options(reminder="feed the cat", hours=2))

    with Session(engine) as session:
        (stored,) = session.exec(select(Reminder)).all()
    assert (stored.content, stored.user_id, stored.timestamp) == ("feed the cat", ASKER_ID, NOW + timedelta(hours=2))
    epoch = int((NOW + timedelta(hours=2)).timestamp())
    assert f"<t:{epoch}:F>" in _reply(discord_client)


async def test_add_without_a_time_stores_nothing(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    cog, _ = _cog(engine)
    await Reminders.add.invoke(cog, make_interaction("reminder"), _options(reminder="never"))

    with Session(engine) as session:
        assert session.exec(select(Reminder)).all() == []
    assert "Give me a time" in _reply(discord_client)


async def test_add_refuses_a_too_long_reminder(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    cog, _ = _cog(engine)
    await Reminders.add.invoke(cog, make_interaction("reminder"), _options(reminder="x" * 1001, minutes=5))

    with Session(engine) as session:
        assert session.exec(select(Reminder)).all() == []
    assert "under 1000 characters" in _reply(discord_client)


async def test_repeat_stores_a_timed_reminder(engine: Engine, make_interaction: InteractionFactory) -> None:
    cog, _ = _cog(engine)
    await Reminders.repeat.invoke(cog, make_interaction("reminder"), _options(reminder="stretch", weeks=1))

    with Session(engine) as session:
        (stored,) = session.exec(select(TimedReminder)).all()
    assert (stored.repeat_every, stored.timestamp) == (timedelta(weeks=1), NOW + timedelta(weeks=1))


async def test_send_due_dms_and_removes_one_off_reminders(engine: Engine) -> None:
    _seed(
        engine,
        Reminder(content="due", user_id=ASKER_ID, timestamp=NOW - timedelta(minutes=1)),
        Reminder(content="later", user_id=ASKER_ID, timestamp=NOW + timedelta(minutes=1)),
    )
    cog, client = _cog(engine)

    assert await cog.send_due(NOW) == 1

    assert [sent.json["content"] for sent in client.requests_to("POST", SEND_DM)] == ["I'm here to remind you about\n`due`"]
    with Session(engine) as session:
        assert [reminder.content for reminder in session.exec(select(Reminder))] == ["later"]


async def test_send_due_moves_repeating_reminders_on(engine: Engine) -> None:
    _seed(engine, TimedReminder(content="water", user_id=ASKER_ID, timestamp=NOW, repeat_every=timedelta(days=1)))
    cog, client = _cog(engine)

    assert await cog.send_due(NOW) == 1

    assert len(client.requests_to("POST", SEND_DM)) == 1
    with Session(engine) as session:
        (timed,) = session.exec(select(TimedReminder)).all()
    assert timed.timestamp == NOW + timedelta(days=1)


async def test_undeliverable_reminder_is_still_removed(engine: Engine) -> None:
    _seed(engine, Reminder(content="due", user_id=ASKER_ID, timestamp=NOW))
    cog, client = _cog(engine)
    client.fail("POST", SEND_DM, ApiResponseError(code=50007, message="Cannot send messages to this user"))

    assert await cog.send_due(NOW) == 1

    with Session(engine) as session:
        assert session.exec(select(Reminder)).all() == []


async def test_remove_by_autocomplete_value(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    (timed_id,) = _seed(engine, TimedReminder(content="water", user_id=ASKER_ID, timestamp=NOW, repeat_every=timedelta(days=1)))
    cog, _ = _cog(engine)

    await Reminders.remove.invoke(cog, make_interaction("reminder"), _options(reminder=f"repeat:{timed_id}"))

    with Session(engine) as session:
        assert session.exec(select(TimedReminder)).all() == []
    assert _reply(discord_client) == "Removed your reminder of\n`water`"


async def test_remove_by_typed_content(engine: Engine, make_interaction: InteractionFactory) -> None:
    _seed(engine, Reminder(content="feed the cat", user_id=ASKER_ID, timestamp=NOW))
    cog, _ = _cog(engine)

    await Reminders.remove.invoke(cog, make_interaction("reminder"), _options(reminder="feed the cat"))

    with Session(engine) as session:
        assert session.exec(select(Reminder)).all() == []


async def test_remove_leaves_other_users_reminders_alone(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    (other_id,) = _seed(engine, Reminder(content="theirs", user_id=99, timestamp=NOW))
    cog, _ = _cog(engine)

    await Reminders.remove.invoke(cog, make_interaction("reminder"), _options(reminder=f"once:{other_id}"))
    await Reminders.remove.invoke(cog, make_interaction("reminder"), _options(reminder="theirs"))

    with Session(engine) as session:
        assert len(session.exec(select(Reminder)).all()) == 1
    assert _reply(discord_client) == "You have no reminder like that."


async def test_autocomplete_suggests_own_matching_reminders(engine: Engine, discord_client: RecordingClient) -> None:
    once_id, timed_id, _ = _seed(
        engine,
        Reminder(content="Feed the cat", user_id=ASKER_ID, timestamp=NOW),
        TimedReminder(content="clean the cat box", user_id=ASKER_ID, timestamp=NOW, repeat_every=timedelta(days=1)),
        Reminder(content="cat of someone else", user_id=99, timestamp=NOW),
    )
    _seed(engine, Reminder(content="unrelated", user_id=ASKER_ID, timestamp=NOW))
    cog, _ = _cog(engine)

    choices = await cog.remove_choices(_autocomplete(discord_client, "CAT"), "CAT")

    assert [(choice.name, choice.value) for choice in choices] == [
        ("🔁 clean the cat box", f"repeat:{timed_id}"),
        ("Feed the cat", f"once:{once_id}"),
    ]


async def test_autocomplete_truncates_long_names(engine: Engine, discord_client: RecordingClient) -> None:
    _seed(engine, Reminder(content="a" * 300, user_id=ASKER_ID, timestamp=NOW))
    cog, _ = _cog(engine)

    (choice,) = await cog.remove_choices(_autocomplete(discord_client, ""), "")

    assert len(choice.name) == 100
