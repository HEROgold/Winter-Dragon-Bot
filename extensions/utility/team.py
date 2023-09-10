import math
import random
import re
from typing import TypedDict

import discord
from discord.ext import tasks
from discord import (
    Member,
    app_commands,
    CategoryChannel,
    VoiceChannel,
    Guild
)

import tools.rainbow as rainbow
from tools.database_tables import Channel, Session, engine
from _types.cogs import GroupCog
from _types.bot import WinterDragon

# TODO: rewrite for sql

# psuedo code to help remember structure in future.
# not sure if User() works inside Teamdb()
# See user lobby association table
# users = [User]
# 
# team = Teamdb(
#     id = None
#     )


# @app_commands.guild_only()
# class Team(GroupCog):
#     def __init__(self, bot: WinterDragon) -> None:
#         self.bot = bot
#         self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")


#     # TODO: rewrite, look at AC channel, sql
#     @tasks.loop(seconds=3600)
#     async def cleanup(self) -> None:
#         self.logger.info("Cleaning Teams channels")
#         if not self.data:
#             return
#         for guild_id in list(self.data):
#             try:
#                 _ = self.data[guild_id]
#             except (KeyError, AttributeError):
#                 return
#             try:
#                 channels_list = list(self.data[guild_id]["Category"]["Channels"])
#             except KeyError:
#                 return
#             guild = discord.utils.get(self.bot.guilds, id=int(guild_id))
#             if not guild or not channels_list:
#                 continue
#             self.logger.debug(f"Cleaning {guild}")
#             for channel_id in channels_list:
#                 channel = guild.get_channel(int(channel_id))
#                 if not channel:
#                     a:list = self.data[guild_id]["Category"]["Channels"]
#                     a.remove(channel_id)
#                     continue
#                 self.logger.debug(f"Cleanup: {channel}")
#                 if type(channel) != VoiceChannel:
#                     self.logger.debug(f"Cleanup: Not voice, {channel}")
#                     continue
#                 self.logger.debug(f"Cleanup: Is voice {channel}")
#                 if len(channel.members) > 0:
#                     continue

#                 voice_channel = discord.utils.get(guild.voice_channels, id=channel.id)
#                 await voice_channel.delete()
#                 channels_list.remove(voice_channel.id)
#                 if channels_list:
#                     continue

#                 del self.data[guild_id]["Category"]["Channels"]
#                 category_id: int = self.data[guild_id]["Category"]["id"]
#                 category_channel = discord.utils.get(guild.categories, id=category_id)
#                 for text_channel in category_channel.text_channels:
#                     await text_channel.delete()
#                 await category_channel.delete()
#                 del self.data[guild_id]["Category"]["id"]
#                 self.set_data(self.data)


#     @Cog.listener()
#     async def on_voice_state_update(self, member:discord.Member, before:discord.VoiceState, after:discord.VoiceState) -> None:
#         self.logger.debug(f"{member} moved from {before} to {after}")
#         # return early if no guild is found.
#         try:
#             guild_id = str(member.guild.id)
#             _ = self.data[guild_id]
#         except (KeyError, AttributeError):
#             return
#         # ignore empty channels list
#         try:
#             channels_list = list(self.data[guild_id]["Category"]["Channels"])
#         except KeyError:
#             pass
#         if before.channel.id not in channels_list:
#             return
#         channel = before.channel
#         if len(channel.members) <= 0:
#             guild = channel.guild
#             voice_channel = discord.utils.get(guild.voice_channels, id=channel.id)
#             await voice_channel.delete()
#             channels_list.remove(voice_channel.id)
#             if not channels_list:
#                 del self.data[guild_id]["Category"]["Channels"]
#                 category_id:int = self.data[guild_id]["Category"]["id"]
#                 category_channel = discord.utils.get(guild.categories, id=category_id)
#                 for text_channel in category_channel.text_channels:
#                     await text_channel.delete()
#                 await category_channel.delete()
#                 del self.data[guild_id]["Category"]["id"]
#                 self.set_data(self.data)


#     async def get_teams_channels(self, channels_list:list[int], guild:discord.Guild) ->  AsyncGenerator[Optional[VoiceChannel], None]:
#         try:
#             for channel_id in channels_list:
#                 yield discord.utils.get(guild.voice_channels, id=channel_id)
#         except KeyError:
#             yield None
#         return


