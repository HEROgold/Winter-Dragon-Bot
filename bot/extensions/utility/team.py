import math
import random

import discord
from discord import CategoryChannel, Guild, Member, VoiceChannel, app_commands

from bot import WinterDragon
from bot.enums.channels import ChannelTypes
from bot.types.aliases import GTPChannel
from bot.types.cogs import GroupCog
from bot.types.dicts import TeamDict
from bot.types.tasks import loop
from database.tables import Channel
from tools import rainbow


TEAM_VOICE = ChannelTypes.TEAM_VOICE.name
TEAM_CATEGORY = ChannelTypes.TEAM_CATEGORY.name
TEAM_LOBBY = ChannelTypes.TEAM_LOBBY.name


@app_commands.guild_only()
class Team(GroupCog):

    @loop(seconds=3600)
    async def delete_empty_team_channels(self) -> None:
        """Delete any empty team channel"""
        with self.session as session:
            channels = session.query(Channel).where(Channel.type == TEAM_VOICE).all()
            for channel in channels:
                if discord_channel := self.bot.get_channel(channel.id):  # noqa: SIM102
                    if discord_channel.members == 0:
                        await discord_channel.delete()
                        session.delete(channel)
        session.commit()

    @delete_empty_team_channels.before_loop
    async def before_update(self) -> None:
        await self.bot.wait_until_ready()


    async def cog_load(self) -> None:
        self.delete_empty_team_channels.start()


    def split_teams(
        self,
        team_count: int,
        members: list[Member],
    ) -> list[TeamDict]:
        """Splits a team evenly around :param:`team_count`"""
        random.shuffle(members)
        # find divide and module by desired team size,
        # and found amount of users
        divide, modulo = divmod(len(members), team_count)
        members_count = math.ceil(divide+modulo)

        # create teams, and fill members with amount of users
        # (evenly split among each team)
        teams: list[TeamDict] = [
            {
                "id": i+1,
                "members": [
                    members[j+i*members_count] for j in range(members_count)
                ],
            }
            for i in range(team_count)
        ]

        self.logger.debug(f"created teams: {teams}")
        return teams


    async def move_team(self, team: TeamDict, channel: VoiceChannel) -> None:
        """Moves a whole team to its channel"""
        self.logger.debug(f"moving {team['members']} to {channel}")
        for user in team["members"]:
            await user.move_to(channel)


    async def create_team_channels(self, teams: list[TeamDict], category: CategoryChannel) -> tuple[list[Channel], list[VoiceChannel]]:
        """Create team channels based on a list of teams, adds those channels to database"""
        with self.session as session:
            db_channels: list[Channel] = []
            discord_channels: list[VoiceChannel] = []
            for team in teams:
                self.logger.debug(f"creating voice for {team}")
                voice = await category.create_voice_channel(name=f"Team {team['id']}")
                discord_channels.append(voice)
                db_channels.append(Channel(
                    id = voice.id,
                    name = voice.name,
                    type = TEAM_VOICE,
                    guild_id = voice.guild.id,
                ))

            session.add_all(db_channels)
            session.commit()
            return db_channels, discord_channels


    def get_team_channels(self, guild: Guild) -> list[Channel]:
        """Get all team channels from database"""
        with self.session as session:
            return session.query(Channel).where(
                Channel.type == TEAM_VOICE,
                Channel.guild_id == guild.id,
            ).all()


    def get_teams_category(self, guild: Guild | None) -> CategoryChannel | None:
        """Find a category channel"""
        with self.session as session:
            if channel := session.query(Channel).where(
                Channel.type == TEAM_CATEGORY,
                Channel.guild_id == guild.id,
            ).first():
                return self.bot.get_channel(channel.id) # type: ignore
            return None


    async def create_teams_category(self, guild: Guild | None) -> CategoryChannel:
        """Create a category channel, and a lobby voice channel"""
        channel = await guild.create_category(name="teams", reason="Creating team category for splitting into teams")
        with self.session as session:
            session.add(Channel(
                id = channel.id,
                name = channel.name,
                type = TEAM_CATEGORY,
                guild_id = guild.id,
            ),
            )
            session.commit()
        return channel


    async def fetch_teams_category(self, guild: Guild | None) -> CategoryChannel:
        """Find a category channel, if it doesn't find any, create it"""
        if category := self.get_teams_category(guild):
            return category
        return await self.create_teams_category(guild)


    def get_teams_lobby(self, guild: Guild | None) -> GTPChannel | None:
        """Find a lobby channel"""
        with self.session as session:
            if channel := session.query(Channel).where(
                Channel.type == TEAM_LOBBY,
                Channel.guild_id == guild.id,
            ).first():
                return self.bot.get_channel(channel.id)
            return None


    async def create_teams_lobby(self, category: GTPChannel | CategoryChannel) -> VoiceChannel:
        """Create a lobby channel"""
        with self.session as session:
            voice = await category.create_voice_channel(name="Lobby", reason="Creating lobby channel for moving users.")
            session.add(Channel(
                id = voice.id,
                name = voice.name,
                type = TEAM_LOBBY,
                guild_id = category.guild.id,
            ))
            session.commit()
            return voice


    async def fetch_teams_lobby(self, category: GTPChannel | CategoryChannel) -> GTPChannel | VoiceChannel:
        """Find a lobby channel, if not found create it"""
        if lobby := self.get_teams_lobby(category.guild):
            return lobby
        return await self.create_teams_lobby(category)


    async def move_from_category(self, teams: list[TeamDict], channel: VoiceChannel) -> None:
        """Handles moving members, if member not in teams lobby, they won't get moved"""
        for team in teams:
            team_to_move: TeamDict = {
                "id": team["id"],
                "members": [],
            }

            for user in team["members"]:
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
        if interaction.user.resolved_permissions.manage_channels is False:
            lobby = self.get_teams_lobby(interaction.guild)
            if lobby is None:
                raise app_commands.errors.MissingPermissions(["manage_channels"])
            await interaction.response.send_message(f"Join the teams lobby here: {lobby.mention}")
            return
        category = await self.fetch_teams_category(interaction.guild)
        lobby = await self.fetch_teams_lobby(category)
        await interaction.response.send_message(f"Join the teams lobby here: {lobby.mention}")


    @app_commands.command(name="voice", description="Randomly split all users from your voice chat, in teams")
    async def slash_team_voice(
        self,
        interaction: discord.Interaction,
        team_count: int = 2,
    ) -> None:
        try:
            members = interaction.user.voice.channel.members
        except AttributeError:
            await interaction.response.send_message(
                "Could not get users from your voice channel, are you in one?",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        category = await self.fetch_teams_category(interaction.guild)
        teams = self.split_teams(team_count, members)

        for _, channel in await self.create_team_channels(teams, category):
            await self.move_from_category(teams, channel) # type: ignore

        await interaction.edit_original_response(content="Users from your voice split among teams")


    @app_commands.command(name="text", description="Randomly split all users, shows teams in message")
    async def slash_team_text(
        self,
        interaction: discord.Interaction,
        team_count: int = 2,
    ) -> None:
        members = interaction.message.mentions

        if members is None:
            try:
                members = interaction.user.voice.channel.members
            except AttributeError:
                await interaction.response.send_message(
                    "Could not get users from your voice channel, are you in one?",
                    ephemeral=True,
                )
                return

        # self.sanitize_members_str(members)

        if len(members) < team_count:
            await interaction.response.send_message(
                f"Not enough members to fill {team_count} teams, got {len(members)} / {team_count}",
                ephemeral=True,
            )
            return

        teams = self.split_teams(team_count, members) # type: ignore

        embed = discord.Embed(
            title="Teams",
            color=random.choice(rainbow.RAINBOW),
        )

        for team in teams:
            embed.add_field(
                name=f"Team {team['id']}",
                value=f"members: {team['members']}",
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Team(bot))
