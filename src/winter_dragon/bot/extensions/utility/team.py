"""Module for managing teams and respective voice channels."""

import math
import random
from collections.abc import Sequence
from typing import cast

import discord
from discord import CategoryChannel, Guild, Interaction, Member, VoiceChannel, app_commands
from discord.abc import PrivateChannel
from sqlmodel import select

from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.bot.core.config import Config
from winter_dragon.bot.core.tasks import loop
from winter_dragon.database.channel_types import ChannelTypes
from winter_dragon.database.tables import Channels


type TeamDict = dict[str, int | list[Member]]


@app_commands.guild_only()
class Team(GroupCog, auto_load=True):
    """A cog for managing teams and respective voice channels."""

    team_cleanup_interval = Config(3600)

    @loop()
    async def delete_empty_team_channels(self) -> None:
        """Delete any empty team channel."""
        channels = self.session.exec(select(Channels).where(Channels.type == ChannelTypes.TEAM_VOICE)).all()
        for channel in channels:
            discord_channel = self.bot.get_channel(channel.id)
            if isinstance(discord_channel, CategoryChannel | PrivateChannel) or discord_channel is None:
                self.logger.debug(f"skipping invalid channel: {discord_channel=}")
                continue
            if len(discord_channel.members) != 0:
                self.logger.debug(f"skipping channel with members: {discord_channel.members}")
                continue
            await discord_channel.delete()
            self.session.delete(channel)
        self.session.commit()

    @delete_empty_team_channels.before_loop
    async def before_update(self) -> None:
        """Wait until the bot is ready. before cleaning up empty channels."""
        await self.bot.wait_until_ready()

    async def cog_load(self) -> None:
        """Start the cog."""
        await super().cog_load()
        # Configure loop interval from config
        self.delete_empty_team_channels.change_interval(seconds=self.team_cleanup_interval)
        self.delete_empty_team_channels.start()

    def split_teams(
        self,
        team_count: int,
        members: list[Member],
    ) -> list[TeamDict]:
        """Split a team evenly around :param:`team_count`."""
        random.shuffle(members)
        # find divide and module by desired team size,
        # and found amount of users
        divide, modulo = divmod(len(members), team_count)
        members_count = math.ceil(divide + modulo)

        # create teams, and fill members with amount of users
        # (evenly split among each team)
        teams: list[TeamDict] = [
            {
                "id": i + 1,
                "members": [members[j + i * members_count] for j in range(members_count)],
            }
            for i in range(team_count)
        ]

        self.logger.debug(f"created teams: {teams}")
        return teams

    async def move_team(self, team: TeamDict, channel: VoiceChannel) -> None:
        """Move a whole team to its channel."""
        self.logger.debug(f"moving {team['members']} to {channel}")
        for user in team["members"]:
            await user.move_to(channel)

    async def create_team_channels(
        self,
        teams: list[TeamDict],
        category: CategoryChannel,
    ) -> tuple[list[Channels], list[VoiceChannel]]:
        """Create team channels based on a list of teams, adds those channels to database."""
        db_channels: list[Channels] = []
        discord_channels: list[VoiceChannel] = []
        for team in teams:
            self.logger.debug(f"creating voice for {team}")
            voice = await category.create_voice_channel(name=f"Team {team['id']}")
            discord_channels.append(voice)
            db_channels.append(
                Channels(
                    id=voice.id,
                    name=voice.name,
                    type=ChannelTypes.TEAM_VOICE,
                    guild_id=voice.guild.id,
                ),
            )

        self.session.add_all(db_channels)
        self.session.commit()
        return db_channels, discord_channels

    def get_team_channels(self, guild: Guild) -> Sequence[Channels]:
        """Get all team channels from winter_dragon.database."""
        return self.session.exec(
            select(Channels).where(
                Channels.type == ChannelTypes.TEAM_VOICE,
                Channels.guild_id == guild.id,
            ),
        ).all()

    def get_teams_category(self, guild: Guild) -> CategoryChannel | None:
        """Find a category channel."""
        if channel := self.session.exec(
            select(Channels).where(
                Channels.type == ChannelTypes.TEAM_CATEGORY,
                Channels.guild_id == guild.id,
            ),
        ).first():
            return cast("CategoryChannel", self.bot.get_channel(channel.id))
        return None

    async def create_teams_category(self, guild: Guild) -> CategoryChannel:
        """Create a category channel, and a lobby voice channel."""
        channel = await guild.create_category(name="teams", reason="Creating team category for splitting into teams")
        self.session.add(
            Channels(
                id=channel.id,
                name=channel.name,
                type=ChannelTypes.TEAM_CATEGORY,
                guild_id=guild.id,
            ),
        )
        self.session.commit()
        return channel

    async def fetch_teams_category(self, guild: Guild) -> CategoryChannel:
        """Find a category channel, if it doesn't find any, create it."""
        if category := self.get_teams_category(guild):
            return category
        return await self.create_teams_category(guild)

    def get_teams_lobby(self, guild: Guild) -> VoiceChannel | None:
        """Find a lobby channel."""
        if channel := self.session.exec(
            select(Channels).where(
                Channels.type == ChannelTypes.TEAM_LOBBY,
                Channels.guild_id == guild.id,
            ),
        ).first():
            return cast("VoiceChannel", self.bot.get_channel(channel.id))
        return None

    async def create_teams_lobby(self, category: CategoryChannel) -> VoiceChannel:
        """Create a lobby channel."""
        voice = await category.create_voice_channel(name="Lobby", reason="Creating lobby channel for moving users.")
        self.session.add(
            Channels(
                id=voice.id,
                name=voice.name,
                type=ChannelTypes.TEAM_LOBBY,
                guild_id=category.guild.id,
            ),
        )
        self.session.commit()
        return voice

    async def fetch_teams_lobby(self, category: CategoryChannel) -> VoiceChannel:
        """Find a lobby channel, if not found create it."""
        if lobby := self.get_teams_lobby(category.guild):
            return lobby
        return await self.create_teams_lobby(category)

    async def move_from_category(self, teams: list[TeamDict], channel: VoiceChannel) -> None:
        """Handle moving members, if member not in teams lobby, they won't get moved."""
        for team in teams:
            team_to_move: TeamDict = {
                "id": team["id"],
                "members": [],
            }

            for user in team["members"]:
                if user.voice is None:
                    continue
                if user.voice.channel == self.get_teams_lobby(channel.guild):
                    team_to_move["members"].append(user)
                    continue
                break
            else:
                continue

            await self.move_team(team_to_move, channel)

    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.command(name="lobby", description="Find the lobby channel, or creates one for teams")
    async def slash_team_lobby(
        self,
        interaction: discord.Interaction,
    ) -> None:
        """Find the lobby channel, or creates one for teams."""
        if not interaction.user:
            self.logger.debug("interaction.user is None")
            return
        if not interaction.guild:
            self.logger.debug("interaction.guild is None")
            await interaction.response.send_message("This command can only be used in a guild.", ephemeral=True)
            return
        if not isinstance(interaction.user, Member):
            self.logger.debug("interaction.user is not a Member")
            await interaction.response.send_message("This command can only be used in a guild.", ephemeral=True)
            return
        if interaction.user.resolved_permissions is None:
            self.logger.debug("interaction.user.resolved_permissions is None")
            await interaction.response.send_message("No permissions found.", ephemeral=True)
            return
        if interaction.user.resolved_permissions.manage_channels:
            await self.fetch_and_send_lobby_info(interaction)
            return
        await self.send_lobby_info(interaction)

    async def send_lobby_info(self, interaction: Interaction) -> None:
        """Send lobby info to user."""
        if not interaction.guild:
            self.logger.debug("interaction.guild is None")
            await interaction.response.send_message("This command can only be used in a guild.", ephemeral=True)
            return
        lobby = self.get_teams_lobby(interaction.guild)
        if lobby is None:
            raise app_commands.errors.MissingPermissions(["manage_channels"])
        await interaction.response.send_message(f"Join the teams lobby here: {lobby.mention}")
        return

    async def fetch_and_send_lobby_info(self, interaction: Interaction) -> None:
        """Fetch the lobby and then send it to the user."""
        """Send lobby info to user."""
        if not interaction.guild:
            self.logger.debug("interaction.guild is None")
            await interaction.response.send_message("This command can only be used in a guild.", ephemeral=True)
            return
        category = await self.fetch_teams_category(interaction.guild)
        if lobby := await self.fetch_teams_lobby(category):
            await interaction.response.send_message(f"Join the teams lobby here: {lobby.mention}")

    @app_commands.command(name="voice", description="Randomly split all users from your voice chat, in teams")
    async def slash_team_voice(
        self,
        interaction: discord.Interaction,
        team_count: int = 2,
    ) -> None:
        """Create teams based on players in the user's voice channel, and move them to their respective channels."""
        if not isinstance(interaction.user, Member) or not interaction.guild:
            self.logger.debug("interaction.user is not a Member")
            await interaction.response.send_message("This command can only be used in a guild.", ephemeral=True)
            return
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "You are not in a voice channel, please join one.",
                ephemeral=True,
            )
            return
        if not interaction.user.voice.channel.members:
            await interaction.response.send_message(
                "You are the only one in your voice channel, please invite some friends.",
                ephemeral=True,
            )
            return
        await interaction.response.defer()

        category = await self.fetch_teams_category(interaction.guild)
        teams = self.split_teams(team_count, interaction.user.voice.channel.members)
        _, channels = await self.create_team_channels(teams, category)
        for channel in channels:
            await self.move_from_category(teams, channel)
        await interaction.edit_original_response(content="Users from your voice split among teams")

    @app_commands.command(name="text", description="Randomly split all users, shows teams in message")
    async def slash_team_text(
        self,
        interaction: discord.Interaction,
        team_count: int = 2,
    ) -> None:
        """Create teams based players in the user's voice channel, and send them in a message showing the teams."""
        if not interaction.message:
            self.logger.debug("interaction.message is None")
            return
        members = cast("list[Member]", interaction.message.mentions)

        if len(members) < team_count:
            await interaction.response.send_message(
                f"Not enough members to fill {team_count} teams, got {len(members)} / {team_count}",
                ephemeral=True,
            )
            return

        teams = self.split_teams(team_count, members)

        embed = discord.Embed(title="Teams")

        for team in teams:
            embed.add_field(
                name=f"Team {team['id']}",
                value=f"members: {team['members']}",
            )

        await interaction.response.send_message(embed=embed)
