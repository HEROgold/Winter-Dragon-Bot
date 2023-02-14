import asyncio
import contextlib
import json
import logging
import math
import os
import random

import discord
from discord import app_commands
from discord.ext import commands

import config
import dragon_database

# TODO: needs testing
class Team(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(f"winter_dragon.{self.__class__.__name__}")
        self.data = None
        self.DATABASE_NAME = self.__class__.__name__
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.DATABASE_NAME}.json"
            self.setup_json()

    def setup_json(self):
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = self.data
                json.dump(data, f)
                f.close
                self.logger.info(f"{self.DATABASE_NAME} Json Created.")
        else:
            self.logger.info(f"{self.DATABASE_NAME} Json Loaded.")

    async def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = await db.get_data(self.DATABASE_NAME)
        else:
            with open(self.DBLocation, 'r') as f:
                data = json.load(f)
        return data

    async def set_data(self, data):
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation,'w') as f:
                json.dump(data, f)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.data:
            self.data = await self.get_data()
        while config.Database.PERIODIC_CLEANUP:
            await self.cleanup()
            await asyncio.sleep(60*60)

    async def cog_unload(self):
        await self.set_data(self.data)

    # FIXME: doesnt delete channels
    async def cleanup(self):
        self.logger.info("Cleaning Teams channels")
        if not self.data:
            self.data = await self.get_data()
        for guild_id in list(self.data):
            channels_list = None
            category_id = None
            with contextlib.suppress(KeyError):
                self.logger.debug(self.data)
                channels_list:list = self.data[guild_id]["Category"]["Channels"]
                category_id:int = self.data[guild_id]["Category"]["id"]
            if not category_id:
                continue
            if not channels_list:
                guild = discord.utils.get(self.bot.guilds, id=int(guild_id))
                category_channel:discord.CategoryChannel = discord.utils.get(guild.channels, id=category_id)
                await category_channel.delete()
                del self.data[guild_id]
            async for channel in self.get_teams_channels(channels_list, guild_id):
                channel:discord.VoiceChannel
                if len(channel.members) == 0:
                    await channel.delete()
                    channels_list.remove(channel.id)
        self.logger.info("Database cleaned up")
        await self.set_data(self.data)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member:discord.Member, before:discord.VoiceState, after:discord.VoiceState):
        if not self.data:
            self.data = await self.get_data()
        try:
            guild_id = str(member.guild.id)
            t = self.data[guild_id]
        except KeyError or AttributeError as e:
            return
        channel = before.channel
        guild = channel.guild
        guild_id = str(guild.id)
        with contextlib.suppress(KeyError):
            channels_list = list(self.data[guild_id]["Category"]["Channels"])
        if before.channel.id not in channels_list:
            return
        if len(channel.members) <= 0:
            voice_channel = discord.utils.get(guild.voice_channels, id=channel.id)
            await voice_channel.delete()
            channels_list.remove(voice_channel.id)
            if not channels_list:
                category_id:int = self.data[guild_id]["Category"]["id"]
                category_channel = discord.utils.get(guild.categories, id=category_id)
                for text_channel in category_channel.text_channels:
                    await text_channel.delete()
                await category_channel.delete()
                self.data_cleanup(self.data, guild_id)
                await self.set_data(self.data)

    def data_cleanup(self, data, guild_id):
        del data[guild_id]["Category"]["id"]
        del data[guild_id]["Category"]["Channels"]
        del data[guild_id]["Category"]["Votes_channel"]
        if not data[guild_id]["Category"]:
            del data[guild_id]["Category"]
        if not data[guild_id]:
            del data[guild_id]

    async def get_teams_channels(self, channels_list:list[int], guild_id:str) -> list[discord.VoiceChannel]|None:
        try:
            guild = discord.utils.get(self.bot.guilds, id=int(guild_id))
            for channel_id in channels_list:
                yield discord.utils.get(guild.voice_channels, id=channel_id)
        except KeyError:
            yield None

    async def DevideTeams(self, TeamCount:int, members:list[discord.Member]) -> dict[int,list[discord.Member]]:
        random.shuffle(members)
        teams = {}
        divide, modulo = divmod(len(members), TeamCount)
        for i in range(TeamCount):
            teams[str(i)] = {}
            for x in range(math.ceil(divide)):
                teams[str(i)][str(x)] = members.pop()
        for i in range(math.ceil(modulo)):
            teams[str(i)][str(x+1)] = members.pop()
        # Translate user object to user id's for later use.
        for k,v in teams.items():
            user_id = [j.id for j in v.values()]
            teams[str(k)] = user_id
        self.logger.info(f"creating teams: {teams}")
        return teams

    # FIXME: and test me
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction:discord.Reaction, user:discord.Member):
        if user.bot == True or reaction.emoji != "✅":
            return
        if not self.data:
            self.data = await self.get_data()
        guild = user.guild
        guild_id = str(guild.id)
        teams:dict = self.data[guild_id]["Category"]["Votes_channel"]["Teams"]
        voted = teams["voted"] or []
        # total_members = list(teams.values().count())
        for members in teams.values():
            if user.id in members:
                voted.append(user.id)
        teams["voted"] = voted
        self.logger.debug(f"teams=`{teams}`, user_id=`{user.id}`, voted=`{voted}`, temp=`{list(teams.values())}")
        if user.id in voted and reaction.count >= len(members+1):
            await reaction.message.delete()
            await self.move_members(teams, guild)

    @app_commands.command(name="teams", description="Randomly split all users in voice chat, in teams")
    @app_commands.guild_only()
    async def slash_team(self, interaction:discord.Interaction, team_count:int=2):
        # await interaction.response.send_message("Creating channels.", ephemeral=True, delete_after=5)
        await interaction.response.defer()
        try:
            members = interaction.user.voice.channel.members
        except AttributeError as e:
            await interaction.followup.send("Could not get members from voice channel.")
            return
        if len(members) < team_count:
            await interaction.followup.send(f"Not enough members in voice channel to fill {team_count} teams. Only found {len(members)}")
            return
        category_channel = await self.get_teams_category(interaction=interaction)
        teams = await self.DevideTeams(TeamCount=team_count, members=members)
        vote_channel = await self.create_vote(interaction, teams)
        await interaction.followup.send(f"Created vote to move members. Go to {vote_channel.mention} to vote.")

    async def create_vote(self, interaction:discord.Interaction, teams:dict) -> discord.TextChannel|None:
        category_channel = await self.get_teams_category(interaction=interaction)
        vote_text_channel = await self.get_votes_channel(category_channel)
        await self.send_vote_message(interaction, vote_text_channel, teams)
        return vote_text_channel

    async def send_vote_message(self, interaction:discord.Interaction, vote_text_channel:discord.TextChannel, teams:dict):
        if not self.data:
            self.data = await self.get_data()
        guild = interaction.guild
        guild_id = str(guild.id)
        vote_txt = f"{interaction.user.mention} used `/Teams`\nThe following users need to vote:"
        members = []
        for i in teams.values():
            members.extend(discord.utils.get(guild.members, id=j) for j in i)
        for member in members:
            vote_txt += f"\n{member.mention}"
        vote_msg = await vote_text_channel.send(vote_txt)
        await vote_msg.add_reaction("✅")
        await vote_msg.add_reaction("⛔")
        self.data[guild_id]["Category"]["Votes_channel"]["Teams"] = teams
        await self.set_data(self.data)

    async def get_votes_channel(self, category_channel:discord.CategoryChannel) -> discord.TextChannel:
        if not self.data:
            self.data = await self.get_data()
        guild_id = str(category_channel.guild.id)
        try:
            vote_ch_id = self.data[guild_id]["Category"]["Votes_channel"]["id"]
            vote_text_channel = discord.utils.get(category_channel.channels, id=vote_ch_id)
        except KeyError as e:
            vote_text_channel = await category_channel.create_text_channel(name="Team splits")
            self.data[guild_id]["Category"]["Votes_channel"] = {"id": vote_text_channel.id}
            await self.set_data(self.data)
        return vote_text_channel

    async def get_teams_category(self, interaction:discord.Interaction) -> discord.CategoryChannel|None:
        if not self.data:
            self.data = await self.get_data()
        guild = interaction.guild
        guild_id = str(guild.id)
        category_channel = None
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True, add_reactions=True, read_message_history=True, speak=True, send_messages=True),
            guild.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.all())
            }
        try:
            category_id:int = self.data[guild_id]["Category"]["id"]
        except KeyError:
            self.logger.info(f"Creating Teams category for {guild}")
            category_channel:discord.CategoryChannel = await guild.create_category(name="Teams", overwrites=overwrites, position=80)
            category_id = category_channel.id
            self.data[guild_id] = {"Category":{"id":category_id}}
        category_channel = discord.utils.get(guild.categories, id=category_id)
        if category_channel is None:
            del self.data[str(guild.id)]["Category"]["id"]
            category_channel = await self.get_teams_category(interaction=interaction)
        await self.set_data(self.data)
        return category_channel

    async def move_members(self, teams:dict[str,list[discord.Member]], guild:discord.Guild):
        for team, member_ids in teams.items():
            if not self.data:
                self.data = await self.get_data()
            try:
                channels_list = self.data[str(guild.id)]["Category"]["Channels"]
            except KeyError as e:
                channels_list = self.data[str(guild.id)]["Category"]["Channels"] = []
            team_number = int(team) + 1
            team_name = f"Team {team_number}"
            category_id = self.data[str(guild.id)]["Category"]["id"]
            category_channel = discord.utils.get(guild.categories, id=category_id)
            team_voice = await category_channel.create_voice_channel(name=team_name)
            channels_list.append(team_voice.id)
            for member_id in member_ids:
                self.logger.debug(f"Moving {member_id} to {team_voice}")
                member = discord.utils.get(guild.members, id=member_id)
                await member.move_to(team_voice)

async def setup(bot:commands.Bot):
	await bot.add_cog(Team(bot))