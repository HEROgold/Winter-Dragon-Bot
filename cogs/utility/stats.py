import asyncio
import datetime
import json
import logging
import os
from re import S
import discord
from discord import app_commands
from discord.ext import commands
from config import main as mainconfig


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot
        DBLocation = ".\\Database/Stats.json"
        self.DBLocation = DBLocation
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                logging.info("Stats Json Created.")
        else:
            logging.info("Stats Json Loaded.")

    async def get_data(self):
        with open(self.DBLocation, "r") as f:
            data = json.load(f)
        return data

    async def set_data(self, data):
        with open(self.DBLocation, "w") as f:
            json.dump(data, f)

    @commands.Cog.listener()
    async def on_ready(self):
        while True:
            await self.update()
            await asyncio.sleep(60 * 5)  # timer to fight ratelimits

    # # FIXME Does not work
    # # {CommandInvokeError("Command raised an exception: TypeError: Command.call() missing 1 required positional argument: 'context'")}
    # # Individual remove stats and create stats work
    # @commands.hybrid_command(name="reset_stats", description="Reset stats of all servers")
    # async def reset_stats(self, ctx:commands.Context):
    #     if ctx.message.author.id != mainconfig.owner_id and not await self.bot.is_owner(ctx.message.author):
    #         await ctx.send("You don't have permissions to use this command")
    #         return
    #     data = await self.get_data()
    #     for guild in self.bot.guilds:
    #         if str(guild.id) in data:
    #             await self.remove_stats_category(ctx=ctx, guild=guild.id)
    #             await self.stats_category(ctx=ctx, guild=guild.id)

    @app_commands.guild_only()
    @app_commands.command(name="servers_stats", description="Get some information about the server!")
    async def slash_stats(self, interaction:discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        users = sum(member.bot == False for member in guild.members)
        bots = sum(member.bot == True for member in guild.members)
        online = sum(member.status != discord.Status.offline and not member.bot for member in guild.members)
        creation_date = guild.created_at.strftime("%Y-%m-%d")
        embed=discord.Embed(title=f"{guild.name} Stats", description=f"Information about {guild.name}", color=0xff0000)
        embed.add_field(name="Users", value=guild.member_count, inline=True)
        embed.add_field(name="Bots", value=bots, inline=True)
        embed.add_field(name="Online", value=online, inline=True)
        embed.add_field(name="Created on", value=creation_date, inline=True)
        embed.add_field(name="Afk channel", value=guild.afk_channel.mention, inline=True)
        await interaction.followup.send(embed=embed)

    async def update(self):
        data = await self.get_data()
        guilds = self.bot.guilds
        for guild in guilds:
            if str(guild.id) in data:
                await asyncio.sleep(1)  # timer between guilds to fight ratelimits
                guild_id = data[str(guild.id)]
                category = list(guild_id.values())[0]
                channels = list(category.values())[0]
                users = sum(member.bot == False for member in guild.members)
                bots = sum(member.bot == True for member in guild.members)
                online = sum(member.status != discord.Status.offline and not member.bot for member in guild.members)
                age = guild.created_at.strftime("%Y-%m-%d")
                time = datetime.datetime.now().strftime("%H:%M")
                online_channel = category["channels"]["online_channel"]
                user_channel = category["channels"]["user_channel"]
                bot_channel = category["channels"]["bot_channel"]
                guild_channel = category["channels"]["guild_channel"]
                time_channel = category["channels"]["time_channel"]
                # await self.bot.get_channel(time_channel).edit(name=f"UTC: {str(time)}")
                await self.bot.get_channel(online_channel).edit(name=f"Online Users {str(online)}")
                await self.bot.get_channel(user_channel).edit(name=f"Total Users: {str(users)}")
                await self.bot.get_channel(bot_channel).edit(name=f"Online Bots: {str(bots)}")
                await self.bot.get_channel(guild_channel).edit(name=f"Created On: {str(age)}")
                logging.info(f"updated Guild: {guild} stat channels")

    # show some guild/server stats
    @commands.hybrid_command(
        brief="Create the Stats category",
        description="This command will create the Stats category which will show some stats about the server.",
        usage="`stats_category`",
    )
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def stats_category(self, ctx:commands.Context, guild=None):
        if guild is None:
            guild = ctx.guild
        overwrite = {
            ctx.guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
            ctx.guild.me: discord.PermissionOverwrite(connect=True),
        }
        data = await self.get_data()
        if str(guild.id) not in data:
            category = await guild.create_category(name="Stats", overwrites=overwrite, position=0)
            online_channel = await category.create_voice_channel(name="Online Users")
            user_channel = await category.create_voice_channel(name="Total Users")
            bot_channel = await category.create_voice_channel(name="Total Bots")
            guild_channel = await category.create_voice_channel(name="Created On:")
            time_channel = await category.create_voice_channel(name="UTC Time")
            data[guild.id] = {category.id: {}}
            data[guild.id][category.id]["channels"] = {
                "category_channel": category.id,
                "online_channel": online_channel.id,
                "user_channel": user_channel.id,
                "bot_channel": bot_channel.id,
                "guild_channel": guild_channel.id,
                "time_channel": time_channel.id,
            }
            await ctx.send("Stats channels are set up")
        else:
            await ctx.send("Stats channels arleady set up")
        await self.set_data(data)

    @commands.hybrid_command(
        brief="Remove the Stats channels",
        description="This command removes the stat channels. Including the Category and all channels in there.",
        usage="`remove_stats_category`",
    )
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def remove_stats_category(self, ctx:commands.Context, guild=None):
        if guild is None:
            guild = ctx.guild
        data = await self.get_data()
        if str(guild.id) not in data:
            await ctx.send("No stats stats found to remove.")
        else:
            guild = data[str(guild.id)]
            category = list(guild.values())[0]
            channels = list(category.values())[0]
            logging.info(channels)
            for k, v in channels.items():
                channel = self.bot.get_channel(v)
                await channel.delete()
            del data[str(ctx.guild.id)]
        await self.set_data(data)

async def setup(bot:commands.Bot):
    await bot.add_cog(Stats(bot))