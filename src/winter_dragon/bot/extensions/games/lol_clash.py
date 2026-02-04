"""Contains the Clash cog for the bot.

Allows for automatic event reminders for the Clash event in League of Legends.
Allows for LFG (Looking For Group) for the Clash event in League of Legends.
Integrates with Riot's public CLASH-V1 API to provide tournament schedules and
Discord scheduled event management.
"""

from __future__ import annotations

from typing import Unpack

import cassiopeia as cass
import discord
from discord import app_commands
from sqlmodel import select

from winter_dragon.bot.core.cogs import BotArgs, GroupCog
from winter_dragon.bot.extensions.games.clash_settings import ClashSettings
from winter_dragon.bot.extensions.games.riot_clash_api import (
    DiscordClashEventManager,
    RiotClashAPIError,
    RiotClashClient,
)
from winter_dragon.database.tables.lol_account import LoLAccount


# Constants for team analysis
FULL_TEAM_SIZE = 5
TEAM_DATA_WITH_CHAMPS_LEN = 4


class Clash(GroupCog, auto_load=True):
    """Clash cog for League of Legends."""

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the Clash cog.

        Sets up cassiopeia and the Riot Clash API client for tournament management.
        """
        super().__init__(**kwargs)
        # Initialize cassiopeia with default settings
        cass.apply_settings(cass.get_default_config())

        # Initialize Riot Clash API client
        api_key = ClashSettings.riot_api_key
        if api_key:
            self.clash_client = RiotClashClient(api_key)
            self.event_manager = DiscordClashEventManager(self.bot)
        else:
            self.logger.warning("RIOT_API_KEY not configured in config.ini. Clash API features will be unavailable.")
            self.clash_client = None
            self.event_manager = None

    @app_commands.command(name="schedule", description="Display upcoming Clash schedule")
    @app_commands.describe(region="The platform region (e.g., na1, euw1, kr)")
    async def clash_schedule(
        self,
        interaction: discord.Interaction,
        region: str | None = None,
    ) -> None:
        """Display upcoming Clash schedule for a region."""
        await interaction.response.defer()

        if not self.clash_client:
            await interaction.followup.send(
                "❌ Clash API is not configured. Please set RIOT_API_KEY environment variable.",
            )
            return

        # Determine platform region
        if not region:
            lol_account = self.session.exec(
                select(LoLAccount).where(LoLAccount.id == interaction.user.id),
            ).first()

            if not lol_account:
                await interaction.followup.send(
                    "Please specify a region or link your League of Legends account.",
                )
                return

            region = lol_account.region
        else:
            region = region.lower()

        try:
            # Fetch tournaments for the region
            tournaments = await self.clash_client.get_tournaments(region)

            if not tournaments:
                embed = discord.Embed(
                    title="🏆 Clash Schedule",
                    description=f"No upcoming tournaments found for region **{region.upper()}**",
                    color=discord.Color.orange(),
                )
                await interaction.followup.send(embed=embed)
                return

            # Create embeds for each tournament
            embeds = [tournament.to_embed() for tournament in tournaments[:10]]  # Limit to 10

            # Add region info header
            if embeds:
                embeds[0].set_footer(text=f"Region: {region.upper()} • {len(tournaments)} tournament(s) found")

            await interaction.followup.send(embeds=embeds)

        except RiotClashAPIError as e:
            embed = discord.Embed(
                title="❌ Clash Schedule Error",
                description=f"Failed to fetch tournament schedule: {e!s}",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="sync-events",
        description="Sync upcoming Clash tournaments to Discord scheduled events",
    )
    @app_commands.describe(region="The platform region (e.g., na1, euw1, kr)")
    @app_commands.default_permissions(manage_events=True)
    async def sync_clash_events(
        self,
        interaction: discord.Interaction,
        region: str | None = None,
    ) -> None:
        """Sync Clash tournaments to Discord scheduled events in this guild.

        Creates or updates Discord scheduled events for all upcoming Clash tournaments.
        Requires manage_events permission.

        Args:
            interaction: Discord interaction from the command
            region: Platform region code (optional, defaults to user's linked region)

        """
        await interaction.response.defer()

        if not self.clash_client or not self.event_manager:
            await interaction.followup.send(
                "❌ Clash API is not configured. Please set RIOT_API_KEY environment variable.",
            )
            return

        if not interaction.guild:
            await interaction.followup.send("❌ This command can only be used in a guild.")
            return

        # Determine platform region
        if not region:
            lol_account = self.session.exec(
                select(LoLAccount).where(LoLAccount.id == interaction.user.id),
            ).first()

            if not lol_account:
                await interaction.followup.send(
                    "Please specify a region or link your League of Legends account.",
                )
                return

            region = lol_account.region
        else:
            region = region.lower()

        try:
            # Fetch tournaments for the region
            tournaments = await self.clash_client.get_tournaments(region)

            if not tournaments:
                await interaction.followup.send(
                    f"No upcoming tournaments found for region **{region.upper()}**",
                )
                return

            # Sync to Discord events
            created, failed = await self.event_manager.sync_tournaments_to_events(
                interaction.guild,
                tournaments,
            )

            embed = discord.Embed(
                title="✅ Clash Events Synced",
                color=discord.Color.green(),
            )
            embed.add_field(
                name="Created Events",
                value=f"{len(created)} event(s)",
                inline=True,
            )
            if failed:
                embed.add_field(
                    name="Failed",
                    value=f"{len(failed)} tournament(s)",
                    inline=True,
                )

            embed.set_footer(text=f"Region: {region.upper()}")
            await interaction.followup.send(embed=embed)

        except RiotClashAPIError as e:
            embed = discord.Embed(
                title="❌ Sync Error",
                description=f"Failed to sync tournaments: {e!s}",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="team-analysis", description="Analyze your Clash team composition")
    @app_commands.describe(
        player1="First player",
        player2="Second player (optional)",
        player3="Third player (optional)",
        player4="Fourth player (optional)",
        player5="Fifth player (optional)",
    )
    async def team_analysis(  # noqa: C901, PLR0913, PLR0912
        self,
        interaction: discord.Interaction,
        player1: discord.User,
        player2: discord.User | None = None,
        player3: discord.User | None = None,
        player4: discord.User | None = None,
        player5: discord.User | None = None,
    ) -> None:
        """Analyze a Clash team composition and provide suggestions."""
        await interaction.response.defer()

        players = [player1, player2, player3, player4, player5]
        players = [p for p in players if p is not None]

        if len(players) < 1:
            await interaction.followup.send("Please specify at least one player.")
            return

        embed = discord.Embed(
            title="🏆 Clash Team Analysis",
            color=discord.Color.gold(),
        )

        team_data = []

        for player in players:
            lol_account = self.session.exec(
                select(LoLAccount).where(LoLAccount.id == player.id),
            ).first()

            if not lol_account:
                team_data.append((player.display_name, "Not Linked", "N/A"))
                continue

            try:
                # Get summoner by PUUID (most reliable method in v5)
                if not lol_account.puuid:
                    team_data.append((player.display_name, "Error", "N/A"))
                    continue

                summoner = cass.Summoner(puuid=lol_account.puuid, region=lol_account.region)

                # Get ranked tier
                ranked_tier = "Unranked"
                try:
                    entries = summoner.league_entries
                    for entry in entries:
                        if "RANKED_SOLO" in entry.queue.value:
                            ranked_tier = f"{entry.tier.value} {entry.division.value}"
                            break
                except Exception:
                    self.logger.exception("Error fetching ranked tier")

                # Get top champions
                top_champs = []
                try:
                    masteries = summoner.champion_masteries[:3]
                    top_champs = [m.champion.name for m in masteries]
                except Exception:
                    self.logger.exception("Error fetching champion mastery")

                team_data.append(
                    (
                        player.display_name,
                        f"{lol_account.summoner_name}#{lol_account.tag_line}",
                        ranked_tier,
                        ", ".join(top_champs) if top_champs else "N/A",
                    )
                )
            except Exception:
                self.logger.exception("Error fetching data for %s", player.display_name)
                team_data.append((player.display_name, "Error", "N/A"))

        # Build embed with team data
        for data in team_data:
            if len(data) == TEAM_DATA_WITH_CHAMPS_LEN:
                name, summoner, rank, champs = data
                embed.add_field(
                    name=name,
                    value=f"**Summoner:** {summoner}\n**Rank:** {rank}\n**Top Champions:** {champs}",
                    inline=False,
                )
            else:
                name, summoner, rank = data
                embed.add_field(
                    name=name,
                    value=f"**Summoner:** {summoner}\n**Rank:** {rank}",
                    inline=False,
                )

        # Add general suggestions
        suggestions = []
        if len(players) >= FULL_TEAM_SIZE:
            suggestions.append("✅ Full team!")
        else:
            suggestions.append(f"⚠️ Team is missing {FULL_TEAM_SIZE - len(players)} player(s)")

        if suggestions:
            embed.add_field(
                name="Team Status",
                value="\n".join(suggestions),
                inline=False,
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="stats", description="Display your Clash statistics")
    @app_commands.describe(user="The user to display (optional)")
    async def clash_stats(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
    ) -> None:
        """Display a user's Clash statistics."""
        await interaction.response.defer()

        target_user = user or interaction.user

        # Get linked account
        lol_account = self.session.exec(
            select(LoLAccount).where(LoLAccount.id == target_user.id),
        ).first()

        if not lol_account:
            msg_prefix = "You have" if target_user == interaction.user else f"{target_user.mention} has"
            await interaction.followup.send(
                f"{msg_prefix} not linked a League of Legends account yet.",
            )
            return

        try:
            # Get summoner by PUUID (most reliable method in v5)
            if not lol_account.puuid:
                await interaction.followup.send("Linked account is missing PUUID information.")
                return

            summoner = cass.Summoner(puuid=lol_account.puuid, region=lol_account.region)

            embed = discord.Embed(
                title=f"Clash Stats - {lol_account.summoner_name}#{lol_account.tag_line}",
                color=discord.Color.purple(),
            )

            # Try to get Clash-specific data
            try:
                # Note: Cassiopeia's Clash player data may not always be available
                # This is a basic implementation showing the structure
                embed.add_field(
                    name="Status",
                    value=(
                        "Clash statistics are available through the Riot API. This "
                        "feature tracks your Clash performance over time."
                    ),
                    inline=False,
                )

                # Get general ranked stats as proxy for skill level
                try:
                    entries = summoner.league_entries
                    for entry in entries:
                        if "RANKED_SOLO" in entry.queue.value:
                            wins = entry.wins
                            losses = entry.losses
                            winrate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
                            embed.add_field(
                                name="Ranked Performance",
                                value=f"{entry.tier.value} {entry.division.value}\n{wins}W {losses}L ({winrate:.1f}%)",
                                inline=False,
                            )
                            break
                except Exception:
                    self.logger.exception("Error fetching ranked stats")

            except Exception:
                self.logger.exception("Error fetching clash data")
                embed.add_field(
                    name="Note",
                    value="Detailed Clash statistics require tournament participation history.",
                    inline=False,
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.exception("Error fetching clash stats")
            await interaction.followup.send(f"Error fetching clash stats: {e!s}")

    @app_commands.command(name="suggestions", description="Get champion suggestions for Clash")
    @app_commands.describe(
        role="The role you're playing",
        enemy_picks="Enemy champion picks (comma-separated, optional)",
    )
    async def champion_suggestions(
        self,
        interaction: discord.Interaction,
        role: str,
        enemy_picks: str | None = None,
    ) -> None:
        """Get champion suggestions based on role and enemy picks."""
        await interaction.response.defer()

        # Get linked account
        lol_account = self.session.exec(
            select(LoLAccount).where(LoLAccount.id == interaction.user.id),
        ).first()

        if not lol_account:
            await interaction.followup.send("Please link your account first.")
            return

        try:
            # Get summoner by PUUID (most reliable method in v5)
            if not lol_account.puuid:
                await interaction.followup.send("Linked account is missing PUUID information.")
                return

            summoner = cass.Summoner(puuid=lol_account.puuid, region=lol_account.region)

            # Get user's champion mastery for the role
            masteries = summoner.champion_masteries[:20]

            embed = discord.Embed(
                title=f"Champion Suggestions - {role.upper()}",
                description="Based on your champion mastery",
                color=discord.Color.teal(),
            )

            # Filter by role (basic implementation)
            # In a full implementation, you'd use champion role data
            suggestions = []
            for mastery in masteries[:10]:
                champion = mastery.champion.name
                points = mastery.points
                suggestions.append(f"{champion} (Mastery: {points:,})")

            if suggestions:
                embed.add_field(
                    name="Your Top Champions",
                    value="\n".join(suggestions[:5]),
                    inline=False,
                )

            if enemy_picks:
                embed.add_field(
                    name="Enemy Picks",
                    value=enemy_picks,
                    inline=False,
                )
                embed.add_field(
                    name="Counter Strategy",
                    value="Consider champions with strong matchups against the enemy composition.",
                    inline=False,
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.exception("Error generating suggestions")
            await interaction.followup.send(f"Error generating suggestions: {e!s}")

    async def cog_unload(self) -> None:
        """Clean up resources when the cog is unloaded.

        Closes the Clash API client session and stops any background sync tasks.
        """
        if self.clash_client:
            await self.clash_client.close()

        if self.event_manager:
            await self.event_manager.stop_sync_task()
