"""The /reminder command group: one-off and repeating reminders, sent as DMs by a background task."""

from datetime import timedelta
from typing import Annotated
lazy from typing import TYPE_CHECKING, override

from sqlmodel import Session, col
from wd_bot.commands import Describe, Length, Lookup
lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_db.extension._herogold import Repository
lazy from wd_discord import AutocompleteInteraction, is_network_error
lazy from wd_discord.timestamp import DiscordTime
lazy from wd_errors import Refused
lazy from wd_types.clock import utc_now

from winter_dragon.cogs.reminder.domain import Reminder, ReminderSettings, TimedReminder
lazy from winter_dragon.cogs.reminder.domain import (
    REMINDER_TABLES,
    delay_from,
    new_reminder,
    next_occurrence,
    owned_reminders,
    reminder_message,
)
lazy from winter_dragon.ui import CreatedEmbed, DeletedEmbed


if TYPE_CHECKING:
    lazy from collections.abc import Generator
    lazy from datetime import datetime

    lazy from wd_discord import Client, CommandInteraction
    lazy from wd_discord.interactions import ApplicationCommandOptionChoice

    lazy from winter_dragon.cogs.reminder.domain import AnyReminder


def reminder_choices(reminders: Generator[AnyReminder], current: str) -> Generator[ApplicationCommandOptionChoice]:
    """Yield a choice for each of ``reminders`` whose content contains ``current``, ignoring case."""
    needle = current.casefold()
    for reminder in reminders:
        if needle in reminder.content.casefold():
            label = "🔁 " if isinstance(reminder, TimedReminder) else ""
            name = f"{label}{reminder.content}"
            yield Lookup.choice(reminder, name)


async def send_reminder(client: Client, reminder: AnyReminder) -> bool:
    """DM ``reminder`` to its user; ``False`` when Discord refused it (e.g. their DMs are closed)."""
    message = await client.users.partial(reminder.user_id).send(reminder_message(reminder.content))
    return not is_network_error(message)


def delete_reminder(session: Session, reminder: AnyReminder) -> None:
    """Soft-delete ``reminder`` through the repository of its table; the caller commits."""
    if isinstance(reminder, TimedReminder):
        Repository[TimedReminder](session).delete(reminder)
    else:
        Repository[Reminder](session).delete(reminder)


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

        The due reminders are read in one scope. Each is then DMed with no session open and settled in its own short
        scope, so a crash repeats at most the DM in flight instead of every DM of the run. A reminder that couldn't be
        delivered is handled the same way, rather than retried every check forever.
        """
        with Session(self.engine) as session:
            due: list[AnyReminder] = [
                *Repository[Reminder](session).qs().where(col(Reminder.timestamp) <= now).all(),
                *Repository[TimedReminder](session).qs().where(col(TimedReminder.timestamp) <= now).all(),
            ]
        for reminder in due:
            await self._deliver(reminder)
            with Session(self.engine) as session:
                self._settle(session, reminder, now)
                session.commit()
        return len(due)

    @staticmethod
    def _settle(session: Session, delivered: AnyReminder, now: datetime) -> None:
        """Soft-delete the delivered reminder, or move a repeating one to its next time; it may be gone already."""
        stored = session.get(type(delivered), delivered.id)
        if stored is None or stored.deleted_at is not None:
            return
        if isinstance(stored, TimedReminder) and stored.repeat_every > timedelta(0):
            stored.timestamp = next_occurrence(stored.timestamp, stored.repeat_every, now)
            session.add(stored)
        else:
            delete_reminder(session, stored)

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
        message = f"On {due}{repeat} I will remind you of\n`{content}`\nUse {self.mention(self.remove)} to cancel it."
        await interaction.respond(embeds=[CreatedEmbed(description=message)], ephemeral=True)

    async def _add(
        self,
        interaction: CommandInteraction,
        content: str,
        delay: timedelta,
        *,
        repeats: bool,
    ) -> None:
        """Store the invoking user's reminder of ``content``, due after ``delay`` and repeating so if ``repeats``."""
        user = interaction.user
        if user is None:
            return
        now = utc_now()
        reminder = new_reminder(content, user.id, now + delay, now, delay if repeats else None)
        if isinstance(reminder, Refused):
            raise reminder
        await self._store(interaction, reminder)

    @Cog.command(name="add", description="Get reminded of something once, after the given time")
    async def add(
        self,
        interaction: CommandInteraction,
        reminder: Annotated[
            str,
            Describe("The text to remind you of"),
            Length(max_length=ReminderSettings.max_content_length),
        ],
        minutes: Annotated[int, Describe("The number of minutes to wait before reminding you")] = 0,
        hours: Annotated[int, Describe("The number of hours to wait before reminding you")] = 0,
        days: Annotated[int, Describe("The number of days to wait before reminding you")] = 0,
    ) -> None:
        """Remind the invoking user of ``reminder`` once, after the given time."""
        await self._add(interaction, reminder, delay_from(minutes=minutes, hours=hours, days=days), repeats=False)

    @Cog.command(name="repeat", description="Get reminded of something over and over, every given time")
    async def repeat(  # noqa: PLR0913 - one option per time unit
        self,
        interaction: CommandInteraction,
        reminder: Annotated[
            str,
            Describe("The text to remind you of"),
            Length(max_length=ReminderSettings.max_content_length),
        ],
        minutes: Annotated[int, Describe("The number of minutes before reminding you again")] = 0,
        hours: Annotated[int, Describe("The number of hours before reminding you again")] = 0,
        days: Annotated[int, Describe("The number of days before reminding you again")] = 0,
        weeks: Annotated[int, Describe("The number of weeks before reminding you again")] = 0,
    ) -> None:
        """Remind the invoking user of ``reminder`` every given time, starting one interval from now."""
        every = delay_from(minutes=minutes, hours=hours, days=days, weeks=weeks)
        await self._add(interaction, reminder, every, repeats=True)

    async def remove_choices(self, interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]:
        """Suggest the invoking user's reminders whose content contains what they typed."""
        user = interaction.user
        if user is None:
            return []
        with Session(self.bind) as session:
            return list(reminder_choices(owned_reminders(session, user.id), current))

    @Cog.command(name="remove", description="Cancel one of your reminders")
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
            delete_reminder(session, reminder)
            session.commit()
        await interaction.respond(embeds=[DeletedEmbed(description=f"Removed your reminder of\n`{content}`")], ephemeral=True)
