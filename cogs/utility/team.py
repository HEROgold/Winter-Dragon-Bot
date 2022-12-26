import logging
import discord
import math
import random
import os
import json
from discord.ext import commands
from discord import app_commands

class TeamSlash(commands.Cog):
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot:commands.Bot = bot
        self.DBLocation = "./Database/Teams.json"
        self.setup_db()

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info("Cleaning Teams channels")
        data = await self.get_data()
        for guild_id in list(data):
            channels_list:list = data[guild_id]["Category"]["Channels"]
            async for channel in self.get_teams_channels(channels_list, guild_id):
                channel:discord.VoiceChannel
                if len(channel.members) == 0:
                    await channel.delete()
                    channels_list.remove(channel.id)
            if not channels_list:
                category_id:int = data[guild_id]["Category"]["id"]
                guild = discord.utils.get(self.bot.guilds, id=int(guild_id))
                category_channel:discord.CategoryChannel = discord.utils.get(guild.channels, id=category_id)
                await category_channel.delete()
                del data[guild_id]
        await self.set_data(data)
        logging.info("Teams cleaned")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member:discord.Member, before:discord.VoiceState, after:discord.VoiceState):
        data = await self.get_data()
        try:
            t = data[guild_id]
        except KeyError:
            return
        channel = before.channel
        guild = channel.guild
        guild_id = str(guild.id)
        channels_list:list = data[guild_id]["Category"]["Channels"]
        if before.channel.id not in channels_list:
            return
        if len(channel.members) <= 0:
            voice_channel = discord.utils.get(guild.voice_channels, id=channel.id)
            await voice_channel.delete()
            channels_list.remove(voice_channel.id)
            if not channels_list:
                category_id:int = data[guild_id]["Category"]["id"]
                category_channel = discord.utils.get(guild.categories, id=category_id)
                await category_channel.delete()
                self.data_cleanup(data, guild_id)
            await self.set_data(data)

    def data_cleanup(self, data, guild_id):
        del data[guild_id]["Category"]["id"]
        del data[guild_id]["Category"]["Channels"]
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

    def setup_db(self):
        # Create database if it doesn't exist, else load it
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                logging.info("Teams Json Created.")
        else:
            logging.info("Teams Json Loaded.")

    # Helper functions to laod and update database
    async def get_data(self) -> dict[str, dict[str, dict[str, int | list]]]:
        with open(self.DBLocation, 'r') as f:
            data = json.load(f)
        return data

    async def set_data(self, data:dict):
        with open(self.DBLocation,'w') as f:
            json.dump(data, f)

    async def CreateVoiceChannel(self, guild:discord.Guild, CategoryChannel:discord.CategoryChannel, ChannelName:str) -> discord.VoiceChannel:
        # sourcery skip: assign-if-exp, inline-immediately-returned-variable, lift-return-into-if, swap-if-expression
        if not CategoryChannel:
            VoiceChannel = await guild.create_voice_channel(name=ChannelName)
        else:
            VoiceChannel = await CategoryChannel.create_voice_channel(name=ChannelName)
        return VoiceChannel

    async def DevideTeams(self, TeamCount:int, members:list[discord.Member]) -> dict[int,list[discord.Member]]:
        random.shuffle(members)
        teams = {}
        divide, modulo = divmod(len(members), TeamCount)
        for i in range(TeamCount):
            teams[i] = {}
            for x in range(math.ceil(divide)):
                teams[i][x] = members.pop()
        for i in range(math.ceil(modulo)):
            teams[i][x+1] = members.pop()
        # Translate user object to user id's for later use.
        for k,v in teams.items():
            user_id = [j.id for j in v.values()]
            teams[k] = user_id
        logging.info(f"teams: {teams}")
        return teams

# TODO: Add vote system to command.
    @app_commands.command(name="teams", description="Randomly split all users in voice chat, in teams")
    async def slash_team(self, interaction:discord.Interaction, team_count:int=2):
        try:
            members = interaction.user.voice.channel.members
        except AttributeError as e:
            await interaction.response.send_message("Could not get members from voice channel.", ephemeral=True)
            return
        if len(members) < team_count:
            await interaction.response.send_message(f"Not enough members in voice channel to fill {team_count} teams. Only found {len(members)}")
            return
        guild = interaction.guild
        category_channel = await self.get_teams_category(interaction=interaction)
        teams = await self.DevideTeams(TeamCount=team_count, members=members)
        await interaction.response.send_message("Splitting teams, Have fun!")
        await self.move_members(category_channel, teams, guild)

    async def get_teams_category(self, interaction:discord.Interaction) -> discord.CategoryChannel|None:
        data = await self.get_data()
        guild = interaction.guild
        guild_id = str(guild.id)
        category_channel = None
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(),
            guild.me: discord.PermissionOverwrite.from_pair(discord.Permissions.all_channel(), discord.Permissions.all())
            }
        try:
            category_id:int = data[guild_id]["Category"]["id"]
        except KeyError:
            logging.info(f"Creating Teams category for {guild}")
            category_channel:discord.CategoryChannel = await guild.create_category(name="Teams", overwrites=overwrites, position=10)
            category_id = category_channel.id
            data[guild_id] = {"Category":{"id":category_id}}
            await self.set_data(data)
        category_channel = discord.utils.get(guild.categories, id=category_id)
        if category_channel is None:
            del data[str(guild.id)]["Category"]["id"]
            await self.set_data(data)
            category_channel = await self.get_teams_category(interaction=interaction)
        return category_channel

    async def move_members(self, category_channel:discord.CategoryChannel, teams:dict[int,list[discord.Member]], guild:discord.Guild):
        for team, member_ids in teams.items():
            data = await self.get_data()
            try:
                channels_list = data[str(category_channel.guild.id)]["Category"]["Channels"]
            except KeyError as e:
                channels_list = data[str(category_channel.guild.id)]["Category"]["Channels"] = []
            team_name = f"Team {team+1}"
            team_voice = await self.CreateVoiceChannel(guild, category_channel, team_name)
            channels_list.append(team_voice.id)
            await self.set_data(data)
            for member_id in member_ids:
                logging.info(f"Moving {member_id} to {team_voice}")
                member = discord.utils.get(guild.members, id=member_id)
                await member.move_to(team_voice)

async def setup(bot:commands.Bot):
	await bot.add_cog(TeamSlash(bot))