import asyncio
import contextlib
import json
import logging
import os
import random

import discord
from discord import app_commands
from discord.ext import commands

import config
import dragon_database
import rainbow

class Stats(commands.GroupCog):
    def __init__(self, bot:commands.Bot):
        self.bot:commands.Bot = bot
        self.database_name = "Stats"
        self.data = None
        self.logger = logging.getLogger("winter_dragon.stats")
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.database_name}.json"
            self.setup_json()

    def setup_json(self):
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                self.logger.info(f"{self.database_name} Json Created.")
        else:
            self.logger.info(f"{self.database_name} Json Loaded.")

    async def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = await db.get_data(self.database_name)
        else:
            with open(self.DBLocation, 'r') as f:
                data = json.load(f)
        return data

    async def set_data(self, data):
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.database_name, data=data)
        else:
            with open(self.DBLocation,'w') as f:
                json.dump(data, f)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.data:
            self.data = await self.get_data()
        await self.update()

    async def cog_unload(self):
        await self.set_data(self.data)

    @commands.Cog.listener()
    async def on_member_update(self, before:discord.Member, after:discord.Member):
        member = before or after
        self.logger.debug(f"Member update: guild='{member.guild}', member='{member}'")
        guild = member.guild
        if not self.data:
            self.data = await self.get_data()
        guild_id = self.data[str(guild.id)]
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
            await peak_channel.edit(name=f"Peak Online: {peak_count}", reason="Reached new peak of online members")
            self.logger.info(f"New peak online reached for {guild}!")

    def setup_db(self):
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                self.logger.info("Stats Json Created.")
        else:
            self.logger.info("Stats Json Loaded.")

    async def create_stats_channels(self, guild:discord.Guild, reason:str=None) -> None:
        if not self.data:
            self.data = await self.get_data()
        overwrite = {
            guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
            guild.me: discord.PermissionOverwrite(connect=True),
        }
        guild_id = str(guild.id)
        category = await guild.create_category(name="Stats", overwrites=overwrite, position=0)
        category_id = str(category.id)
        online_channel = await category.create_voice_channel(name="Online Users:", reason=reason)
        user_channel = await category.create_voice_channel(name="Total Users:", reason=reason)
        bot_channel = await category.create_voice_channel(name="Total Bots:", reason=reason)
        guild_channel = await category.create_voice_channel(name="Created On:", reason=reason)
        peak_channel = await category.create_voice_channel(name="Peak Online:", reason=reason)
        self.data[guild_id] = {category_id: {}}
        self.data[guild_id][category_id]["channels"] = {
            "category_channel": category.id,
            "online_channel": online_channel.id,
            "user_channel": user_channel.id,
            "bot_channel": bot_channel.id,
            "guild_channel": guild_channel.id,
            "peak_online" : peak_channel.id
        }
        self.logger.info(f"Created stats channels for: guild='{guild}'")
        await self.set_data(self.data)

    async def remove_stats_channels(self, guild:discord.Guild, reason:str=None) -> None:
        if not self.data:
            self.data = await self.get_data()
        guild_id = str(guild.id)
        guild_dict = self.data[guild_id]
        category = list(guild_dict.values())[0]
        channels = list(category.values())[0]
        self.logger.info(f"Removing stats channels for: guild='{guild}', channels='{channels}'")
        for channel_name, channel_id in channels.items():
            with contextlib.suppress(AttributeError):
                channel = discord.utils.get(guild.channels, id=int(channel_id))
                await channel.delete(reason=reason)
        del self.data[guild_id]
        await self.set_data(self.data)

    async def update(self):
        if not self.data:
            self.data = await self.get_data()
        guilds = self.bot.guilds
        for guild in guilds:
            if str(guild.id) in self.data:
                # timer between guilds to fight ratelimits
                await asyncio.sleep(1)
                guild_id = self.data[str(guild.id)]
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
                with contextlib.suppress(AttributeError):
                    try:
                        peak_count = int(peak_channel.name[13:])
                    except ValueError:
                        peak_count = 0
                peak_online = max(online, peak_count)
                await self.bot.get_channel(online_channel_id).edit(name=f"Online Users: {str(online)}", reason="Stats update")
                await self.bot.get_channel(user_channel_id).edit(name=f"Total Users: {str(users)}", reason="Stats update")
                await self.bot.get_channel(bot_channel_id).edit(name=f"Online Bots: {str(bots)}", reason="Stats update")
                await self.bot.get_channel(guild_channel_id).edit(name=f"Created On: {str(age)}", reason="Stats update")
                await peak_channel.edit(name=f"Peak Online: {peak_online}", reason="Stats update")
                self.logger.info(f"Updated stat channels: guild='{guild}'")
        # timer to fight ratelimits
        await asyncio.sleep(60 * 5)
        await self.update()

    @app_commands.guild_only()
    @app_commands.command(name="show", description="Get some information about the server!")
    async def slash_stats_show(self, interaction:discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        users = sum(member.bot == False for member in guild.members)
        bots = sum(member.bot == True for member in guild.members)
        online = sum(member.status != discord.Status.offline and not member.bot for member in guild.members)
        creation_date = guild.created_at.strftime("%Y-%m-%d")
        embed=discord.Embed(title=f"{guild.name} Stats", description=f"Information about {guild.name}", color=random.choice(rainbow.RAINBOW))
        try:
            embed.add_field(name="Users", value=guild.member_count, inline=True)
            embed.add_field(name="Bots", value=bots, inline=True)
            embed.add_field(name="Online", value=online, inline=True)
            embed.add_field(name="Created on", value=creation_date, inline=True)
            embed.add_field(name="Afk channel", value=guild.afk_channel.mention, inline=True)
        except AttributeError as e:
            self.logger.warning(f"{e}: Likely caused by non-existing AFK channel")
        self.logger.debug(f"Showing guild stats: guild='{interaction.guild}' user={interaction.user}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="add",
        description="This command will create the Stats category which will show some stats about the server."
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    async def slash_stats_category_add(self, interaction:discord.Interaction):
        if not self.data:
            self.data = await self.get_data()
        guild_id = str(interaction.guild.id)
        if guild_id not in self.data:
            await self.create_stats_channels(guild=interaction.guild, reason=f"Requested by {interaction.user.display_name} using `/stats add`")
            await interaction.response.send_message("Stats channels are set up", ephemeral=True)
        else:
            await interaction.response.send_message("Stats channels arleady set up", ephemeral=True)

    @app_commands.command(
        name="remove",
        description="This command removes the stat channels. Including the Category and all channels in there."
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    async def slash_remove_stats_category(self, interaction:discord.Interaction):
        if not self.data:
            self.data = await self.get_data()
        if str(interaction.guild.id) not in self.data:
            await interaction.response.send_message("No stats stats found to remove.", ephemeral=True)
            return
        await self.remove_stats_channels(guild=interaction.guild, reason=f"Requested by {interaction.user.display_name} using `/stats remove`")
        await interaction.response.send_message("Removed stats channels", ephemeral=True)

    @app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
    @app_commands.command(name="reset", description="Reset stats of all servers")
    async def reset_stats(self, interaction:discord.Interaction):
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        self.logger.warning(f"Resetting all guild/stats channels > by: {interaction.user}")
        if not self.data:
            self.data = await self.get_data()
        await interaction.response.defer(ephemeral=True)
        for guild_id in self.data.keys():
            guild = discord.utils.get(self.bot.guilds, id=guild_id)
            await self.remove_stats_channels(guild=guild, reason="Resetting all stats channels")
            await self.create_stats_channels(guild=guild, reason="Resetting all stats channels")
            self.logger.info(f"Reset stats for: {guild}")
        await interaction.followup.send("Reset all server stat channels", ephemeral=True)

async def setup(bot:commands.Bot):
    await bot.add_cog(Stats(bot))