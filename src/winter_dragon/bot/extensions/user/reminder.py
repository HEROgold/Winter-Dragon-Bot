"""Module for reminding users of things."""

import datetime

import discord
from discord import app_commands
from discord.app_commands import Choice
from sqlmodel import select

from winter_dragon.bot.core.config import Config
from winter_dragon.bot.core.tasks import loop
from winter_dragon.database.tables import Reminder as ReminderDb
from winter_dragon.database.tables.reminder import TimedReminder
from winter_dragon.discord.cogs import Cog


WEEKS_IN_MONTH = 4


class Reminder(Cog, auto_load=True):
    """Cog for setting reminders."""

    reminder_check_interval = Config(60)

    async def cog_load(self) -> None:
        """Load the cog."""
        await super().cog_load()
        # Configure loop interval from config
        self.send_reminder.change_interval(seconds=self.reminder_check_interval)
        self.send_reminder.start()

    @loop()
    async def send_reminder(self) -> None:
        """Task to send reminders to users."""
        results = self.session.exec(
            select(ReminderDb).where(ReminderDb.timestamp <= datetime.datetime.now(datetime.UTC)),
        )
        if not results.all():
            return
        for i in results.all():
            self.logger.debug(f"sending reminder {i.content=} to {i.user_id=}")
            member = discord.utils.get(self.bot.users, id=i.user_id)
            if member is None:
                self.logger.debug(f"member {i.user_id} not found")
                self.session.delete(i)
                continue
            dm = await member.create_dm()
            await dm.send(f"I'm here to remind you about\n`{i.content}`")
            self.session.delete(i)
        self.session.commit()

    @send_reminder.before_loop
    async def before_send_reminder(self) -> None:
        """Wait until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()

    @app_commands.command(name="remind", description="Set a reminder for yourself!")
    async def slash_reminder(
        self,
        interaction: discord.Interaction,
        reminder: str,
        minutes: int = 0,
        hours: int = 0,
        days: int = 0,
    ) -> None:
        """Set a reminder for the user."""
        if minutes + hours + days == 0:
            await interaction.response.send_message("Give me a time so i can remind you!", ephemeral=True)
            return

        seconds = minutes * 60 + hours * 3600 + days * 86400
        member = interaction.user
        time = datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=seconds)
        self.session.add(
            ReminderDb(
                content=reminder,
                user_id=member.id,
                timestamp=time,
            ),
        )
        self.session.commit()
        epoch = int(time.timestamp())
        await interaction.response.send_message(f"at <t:{epoch}> I will remind you of \n`{reminder}`", ephemeral=True)

    @app_commands.command(name="timed_reminder", description="Set a reminder that repeats every so often.")
    async def slash_repeat_reminder(  # noqa: PLR0913
        self,
        interaction: discord.Interaction,
        reminder: str,
        minutes: int = 0,
        hours: int = 0,
        days: int = 0,
        weeks: int = 0,
        years: int = 0,
    ) -> None:
        """Set a repeating reminder for the user."""
        if minutes + hours + days + weeks + years == 0:
            await interaction.response.send_message("Give me a time so i can remind you!", ephemeral=True)
            return

        repeat = datetime.timedelta(minutes=minutes, hours=hours, days=days, weeks=weeks + years * WEEKS_IN_MONTH)
        member = interaction.user
        time = datetime.datetime.now(datetime.UTC) + repeat
        self.session.add(
            TimedReminder(
                content=reminder,
                user_id=member.id,
                timestamp=time,
                repeat_every=repeat,
            ),
        )
        self.session.commit()
        epoch = int(time.timestamp())
        await interaction.response.send_message(f"at <t:{epoch}> I will remind you of \n`{reminder}`", ephemeral=True)

    @app_commands.command(name="remove_reminder")
    async def slash_remove_reminder(self, interaction: discord.Interaction, reminder: str) -> None:
        """Let a user remove any of their reminders."""

    @slash_remove_reminder.autocomplete("reminder")
    async def autocomplete_active_reminders(self, interaction: discord.Interaction, current: str) -> list[Choice]:
        """Autocomplete active reminders for the user."""
        query = select(ReminderDb, TimedReminder).where(
            interaction.user.id in (ReminderDb.user_id, TimedReminder.user_id),
            current.casefold() in ReminderDb.content.casefold() or current.casefold() in TimedReminder.content.casefold(),
        )

        return [
            Choice(name=reminder.content, value=reminder.id)
            for reminder in self.session.exec(query).all()
            if reminder.user_id == interaction.user.id
        ]
