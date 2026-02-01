"""Module for league of legends related Cogs."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Unpack

import cassiopeia as cass
import discord
from discord import app_commands
from sqlmodel import select

from winter_dragon.bot.core.cogs import BotArgs, GroupCog
from winter_dragon.database.tables.lol_account import LoLAccount

if TYPE_CHECKING:
    from winter_dragon.bot.core.bot import WinterDragon


# Riot API regions
REGIONS = [
    "BR1",  # Brazil
    "EUN1",  # Europe Nordic & East
    "EUW1",  # Europe West
    "JP1",  # Japan
    "KR",  # Korea
    "LA1",  # Latin America North
    "LA2",  # Latin America South
    "NA1",  # North America
    "OC1",  # Oceania
    "TR1",  # Turkey
    "RU",  # Russia
    "PH2",  # Philippines
    "SG2",  # Singapore
    "TH2",  # Thailand
    "TW2",  # Taiwan
    "VN2",  # Vietnam
]


class LeagueOfLegends(GroupCog, auto_load=True):
    """League of Legends game.

    It allows users to get information about their games.
    It can watch and track (ranked) games.

    It can also track the user their:
    - rank and rank history.
    - match history.
    - champion mastery.
    - champion statistics.
    - champion leaderboard.
    """

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the League of Legends cog."""
        super().__init__(**kwargs)
        # Initialize cassiopeia with default settings
        cass.apply_settings(cass.get_default_config())

    @app_commands.command(name="link", description="Link your League of Legends account")
    @app_commands.describe(
        summoner_name="Your summoner name",
        tag_line="Your tag line (e.g., NA1)",
        region="Your region",
    )
    async def link_account(
        self,
        interaction: discord.Interaction,
        summoner_name: str,
        tag_line: str,
        region: str,
    ) -> None:
        """Link a League of Legends account to the user's Discord account."""
        await interaction.response.defer(ephemeral=True)

        # Validate region
        region_upper = region.upper()
        if region_upper not in REGIONS:
            await interaction.followup.send(
                f"Invalid region. Please choose from: {', '.join(REGIONS)}",
                ephemeral=True,
            )
            return

        try:
            # Set region for cassiopeia
            cass.set_default_region(region_upper)

            # Get summoner info using Riot ID (name + tag)
            summoner = cass.Summoner(name=summoner_name, region=region_upper)

            # Check if account already exists
            existing = self.session.exec(
                select(LoLAccount).where(LoLAccount.id == interaction.user.id),
            ).first()

            if existing:
                # Update existing account
                existing.summoner_name = summoner_name
                existing.tag_line = tag_line
                existing.region = region_upper
                existing.puuid = summoner.puuid
                existing.summoner_id = summoner.id
                existing.account_id = summoner.account_id
                existing.profile_icon_id = summoner.profile_icon.id
                existing.summoner_level = summoner.level
                existing.last_updated = int(time.time())
                self.session.add(existing)
            else:
                # Create new account
                lol_account = LoLAccount(
                    id=interaction.user.id,
                    summoner_name=summoner_name,
                    tag_line=tag_line,
                    region=region_upper,
                    puuid=summoner.puuid,
                    summoner_id=summoner.id,
                    account_id=summoner.account_id,
                    profile_icon_id=summoner.profile_icon.id,
                    summoner_level=summoner.level,
                    last_updated=int(time.time()),
                )
                self.session.add(lol_account)

            self.session.commit()

            embed = discord.Embed(
                title="✅ Account Linked",
                description=f"Successfully linked **{summoner_name}#{tag_line}** ({region_upper})",
                color=discord.Color.green(),
            )
            embed.add_field(name="Level", value=str(summoner.level), inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.exception("Error linking LoL account")
            await interaction.followup.send(
                f"Error linking account: {e!s}\n\nPlease check your summoner name, tag, and region.",
                ephemeral=True,
            )

    @app_commands.command(name="unlink", description="Unlink your League of Legends account")
    async def unlink_account(self, interaction: discord.Interaction) -> None:
        """Unlink a League of Legends account from the user's Discord account."""
        await interaction.response.defer(ephemeral=True)

        existing = self.session.exec(
            select(LoLAccount).where(LoLAccount.id == interaction.user.id),
        ).first()

        if not existing:
            await interaction.followup.send(
                "You don't have a linked account.",
                ephemeral=True,
            )
            return

        self.session.delete(existing)
        self.session.commit()

        await interaction.followup.send(
            "✅ Account unlinked successfully.",
            ephemeral=True,
        )

    @app_commands.command(name="profile", description="Display your League of Legends profile")
    @app_commands.describe(user="The user to display (optional)")
    async def profile(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
    ) -> None:
        """Display a user's League of Legends profile."""
        await interaction.response.defer()

        target_user = user or interaction.user

        # Get linked account
        lol_account = self.session.exec(
            select(LoLAccount).where(LoLAccount.id == target_user.id),
        ).first()

        if not lol_account:
            await interaction.followup.send(
                f"{'You have' if target_user == interaction.user else f'{target_user.mention} has'} not linked a League of Legends account yet.",
            )
            return

        try:
            # Set region
            cass.set_default_region(lol_account.region)

            # Get summoner
            summoner = cass.Summoner(name=lol_account.summoner_name, region=lol_account.region)

            # Create embed
            embed = discord.Embed(
                title=f"{summoner.name}#{lol_account.tag_line}",
                color=discord.Color.blue(),
            )
            embed.add_field(name="Region", value=lol_account.region, inline=True)
            embed.add_field(name="Level", value=str(summoner.level), inline=True)

            # Get ranked information
            try:
                ranked_positions = summoner.league_entries
                for entry in ranked_positions:
                    queue_name = entry.queue.value.replace("_", " ").title()
                    rank_info = f"{entry.tier.value} {entry.division.value}"
                    lp = entry.league_points
                    wins = entry.wins
                    losses = entry.losses
                    winrate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

                    embed.add_field(
                        name=queue_name,
                        value=f"{rank_info} ({lp} LP)\n{wins}W {losses}L ({winrate:.1f}%)",
                        inline=False,
                    )
            except Exception:
                self.logger.exception("Error fetching ranked info")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.exception("Error fetching profile")
            await interaction.followup.send(f"Error fetching profile: {e!s}")

    @app_commands.command(name="match-history", description="Display recent match history")
    @app_commands.describe(
        user="The user to display (optional)",
        count="Number of matches to display (1-10)",
    )
    async def match_history(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
        count: int = 5,
    ) -> None:
        """Display a user's recent match history."""
        await interaction.response.defer()

        target_user = user or interaction.user
        count = max(1, min(10, count))  # Clamp between 1 and 10

        # Get linked account
        lol_account = self.session.exec(
            select(LoLAccount).where(LoLAccount.id == target_user.id),
        ).first()

        if not lol_account:
            await interaction.followup.send(
                f"{'You have' if target_user == interaction.user else f'{target_user.mention} has'} not linked a League of Legends account yet.",
            )
            return

        try:
            # Set region
            cass.set_default_region(lol_account.region)

            # Get summoner
            summoner = cass.Summoner(name=lol_account.summoner_name, region=lol_account.region)

            # Get match history
            match_history = summoner.match_history[:count]

            if not match_history:
                await interaction.followup.send("No recent matches found.")
                return

            embed = discord.Embed(
                title=f"Match History - {summoner.name}#{lol_account.tag_line}",
                color=discord.Color.blue(),
            )

            for i, match in enumerate(match_history, 1):
                try:
                    participant = match.participants[summoner]
                    champion = participant.champion.name
                    kda = f"{participant.stats.kills}/{participant.stats.deaths}/{participant.stats.assists}"
                    win = "✅ Victory" if participant.stats.win else "❌ Defeat"
                    game_mode = match.queue.value.replace("_", " ").title()

                    # Calculate KDA ratio
                    deaths = max(participant.stats.deaths, 1)
                    kda_ratio = (participant.stats.kills + participant.stats.assists) / deaths

                    field_value = (
                        f"{win}\n"
                        f"Champion: {champion}\n"
                        f"KDA: {kda} ({kda_ratio:.2f}:1)\n"
                        f"Mode: {game_mode}"
                    )

                    embed.add_field(
                        name=f"Match {i}",
                        value=field_value,
                        inline=True,
                    )
                except Exception:
                    self.logger.exception(f"Error processing match {i}")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.exception("Error fetching match history")
            await interaction.followup.send(f"Error fetching match history: {e!s}")

    @app_commands.command(name="champion-mastery", description="Display champion mastery information")
    @app_commands.describe(
        user="The user to display (optional)",
        count="Number of champions to display (1-10)",
    )
    async def champion_mastery(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
        count: int = 5,
    ) -> None:
        """Display a user's champion mastery."""
        await interaction.response.defer()

        target_user = user or interaction.user
        count = max(1, min(10, count))

        # Get linked account
        lol_account = self.session.exec(
            select(LoLAccount).where(LoLAccount.id == target_user.id),
        ).first()

        if not lol_account:
            await interaction.followup.send(
                f"{'You have' if target_user == interaction.user else f'{target_user.mention} has'} not linked a League of Legends account yet.",
            )
            return

        try:
            # Set region
            cass.set_default_region(lol_account.region)

            # Get summoner
            summoner = cass.Summoner(name=lol_account.summoner_name, region=lol_account.region)

            # Get champion masteries
            masteries = summoner.champion_masteries[:count]

            if not masteries:
                await interaction.followup.send("No champion mastery data found.")
                return

            embed = discord.Embed(
                title=f"Champion Mastery - {summoner.name}#{lol_account.tag_line}",
                color=discord.Color.gold(),
            )

            for i, mastery in enumerate(masteries, 1):
                try:
                    champion = mastery.champion.name
                    level = mastery.level
                    points = mastery.points

                    embed.add_field(
                        name=f"{i}. {champion}",
                        value=f"Level {level} | {points:,} points",
                        inline=True,
                    )
                except Exception:
                    self.logger.exception(f"Error processing mastery {i}")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.exception("Error fetching champion mastery")
            await interaction.followup.send(f"Error fetching champion mastery: {e!s}")
