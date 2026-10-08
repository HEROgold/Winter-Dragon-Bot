"""The /reminder command group: one-off and repeating reminders, sent as DMs by a background task."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
lazy import asyncio
lazy from typing import TYPE_CHECKING, override

from sqlalchemy import BigInteger
from sqlmodel import Field, Session, col, select
from wd_db.extension.columns import AwareDateTime
from wd_db.extension.model import SQLModel
lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_config.reminder import ReminderSettings
lazy from wd_discord import AutocompleteInteraction, is_network_error
lazy from wd_discord.interactions import ApplicationCommandOptionChoice
lazy from wd_discord.timestamp import DiscordTime


if TYPE_CHECKING:
    lazy from collections.abc import Generator

    lazy from wd_discord import Client, CommandInteraction


MAX_DELAY = timedelta(days=3650)
"""How far ahead a reminder may be set, or how long a repeating one may wait between reminders."""
MAX_CONTENT_LENGTH = 1000
"""The longest reminder text accepted, keeping the reminder DM well within Discord's message limit."""
MAX_CHOICE_NAME_LENGTH = 100
"""Discord's limit on the length of an autocomplete choice's name."""
SECONDS_PER_UNIT = {"minutes": 60, "hours": 3600, "days": 86400, "weeks": 604800}


class ReminderBase(SQLModel):
    """What one-off and repeating reminders share; ``user_id`` is the Discord user to remind."""

    content: str
    user_id: int = Field(sa_type=BigInteger, index=True)
    timestamp: datetime = Field(sa_type=AwareDateTime)
    """When the reminder is due next."""


class Reminder(ReminderBase, table=True):
    """A reminder sent once, then removed."""


class TimedReminder(ReminderBase, table=True):
    """A reminder sent again every :attr:`repeat_every`, until removed."""

    repeat_every: timedelta


type AnyReminder = Reminder | TimedReminder

REMINDER_TABLES = (Reminder, TimedReminder)
"""Every table the reminder cog creates on load."""
CHOICE_PREFIXES: dict[type[AnyReminder], str] = {Reminder: "once", TimedReminder: "repeat"}
"""How an autocomplete choice's value says which table its reminder is in."""


def utc_now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(UTC)


def delay_from(**amounts: int) -> timedelta | None:
    """Return the delay made of ``amounts`` per unit (``minutes=5, hours=1``), or ``None`` if it's not in (0, MAX_DELAY].

    Adds whole seconds as integers first, so an absurd amount is refused rather than overflowing ``timedelta``.
    """
    seconds = sum(SECONDS_PER_UNIT[unit] * amount for unit, amount in amounts.items())
    if not 0 < seconds <= MAX_DELAY.total_seconds():
        return None
    return timedelta(seconds=seconds)


def next_occurrence(due: datetime, repeat_every: timedelta, now: datetime) -> datetime:
    """Return the first time after ``now`` that a reminder due at ``due`` and repeating every ``repeat_every`` is due.

    Skips the occurrences missed while the bot was offline, instead of sending each of them.
    """
    missed = (now - due) // repeat_every if now >= due else -1
    return due + repeat_every * (missed + 1)


def reminder_message(content: str) -> str:
    """Return the DM reminding someone of ``content``."""
    return f"I'm here to remind you about\n`{content}`"


def choice_value(reminder: AnyReminder) -> str:
    """Return the autocomplete value naming ``reminder``: its table and ID, like ``repeat:12``."""
    return f"{CHOICE_PREFIXES[type(reminder)]}:{reminder.id}"


def owned_reminders(session: Session, user_id: int) -> Generator[AnyReminder]:
    """Yield every reminder of the user ``user_id``: repeating ones first, then one-off ones by when they're due."""
    yield from session.exec(select(TimedReminder).where(TimedReminder.user_id == user_id))
    yield from session.exec(select(Reminder).where(Reminder.user_id == user_id).order_by(col(Reminder.timestamp)))


def find_reminder(session: Session, user_id: int, reminder: str) -> AnyReminder | None:
    """Return the reminder of the user ``user_id`` that ``reminder`` names.

    That's a :func:`choice_value` picked from autocomplete, or else typed text matching a reminder's content.
    """
    prefix, _, reminder_id = reminder.partition(":")
    for model, model_prefix in CHOICE_PREFIXES.items():
        if prefix == model_prefix and reminder_id.isdigit():
            found = session.get(model, int(reminder_id))
            if found is not None and found.user_id == user_id:
                return found
    return next((owned for owned in owned_reminders(session, user_id) if owned.content == reminder), None)


def reminder_choices(reminders: Generator[AnyReminder], current: str) -> Generator[ApplicationCommandOptionChoice]:
    """Yield a choice for each of ``reminders`` whose content contains ``current``, ignoring case."""
    needle = current.casefold()
    for reminder in reminders:
        if needle in reminder.content.casefold():
            label = "🔁 " if isinstance(reminder, TimedReminder) else ""
            name = f"{label}{reminder.content}"
            if len(name) > MAX_CHOICE_NAME_LENGTH:
                name = name[: MAX_CHOICE_NAME_LENGTH - 1] + "…"
            yield ApplicationCommandOptionChoice(name=name, value=choice_value(reminder))


async def send_reminder(client: Client, reminder: AnyReminder) -> bool:
    """DM ``reminder`` to its user; ``False`` when Discord refused it (e.g. their DMs are closed)."""
    message = await client.users.partial(reminder.user_id).send(reminder_message(reminder.content))
    return not is_network_error(message)


