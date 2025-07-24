"""Module for importing calendar events from files and shared links."""
import datetime
from typing import cast

import aiohttp
import discord
from discord import app_commands
from icalendar import Calendar, Event
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.database.tables import Reminder as ReminderDb


class CalendarImport(GroupCog):
    """Cog for importing calendar events from files and shared links."""

    def parse_ics_content(self, ics_content: str) -> list[dict]:
        """Parse ICS content and return a list of event dictionaries."""
        try:
            calendar = Calendar.from_ical(ics_content)
            events = []

            for component in calendar.walk():
                if component.name == "VEVENT":
                    event = cast("Event", component)

                    # Extract event data
                    summary = str(event.get("summary", "Imported Event"))
                    start_time = event.get("dtstart")
                    description = str(event.get("description", ""))

                    if start_time:
                        # Handle both datetime and date objects
                        if hasattr(start_time.dt, "astimezone"):
                            # It's a datetime object
                            event_datetime = start_time.dt.astimezone(datetime.UTC)
                        else:
                            # It's a date object, convert to datetime at midnight UTC
                            event_datetime = datetime.datetime.combine(
                                start_time.dt,
                                datetime.time.min,
                                datetime.UTC,
                            )

                        events.append({
                            "summary": summary,
                            "datetime": event_datetime,
                            "description": description,
                        })
        except Exception:
            self.logger.exception("Error parsing ICS content")
            return []
        else:
            return events

    def create_reminders_from_events(self, events: list[dict], user_id: int) -> int:
        """Create reminder entries from calendar events."""
        created_count = 0

        for event in events:
            # Only create reminders for future events
            if event["datetime"] > datetime.datetime.now(datetime.UTC):
                content = f"{event['summary']}"
                if event["description"]:
                    content += f" - {event['description']}"

                self.session.add(ReminderDb(
                    content=content,
                    user_id=user_id,
                    timestamp=event["datetime"],
                ))
                created_count += 1

        self.session.commit()
        return created_count

    @app_commands.command(name="file", description="Import events from an uploaded calendar file (.ics)")
    async def slash_import_file(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment,
    ) -> None:
        """Import calendar events from an uploaded .ics file."""
        if not file.filename.lower().endswith(".ics"):
            await interaction.response.send_message(
                "Please upload a valid .ics calendar file.",
                ephemeral=True,
            )
            return

        if file.size > 1024 * 1024:  # 1MB limit
            await interaction.response.send_message(
                "File is too large. Please upload a file smaller than 1MB.",
                ephemeral=True,
            )
            return

        try:
            await interaction.response.defer(ephemeral=True)

            # Download and read the file content
            ics_content = await file.read()
            ics_str = ics_content.decode("utf-8")

            # Parse the calendar
            events = self.parse_ics_content(ics_str)

            if not events:
                await interaction.edit_original_response(
                    content="No events found in the calendar file.",
                )
                return

            # Create reminders from events
            created_count = self.create_reminders_from_events(events, interaction.user.id)

            if created_count == 0:
                await interaction.edit_original_response(
                    content="No future events found to import. All events may be in the past.",
                )
            else:
                await interaction.edit_original_response(
                    content=f"Successfully imported {created_count} future events from your calendar file. "
                           f"You will receive reminders for these events.",
                )

        except Exception:
            self.logger.exception("Error importing calendar file")
            await interaction.edit_original_response(
                content="Failed to import calendar file. Please ensure it's a valid .ics file.",
            )

    @app_commands.command(name="link", description="Import events from a shared calendar link")
    async def slash_import_link(
        self,
        interaction: discord.Interaction,
        url: str,
    ) -> None:
        """Import calendar events from a shared calendar URL."""
        # Basic URL validation
        if not url.startswith(("http://", "https://")):
            await interaction.response.send_message(
                "Please provide a valid URL starting with http:// or https://",
                ephemeral=True,
            )
            return

        try:
            await interaction.response.defer(ephemeral=True)

            # Download the calendar content
            headers = {
                "User-Agent": "Winter Dragon Bot Calendar Importer",
            }

            async with (
                aiohttp.ClientSession() as session,
                session.get(url, headers=headers, timeout=30) as response,
            ):
                response.raise_for_status()
                ics_content = await response.text()

            # Parse the calendar
            events = self.parse_ics_content(ics_content)

            if not events:
                await interaction.edit_original_response(
                    content="No events found in the calendar link.",
                )
                return

            # Create reminders from events
            created_count = self.create_reminders_from_events(events, interaction.user.id)

            if created_count == 0:
                await interaction.edit_original_response(
                    content="No future events found to import. All events may be in the past.",
                )
            else:
                await interaction.edit_original_response(
                    content=f"Successfully imported {created_count} future events from the calendar link. "
                           f"You will receive reminders for these events.",
                )

        except aiohttp.ClientError:
            self.logger.exception("Error downloading calendar from URL")
            await interaction.edit_original_response(
                content="Failed to download calendar from the provided URL. "
                       "Please check the URL and try again.",
            )
        except Exception:
            self.logger.exception("Error importing calendar from link")
            await interaction.edit_original_response(
                content="Failed to import calendar from link. "
                       "Please ensure it's a valid calendar URL.",
            )


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(CalendarImport(bot=bot))
