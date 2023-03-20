import datetime
import logging
import random
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config

@app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
class BotC(commands.GroupCog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot:commands.Bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        self.STATUS = [
            "dnd",
            "do_not_disturb",
            "idle", "invisible",
            "offline",
            "online",
            "random"
        ]
        self.STATUSTYPE = [
            discord.Status.dnd,
            discord.Status.do_not_disturb,
            discord.Status.idle,
            discord.Status.invisible,
            discord.Status.offline,
            discord.Status.online,
        ]
        self.ACTIVITIES = [
            "competing",
            # "custom",
            "listening",
            "playing",
            "streaming",
            "watching",
            "random"
        ]
        self.ACTIVITYTYPE = [
            discord.ActivityType.competing,
            discord.ActivityType.custom,
            discord.ActivityType.listening,
            discord.ActivityType.playing,
            discord.ActivityType.streaming,
            discord.ActivityType.watching,
        ]
        self.STATUSMSG = [
            "Licking a wedding cake",
            "Eating a wedding cake",
            "Comparing wedding cakes",
            "Taste testing a wedding cake",
            "Crashing a wedding to eat their cake",
            "Getting married to eat a cake",
            "Throwing a wedding cake",
            "Devouring a wedding cake",
            "Sniffing wedding cakes",
            "Touching a wedding cake",
            "Magically spawning a wedding cake"
        ]

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.activity_switch.start()

    @tasks.loop(seconds=config.Activity.PERIODIC_TIME)
    async def activity_switch(self) -> None:
        if config.Activity.RANDOM_ACTIVITY != True:
            self.activity_switch.stop()
            return
        status, activity = self.get_random_activity()
        # if status is None or activity is None:
            # activity = discord.Activity(type=discord.ActivityType.competing, name="Licking wedding cakes")
        await self.bot.change_presence(status=status, activity=activity)
        self.logger.debug(f"Activity and status set to {activity}")
        if config.Activity.PERIODIC_CHANGE != True:
            self.activity_switch.stop()
            return

    def get_random_activity(self) -> tuple[discord.Status, discord.Activity] | None:
        status = None
        activity_type = None
        while status in [discord.Status.invisible, discord.Status.offline, None]:
            status:discord.Status = random.choice(self.STATUSTYPE)
        while activity_type in [discord.ActivityType.custom, None]:
            activity_type:discord.ActivityType = random.choice(self.ACTIVITYTYPE)
        activity:discord.Activity = discord.Activity(type=activity_type, name=random.choice(self.STATUSMSG))
        return status, activity

    @app_commands.command(name="activity", description="change bot activity")
    async def slash_bot_activity(self, interaction: discord.Interaction, status:str, activity:str, msg:str="") -> None:
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        if status.lower() not in self.STATUS:
            await interaction.response.send_message(f"Status not found, can only be\n{self.STATUS}",ephemeral=True)
            return
        elif activity.lower() not in self.ACTIVITIES:
            await interaction.response.send_message(f"Activity not found, can only be\n{self.ACTIVITIES}", ephemeral=True)
            return
        elif status.lower() == "random" and activity.lower() == "random":
            config.Activity.PERIODIC_CHANGE = True
            self.logger.info(f"Turned on periodic activity change by {interaction.user}")
            await interaction.response.send_message("I will randomly change my status and activity", ephemeral=True)
            self.activity_switch.start()
            return
        elif status.lower() == "random" or activity.lower() == "random":
            await interaction.response.send_message("Both status and activity need to be random or not chosen.", ephemeral=True)
            return
        else:
            status_attr = getattr(discord.Status, status, discord.Status.online)
            activity_type = getattr(discord.ActivityType, activity, discord.ActivityType.playing)
            activity_obj = discord.Activity(type=activity_type, name=msg)
            await self.bot.change_presence(status=status_attr, activity=activity_obj)
            await interaction.response.send_message("Updated my activity!", ephemeral=True)
            self.logger.debug(f"Activity and status set to {activity} by {interaction.user}")
            self.logger.info(f"Turned off periodic activity change by {interaction.user}")
            config.Activity.PERIODIC_CHANGE = False
            self.activity_switch.stop()

    @slash_bot_activity.autocomplete("status")
    async def activity_autocomplete_status(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=stat, value=stat)
            for stat in self.STATUS
            if current.lower() in stat.lower()
        ]

    @slash_bot_activity.autocomplete("activity")
    async def activity_autocomplete_activitytype(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=activity, value=activity)
            for activity in self.ACTIVITIES
            if current.lower() in activity.lower()
        ]

    @app_commands.command(
        name = "announce",
        description = "Announce important messages on all servers the bot runs on"
        )
    @app_commands.guild_only()
    async def slash_bot_announce(self, interaction: discord.Interaction, msg:str) -> None:
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        for guild in self.bot.guilds:
            await self.bot.get_channel(guild.public_updates_channel.id).send(msg)
        await interaction.response.send_message("Message send to all update channels on all servers!", ephemeral=True)

    @app_commands.command(
        name = "ping",
        description = "show latency"
    )
    async def slash_ping(self, interaction:discord.Interaction) -> None:
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        latency = round(self.bot.latency * 1000)
        start_time = time.time()
        await interaction.response.defer()
        measured_time = time.time() - start_time
        final = round(measured_time * 1000)

        if latency < 250:
            color = 0x11ff00
        elif latency < 450:
            color = 0xddff00
        elif latency < 600:
            color = 0xff8800
        elif latency < 800:
            color = 0xff4400
        else:
            color = 0xff0000

        embed = discord.Embed(
            title=":ping_pong: Pong!",
            color=color,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.add_field(name="Websocket", value=f"```json\n{latency} ms```", inline=False)
        embed.add_field(name="Response", value=f"```json\n{final} ms```", inline=False)
        await interaction.followup.send(embed=embed)


async def setup(bot:commands.Bot) -> None:
	await bot.add_cog(BotC(bot))