#     async def divide_teams(self, team_count: int, members: list[discord.Member]) -> dict[int,list[str]]:
#         random.shuffle(members)
#         teams = {}
#         divide, modulo = divmod(len(members), team_count)
#         for i in range(team_count):
#             teams[str(i)] = {}
#             for x in range(math.ceil(divide)):
#                 teams[str(i)][str(x)] = members.pop()
#         for i in range(math.ceil(modulo)):
#             teams[str(i)][str(x+1)] = members.pop()
#         # Translate user object to user id's for later use.
#         for k,v in teams.items():
#             user_id = [j.id for j in v.values()]
#             teams[str(k)] = user_id
#         self.logger.debug(f"creating teams: {teams}")
#         return teams


#     @Cog.listener()
#     async def on_reaction_add(self, reaction:discord.Reaction, user:discord.Member) -> None:
#         self.logger.debug(f"{user} reacted with {reaction}")
#         if user.bot == True or reaction.emoji != "✅":
#             self.logger.debug("user is bot, or emoji not ✅")
#             return
#         guild = user.guild
#         guild_id = str(guild.id)
#         if not self.data:
#             self.data = self.get_data()
#         return await self.vote_handler(reaction, user, guild, guild_id)


#     async def vote_handler(self, reaction:discord.Reaction, user:discord.Member, guild:discord.Guild, guild_id:str) -> None:
#         try:
#             d_teams:dict = self.data[guild_id]["Category"]["Votes_channel"]["Teams"]
#         except KeyError:
#             return
#         for team_key, team_group in list(d_teams.items()):
#             team_group:dict
#             self.logger.debug(f"teamgroup = {team_group}")
#             try:
#                 voted = team_group["voted"]
#             except KeyError:
#                 voted = team_group["voted"] = []
#             to_vote = []
#             for k, v in team_group.items():
#                 if k != "voted":
#                     to_vote.extend(v)
#             for team_id in list(team_group):
#                 if team_id == "voted":
#                     continue
#                 self.logger.debug(f"{team_id=}, {user.id=}")
#                 if user.id not in to_vote:
#                     self.logger.debug(f"removing {reaction}, {user.id}: not in {to_vote} or {user.bot}")
#                     await reaction.remove(user)
#                     continue
#                 elif user.id not in voted:
#                     voted.append(user.id)
#             self.logger.debug(f"to vote= {to_vote}, voted= {voted}")
#             if len(voted) == len(to_vote):
#                 await reaction.message.delete()
#                 del team_group["voted"]
#                 await self.team_move(team_group, guild)
#                 del d_teams[team_key]


#     @app_commands.command(
#             name="voice",
#             description="Randomly split all users from your voice chat, in teams"
#             )
#     async def slash_team_voice(
#         self,
#         interaction: discord.Interaction,
#         team_count: int=2
#     ) -> None:
#         # await interaction.response.send_message("Creating channels.", ephemeral=True, delete_after=5)
#         try:
#             members = interaction.user.voice.channel.members
#         except AttributeError:
#             await interaction.response.send_message("Could not get members from voice channel.", ephemeral=True)
#             return
#         if len(members) < team_count:
#             await interaction.response.send_message(f"Not enough members in voice channel to fill {team_count} teams. Only found {len(members)}", ephemeral=True)
#             return
#         await self.get_teams_category(interaction=interaction)
#         teams = await self.divide_teams(team_count=team_count, members=members)
#         vote_channel = await self.create_vote(interaction, teams)
#         await interaction.response.send_message(f"Created vote to move members. Go to {vote_channel.mention} to vote.", ephemeral=True)


