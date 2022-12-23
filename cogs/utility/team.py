import logging
import discord
import math
import random
import os
import json
import config
import asyncio
import contextlib
from discord.ext import commands
from discord.ui import Button, View
from discord import app_commands

# TODO: Rewrite, Take info from Autochannel.py

class Team(commands.Cog):
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot:commands.Bot = bot
        self.DBLocation = "./Database/Teams.json"
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
    async def get_data(self):
        with open(self.DBLocation, 'r') as f:
            data = json.load(f)
        return data

    async def set_data(self, data):
        with open(self.DBLocation,'w') as f:
            json.dump(data, f)

    @commands.Cog.listener()
    async def on_ready(self):
        # Delete empty channels, and categories every hour since startup.
        # When loaded, loop over all guilds, and check if they are in DB
        while True:
            logging.info("Cleaning Team Channels...")
            with contextlib.suppress(Exception):
                data = await self.get_data()
                for guild in self.bot.guilds:
                    for category in guild.categories:
                        Category_id = data[str(guild.id)]["CategoryChannelId"]
                        for channel in category.voice_channels:
                            if int(channel.id) in (data[str(guild.id)][Category_id]).values():
                                logging.info(f"Channel: {channel}")
                                if len(channel.members) <= 0:
                                    await channel.delete()
                                    del data[str(guild.id)][Category_id][channel.name]
                        if len(category.voice_channels) <= 0:
                            await category.delete()
                            del data[str(guild.id)]["CategoryChannelId"]
                            del data[str(guild.id)][Category_id]
            await self.set_data(data)
            logging.info("Team Channels Cleaned.")
            await asyncio.sleep(60*60)

    async def CreateButton(self, label:str, style:discord.ButtonStyle):
        return Button(label=label, style=style)

    async def CreateCategoryChannel(self, ctx:commands.Context, overwrites, ChannelName:str):
        return await ctx.guild.create_category(name=ChannelName, overwrites=overwrites, position=10)

    async def CreateVoiceChannel(self, ctx:commands.Context, CategoryChannel, ChannelName:str):
        # sourcery skip: assign-if-exp, inline-immediately-returned-variable, lift-return-into-if, swap-if-expression
        if not CategoryChannel:
            VoiceChannel = await ctx.guild.create_voice_channel(name = ChannelName)
        else:
            VoiceChannel = await CategoryChannel.create_voice_channel(name = ChannelName)
        return VoiceChannel

