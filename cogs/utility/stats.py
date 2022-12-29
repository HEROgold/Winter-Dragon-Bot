import asyncio
import json
import logging
import os
import discord
from discord import app_commands
from discord.ext import commands
from discord import app_commands
import config


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot
        DBLocation = ".\\Database/Stats.json"
        self.DBLocation = DBLocation
        self.setup_db()

    @commands.Cog.listener()
    async def on_ready(self):
        while True:
            await self.update()
            await asyncio.sleep(60 * 5)  # timer to fight ratelimits

    @commands.Cog.listener()
    async def on_member_update(self, before:discord.Member, after:discord.Member):
        member = before or after
        guild = member.guild
        data = await self.get_data()
        guild_id = data[str(guild.id)]
        category = list(guild_id.values())[0]
        channels = list(category.values())[0]
        peak_channel_id = channels["peak_online"]
        peak_channel = discord.utils.get(guild.channels, id=peak_channel_id)
        try:
            peak_count = int(peak_channel.name[13:])
        except ValueError:
            peak_count = 0
        online = sum(member.status != discord.Status.offline and not member.bot for member in guild.members)
        if online > peak_count:
            await peak_channel.edit(name=f"Peak Online: {peak_count}")
            logging.info(f"New peak online reached for {guild}!")

    def setup_db(self):
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                logging.info("Stats Json Created.")
        else:
            logging.info("Stats Json Loaded.")

    async def get_data(self) -> dict[str, dict[str, dict[str, dict[str, int]]]]:
        with open(self.DBLocation, "r") as f:
            data = json.load(f)
        return data

    async def set_data(self, data):
        with open(self.DBLocation, "w") as f:
            json.dump(data, f)

    async def create_stats_channels(self, guild:discord.Guild) -> None:
        data = await self.get_data()
        overwrite = {
            guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
            guild.me: discord.PermissionOverwrite(connect=True),
        }
        guild_id = str(guild.id)
        category = await guild.create_category(name="Stats", overwrites=overwrite, position=0)
        online_channel = await category.create_voice_channel(name="Online Users")
        user_channel = await category.create_voice_channel(name="Total Users")
        bot_channel = await category.create_voice_channel(name="Total Bots")
        guild_channel = await category.create_voice_channel(name="Created On:")
        peak_channel = await category.create_voice_channel(name="Peak Online:")
        data[guild_id] = {category.id: {}}
        data[guild_id][category.id]["channels"] = {
            "category_channel": category.id,
            "online_channel": online_channel.id,
            "user_channel": user_channel.id,
            "bot_channel": bot_channel.id,
            "guild_channel": guild_channel.id,
            "peak_online" : peak_channel.id
        }
        await self.set_data(data)

    async def remove_stats_channels(self, guild:discord.Guild) -> None:
        data = await self.get_data()
        guild_id = str(guild.id)
        guild_dict = data[guild_id]
        category = list(guild_dict.values())[0]
        channels = list(category.values())[0]
        logging.info(f"Removing {channels}")
        for channel_name, channel_id in channels.items():
            channel = discord.utils.get(guild.channels, id=int(channel_id))
            await channel.delete()
        del data[guild_id]
        return data

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
                online_channel_id = channels["online_channel"]
                user_channel_id = channels["user_channel"]
                bot_channel_id = channels["bot_channel"]
                guild_channel_id = channels["guild_channel"]
                peak_channel_id = channels["peak_online"]
                peak_channel = discord.utils.get(guild.channels, id=peak_channel_id)
                try:
                    peak_count = int(peak_channel.name[13:])
                except ValueError:
                    peak_count = 0
                peak_online = max(online, peak_count)
                await self.bot.get_channel(online_channel_id).edit(name=f"Online Users {str(online)}")
                await self.bot.get_channel(user_channel_id).edit(name=f"Total Users: {str(users)}")
                await self.bot.get_channel(bot_channel_id).edit(name=f"Online Bots: {str(bots)}")
                await self.bot.get_channel(guild_channel_id).edit(name=f"Created On: {str(age)}")
                await peak_channel.edit(name=f"Peak Online: {peak_online}")
                logging.info(f"Updated Guild: {guild} stat channels")

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

    @app_commands.command(
        name="stats_category_add",
        description="This command will create the Stats category which will show some stats about the server."
    )
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def slash_stats_category_add(self, interaction:discord.Interaction):
        data = await self.get_data()
        guild_id = str(interaction.guild.id)
        if guild_id not in data:
            await self.create_stats_channels(guild=interaction.guild)
            await interaction.response.send_message("Stats channels are set up", ephemeral=True)
        else:
            await interaction.response.send_message("Stats channels arleady set up", ephemeral=True)

    @app_commands.command(
        name="stats_category_remove",
        description="This command removes the stat channels. Including the Category and all channels in there."
    )
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def slash_remove_stats_category(self, interaction:discord.Interaction):
        data = await self.get_data()
        if str(interaction.guild.id) not in data:
            await interaction.response.send_message("No stats stats found to remove.", ephemeral=True)
            return
        await self.remove_stats_channels(guild=interaction.guild)
        await interaction.response.send_message("Removed stats channels", ephemeral=True)
        await self.set_data(data)

    @app_commands.command(name="stats_category_reset", description="Reset stats of all servers")
    async def reset_stats(self, interaction:discord.Interaction):
        if interaction.user.id != config.main.owner_id and not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("You don't have permissions to use this command", ephemeral=True)
            return
        logging.info("Resetting stats channels")
        data = await self.get_data()
        await interaction.response.defer(ephemeral=True)
        for guild in self.bot.guilds:
            if str(guild.id) in data:
                guild = discord.utils.get(self.bot.guilds, id=guild.id)
                await self.remove_stats_channels(guild=guild)
                await self.create_stats_channels(guild=guild)
                logging.info(f"Reset stats for: {guild}")
        await interaction.followup.send("Reset all server stat channels", ephemeral=True)

async def setup(bot:commands.Bot):
    await bot.add_cog(Stats(bot))