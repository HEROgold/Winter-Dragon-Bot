"""The /reminder command group: one-off and repeating reminders, sent as DMs by a background task."""

from datetime import datetime, timedelta
from typing import Annotated
lazy from typing import TYPE_CHECKING, ClassVar, override

from sqlalchemy import BigInteger
from sqlmodel import Field, Session, col
from wd_bot.commands import Describe, Lookup
from wd_db.extension.columns import AwareDateTime
from wd_db.extension.lifecycle import LifecycleModel, Ownership
lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_db.extension.lifecycle import alive, alive_by_id, create_or_restore, owned_by, soft_delete
lazy from wd_discord import AutocompleteInteraction, is_network_error
lazy from wd_discord.interactions import MAX_CHOICE_NAME_LENGTH, ApplicationCommandOptionChoice
lazy from wd_discord.timestamp import DiscordTime
lazy from wd_errors import Refused
lazy from wd_types.clock import utc_now

lazy from winter_dragon.config import CogConfig
lazy from winter_dragon.ui import CreatedEmbed, DeletedEmbed


if TYPE_CHECKING:
    lazy from collections.abc import Generator

    lazy from wd_discord import Client, CommandInteraction


SECONDS_PER_UNIT = {"minutes": 60, "hours": 3600, "days": 86400, "weeks": 604800}


class ReminderSettings:
    """Settings for reminders, in their ``cogs.ini`` section."""

    check_interval = CogConfig(60)
    """Seconds between two looks for due reminders; a reminder arrives at most this late."""
    max_delay_days = CogConfig(3650)
    """Days ahead a reminder may be set, or a repeating one may wait between reminders."""
    max_content_length = CogConfig(1000)
    """The longest reminder text accepted, keeping the reminder DM well within Discord's message limit."""


class ReminderBase(LifecycleModel):
    """What one-off and repeating reminders share; ``user_id`` is the Discord user to remind, who owns it."""

    ownership: ClassVar[Ownership] = Ownership(member="user_id")

    content: str
    user_id: int = Field(sa_type=BigInteger, index=True)
    timestamp: datetime = Field(sa_type=AwareDateTime)
    """When the reminder is due next."""


class Reminder(ReminderBase, table=True):
    """A reminder sent once, then soft-deleted."""


class TimedReminder(ReminderBase, table=True):
    """A reminder sent again every :attr:`repeat_every`, until removed."""

    repeat_every: timedelta


type AnyReminder = Reminder | TimedReminder

REMINDER_TABLES = (Reminder, TimedReminder)
"""Every table the reminder cog creates on load."""


def delay_from(**amounts: int) -> timedelta | None:
    """Return the delay made of ``amounts`` per unit (``minutes=5, hours=1``), or ``None`` if it's out of range.

    The range is (0, :attr:`ReminderSettings.max_delay_days`].

    Adds whole seconds as integers first, so an absurd amount is refused rather than overflowing ``timedelta``.
    """
    seconds = sum(SECONDS_PER_UNIT[unit] * amount for unit, amount in amounts.items())
    if not 0 < seconds <= timedelta(days=ReminderSettings.max_delay_days).total_seconds():
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


def owned_reminders(session: Session, user_id: int) -> Generator[AnyReminder]:
    """Yield every reminder of the user ``user_id``: repeating ones first, then one-off ones by when they're due."""
    yield from session.exec(owned_by(TimedReminder, member=user_id))
    yield from session.exec(owned_by(Reminder, member=user_id).order_by(col(Reminder.timestamp)))


def reminder_choices(reminders: Generator[AnyReminder], current: str) -> Generator[ApplicationCommandOptionChoice]:
    """Yield a choice for each of ``reminders`` whose content contains ``current``, ignoring case."""
    needle = current.casefold()
    for reminder in reminders:
        if needle in reminder.content.casefold():
            label = "🔁 " if isinstance(reminder, TimedReminder) else ""
            name = f"{label}{reminder.content}"
            if len(name) > MAX_CHOICE_NAME_LENGTH:
                name = name[: MAX_CHOICE_NAME_LENGTH - 1] + "…"
            yield Lookup.choice(reminder, name)


async def send_reminder(client: Client, reminder: AnyReminder) -> bool:
    """DM ``reminder`` to its user; ``False`` when Discord refused it (e.g. their DMs are closed)."""
    message = await client.users.partial(reminder.user_id).send(reminder_message(reminder.content))
    return not is_network_error(message)


