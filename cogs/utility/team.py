import contextlib
import logging
import math
import os
import pickle
import random
import re
from typing import AsyncGenerator, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
import rainbow
from tools import app_command_tools, dragon_database_Mongo

# TODO: needs testing

@app_commands.guild_only()
class Team(commands.GroupCog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        self.data = None
        self.DATABASE_NAME = self.__class__.__name__
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.DATABASE_NAME}.pkl"
            self.setup_db_file()

    def setup_db_file(self) -> None:
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "wb") as f:
                data = self.data
                pickle.dump(data, f)
                f.close
                self.logger.info(f"{self.DATABASE_NAME}.pkl Created.")
        else:
            self.logger.info(f"{self.DATABASE_NAME}.pkl File Exists.")

    def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database_Mongo.Database()
            data = db.get_data(self.DATABASE_NAME)
        elif os.path.getsize(self.DBLocation) > 0:
            with open(self.DBLocation, "rb") as f:
                data = pickle.load(f)
        return data

    def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database_Mongo.Database()
            db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "wb") as f:
                pickle.dump(data, f)

    async def cog_load(self) -> None:
        if not self.data:
            self.data = self.get_data()
        if config.Database.PERIODIC_CLEANUP:
            self.cleanup.start()

    async def cog_unload(self) -> None:
        self.set_data(self.data)

    # FIXME: doesnt delete channels
    # TODO: test if fixed/test
    # TODO: rewrite, look at AC channel
    @tasks.loop(seconds=3600)
    async def cleanup(self) -> None:
        self.logger.info("Cleaning Teams channels")
        if not self.data:
            return
        for guild_id in list(self.data):
            try:
                _ = self.data[guild_id]
    
            except (KeyError, AttributeError):
                return
            try:
                channels_list = list(self.data[guild_id]["Category"]["Channels"])
            except KeyError:
                return
            guild = discord.utils.get(self.bot.guilds, id=int(guild_id))
            if not guild or not channels_list:
                continue
            self.logger.debug(f"Cleaning {guild}")
            for channel_id in channels_list:
                channel = guild.get_channel(int(channel_id))
                if not channel:
                    a:list = self.data[guild_id]["Category"]["Channels"]
                    a.remove(channel_id)
                    continue
                self.logger.debug(f"Cleanup: {channel}")
                if type(channel) != discord.VoiceChannel:
                    self.logger.debug(f"Cleanup: Not voice, {channel}")
                    continue
                self.logger.debug(f"Cleanup: Is voice {channel}")
                if len(channel.members) > 0:
                    continue
    
                voice_channel = discord.utils.get(guild.voice_channels, id=channel.id)
                await voice_channel.delete()
                channels_list.remove(voice_channel.id)
                if channels_list:
                    continue
    
                del self.data[guild_id]["Category"]["Channels"]
                category_id: int = self.data[guild_id]["Category"]["id"]
                category_channel = discord.utils.get(guild.categories, id=category_id)
                for text_channel in category_channel.text_channels:
                    await text_channel.delete()
                await category_channel.delete()
                del self.data[guild_id]["Category"]["id"]
                self.set_data(self.data)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member:discord.Member, before:discord.VoiceState, after:discord.VoiceState) -> None:
        try:
            guild_id = str(member.guild.id)
            _ = self.data[guild_id]
        except (KeyError, AttributeError):
            return
        with contextlib.suppress(KeyError):
            channels_list = list(self.data[guild_id]["Category"]["Channels"])
        if before.channel.id not in channels_list:
            return
        channel = before.channel
        if len(channel.members) <= 0:
            guild = channel.guild
            voice_channel = discord.utils.get(guild.voice_channels, id=channel.id)
            await voice_channel.delete()
            channels_list.remove(voice_channel.id)
            if not channels_list:
                del self.data[guild_id]["Category"]["Channels"]
                category_id:int = self.data[guild_id]["Category"]["id"]
                category_channel = discord.utils.get(guild.categories, id=category_id)
                for text_channel in category_channel.text_channels:
                    await text_channel.delete()
                await category_channel.delete()
                del self.data[guild_id]["Category"]["id"]
                self.set_data(self.data)

    async def get_teams_channels(self, channels_list:list[int], guild:discord.Guild) ->  AsyncGenerator[Optional[discord.VoiceChannel], None]:
        try:
            for channel_id in channels_list:
                yield discord.utils.get(guild.voice_channels, id=channel_id)
        except KeyError:
            yield None
        return

    async def DevideTeams(self, team_count:int, members:list[discord.Member]) -> dict[int,list[str]]:
        random.shuffle(members)
        teams = {}
        divide, modulo = divmod(len(members), team_count)
        for i in range(team_count):
            teams[str(i)] = {}
            for x in range(math.ceil(divide)):
                teams[str(i)][str(x)] = members.pop()
        for i in range(math.ceil(modulo)):
            teams[str(i)][str(x+1)] = members.pop()
        # Translate user object to user id's for later use.
        for k,v in teams.items():
            user_id = [j.id for j in v.values()]
            teams[str(k)] = user_id
        self.logger.debug(f"creating teams: {teams}")
        return teams

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction:discord.Reaction, user:discord.Member) -> None:
        self.logger.debug(f"{user} reacted with {reaction}")
        if user.bot == True or reaction.emoji != "✅":
            self.logger.debug("user is bot, or emoji not ✅")
            return
        guild = user.guild
        guild_id = str(guild.id)
        if not self.data:
            self.data = self.get_data()
        return await self.vote_handler(reaction, user, guild, guild_id)

    async def vote_handler(self, reaction:discord.Reaction, user:discord.Member, guild:discord.Guild, guild_id:str) -> None:
        try:
            d_teams:dict = self.data[guild_id]["Category"]["Votes_channel"]["Teams"]
        except KeyError:
            return
        for team_key, team_group in list(d_teams.items()):
            team_group:dict
            self.logger.debug(f"teamgroup = {team_group}")
            try:
                voted = team_group["voted"]
            except KeyError:
                voted = team_group["voted"] = []
            to_vote = []
            for k, v in team_group.items():
                if k != "voted":
                    to_vote.extend(v)
            for team_id in list(team_group):
                if team_id == "voted":
                    continue
                self.logger.debug(f"team=`{team_id}`, user_id=`{user.id}`")
                if user.id not in to_vote:
                    self.logger.debug(f"removing {reaction}, {user.id}: not in {to_vote} or {user.bot}")
                    await reaction.remove(user)
                    continue
                elif user.id not in voted:
                    voted.append(user.id)
            self.logger.debug(f"to vote= {to_vote}, voted= {voted}")
            if len(voted) == len(to_vote):
                await reaction.message.delete()
                del team_group["voted"]
                await self.team_move(team_group, guild)
                del d_teams[team_key]

    @app_commands.command(
            name="voice",
            description="Randomly split all users from your voice chat, in teams"
            )
    async def slash_team_voice(
        self,
        interaction: discord.Interaction,
        team_count: int=2
    ) -> None:
        # await interaction.response.send_message("Creating channels.", ephemeral=True, delete_after=5)
        try:
            members = interaction.user.voice.channel.members
        except AttributeError:
            await interaction.response.send_message("Could not get members from voice channel.", ephemeral=True)
            return
        if len(members) < team_count:
            await interaction.response.send_message(f"Not enough members in voice channel to fill {team_count} teams. Only found {len(members)}", ephemeral=True)
            return
        await self.get_teams_category(interaction=interaction)
        teams = await self.DevideTeams(team_count=team_count, members=members)
        vote_channel = await self.create_vote(interaction, teams)
        await interaction.response.send_message(f"Created vote to move members. Go to {vote_channel.mention} to vote.", ephemeral=True)

    @app_commands.command(
            name="chat",
            description="get a random list of teams, based on members given."
    )
    async def slash_team_chat(
        self,
        interaction: discord.Interaction,
        members: str,
        team_count: int=2
    ) -> None:
        members = members.split()
        for member in members:
            reg_result = re.findall(r"<@*&*\d+>", member)[0]
            self.logger.debug(f"Getting mention, {member, reg_result}")
            if member != reg_result:
                break
        else:
            if len(members) < team_count:
                await interaction.response.send_message(f"Not enough members to fill {team_count} teams. Only got {len(members)}", ephemeral=True)
                return
            xref_members = [
                member for member in interaction.guild.members
                for chat_member in members
                if chat_member == member.mention
            ]
            self.logger.debug(f"{xref_members=}")
            await self.get_teams_category(interaction=interaction)
            teams = await self.DevideTeams(team_count=team_count, members=xref_members)
            embed = discord.Embed(
                title="Teams",
                color=random.choice(rainbow.RAINBOW),
            )
            for team, team_members in teams.items():
                members = [discord.utils.get(interaction.guild.members, id=j).mention for j in team_members]
                embed.add_field(name=team, value=members)
            await interaction.response.send_message(embed=embed)
            return
        # when loop doesn't complete completely, continue from here
        await interaction.response.send_message(
            f"{member} was not a mentioned user. Please mention members like so:\n<@!{self.bot.user.id}>, <@!216308400336797706>",
            ephemeral=True
        )

    async def create_vote(self, interaction:discord.Interaction, teams:dict) -> discord.TextChannel|None:
        category_channel = await self.get_teams_category(interaction=interaction)
        vote_text_channel = await self.get_votes_channel(category_channel)
        await self.send_vote_message(interaction, vote_text_channel, teams)
        return vote_text_channel

    async def send_vote_message(self, interaction:discord.Interaction, vote_text_channel:discord.TextChannel, teams:dict) -> None:
        if not self.data:
            self.data = self.get_data()
        guild = interaction.guild
        guild_id = str(guild.id)
        cmd = await app_command_tools.Converter(bot=self.bot).get_app_command(self.slash_team_voice)
        vote_txt = f"{interaction.user.mention} used {cmd.mention}\nThe following users need to vote:"
        for team, team_members in teams.items():
            vote_txt += f"\nTeam {int(team) + 1}"
            members = [discord.utils.get(guild.members, id=j) for j in team_members]
            for member in members:
                vote_txt += f"\n{member.mention}"
        vote_msg = await vote_text_channel.send(vote_txt)
        await vote_msg.add_reaction("✅")
        await vote_msg.add_reaction("⛔")
        try:
            d_teams:dict = self.data[guild_id]["Category"]["Votes_channel"]["Teams"]
        except KeyError:
            d_teams = self.data[guild_id]["Category"]["Votes_channel"]["Teams"] = {}
        index = str(len(d_teams.keys()))
        d_teams[index] = teams
        # self.logger.debug(f"teams:{teams}, index:{index}, dteams{d_teams}")
        self.set_data(self.data)

    async def get_votes_channel(self, category_channel:discord.CategoryChannel) -> discord.TextChannel:
        if not self.data:
            self.data = self.get_data()
        guild_id = str(category_channel.guild.id)
        try:
            vote_ch_id = self.data[guild_id]["Category"]["Votes_channel"]["id"]
            vote_text_channel = discord.utils.get(category_channel.channels, id=vote_ch_id)
        except KeyError:
            vote_text_channel = await category_channel.create_text_channel(name="Team splits")
            self.data[guild_id]["Category"]["Votes_channel"] = {"id": vote_text_channel.id}
            self.set_data(self.data)
        return vote_text_channel

    async def get_teams_category(self, interaction:discord.Interaction) -> discord.CategoryChannel|None:
        if not self.data:
            self.data = self.get_data()
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
        self.set_data(self.data)
        return category_channel

    async def team_move(self, teams:dict[str,list[discord.Member]], guild:discord.Guild) -> None:
        for team, member_ids in teams.items():
            if not self.data:
                self.data = self.get_data()
            try:
                channels_list = self.data[str(guild.id)]["Category"]["Channels"]
            except KeyError:
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

async def setup(bot:commands.Bot) -> None:
	await bot.add_cog(Team(bot))