"""Make discord Events, marking upcoming voting and tournament start times.

This module integrates with the Riot Clash API to fetch tournament dates
and automatically creates Discord scheduled events for them if they don't
already exist in the guild.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Unpack

import discord
from discord import app_commands
from discord.ext import tasks
from herogold.log import LoggerMixin

from winter_dragon.bot.core.cogs import BotArgs, Cog
from winter_dragon.bot.extensions.games.clash_settings import ClashSettings
from winter_dragon.bot.extensions.games.riot_clash_api import (
    DiscordClashEventManager,
    Platform,
    RiotClashAPIError,
    RiotClashClient,
)


if TYPE_CHECKING:
    from discord.ext import commands

# Constants
MAX_EVENTS_DISPLAY = 10  # Maximum number of events to display in list


class TournamentEventManager(Cog, LoggerMixin):
    """Manages Discord scheduled events for tournaments.

    Automatically syncs Clash tournament schedules to Discord events
    and provides commands to manually manage tournament events.
    """

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the tournament event manager.

        Args:
        ----
            **kwargs: Cog initialization arguments including bot instance

        """
        super().__init__(**kwargs)

        # Initialize Riot Clash API client
        api_key = ClashSettings.riot_api_key
        if api_key:
            self.clash_client = RiotClashClient(api_key)
            self.event_manager = DiscordClashEventManager(self.bot)
            self.logger.info("TournamentEventManager initialized with Riot API")
        else:
            self.clash_client = None
            self.event_manager = None
            self.logger.warning("RIOT_API_KEY not configured. Tournament event features will be unavailable.")

        # Track guilds with auto-sync enabled
        self.auto_sync_guilds: dict[int, Platform] = {}  # guild_id -> platform

    async def cog_load(self) -> None:
        """Start background tasks when cog loads."""
        self.logger.info("TournamentEventManager cog loading...")
        if self.clash_client and self.event_manager:
            self.auto_sync_task.start()
            self.logger.info("Auto-sync task started successfully")
        else:
            self.logger.warning("Auto-sync task not started - Clash API unavailable")
        self.logger.info("TournamentEventManager cog loaded")

    async def cog_unload(self) -> None:
        """Stop background tasks when cog unloads."""
        self.logger.info("TournamentEventManager cog unloading...")
        if self.auto_sync_task.is_running():
            self.auto_sync_task.cancel()
            self.logger.info("Auto-sync task stopped")

        if self.clash_client:
            await self.clash_client.close()
            self.logger.info("Clash client closed")

        self.logger.info("TournamentEventManager cog unloaded")

    @tasks.loop(hours=1)
    async def auto_sync_task(self) -> None:
        """Background task to automatically sync tournaments to events every hour."""
        if not self.clash_client or not self.event_manager:
            return

        self.logger.debug(f"Running auto-sync for {len(self.auto_sync_guilds)} guild(s)")

        guilds_to_remove = []

        for guild_id, platform in list(self.auto_sync_guilds.items()):
            try:
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    self.logger.warning(f"Guild {guild_id} not found, removing from auto-sync")
                    guilds_to_remove.append(guild_id)
                    continue

                tournaments = await self.clash_client.get_tournaments(platform)

                if not tournaments:
                    self.logger.debug(f"No tournaments found for guild {guild.name} (region: {platform})")
                    continue

                # Sync with duplicate detection (remove_old=False to preserve existing events)
                created, failed = await self.event_manager.sync_tournaments_to_events(guild, tournaments, remove_old=False)

                if created or failed:
                    self.logger.info(
                        f"Auto-sync for guild {guild.name}: "
                        f"{len(created)} created, {len(failed)} failed, "
                        f"{len(tournaments)} total tournaments"
                    )

            except RiotClashAPIError:
                self.logger.exception(f"Auto-sync failed for guild {guild_id}")
            except Exception:
                self.logger.exception(f"Unexpected error in auto-sync for guild {guild_id}")

        # Remove guilds that no longer exist
        for guild_id in guilds_to_remove:
            del self.auto_sync_guilds[guild_id]

    @auto_sync_task.before_loop
    async def before_auto_sync(self) -> None:
        """Wait for bot to be ready before starting auto-sync."""
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="sync-clash-events",
        description="Sync Clash tournaments to Discord scheduled events",
    )
    @app_commands.describe(
        region="Platform region (e.g., na1, euw1, kr)",
        remove_old="Remove old Clash events before creating new ones",
    )
    @app_commands.default_permissions(manage_events=True)
    async def sync_clash_events(
        self,
        interaction: discord.Interaction,
        region: str,
        remove_old: bool = True,
    ) -> None:
        """Manually sync Clash tournaments to Discord scheduled events.

        Fetches upcoming Clash tournaments from the Riot API and creates
        Discord scheduled events for them if they don't already exist.

        Args:
        ----
            interaction: Discord interaction from the command
            region: Platform region code (e.g., na1, euw1, kr)
            remove_old: Whether to remove old Clash events first

        """
        self.logger.info(
            f"User {interaction.user.id} ({interaction.user.name}) executing /sync-clash-events "
            f"in guild {interaction.guild.name if interaction.guild else 'DM'} (region={region})"
        )
        await interaction.response.defer()

        if not self.clash_client or not self.event_manager:
            await interaction.followup.send(
                "❌ Clash API is not configured. Please set RIOT_API_KEY in config.ini.",
                ephemeral=True,
            )
            return

        if not interaction.guild:
            await interaction.followup.send(
                "❌ This command can only be used in a guild.",
                ephemeral=True,
            )
            return

        try:
            platform = Platform(region.lower())
            self.logger.info(f"Syncing Clash events for guild {interaction.guild.name} (region: {platform})")

            # Fetch tournaments
            tournaments = await self.clash_client.get_tournaments(platform)

            if not tournaments:
                embed = discord.Embed(
                    title="🏆 Clash Event Sync",
                    description=f"No upcoming tournaments found for region **{region.upper()}**",
                    color=discord.Color.orange(),
                )
                await interaction.followup.send(embed=embed)
                return

            # Sync to Discord events
            created, failed = await self.event_manager.sync_tournaments_to_events(
                interaction.guild, tournaments, remove_old=remove_old
            )

            # Count skipped (already existing) tournaments
            skipped = len(tournaments) - len(created) - len(failed)

            # Create response embed
            embed = discord.Embed(
                title="🏆 Clash Event Sync Complete",
                description=f"Processed {len(tournaments)} tournament(s) from **{region.upper()}**",
                color=discord.Color.green(),
            )

            if created:
                embed.add_field(
                    name="✅ Created Events",
                    value=f"{len(created)} event(s)",
                    inline=True,
                )

            if skipped > 0 and not remove_old:
                embed.add_field(
                    name="⏭️ Skipped",
                    value=f"{skipped} (already exist)",
                    inline=True,
                )

            if failed:
                embed.add_field(
                    name="❌ Failed",
                    value=f"{len(failed)} tournament(s)",
                    inline=True,
                )

            # Add tournament details
            if tournaments:
                upcoming = [t for t in tournaments if t.start_time is not None]
                if upcoming:
                    next_tournament = min(upcoming, key=lambda t: t.start_time or t.schedule[0].started_at)
                    if next_tournament.start_time:
                        time_str = discord.utils.format_dt(next_tournament.start_time, style="R")
                        embed.add_field(
                            name="⏰ Next Tournament",
                            value=f"{next_tournament.name} - {time_str}",
                            inline=False,
                        )

            embed.set_footer(text=f"Region: {region.upper()}")
            await interaction.followup.send(embed=embed)

            self.logger.info(f"Clash sync completed for {interaction.guild.name}: {len(created)} created, {len(failed)} failed")

        except ValueError:
            await interaction.followup.send(
                f"❌ Invalid region: **{region}**. Use codes like: na1, euw1, kr, etc.",
                ephemeral=True,
            )
        except RiotClashAPIError:
            embed = discord.Embed(
                title="❌ Clash Event Sync Error",
                description="Failed to sync tournament schedule",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)
            self.logger.exception("Clash API error during sync")

    @app_commands.command(
        name="enable-auto-sync",
        description="Enable automatic hourly sync of Clash events",
    )
    @app_commands.describe(region="Platform region (e.g., na1, euw1, kr)")
    @app_commands.default_permissions(manage_events=True)
    async def enable_auto_sync(
        self,
        interaction: discord.Interaction,
        region: str,
    ) -> None:
        """Enable automatic hourly synchronization of Clash events.

        When enabled, the bot will check for new Clash tournaments every hour
        and automatically create Discord scheduled events for them.

        Args:
        ----
            interaction: Discord interaction from the command
            region: Platform region code

        """
        self.logger.info(
            f"User {interaction.user.id} ({interaction.user.name}) executing /enable-auto-sync "
            f"in guild {interaction.guild.name if interaction.guild else 'DM'} (region={region})"
        )
        await interaction.response.defer(ephemeral=True)

        if not self.clash_client or not self.event_manager:
            await interaction.followup.send(
                "❌ Clash API is not configured. Please set RIOT_API_KEY in config.ini.",
            )
            return

        if not interaction.guild:
            await interaction.followup.send("❌ This command can only be used in a guild.")
            return

        try:
            platform = Platform(region.lower())
            self.auto_sync_guilds[interaction.guild.id] = platform

            embed = discord.Embed(
                title="✅ Auto-Sync Enabled",
                description=(
                    f"Automatic Clash event sync enabled for **{region.upper()}**\n\n"
                    "The bot will check for new tournaments every hour and "
                    "create Discord events automatically."
                ),
                color=discord.Color.green(),
            )
            embed.set_footer(text="Use /disable-auto-sync to stop automatic syncing")

            await interaction.followup.send(embed=embed)

            self.logger.info(f"Auto-sync enabled for guild {interaction.guild.name} (region: {platform})")

        except ValueError:
            await interaction.followup.send(
                f"❌ Invalid region: **{region}**. Use codes like: na1, euw1, kr, etc.",
            )

    @app_commands.command(
        name="disable-auto-sync",
        description="Disable automatic hourly sync of Clash events",
    )
    @app_commands.default_permissions(manage_events=True)
    async def disable_auto_sync(self, interaction: discord.Interaction) -> None:
        """Disable automatic hourly synchronization of Clash events.

        Args:
        ----
            interaction: Discord interaction from the command

        """
        self.logger.info(
            f"User {interaction.user.id} ({interaction.user.name}) executing /disable-auto-sync "
            f"in guild {interaction.guild.name if interaction.guild else 'DM'}"
        )
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await interaction.followup.send("❌ This command can only be used in a guild.")
            return

        if interaction.guild.id not in self.auto_sync_guilds:
            await interaction.followup.send(
                "ℹ️ Auto-sync is not currently enabled for this guild.",
            )
            return

        del self.auto_sync_guilds[interaction.guild.id]

        embed = discord.Embed(
            title="✅ Auto-Sync Disabled",
            description="Automatic Clash event sync has been disabled for this guild.",
            color=discord.Color.blue(),
        )
        embed.set_footer(text="Use /enable-auto-sync to re-enable automatic syncing")

        await interaction.followup.send(embed=embed)

        self.logger.info(f"Auto-sync disabled for guild {interaction.guild.name}")

    @app_commands.command(
        name="list-clash-events",
        description="List all Clash-related scheduled events in this guild",
    )
    async def list_clash_events(self, interaction: discord.Interaction) -> None:
        """List all Clash-related scheduled events in the guild.

        Args:
        ----
            interaction: Discord interaction from the command

        """
        self.logger.info(
            f"User {interaction.user.id} ({interaction.user.name}) executing /list-clash-events "
            f"in guild {interaction.guild.name if interaction.guild else 'DM'}"
        )
        await interaction.response.defer()

        if not interaction.guild:
            await interaction.followup.send(
                "❌ This command can only be used in a guild.",
                ephemeral=True,
            )
            return

        try:
            clash_events = [event for event in interaction.guild.scheduled_events if event.name.startswith("🏆")]

            if not clash_events:
                embed = discord.Embed(
                    title="🏆 Clash Events",
                    description="No Clash-related scheduled events found in this guild.",
                    color=discord.Color.orange(),
                )
                await interaction.followup.send(embed=embed)
                return

            embed = discord.Embed(
                title="🏆 Clash Events",
                description=f"Found {len(clash_events)} Clash event(s) scheduled",
                color=discord.Color.gold(),
            )

            for event in clash_events[:MAX_EVENTS_DISPLAY]:
                event_time = discord.utils.format_dt(event.start_time, style="F")
                embed.add_field(
                    name=event.name,
                    value=f"📅 {event_time}\n👥 {event.user_count} interested",
                    inline=False,
                )

            if len(clash_events) > MAX_EVENTS_DISPLAY:
                embed.set_footer(text=f"Showing first {MAX_EVENTS_DISPLAY} of {len(clash_events)} events")

            await interaction.followup.send(embed=embed)

        except discord.DiscordException:
            await interaction.followup.send(
                "\u274c Failed to fetch scheduled events",
                ephemeral=True,
            )
            self.logger.exception(f"Failed to fetch events for {interaction.guild.name}")


async def setup(bot: commands.Bot) -> None:
    """Load the TournamentEventManager cog.

    Args:
    ----
        bot: Discord bot instance

    """
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Loading TournamentEventManager extension...")
    try:
        await bot.add_cog(TournamentEventManager(bot=bot))
        logger.info("TournamentEventManager extension loaded successfully")
    except Exception as e:
        logger.exception(f"Failed to load TournamentEventManager: {e}")
        raise