#    # WIP!
#   Error: In command 'teams_temp' defined in function 'Team.slash_team', In parameter 'TeamCount', name: Command name is invalid
#    @app_commands.command(name="teams", description="Split the current voice chat into teams!")
#    async def slash_team(self, interaction:discord.Interaction, TeamCount:int=2):
#        try:
#            VcMembers = interaction.user.voice.channel.members
#        except Exception as e:
#            interaction.response.send_message("Could not get a list of users in your voice channel", ephemeral=True)
#            logging.info(e)
#        if len(VcMembers) >= TeamCount:
#            teams = await self.DevideTeams(TeamCount=TeamCount, members=VcMembers)
#            category_channel = interaction.guild.create_category(name="Teams")
#            data = await self.get_data()
#            data[str(interaction.guild.id)]["CategoryChannelId"] = str(category_channel.id)
#            for team, members in teams.items():
#                category_channel:discord.CategoryChannel
#                TeamName = f"Team {team}"
#                voice_channel = category_channel.create_voice_channel(name=TeamName)
#                data[str(interaction.guild.id)][str(category_channel.id)][TeamName] = voice_channel.id
#                for member in members:
#                    member:discord.Member
#                    member.move_to(voice_channel)
#        else:
#            interaction.response.send_message(f"Not enough users to fill {TeamCount} teams.", ephemeral=True)

    async def DevideTeams(self, TeamCount:int, members) -> dict:
        random.shuffle(members)
        teams = {}
        divide, modulo = divmod(len(members), TeamCount)
        for i in range(TeamCount):
            teams[i] = {}
            for x in range(math.ceil(divide)):
                teams[i][x] = members.pop()
        for i in range(math.ceil(modulo)):
            teams[i][x+1] = members.pop()
        for k,v in teams.items():
            NameList = [str(j) for j in v.values()]
            teams[k] = NameList
        logging.info(teams)
        return teams

    @commands.command(name = "team",
                    usage="`team [TeamCount] [Names]`:\n Example: `team 2 @User1 @user2 @user3`,\n`team 2 User1 User2`,\n`team 2` ",
                    description = "Use the team command to create an X number of teams and fill them evenly with all provided `names` or `mentioned users`. Without adding ANY names, it grabs all users in current voice chat and creates teams based on those members.",
                    brief = "Quickly create teams, or split your voice chat into teams")
    @commands.guild_only()
    @commands.has_permissions()
    @commands.bot_has_permissions()
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def team(self, ctx:commands.Context, TeamCount:int=2, *, Names:str=None):
        logging.info(TeamCount, Names)
        # Check if user supplied names or just used it without names
        if not Names:
            UserPing = ""
            Names = []
            FromVc = True
            try:
                VcMembers = ctx.message.author.voice.channel.members
            except:
                if config.team.dm_instead == True:
                    dm = await ctx.author.create_dm()
                    await dm.send(f"Could not get users in your voice channel, are you in one? if not, try the `help team` command!")
                    return
                else:
                    ctx.send(f"Could not get users in your voice channel, are you in one? if not, try the `help team` command!")
                    return
            logging.info(F"VcMembers: {VcMembers}")
            # Check if user is alone in VoiceChannel or not.
            if len(VcMembers) > 1:
                for Member in VcMembers:
                    UserPing += f"<@{Member.id}>\n" # Use this only in embed
                Names = UserPing
            else:
                if config.team.dm_instead == True:
                    dm = await ctx.author.create_dm()
                    await dm.send(f"Could not get enough users in your voice channel. (More then 1 required)")
                    return
                else:
                    ctx.send(f"Could not get enough users in your voice channel. (More then 1 required)")
                    return
        else:
            logging.info(f"Names: {Names}")
            FromVc = False
        # Check if Names is already a list, then pass it to SplitNames.
        # else, (expected) split the string into a list of names 
        if isinstance(Names, list):
            SplitNames = Names
        else:
            SplitNames = Names.split()
        length = len(SplitNames)
        random.shuffle(SplitNames)
        divide = length // TeamCount
        modulo = length % TeamCount
        em = discord.Embed(title="Teams List!", colour=(random.randint(0,16777215)))
        # check if enough users are available to fill all teams
        if (math.floor(divide)) <= 0:
            await ctx.send(f"Not enough Users to fill all teams! got {length} users to fill {TeamCount} teams.")
            return
        else:
            # if enough users for all teams, split them evenly over all teams
            teams = dict()
            for i in range(0, TeamCount):
                # Create dict for each team
                teams[i] = dict()
                for x in range(0, math.ceil(divide)):
                    # Add users to team dictionary, Fills full teams.
                    teams[i][x] = SplitNames.pop()
            #repeat previous loop, but for remaining players. EX:(This makes team 1 size of 3, and team 2 size of 2)
            for i in range(0, math.ceil(modulo)):
                teams[i][x+1] = SplitNames.pop()
            for k,v in teams.items(): # k for team, v for list of members
                logging.info(f"Team Members List: {v}")
                NameList = []
                for j in v.values():
                    NameList.append(str(j))
                # add embed field per team
                em.add_field(name=(f"Team {k+1}"), value=NameList)
                teams[k] = NameList
            # If command is NOT used by user in voice channel, just send teams list.
            # If command is used by user in voice channel, Add button to split all members in that channel to their own team channel.
            if not FromVc:
                logging.info(f"Not from vc")
                await ctx.send(embed = em)
            else:
                logging.info(f"From VC")
                # Create button, and add to a view
                Button = await self.CreateButton(label="Split Voice Chats", style=discord.ButtonStyle.primary)
                view = View()
                view.add_item(Button)
                data = await self.get_data()
                try:
                    DBGuild_Id = data[str(ctx.guild.id)]
                except Exception as e:
                    if isinstance(e, KeyError):
                        data[str(ctx.guild.id)] = dict()
                    else:
                        logging.info(f"Unexpected Error: {e}")
                async def ButtonAction(interaction: discord.Interaction):
                    # Set permissions for voice channels
                    overwrites = {
                    ctx.guild.default_role: discord.PermissionOverwrite(connect=True, view_channel=True),
                    ctx.guild.me: discord.PermissionOverwrite(connect=True)
                    }
                    # Get and create CategoryChannel if it exists
                    try:
                        CategoryChannel = discord.utils.get(ctx.guild.channels, id=(int(data[str(ctx.guild.id)]["CategoryChannelId"])))
                        logging.info(f"Category channel found: {CategoryChannel}")
                    except Exception as e:
                        if isinstance(e, KeyError):
                            CategoryChannel = await self.CreateCategoryChannel(ctx, overwrites=overwrites, ChannelName="Teams")
                            data[str(ctx.guild.id)]["CategoryChannelId"] = str(CategoryChannel.id)
                            data[str(ctx.guild.id)][str(CategoryChannel.id)] = dict()
                        else:
                            logging.info(f"Unexpected Error: {e}")
                    for k,v in teams.items(): # k = Team, v = UsersList. Create Voice channel per team
                        TeamName = f"Team {k+1}"
                        # Add Team X to database, if it is not there yet.
                        try:
                            # logging.info(self.bot.get_channel((int(data[str(ctx.guild.id)][str(CategoryChannel.id)][TeamName]))))
                            # logging.info(data[str(ctx.guild.id)][str(CategoryChannel.id)][TeamName])
                            VoiceChannel = discord.utils.get(ctx.guild.channels, id=(int(data[str(ctx.guild.id)][str(CategoryChannel.id)][TeamName])))
                            logging.info(f"Voice channel found: {VoiceChannel}")
                        except Exception as e:
                            if isinstance(e, KeyError):
                                VoiceChannel = await self.CreateVoiceChannel(ctx, ChannelName=TeamName, CategoryChannel=CategoryChannel)
                                data[str(ctx.guild.id)][str(CategoryChannel.id)][TeamName] = VoiceChannel.id
                            else:
                                logging.info(f"Unexpected Error: {e}")
                        data[str(ctx.guild.id)][str(CategoryChannel.id)][TeamName] = VoiceChannel.id
                        # loop over all members in VoiceChannel, then loop over eash user for THAT team, then crossreference, and use VcMembers to move the users found in
                        # THAT team's members list
                        for i in VcMembers:
                            for user in v:
                                if int(i.id) == int(user[2:-1]):
                                    await i.move_to(VoiceChannel)
                                logging.info(f"TEAM: {k}, USER: {user}, Name: {i}")
                    await interaction.response.send_message("Teams have been split!")
                    await self.set_data(data=data)
                Button.callback = ButtonAction
                await ctx.send(embed=em, view=view)

async def setup(bot:commands.Bot):
	await bot.add_cog(Team(bot))