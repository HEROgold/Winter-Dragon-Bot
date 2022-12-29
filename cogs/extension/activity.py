﻿import asyncio
import logging
import random
import discord
import config
from discord.ext import commands
from discord import app_commands


class Activity(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot
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
    async def on_ready(self):
        status, activity = self.get_random_activity()
        if status is None or activity is None:
            activity = discord.Activity(type=discord.ActivityType.competing, name="Licking wedding cakes")
        await self.bot.change_presence(status=status, activity=activity)
        logging.info(f"Activity and status set to {activity}")
        if config.activity.periodic_change == True:
            await asyncio.sleep(config.activity.periodic_time)
            await self.on_ready()

    def get_random_activity(self):
        if config.activity.random_activity != True:
            return None
        status = None
        activity_type = None
        while status in [discord.Status.invisible, discord.Status.offline, None]:
            status:discord.Status = random.choice(self.STATUSTYPE)
        while activity_type in [discord.ActivityType.custom, None]:
            activity_type:discord.ActivityType = random.choice(self.ACTIVITYTYPE)
        activity:discord.Activity = discord.Activity(type=activity_type, name=random.choice(self.STATUSMSG))
        return status,activity

    @app_commands.command(name="bot_activity", description="change bot activity")
    async def slash_activity(self, interaction: discord.Interaction, status:str, activity:str, msg:str=""):
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        await interaction.response.defer(ephemeral=True)
        if status.lower() not in self.STATUS:
            await interaction.followup.send(f"Status not found, can only be\n{self.STATUS}",ephemeral=True)
            return
        elif activity.lower() not in self.ACTIVITIES:
            await interaction.followup.send(f"Activity not found, can only be\n{self.ACTIVITIES}", ephemeral=True)
            return
        elif status.lower() == "random" and activity.lower() == "random":
            config.activity.periodic_change = True
            logging.info("Turned on periodic activity change")
            await interaction.followup.send("I will randomly change my status and activity", ephemeral=True)
            await self.on_ready()
            return
        elif status.lower() == "random" or activity.lower() == "random":
            await interaction.followup.send("Both status and activity need to be random or not chosen.", ephemeral=True)
            return
        else:
            StatusAttr = getattr(discord.Status, status, discord.Status.online)
            ActivityType = getattr(discord.ActivityType, activity, discord.ActivityType.playing)
            ActivityObj = discord.Activity(type=ActivityType, name=msg)
            await self.bot.change_presence(status=StatusAttr, activity=ActivityObj)
            await interaction.followup.send("Updated my activity!", ephemeral=True)
            logging.info(f"Activity and status set to {activity} by {interaction.user}")
            logging.info("Turned off periodic activity change")
            config.activity.periodic_change = False

    @slash_activity.autocomplete("status")
    async def activity_autocomplete_status(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=stat, value=stat)
            for stat in self.STATUS
            if current.lower() in stat.lower()
        ]

    @slash_activity.autocomplete("activity")
    async def activity_autocomplete_activitytype(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=activity, value=activity)
            for activity in self.ACTIVITIES
            if current.lower() in activity.lower()
        ]

async def setup(bot:commands.Bot):
    await bot.add_cog(Activity(bot))