#     @app_commands.command(
#             name="chat",
#             description="get a random list of teams, based on members given."
#     )
#     async def slash_team_chat(
#         self,
#         interaction: discord.Interaction,
#         members: str,
#         team_count: int=2
#     ) -> None:
#         members = members.split()
#         for member in members:
#             reg_result = re.findall(r"<@*&*\d+>", member)[0]
#             self.logger.debug(f"Getting mention, {member, reg_result}")
#             if member != reg_result:
#                 break
#         else:
#             if len(members) < team_count:
#                 await interaction.response.send_message(f"Not enough members to fill {team_count} teams. Only got {len(members)}", ephemeral=True)
#                 return
#             xref_members = [
#                 member for member in interaction.guild.members
#                 for chat_member in members
#                 if chat_member == member.mention
#             ]
#             self.logger.debug(f"{xref_members=}")
#             await self.get_teams_category(interaction=interaction)
#             teams = await self.divide_teams(team_count=team_count, members=xref_members)
#             embed = discord.Embed(
#                 title="Teams",
#                 color=random.choice(rainbow.RAINBOW),
#             )
#             for team, team_members in teams.items():
#                 members = [discord.utils.get(interaction.guild.members, id=j).mention for j in team_members]
#                 embed.add_field(name=team, value=members)
#             await interaction.response.send_message(embed=embed)
#             return
#         # when loop doesn't complete completely, continue from here
#         await interaction.response.send_message(
#             f"{member} was not a mentioned user. Please mention members like so:\n<@!{self.bot.user.id}>, <@!216308400336797706>",
#             ephemeral=True
#         )


#     async def create_vote(self, interaction:discord.Interaction, teams:dict) -> discord.TextChannel|None:
#         category_channel = await self.get_teams_category(interaction=interaction)
#         vote_text_channel = await self.get_votes_channel(category_channel)
#         await self.send_vote_message(interaction, vote_text_channel, teams)
#         return vote_text_channel


#     async def send_vote_message(self, interaction:discord.Interaction, vote_text_channel:discord.TextChannel, teams:dict) -> None:
#         if not self.data:
#             self.data = self.get_data()
#         guild = interaction.guild
#         guild_id = str(guild.id)
#         cmd = await app_command_tools.Converter(bot=self.bot).get_app_command(self.slash_team_voice)
#         vote_txt = f"{interaction.user.mention} used {cmd.mention}\nThe following users need to vote:"
#         for team, team_members in teams.items():
#             vote_txt += f"\nTeam {int(team) + 1}"
#             members = [discord.utils.get(guild.members, id=j) for j in team_members]
#             for member in members:
#                 vote_txt += f"\n{member.mention}"
#         vote_msg = await vote_text_channel.send(vote_txt)
#         await vote_msg.add_reaction("✅")
#         await vote_msg.add_reaction("⛔")
#         try:
#             d_teams:dict = self.data[guild_id]["Category"]["Votes_channel"]["Teams"]
#         except KeyError:
#             d_teams = self.data[guild_id]["Category"]["Votes_channel"]["Teams"] = {}
#         index = str(len(d_teams.keys()))
#         d_teams[index] = teams
#         # self.logger.debug(f"teams:{teams}, index:{index}, dteams{d_teams}")
#         self.set_data(self.data)


#     async def get_votes_channel(self, category_channel:CategoryChannel) -> discord.TextChannel:
#         if not self.data:
#             self.data = self.get_data()
#         guild_id = str(category_channel.guild.id)
#         try:
#             vote_ch_id = self.data[guild_id]["Category"]["Votes_channel"]["id"]
#             vote_text_channel = discord.utils.get(category_channel.channels, id=vote_ch_id)
#         except KeyError:
#             vote_text_channel = await category_channel.create_text_channel(name="Team splits")
#             self.data[guild_id]["Category"]["Votes_channel"] = {"id": vote_text_channel.id}
#             self.set_data(self.data)
#         return vote_text_channel


#     async def get_teams_category(self, interaction:discord.Interaction) -> CategoryChannel|None:
#         if not self.data:
#             self.data = self.get_data()
#         guild = interaction.guild
#         guild_id = str(guild.id)
#         category_channel = None
#         overwrites = {
#             guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True, add_reactions=True, read_message_history=True, speak=True, send_messages=True),
#             guild.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.all())
#             }
#         try:
#             category_id:int = self.data[guild_id]["Category"]["id"]
#         except KeyError:
#             self.logger.info(f"Creating Teams category for {guild}")
#             category_channel:CategoryChannel = await guild.create_category(name="Teams", overwrites=overwrites, position=80)
#             category_id = category_channel.id
#             self.data[guild_id] = {"Category":{"id":category_id}}
#         category_channel = discord.utils.get(guild.categories, id=category_id)
#         if category_channel is None:
#             del self.data[str(guild.id)]["Category"]["id"]
#             category_channel = await self.get_teams_category(interaction=interaction)
#         self.set_data(self.data)
#         return category_channel


