import datetime
import itertools
import logging
import random
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks
import psutil

import config


@app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
class BotC(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        self.STATUS = [
            "dnd",
            "do_not_disturb",
            "idle", "invisible",
            "offline",
            "online",
            "random"
        ]
        self.STATUS_TYPE = [
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
        self.ACTIVITY_TYPE = [
            discord.ActivityType.competing,
            discord.ActivityType.custom,
            discord.ActivityType.listening,
            discord.ActivityType.playing,
            discord.ActivityType.streaming,
            discord.ActivityType.watching,
        ]
        self.STATUS_MSG = [
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
            status:discord.Status = random.choice(self.STATUS_TYPE)
        while activity_type in [discord.ActivityType.custom, None]:
            activity_type:discord.ActivityType = random.choice(self.ACTIVITY_TYPE)
        activity:discord.Activity = discord.Activity(type=activity_type, name=random.choice(self.STATUS_MSG))
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
        ] or [
            app_commands.Choice(name=stat, value=stat)
            for stat in self.STATUS
        ]

    @slash_bot_activity.autocomplete("activity")
    async def activity_autocomplete_activity(
        self,
        interaction:
        discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=activity, value=activity)
            for activity in self.ACTIVITIES
            if current.lower() in activity.lower()
        ] or [
            app_commands.Choice(name=activity, value=activity)
            for activity in self.ACTIVITIES
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
    async def slash_ping(self, interaction: discord.Interaction) -> None:
        # Credits go to https://discord.com/channels/336642139381301249/1080409171050115092
        # Modified their code to fit my needs
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner

        latency = round(self.bot.latency * 1000)

        start_time = time.time()
        await interaction.response.defer()
        measured_time = time.time() - start_time
        response = round(measured_time * 1000)

        from tools.database_tables import User
        start_time = time.time()
        User.fetch_user(id=interaction.user.id)
        measured_time = time.time() - start_time
        database = round(measured_time * 1000)

        results = list(map(self.get_latency_colors, [latency, response, database]))

        colors = [i[1] for i in results]
        colors.sort(reverse=True)
        color = colors[0]
        colored_websocket, _ = results[0]
        colored_api_response, _ = results[1]
        colored_database, _ = results[2]

        end_tag = "```"
        embed = discord.Embed(
            title=":ping_pong: Pong!",
            color=color,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.add_field(name="Websocket", value=f"{colored_websocket}{latency} ms {end_tag}", inline=False)
        embed.add_field(name="Response", value=f"{colored_api_response}{response} ms {end_tag}", inline=False)
        embed.add_field(name="Database", value=f"{colored_database}{database} ms {end_tag}", inline=False)
        await interaction.followup.send(embed=embed)


    # Potentially cleaner code \/ compared to code below that
    # add field names
    @app_commands.command(
        name="test_performance",
        description="Show bot's Performance (Bot developer only)"
    )
    async def a(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="Performance",
            color=0,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        end_tag = "```"

        worst_color = 0
        for i, value in enumerate([
            psutil.cpu_percent(),
            psutil.virtual_memory().percent,
            psutil.net_io_counters().bytes_sent,
            psutil.net_io_counters().bytes_recv,
            psutil.net_io_counters().packets_sent,
            psutil.net_io_counters().packets_recv
        ]):
            self.logger.debug(f"{i=}, {value=}")
            if i < 2:
                ansi_color, color = self.get_colors(value, max_amount=100)
            elif i < 4:
                ansi_color, color = self.get_colors(value, max_amount=10_000_000_000)
            elif i < 6:
                ansi_color, color = self.get_colors(value, max_amount=1_000_000_000)

            colors = [worst_color, color]
            colors.sort(reverse=True)
            worst_color = colors[0]

            embed.add_field(
                name=f"{i}",
                value=f"{ansi_color} {value} {end_tag}",
                inline=False
            )

        embed.color = worst_color
        await interaction.response.send_message(embed=embed)


    # TODO: Make and show a graph with 1 hour timeline.
    @app_commands.command(
        name="performance",
        description="Show bot's Performance (Bot developer only)"
    )
    async def slash_performance(self, interaction: discord.Interaction) -> None:
        if not self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        
        cpu_percent = psutil.cpu_percent()
        ram_percent = psutil.virtual_memory().percent
        percent_colors = list(map(self.get_percentage_colors, [cpu_percent, ram_percent]))
        cpu_color, _ = percent_colors[0]
        ram_color, _ = percent_colors[1]

        bytes_sent = psutil.net_io_counters().bytes_sent
        bytes_received = psutil.net_io_counters().bytes_recv
        bytes_colors = list(map(self.get_bytes_colors, [bytes_sent, bytes_received]))
        bytes_sent_color, _ = bytes_colors[0]
        bytes_received_color, _ = bytes_colors[1]

        packets_sent = psutil.net_io_counters().packets_sent
        packets_received = psutil.net_io_counters().packets_recv
        packets_colors = list(map(self.get_packets_colors, [packets_sent, packets_received]))
        packets_sent_color, _ = packets_colors[0]
        packets_received_color, _ = packets_colors[1]

        colors = [i[1] for i in list(itertools.chain(percent_colors, bytes_colors, packets_colors))]
        colors.sort(reverse=True)

        embed = discord.Embed(
            title="Performance",
            color=colors[0],
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        end_tag = "```"
        embed.add_field(
            name="Bytes sent",
            value=f"{bytes_sent_color} {bytes_sent} {end_tag}",
            inline=False
        )
        embed.add_field(
            name="Bytes received",
            value=f"{bytes_received_color} {bytes_received} {end_tag}",
            inline=False
        )
        embed.add_field(
            name="Packets sent",
            value=f"{packets_sent_color} {packets_sent} {end_tag}",
            inline=False
        )
        embed.add_field(
            name="Packets received",
            value=f"{packets_received_color} {packets_received} {end_tag}",
            inline=False
        )
        embed.add_field(
            name="CPU usage",
            value=f"{cpu_color} {cpu_percent}%{end_tag}",
            inline=False
        )
        embed.add_field(
            name="RAM usage",
            value=f"{ram_color} {ram_percent}%{end_tag}",
            inline=False
        )

        await interaction.response.send_message(embed=embed)


    def get_colors(
        self,
        value: int,
        max_amount: int
    ) -> tuple[str, int]:
        """Get colors based on given max value, with predefined percentages"""
        if value < (max_amount * 0.4):
            ansi_start = "```ansi\n\033[2;32m"
            color = 0x11ff00
        elif value < (max_amount * 0.45):
            ansi_start = "```ansi\n\033[2;33m"
            color = 0xddff00
        elif value < (max_amount * 0.6):
            ansi_start = "```ansi\n\033[2;33m"
            color = 0xff8800
        elif value < (max_amount * 0.8):
            ansi_start = "```ansi\n\033[2;31m"
            color = 0xff4400
        else:
            ansi_start = "```ansi\n\033[2;31m"
            color = 0xff0000
        return ansi_start, color

    def get_latency_colors(self, latency) -> tuple[str, int]:
        return self.get_colors(latency, 1000)

    def get_percentage_colors(self, percentage) -> tuple[str, int]:
        return self.get_colors(percentage, 100)

    def get_bytes_colors(self, bytes_count) -> tuple[str, int]:
        return self.get_colors(bytes_count, 10_000_000_000)

    def get_packets_colors(self, packets_count) -> tuple[str, int]:
        return self.get_colors(packets_count, 1_000_000_000)


async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(BotC(bot))