class Reminders(GroupCog, name="reminder", description="Set reminders for yourself"):
    """Stores reminders and DMs them to their users when due, from a background task."""

    _task: asyncio.Task[None] | None = None

    @override
    async def load(self) -> None:
        """Create the reminder tables if missing, then start the background task sending due reminders."""
        self.create_tables(*REMINDER_TABLES)
        self._task = self.bot.loop.create_task(self._run())

    @override
    async def unload(self) -> None:
        """Stop the background task."""
        if self._task is not None:
            self._task.cancel()
            self._task = None
        await super().unload()

    async def _run(self) -> None:
        """Send due reminders every :attr:`ReminderSettings.check_interval` seconds, forever."""
        while True:
            try:
                await self.send_due(utc_now())
            except Exception:
                self.logger.exception(t"Sending due reminders failed")
            await asyncio.sleep(ReminderSettings.check_interval)

    async def send_due(self, now: datetime) -> int:
        """DM every reminder due at ``now``; remove one-off ones and move repeating ones on. Return how many were due.

        A reminder that couldn't be delivered is handled the same way, rather than retried every check forever.
        """
        due = 0
        with Session(self.bind) as session:
            for reminder in session.exec(select(Reminder).where(Reminder.timestamp <= now)).all():
                await self._deliver(reminder)
                session.delete(reminder)
                session.commit()
                due += 1
            for timed in session.exec(select(TimedReminder).where(TimedReminder.timestamp <= now)).all():
                await self._deliver(timed)
                if timed.repeat_every > timedelta(0):
                    timed.timestamp = next_occurrence(timed.timestamp, timed.repeat_every, now)
                    session.add(timed)
                else:
                    session.delete(timed)
                session.commit()
                due += 1
        return due

    async def _deliver(self, reminder: AnyReminder) -> None:
        if not await send_reminder(self.bot.client, reminder):
            self.logger.warning(t"Could not DM reminder {reminder.id} to {reminder.user_id}")

    async def _store(self, interaction: CommandInteraction, reminder: AnyReminder) -> None:
        """Save ``reminder``, then tell the invoking user when it's due."""
        due = DiscordTime(reminder.timestamp).with_relative()
        content = reminder.content
        with Session(self.bind) as session:
            session.add(reminder)
            session.commit()
        repeat = " and then every so often" if isinstance(reminder, TimedReminder) else ""
        await interaction.respond(
            f"On {due}{repeat} I will remind you of\n`{content}`\nUse {self.mention(self.remove)} to cancel it.",
            ephemeral=True,
        )

    async def _validated(self, interaction: CommandInteraction, content: str, delay: timedelta | None) -> timedelta | None:
        """Return ``delay`` if a new reminder of ``content`` may wait that long; else tell the invoking user why not."""
        if delay is None:
            message = f"Give me a time between 1 minute and {MAX_DELAY.days} days from now, so I can remind you!"
        elif len(content) > MAX_CONTENT_LENGTH:
            message = f"Keep your reminder under {MAX_CONTENT_LENGTH} characters."
        else:
            return delay
        await interaction.respond(message, ephemeral=True)
        return None

    @Cog.command(name="add", description="Get reminded of something once, after the given time")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def add(
        self,
        interaction: CommandInteraction,
        reminder: str,
        minutes: int = 0,
        hours: int = 0,
        days: int = 0,
    ) -> None:
        """Remind the invoking user of ``reminder`` once, after the given time."""
        user = interaction.user
        delay = delay_from(minutes=minutes, hours=hours, days=days)
        if user is None or (delay := await self._validated(interaction, reminder, delay)) is None:
            return
        await self._store(interaction, Reminder(content=reminder, user_id=int(user.id), timestamp=utc_now() + delay))

    @Cog.command(name="repeat", description="Get reminded of something over and over, every given time")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def repeat(  # noqa: PLR0913 - one option per time unit
        self,
        interaction: CommandInteraction,
        reminder: str,
        minutes: int = 0,
        hours: int = 0,
        days: int = 0,
        weeks: int = 0,
    ) -> None:
        """Remind the invoking user of ``reminder`` every given time, starting one interval from now."""
        user = interaction.user
        every = delay_from(minutes=minutes, hours=hours, days=days, weeks=weeks)
        if user is None or (every := await self._validated(interaction, reminder, every)) is None:
            return
        timed = TimedReminder(content=reminder, user_id=int(user.id), timestamp=utc_now() + every, repeat_every=every)
        await self._store(interaction, timed)

    @Cog.command(name="remove", description="Cancel one of your reminders")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def remove(self, interaction: CommandInteraction, reminder: str) -> None:
        """Remove the invoking user's reminder named by ``reminder``."""
        user = interaction.user
        if user is None:
            return
        with Session(self.bind) as session:
            found = find_reminder(session, int(user.id), reminder)
            content = None if found is None else found.content
            if found is not None:
                session.delete(found)
                session.commit()
        if content is None:
            await interaction.respond("You have no reminder like that.", ephemeral=True)
            return
        await interaction.respond(f"Removed your reminder of\n`{content}`", ephemeral=True)

    @remove.autocomplete("reminder")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def remove_choices(self, interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]:
        """Suggest the invoking user's reminders whose content contains what they typed."""
        user = interaction.user
        if user is None:
            return []
        with Session(self.bind) as session:
            return list(reminder_choices(owned_reminders(session, int(user.id)), current))
