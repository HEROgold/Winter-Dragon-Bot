"""Module for bot activity and status management."""

import random
from typing import Unpack

import discord
from discord import ActivityType, Status, app_commands
from discord.ext import commands

from winter_dragon.bot.core.cogs import BotArgs, GroupCog
from winter_dragon.bot.core.config import Config
from winter_dragon.bot.core.settings import Settings
from winter_dragon.bot.core.tasks import loop


INVALID_RNG_STATUS = [
    Status.invisible,
    Status.offline,
]
INVALID_RNG_ACTIVITY = [
    ActivityType.custom,
    ActivityType.unknown,
]


@app_commands.guilds(Settings.support_guild_id)
class BotActivity(GroupCog, auto_load=True):
    """Cog to control the bot's activity and status."""

    random_activity = Config(default=True)
    periodic_change = Config(default=True)
    periodic_time = Config(180)

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the bot activity cog."""
        super().__init__(**kwargs)

    async def cog_load(self) -> None:
        """When the cog loads, start activity statuses."""
        await super().cog_load()
        # Configure loop intervals from config
        self.activity_switch.change_interval(seconds=self.periodic_time)
        self.activity_switch.start()

    @loop()
    async def activity_switch(self) -> None:
        """Switch the bot's activity and status periodically. Uses activity.periodic_time config."""
        if not self.random_activity:
            self.activity_switch.stop()
            return
        status, activity = self.get_random_activity()

        await self.bot.change_presence(status=status, activity=activity)
        self.logger.debug(f"Activity and status set to {activity}")
        if not self.periodic_change:
            self.activity_switch.stop()
            return

    def get_random_activity(self) -> tuple[discord.Status, discord.Activity]:
        """Get a random valid activity and status."""
        status = random.choice([i for i in Status if i not in INVALID_RNG_STATUS])  # noqa: S311
        activity_type = random.choice([i for i in ActivityType if i not in INVALID_RNG_ACTIVITY])  # noqa: S311

        activity = discord.Activity(
            type=activity_type,
            name=random.choice(Settings.bot_status_messages),  # noqa: S311
        )
        return status, activity

    async def _start_randomizer(self, interaction: discord.Interaction) -> None:
        self.periodic_change = True
        self.logger.info(f"Turned on periodic activity change by {interaction.user}")
        await interaction.response.send_message("I will randomly change my status and activity", ephemeral=True)
        self.activity_switch.start()

    @commands.is_owner()
    @app_commands.command(name="activity", description="change bot activity")
    async def slash_bot_activity(
        self,
        interaction: discord.Interaction,
        status: str,
        activity: str,
        msg: str = "",
    ) -> None:
        """Change the bot's activity and status."""
        status = status.lower()
        activity = activity.lower()
        statuses = ", ".join([i.name for i in Status])
        activities = ", ".join([i.name for i in ActivityType])

        if status not in [i.name.lower() for i in Status]:
            await interaction.response.send_message(f"Status not found, can only be\n{statuses}", ephemeral=True)
            return

        if activity not in [i.name.lower() for i in ActivityType]:
            await interaction.response.send_message(f"Activity not found, can only be\n{activities}", ephemeral=True)
            return

        if status == "random" and activity == "random":
            await self._start_randomizer(interaction)
            return

        if status == "random" or activity == "random":
            await interaction.response.send_message(
                "Both status and activity need to be random or not chosen.",
                ephemeral=True,
            )
            return

        status_attr = discord.Status[status] or discord.Status.online
        activity_type = discord.ActivityType[activity] or discord.ActivityType.playing
        activity_obj = discord.Activity(type=activity_type, name=msg)

        await self.bot.change_presence(status=status_attr, activity=activity_obj)
        await interaction.response.send_message("Updated my activity!", ephemeral=True)
        self.logger.debug(f"Activity and status set to {activity} by {interaction.user}")
        self.logger.info(f"Turned off periodic activity change by {interaction.user}")

        self.periodic_change = False
        self.activity_switch.stop()
        return

    @slash_bot_activity.autocomplete("status")
    async def activity_autocomplete_status(
        self,
        interaction: discord.Interaction,  # noqa: ARG002
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for the status command."""
        statuses = [i.name for i in Status]
        return [app_commands.Choice(name=stat, value=stat) for stat in statuses if current.lower() in stat.lower()] or [
            app_commands.Choice(name=stat, value=stat) for stat in statuses
        ]

    @slash_bot_activity.autocomplete("activity")
    async def activity_autocomplete_activity(
        self,
        interaction: discord.Interaction,  # noqa: ARG002
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for the activity command."""
        activities = [i.name for i in ActivityType]
        return [
            app_commands.Choice(name=activity, value=activity) for activity in activities if current.lower() in activity.lower()
        ] or [app_commands.Choice(name=activity, value=activity) for activity in activities]

    @activity_switch.before_loop
    async def before_update(self) -> None:
        """Wait until the bot is ready before starting the loops."""
        await self.bot.wait_until_ready()