#     async def team_move(self, teams:dict[str,list[discord.Member]], guild:discord.Guild) -> None:
#         for team, member_ids in teams.items():
#             if not self.data:
#                 self.data = self.get_data()
#             try:
#                 channels_list = self.data[str(guild.id)]["Category"]["Channels"]
#             except KeyError:
#                 channels_list = self.data[str(guild.id)]["Category"]["Channels"] = []
#             team_number = int(team) + 1
#             team_name = f"Team {team_number}"
#             category_id = self.data[str(guild.id)]["Category"]["id"]
#             category_channel = discord.utils.get(guild.categories, id=category_id)
#             team_voice = await category_channel.create_voice_channel(name=team_name)
#             channels_list.append(team_voice.id)
#             for member_id in member_ids:
#                 self.logger.debug(f"Moving {member_id} to {team_voice}")
#                 member = discord.utils.get(guild.members, id=member_id)
#                 await member.move_to(team_voice)



TEAM_VOICE_TYPE = "TeamsVoice"
TEAM_CATEGORY_TYPE = "TeamsCategory"
TEAM_LOBBY_TYPE = "TeamsLobby"


class TeamDict(TypedDict):
    id: int
    members: list[discord.User | discord.Member]


@app_commands.guild_only()
class Team(GroupCog):

    @tasks.loop(seconds=3600)
    async def delete_empty_team_channels(self) -> None:
        """Delete any empty team channel"""
        with Session(engine) as session:
            channels = session.query(Channel).where(Channel.type == TEAM_VOICE_TYPE).all()
            for channel in channels:
                discord_channel = self.bot.get_channel(channel.id)
                if discord_channel.members == 0:
                    await discord_channel.delete()
                    session.delete(channel)
        session.commit()

    @delete_empty_team_channels.before_loop
    async def before_update(self) -> None:
        self.logger.info("Waiting until bot is online")
        await self.bot.wait_until_ready()


    async def cog_load(self) -> None:
        self.delete_empty_team_channels.start()


    def split_teams(
        self,
        team_count: int,
        members: list[discord.User | discord.Member]
    ) -> list[TeamDict]:
        """Splits a team evenly around :param:`team_count`"""
        random.shuffle(members)
        # find divide and module by desired team size,
        # and found amount of users
        divide, modulo = divmod(len(members), team_count)

        # create teams, and fill members with amount of users
        # (evenly split among each team)
        teams: list[TeamDict] = [
            {
                "id": i+1,
                "members": [
                    members.pop() for _ in range(math.ceil(divide))
                ].extend(members.pop() for _ in range(math.ceil(modulo))),
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
        with Session(engine) as session:
            db_channels: list[Channel] = []
            discord_channels: list[VoiceChannel] = []
            for team in teams:
                self.logger.debug(f"creating voice for {team}")
                voice = await category.create_voice_channel(name=f"Team {team['id']}")
                discord_channels.append(voice)
                db_channels.append(Channel(
                    id = voice.id,
                    name = voice.name,
                    type = TEAM_VOICE_TYPE,
                    guild_id = voice.guild.id,
                ))

            session.add_all(db_channels)
            session.commit()
            return db_channels, discord_channels


    def get_team_channels(self, guild: Guild) -> list[Channel]:
        """Get all team channels from database"""
        with Session(engine) as session:
            return session.query(Channel).where(
                Channel.type == TEAM_VOICE_TYPE,
                Channel.guild_id == guild.id
            ).all()


    def get_teams_category(self, guild: Guild) -> CategoryChannel:
        """Find a category channel"""
        with Session(engine) as session:
            if channel := session.query(Channel).where(
                Channel.type == TEAM_CATEGORY_TYPE,
                Channel.guild_id == guild.id
            ).first():
                return self.bot.get_channel(channel.id)


    async def create_teams_category(self, guild: Guild) -> CategoryChannel:
        """Create a category channel, and a lobby voice channel"""
        channel = await guild.create_category(name="teams", reason="Creating team category for splitting into teams")
        with Session(engine) as session:
            session.add(Channel(
                id = channel.id,
                name = channel.name,
                type = TEAM_CATEGORY_TYPE,
                guild_id = guild.id
            )
            )
            session.commit()
        return channel


    async def fetch_teams_category(self, guild: Guild) -> CategoryChannel:
        """Find a category channel, if it doesn't find any, create it"""
        if category := self.get_teams_category(guild):
            return category
        return await self.create_teams_category(guild)


    def get_teams_lobby(self, guild: Guild) -> VoiceChannel:
        """Find a lobby channel"""
        with Session(engine) as session:
            if channel := session.query(Channel).where(
                Channel.type == TEAM_LOBBY_TYPE,
                Channel.guild_id == guild.id
            ).first():
                return self.bot.get_channel(channel.id)


    async def create_teams_lobby(self, category: CategoryChannel) -> VoiceChannel:
        """Create a lobby channel"""
        with Session(engine) as session:
            voice = await category.create_voice_channel(name="Lobby", reason="Creating lobby channel for moving users.")
            session.add(Channel(
                id = voice.id,
                name = voice.name,
                type = TEAM_LOBBY_TYPE,
                guild_id = category.guild.id
            ))
            session.commit()
            return voice


    async def fetch_teams_lobby(self, category: CategoryChannel) -> VoiceChannel | None:
        """Find a lobby channel, if not found create it"""
        if lobby := self.get_teams_lobby(category.guild):
            return lobby
        return await self.create_teams_lobby(category)


    async def move_from_category(self, teams: list[TeamDict], channel: VoiceChannel):
        """Handles moving members, if member not in teams lobby, they won't get moved"""
        for team in teams:
            team_to_move: TeamDict = {
                "id": team["id"],
            }

            for user in team["members"]:
                if user.voice.channel == self.get_teams_lobby(channel.guild):
                    team_to_move["members"] += user
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
        if interaction.user.resolved_permissions.manage_channels == False:
            lobby = self.get_teams_lobby(interaction.guild)
            if lobby is None:
                raise app_commands.errors.MissingPermissions(["manage_channels"])
            await interaction.response.send_message(f"Join the teams lobby here: {lobby.mention}")
            return
        else:
            category = await self.fetch_teams_category(interaction.guild)
            lobby = await self.fetch_teams_lobby(category)
            await interaction.response.send_message(f"Join the teams lobby here: {lobby.mention}")


    @app_commands.command(name="voice", description="Randomly split all users from your voice chat, in teams")
    async def slash_team_voice(
        self,
        interaction: discord.Interaction,
        team_count: int = 2
    ) -> None:
        try:
            voice_members = interaction.user.voice.channel.members
        except AttributeError:
            await interaction.response.send_message(
                "Could not get users from your voice channel, are you in one?",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        category = await self.fetch_teams_category(interaction.guild)
        teams = self.split_teams(team_count, voice_members)

        for _, channel in await self.create_team_channels(teams, category):
            await self.move_from_category(teams, channel)

        await interaction.followup.edit_message("Users from your voice split among teams")


    # FIXME: dc_member is None
    # TODO: add debugs
    def sanitize_members_str(self, members: str) -> list[Member]:
        sanitized: list[Member] = []
        for member in members.split():
            member_id = member[2:-1]
            reg_result = re.search(r"<@*&*\d+>", member)
            dc_member = discord.utils.get(list(self.bot.get_all_members()), id=member_id)
            self.logger.debug(f"Getting member from text, {member=}, {reg_result=}, {dc_member=}")
            if member_id != dc_member.id:
                continue
            sanitized.append(dc_member)
        return sanitized


    @app_commands.command(name="text", description="Randomly split all users, shows teams in message")
    async def slash_team_text(
        self,
        interaction: discord.Interaction,
        members: str,
        team_count: int = 2,
    ) -> None:
        if members is None:
            try:
                members = interaction.user.voice.channel.members
            except AttributeError:
                await interaction.response.send_message(
                    "Could not get users from your voice channel, are you in one?",
                    ephemeral=True
                )
                return

        self.sanitize_members_str(members)

        if len(members) < team_count:
            await interaction.response.send_message(
                f"Not enough members to fill {team_count} teams, got {len(members)} / {team_count}",
                ephemeral=True
            )
            return

        teams = self.split_teams(team_count, members)

        embed = discord.Embed(
            title="Teams",
            color=random.choice(rainbow.RAINBOW)
        )

        for team in teams:
            embed.add_field(
                name=f"Team {team['id']}",
                value=f"members: {team['members']}"
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot: WinterDragon) -> None:
	await bot.add_cog(Team(bot))
