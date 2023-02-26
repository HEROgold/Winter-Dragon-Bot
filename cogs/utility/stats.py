import contextlib
import pickle
import logging
import os
import random

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
import tools.dragon_database as dragon_database
import rainbow

@app_commands.guild_only()
class Stats(commands.GroupCog):
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

    async def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = await db.get_data(self.DATABASE_NAME)
        elif os.path.getsize(self.DBLocation) > 0:
            with open(self.DBLocation, "rb") as f:
                data = pickle.load(f)
        return data

    async def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "wb") as f:
                pickle.dump(data, f)

    async def cog_load(self) -> None:
        if not self.data:
            self.data = await self.get_data()
        self.update.start()

    async def cog_unload(self) -> None:
        await self.set_data(self.data)

    @commands.Cog.listener()
    async def on_member_update(self, before:discord.Member, after:discord.Member) -> None:
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
        user_channel = await category.create_voice_channel(name="Total Users:", reason=reason)
        online_channel = await category.create_voice_channel(name="Online Users:", reason=reason)
        bot_channel = await category.create_voice_channel(name="Total Bots:", reason=reason)
        peak_channel = await category.create_voice_channel(name="Peak Online:", reason=reason)
        guild_channel = await category.create_voice_channel(name="Created On:", reason=reason)
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
        for channel_id in channels.values():
            with contextlib.suppress(AttributeError):
                channel = discord.utils.get(guild.channels, id=int(channel_id))
                await channel.delete(reason=reason)
        del self.data[guild_id]
        await self.set_data(self.data)

    @tasks.loop(seconds=3600)
    async def update(self) -> None:  # sourcery skip: low-code-quality
        if not self.data:
            self.data = await self.get_data()
        # TODO: remove after cog_load() is added/working
        if not self.data:
            return
        # Note: keep for loop with if.
        # because fetching guild won't let the bot get members from guild. Commented code below, don't work>
        guilds = self.bot.guilds
        for guild in guilds:
            if str(guild.id) not in self.data:
                continue
            self.logger.info(f"Updating stat channels: guild='{guild}'")
            guild_id = self.data[str(guild.id)]
            category = list(guild_id.values())[0]
            channels = list(category.values())[0]
            user_channel_id = channels["user_channel"]
            online_channel_id = channels["online_channel"]
            bot_channel_id = channels["bot_channel"]
            peak_channel_id = channels["peak_online"]
            guild_channel_id = channels["guild_channel"]
            peak_channel = discord.utils.get(guild.channels, id=peak_channel_id) or await guild.fetch_channel(peak_channel_id)
            guild_channel = discord.utils.get(guild.channels, id=guild_channel_id) or await guild.fetch_channel(guild_channel_id)
            bot_channel = discord.utils.get(guild.channels, id=bot_channel_id) or await guild.fetch_channel(bot_channel_id)
            user_channel = discord.utils.get(guild.channels, id=user_channel_id) or await guild.fetch_channel(user_channel_id)
            online_channel = discord.utils.get(guild.channels, id=online_channel_id) or await guild.fetch_channel(online_channel_id)
            self.logger.debug(f"Channels list: {peak_channel}, {user_channel}, {bot_channel}, {online_channel}, {guild_channel}")
            try:
                peak_count = int(peak_channel.name[13:])
            except ValueError:
                peak_count = 0
            users = sum(member.bot == False for member in guild.members)
            bots = sum(member.bot == True for member in guild.members)
            online = sum(member.status != discord.Status.offline and not member.bot for member in guild.members)
            peak_online = max(online, peak_count)
            age = guild.created_at.strftime("%Y-%m-%d")
            self.logger.debug(f"Channels Stats: {peak_online},{users}, {bots}, {online},  {age}, {list(guild.members)}")
            if ((new_name := f"Online Users: {online}") != online_channel.name):
                await online_channel.edit(name=new_name, reason="Stats update")
            if ((new_name := f"Total Users: {users}") != user_channel.name):
                await user_channel.edit(name=new_name, reason="Stats update")
            if ((new_name := f"Online Bots: {bots}") != bot_channel.name):
                await bot_channel.edit(name=new_name, reason="Stats update")
            if ((new_name := f"Created On: {age}") != guild_channel.name):
                await guild_channel.edit(name=new_name, reason="Stats update")
            if ((new_name := f"Peak Online: {peak_online}") != peak_channel.name):
                await peak_channel.edit(name=new_name, reason="Stats update")
            self.logger.info(f"Updated stat channels: guild='{guild}'")

    @app_commands.command(name="show", description="Get some information about the server!")
    async def slash_stats_show(self, interaction:discord.Interaction) -> None:
        guild = interaction.guild
        # users = sum(member.bot == False for member in guild.members)
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
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="add",
        description="This command will create the Stats category which will show some stats about the server."
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    async def slash_stats_category_add(self, interaction:discord.Interaction) -> None:
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
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    async def slash_remove_stats_category(self, interaction:discord.Interaction) -> None:
        if not self.data:
            self.data = await self.get_data()
        if str(interaction.guild.id) not in self.data:
            await interaction.response.send_message("No stats stats found to remove.", ephemeral=True)
            return
        await self.remove_stats_channels(guild=interaction.guild, reason=f"Requested by {interaction.user.display_name} using `/stats remove`")
        await interaction.response.send_message("Removed stats channels", ephemeral=True)

    @app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
    @app_commands.command(name="reset", description="Reset stats of all servers")
    async def reset_stats(self, interaction:discord.Interaction) -> None:
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        self.logger.warning(f"Resetting all guild/stats channels > by: {interaction.user}")
        if not self.data:
            self.data = await self.get_data()
        for guild_id in self.data.keys():
            guild = discord.utils.get(self.bot.guilds, id=guild_id)
            await self.remove_stats_channels(guild=guild, reason="Resetting all stats channels")
            await self.create_stats_channels(guild=guild, reason="Resetting all stats channels")
            self.logger.info(f"Reset stats for: {guild}")
        await interaction.response.send_message("Reset all server stat channels", ephemeral=True)

async def setup(bot:commands.Bot) -> None:
    await bot.add_cog(Stats(bot))