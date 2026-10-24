"""Unit tests: the /reminder commands, their autocomplete, and sending due reminders (no network)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import text
from sqlmodel import Session
from wd_bot.testing import detached_cog
from wd_db.extension.lifecycle import alive
from wd_db.testing import seed, sqlite_engine
from wd_discord import AutocompleteInteraction
from wd_discord.errors.api import ApiResponseError
from wd_discord.gateway.events import AutocompleteInteraction as AutocompleteInteractionModel
from wd_discord.gateway.events import InteractionData, InteractionDataOption, InteractionType
from wd_discord.resources.user import User
from wd_discord.testing import RecordingClient, message_json, user_json

import winter_dragon.cogs.reminder as module
from winter_dragon.cogs.reminder import Reminder, Reminders, TimedReminder, delay_from, next_occurrence
from winter_dragon.config import Settings


if TYPE_CHECKING:
    from collections.abc import Coroutine

    from conftest import InteractionFactory
    from sqlalchemy import Engine


NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
ASKER_ID = 3
OPEN_DM = "/users/@me/channels"
SEND_DM = "/channels/6/messages"


@pytest.fixture(autouse=True)
def frozen_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "utc_now", lambda: NOW)


def _cog(engine: Engine, **bot: object) -> tuple[Reminders, RecordingClient]:
    """Build a Reminders cog on ``engine`` without running Cog.__init__, on a client that accepts DMs."""
    client = RecordingClient()
    client.reply("POST", OPEN_DM, {"id": "6", "type": 1})
    client.reply("POST", SEND_DM, message_json())
    return detached_cog(Reminders, engine=engine, client=client, **bot), client


def _options(**values: str | int) -> list[InteractionDataOption]:
    return [
        InteractionDataOption(name=name, type=3 if isinstance(value, str) else 4, value=value) for name, value in values.items()
    ]


def _reply(discord_client: RecordingClient) -> str:
    return discord_client.interaction_responses()[-1]["data"]["content"]


def _embed(discord_client: RecordingClient) -> dict[str, object]:
    return discord_client.interaction_responses()[-1]["data"]["embeds"][0]


def _autocomplete(client: RecordingClient, current: str) -> AutocompleteInteraction:
    model = AutocompleteInteractionModel(
        id="1",
        application_id="2",
        type=InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE,
        token="tok",  # noqa: S106
        version=1,
        user=User.model_validate(user_json(id=str(ASKER_ID), username="asker")),
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
        (stored,) = session.exec(alive(Reminder)).all()
    assert (stored.content, stored.user_id, stored.timestamp) == ("feed the cat", ASKER_ID, NOW + timedelta(hours=2))
    epoch = int((NOW + timedelta(hours=2)).timestamp())
    embed = _embed(discord_client)
    assert f"<t:{epoch}:F>" in str(embed["description"])
    assert embed["color"] == int(Settings.created_color)


async def test_add_without_a_time_stores_nothing(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    cog, _ = _cog(engine)
    await Reminders.add.invoke(cog, make_interaction("reminder"), _options(reminder="never"))

    with Session(engine) as session:
        assert session.exec(alive(Reminder)).all() == []
    assert "Give me a time" in _reply(discord_client)


async def test_add_refuses_a_too_long_reminder(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    cog, _ = _cog(engine)
    await Reminders.add.invoke(cog, make_interaction("reminder"), _options(reminder="x" * 1001, minutes=5))

    with Session(engine) as session:
        assert session.exec(alive(Reminder)).all() == []
    assert "under 1000 characters" in _reply(discord_client)


async def test_repeat_stores_a_timed_reminder(engine: Engine, make_interaction: InteractionFactory) -> None:
    cog, _ = _cog(engine)
    await Reminders.repeat.invoke(cog, make_interaction("reminder"), _options(reminder="stretch", weeks=1))

    with Session(engine) as session:
        (stored,) = session.exec(alive(TimedReminder)).all()
    assert (stored.repeat_every, stored.timestamp) == (timedelta(weeks=1), NOW + timedelta(weeks=1))


async def test_send_due_dms_and_removes_one_off_reminders(engine: Engine) -> None:
    seed(
        engine,
        Reminder(content="due", user_id=ASKER_ID, timestamp=NOW - timedelta(minutes=1)),
        Reminder(content="later", user_id=ASKER_ID, timestamp=NOW + timedelta(minutes=1)),
    )
    cog, client = _cog(engine)

    assert await cog.send_due(NOW) == 1

    assert [sent.json["content"] for sent in client.requests_to("POST", SEND_DM)] == ["I'm here to remind you about\n`due`"]
    with Session(engine) as session:
        assert [reminder.content for reminder in session.exec(alive(Reminder))] == ["later"]


async def test_send_due_moves_repeating_reminders_on(engine: Engine) -> None:
    seed(engine, TimedReminder(content="water", user_id=ASKER_ID, timestamp=NOW, repeat_every=timedelta(days=1)))
    cog, client = _cog(engine)

    assert await cog.send_due(NOW) == 1

    assert len(client.requests_to("POST", SEND_DM)) == 1
    with Session(engine) as session:
        (timed,) = session.exec(alive(TimedReminder)).all()
    assert timed.timestamp == NOW + timedelta(days=1)


async def test_undeliverable_reminder_is_still_removed(engine: Engine) -> None:
    seed(engine, Reminder(content="due", user_id=ASKER_ID, timestamp=NOW))
    cog, client = _cog(engine)
    client.fail("POST", SEND_DM, ApiResponseError(code=50007, message="Cannot send messages to this user"))

    assert await cog.send_due(NOW) == 1

    with Session(engine) as session:
        assert session.exec(alive(Reminder)).all() == []


async def test_remove_by_autocomplete_value(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    (timed_id,) = seed(engine, TimedReminder(content="water", user_id=ASKER_ID, timestamp=NOW, repeat_every=timedelta(days=1)))
    cog, _ = _cog(engine)

    await Reminders.remove.invoke(cog, make_interaction("reminder"), _options(reminder=f"repeat:{timed_id}"))

    with Session(engine) as session:
        assert session.exec(alive(TimedReminder)).all() == []
    assert _embed(discord_client) == {"description": "Removed your reminder of\n`water`", "color": int(Settings.deleted_color)}


async def test_remove_by_typed_content(engine: Engine, make_interaction: InteractionFactory) -> None:
    seed(engine, Reminder(content="feed the cat", user_id=ASKER_ID, timestamp=NOW))
    cog, _ = _cog(engine)

    await Reminders.remove.invoke(cog, make_interaction("reminder"), _options(reminder="feed the cat"))

    with Session(engine) as session:
        assert session.exec(alive(Reminder)).all() == []


async def test_remove_leaves_other_users_reminders_alone(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    (other_id,) = seed(engine, Reminder(content="theirs", user_id=99, timestamp=NOW))
    cog, _ = _cog(engine)

    await Reminders.remove.invoke(cog, make_interaction("reminder"), _options(reminder=f"once:{other_id}"))
    await Reminders.remove.invoke(cog, make_interaction("reminder"), _options(reminder="theirs"))

    with Session(engine) as session:
        assert len(session.exec(alive(Reminder)).all()) == 1
    assert _reply(discord_client) == "You have no reminder like that."


async def test_autocomplete_suggests_own_matching_reminders(engine: Engine, discord_client: RecordingClient) -> None:
    once_id, timed_id, _ = seed(
        engine,
        Reminder(content="Feed the cat", user_id=ASKER_ID, timestamp=NOW),
        TimedReminder(content="clean the cat box", user_id=ASKER_ID, timestamp=NOW, repeat_every=timedelta(days=1)),
        Reminder(content="cat of someone else", user_id=99, timestamp=NOW),
    )
    seed(engine, Reminder(content="unrelated", user_id=ASKER_ID, timestamp=NOW))
    cog, _ = _cog(engine)

    choices = await cog.remove_choices(_autocomplete(discord_client, "CAT"), "CAT")

    assert [(choice.name, choice.value) for choice in choices] == [
        ("🔁 clean the cat box", f"repeat:{timed_id}"),
        ("Feed the cat", f"once:{once_id}"),
    ]


async def test_autocomplete_truncates_long_names(engine: Engine, discord_client: RecordingClient) -> None:
    seed(engine, Reminder(content="a" * 300, user_id=ASKER_ID, timestamp=NOW))
    cog, _ = _cog(engine)

    (choice,) = await cog.remove_choices(_autocomplete(discord_client, ""), "")

    assert len(choice.name) == 100


def _no_background_task(coroutine: Coroutine[object, object, None]) -> None:
    coroutine.close()


async def _loaded_cog(engine: Engine) -> tuple[Reminders, RecordingClient]:
    """Build a Reminders cog on ``engine`` and load it, without starting its background task."""
    cog, client = _cog(engine, loop=SimpleNamespace(create_task=_no_background_task))
    await cog.load()
    return cog, client


def _sent(client: RecordingClient) -> list[str]:
    return [sent.json["content"] for sent in client.requests_to("POST", SEND_DM)]


async def test_removed_reminder_is_not_sent_and_cannot_be_removed_again(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    (once_id,) = seed(engine, Reminder(content="feed the cat", user_id=ASKER_ID, timestamp=NOW))
    cog, client = _cog(engine)

    await Reminders.remove.invoke(cog, make_interaction("reminder"), _options(reminder=f"once:{once_id}"))
    await Reminders.remove.invoke(cog, make_interaction("reminder"), _options(reminder=f"once:{once_id}"))

    assert _reply(discord_client) == "You have no reminder like that."
    assert await cog.send_due(NOW) == 0
    assert _sent(client) == []
    assert await cog.remove_choices(_autocomplete(discord_client, ""), "") == []


async def test_delivered_reminder_is_soft_deleted_and_not_sent_again(engine: Engine) -> None:
    (once_id,) = seed(engine, Reminder(content="due", user_id=ASKER_ID, timestamp=NOW))
    cog, client = _cog(engine)

    assert await cog.send_due(NOW) == 1
    assert await cog.send_due(NOW + timedelta(minutes=1)) == 0

    assert len(_sent(client)) == 1
    with Session(engine) as session:
        delivered = session.get(Reminder, once_id)
    assert delivered is not None
    assert delivered.deleted_at is not None


async def test_reminders_in_old_tables_still_work_after_load(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    engine = sqlite_engine(tables=False)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE reminder (id INTEGER PRIMARY KEY, content VARCHAR NOT NULL, user_id BIGINT NOT NULL,"
                " timestamp DATETIME NOT NULL)",
            ),
        )
        connection.execute(
            text(
                "CREATE TABLE timedreminder (id INTEGER PRIMARY KEY, content VARCHAR NOT NULL, user_id BIGINT NOT NULL,"
                " timestamp DATETIME NOT NULL, repeat_every DATETIME NOT NULL)",
            ),
        )
        connection.execute(
            text(
                "INSERT INTO reminder VALUES (1, 'old due', 3, '2026-10-08 11:00:00.000000'),"
                " (2, 'old later', 3, '2026-10-09 12:00:00.000000')",
            ),
        )
    cog, client = await _loaded_cog(engine)

    assert await cog.send_due(NOW) == 1
    await Reminders.remove.invoke(cog, make_interaction("reminder"), _options(reminder="once:2"))
    await Reminders.repeat.invoke(cog, make_interaction("reminder"), _options(reminder="stretch", days=1))

    assert _sent(client) == [module.reminder_message("old due")]
    assert _embed(discord_client)["color"] == int(Settings.created_color)
    assert await cog.send_due(NOW + timedelta(days=2)) == 1
    assert _sent(client)[-1] == module.reminder_message("stretch")