class Reminders(GroupCog, name="reminder", description="Set reminders for yourself"):
    """Stores reminders and DMs them to their users when due, from a background task."""

    @override
    async def load(self) -> None:
        """Create the reminder tables if missing; the bot then starts :meth:`deliver_due`."""
        self.create_tables(*REMINDER_TABLES)

    @Cog.periodic(seconds=lambda: ReminderSettings.check_interval)
    async def deliver_due(self) -> None:
        """Send the reminders due now; the bot repeats it every :attr:`ReminderSettings.check_interval` seconds."""
        await self.send_due(utc_now())

    async def send_due(self, now: datetime) -> int:
        """DM every reminder due at ``now``; soft-delete one-off ones and move repeating ones on. Return how many were due.

        A reminder that couldn't be delivered is handled the same way, rather than retried every check forever.
        """
        due = 0
        with Session(self.bind) as session:
            for reminder in session.exec(alive(Reminder).where(Reminder.timestamp <= now)).all():
                await self._deliver(reminder)
                soft_delete(session, reminder)
                session.commit()
                due += 1
            for timed in session.exec(alive(TimedReminder).where(TimedReminder.timestamp <= now)).all():
                await self._deliver(timed)
                if timed.repeat_every > timedelta(0):
                    timed.timestamp = next_occurrence(timed.timestamp, timed.repeat_every, now)
                    session.add(timed)
                else:
                    soft_delete(session, timed)
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
            create_or_restore(session, reminder)
            session.commit()
        repeat = " and then every so often" if isinstance(reminder, TimedReminder) else ""
        message = f"On {due}{repeat} I will remind you of\n`{content}`\nUse {self.mention(self.remove)} to cancel it."
        await interaction.respond(embeds=[CreatedEmbed(description=message)], ephemeral=True)

    @staticmethod
    def _validated(content: str, delay: timedelta | None) -> timedelta:
        """Return ``delay`` if a new reminder of ``content`` may wait that long; refuse saying why not otherwise."""
        if delay is None:
            days = ReminderSettings.max_delay_days
            msg = f"Give me a time between 1 minute and {days} days from now, so I can remind you!"
            raise Refused(msg)
        if len(content) > ReminderSettings.max_content_length:
            msg = f"Keep your reminder under {ReminderSettings.max_content_length} characters."
            raise Refused(msg)
        return delay

    @Cog.command(name="add", description="Get reminded of something once, after the given time")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def add(
        self,
        interaction: CommandInteraction,
        reminder: Annotated[str, Describe("The text to remind you of")],
        minutes: Annotated[int, Describe("The number of minutes to wait before reminding you")] = 0,
        hours: Annotated[int, Describe("The number of hours to wait before reminding you")] = 0,
        days: Annotated[int, Describe("The number of days to wait before reminding you")] = 0,
    ) -> None:
        """Remind the invoking user of ``reminder`` once, after the given time."""
        user = interaction.user
        if user is None:
            return
        delay = self._validated(reminder, delay_from(minutes=minutes, hours=hours, days=days))
        await self._store(interaction, Reminder(content=reminder, user_id=int(user.id), timestamp=utc_now() + delay))

    @Cog.command(name="repeat", description="Get reminded of something over and over, every given time")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def repeat(  # noqa: PLR0913 - one option per time unit
        self,
        interaction: CommandInteraction,
        reminder: Annotated[str, Describe("The text to remind you of")],
        minutes: Annotated[int, Describe("The number of minutes before reminding you again")] = 0,
        hours: Annotated[int, Describe("The number of hours before reminding you again")] = 0,
        days: Annotated[int, Describe("The number of days before reminding you again")] = 0,
        weeks: Annotated[int, Describe("The number of weeks before reminding you again")] = 0,
    ) -> None:
        """Remind the invoking user of ``reminder`` every given time, starting one interval from now."""
        user = interaction.user
        if user is None:
            return
        every = self._validated(reminder, delay_from(minutes=minutes, hours=hours, days=days, weeks=weeks))
        timed = TimedReminder(content=reminder, user_id=int(user.id), timestamp=utc_now() + every, repeat_every=every)
        await self._store(interaction, timed)

    async def remove_choices(self, interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]:
        """Suggest the invoking user's reminders whose content contains what they typed."""
        user = interaction.user
        if user is None:
            return []
        with Session(self.bind) as session:
            return list(reminder_choices(owned_reminders(session, int(user.id)), current))

    @Cog.command(name="remove", description="Cancel one of your reminders")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def remove(
        self,
        interaction: CommandInteraction,
        reminder: Annotated[Reminder | TimedReminder, Lookup(remove_choices), Describe("The reminder to remove")],
    ) -> None:
        """Remove the invoking user's ``reminder``; refuse another member's."""
        user = interaction.user
        if user is None:
            return
        if reminder.user_id != int(user.id):
            msg = "That isn't your reminder; pick one from the list."
            raise Refused(msg)
        content = reminder.content
        with Session(self.bind) as session:
            soft_delete(session, reminder)
            session.commit()
        await interaction.respond(embeds=[DeletedEmbed(description=f"Removed your reminder of\n`{content}`")], ephemeral=True)
