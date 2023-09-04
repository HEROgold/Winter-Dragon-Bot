import datetime
import logging
import os
import random
import time
from collections import namedtuple

import discord
import psutil
from discord import app_commands
from discord.ext import commands, tasks
from matplotlib import pyplot as plt

from tools.config_reader import config

IMG_DIR = "./database/img/"
METRICS_FILE = f"{IMG_DIR}system_metrics.png"
END_CODEBLOCK = "```"

STATUS = [
    "dnd",
    "do_not_disturb",
    "idle", "invisible",
    "offline",
    "online",
    "random"
]
STATUS_TYPE = [
    discord.Status.dnd,
    discord.Status.do_not_disturb,
    discord.Status.idle,
    discord.Status.invisible,
    discord.Status.offline,
    discord.Status.online,
]
ACTIVITIES = [
    "competing",
    # "custom",
    "listening",
    "playing",
    "streaming",
    "watching",
    "random",
]
ACTIVITY_TYPE = [
    discord.ActivityType.competing,
    discord.ActivityType.custom,
    discord.ActivityType.listening,
    discord.ActivityType.playing,
    discord.ActivityType.streaming,
    discord.ActivityType.watching,
]
STATUS_MSG = [
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
    "Magically spawning a wedding cake",
]

# copied from the library, this fixes type-hint
Snetio = namedtuple(
    "snetio",
    [
        "bytes_sent",
        "bytes_recv",
        "packets_sent",
        "packets_recv",
        "errin",
        "errout",
        "dropin",
        "dropout",
    ],
) # type: ignore


@app_commands.guilds(config.getint("Main", "support_guild_id"))
class BotC(commands.GroupCog):
    timestamps: list[float]
    cpu_percentages: list[float]
    net_io_counters: list[Snetio]
    ram_percentages: list[float]
    bytes_sent: list[int]
    bytes_received: list[int]
    packets_sent: list[int]
    packets_received: list[int]


    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")
        self.timestamps = []
        self.cpu_percentages = []
        self.net_io_counters = []
        self.ram_percentages = []
        self.bytes_sent = []
        self.bytes_received = []
        self.packets_sent = []
        self.packets_received = []


    async def cog_load(self) -> None:
        self.activity_switch.start()
        self.gather_metrics_loop.start()


    @tasks.loop(seconds=config.getint("Activity", "periodic_time"))
    async def activity_switch(self) -> None:
        if not config.getboolean("Activity", "random_activity"):
            self.activity_switch.stop()
            return
        status, activity = self.get_random_activity()

        await self.bot.change_presence(status=status, activity=activity)
        self.logger.debug(f"Activity and status set to {activity}")
        if not config.getboolean("Activity", "periodic_change"):
            self.activity_switch.stop()
            return


    def get_random_activity(self) -> tuple[discord.Status, discord.Activity]:
        status = None
        activity_type = None

        while status in (discord.Status.invisible, discord.Status.offline, None):
            status = random.choice(STATUS_TYPE)

        while activity_type in (discord.ActivityType.custom, None):
            activity_type = random.choice(ACTIVITY_TYPE)

        activity = discord.Activity(
            type=activity_type,
            name=random.choice(STATUS_MSG)
        )
        return status, activity


    @app_commands.command(name="activity", description="change bot activity")
    @commands.is_owner()
    async def slash_bot_activity(
        self,
        interaction: discord.Interaction,
        status: str,
        activity: str,
        msg: str = ""
    ) -> None:
        if status.lower() not in STATUS:
            await interaction.response.send_message(
                f"Status not found, can only be\n{STATUS}", ephemeral=True
            )
            return
        if activity.lower() not in ACTIVITIES:
            await interaction.response.send_message(
                f"Activity not found, can only be\n{ACTIVITIES}", ephemeral=True
            )
            return
        if status.lower() == "random" and activity.lower() == "random":
            config["Activity"]["PERIODIC_CHANGE"] = True
            self.logger.info(f"Turned on periodic activity change by {interaction.user}")
            await interaction.response.send_message(
                "I will randomly change my status and activity", ephemeral=True
            )
            self.activity_switch.start()
            return
        if status.lower() == "random" or activity.lower() == "random":
            await interaction.response.send_message(
                "Both status and activity need to be random or not chosen.", ephemeral=True
            )
            return
        status_attr = getattr(discord.Status, status, discord.Status.online)
        activity_type = getattr(discord.ActivityType, activity, discord.ActivityType.playing)
        activity_obj = discord.Activity(type=activity_type, name=msg)
        await self.bot.change_presence(status=status_attr, activity=activity_obj)
        await interaction.response.send_message("Updated my activity!", ephemeral=True)
        self.logger.debug(f"Activity and status set to {activity} by {interaction.user}")
        self.logger.info(f"Turned off periodic activity change by {interaction.user}")
        config["Activity"]["PERIODIC_CHANGE"] = "False"
        self.activity_switch.stop()


    @slash_bot_activity.autocomplete("status")
    async def activity_autocomplete_status(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=stat, value=stat)
            for stat in STATUS
            if current.lower() in stat.lower()
        ] or [app_commands.Choice(name=stat, value=stat) for stat in STATUS]


    @slash_bot_activity.autocomplete("activity")
    async def activity_autocomplete_activity(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=activity, value=activity)
            for activity in ACTIVITIES
            if current.lower() in activity.lower()
        ] or [app_commands.Choice(name=activity, value=activity) for activity in ACTIVITIES]


    @commands.is_owner()
    @app_commands.guild_only()
    @app_commands.command(name="announce", description="Announce important messages on all servers the bot runs on")
    async def slash_bot_announce(self, interaction: discord.Interaction, msg: str) -> None:
        for guild in self.bot.guilds:
            await self.bot.get_channel(guild.public_updates_channel.id).send(msg)

        await interaction.response.send_message(
            "Message send to all update channels on all servers!",
            ephemeral=True
        )


    @app_commands.command(name="ping", description="show latency")
    @commands.is_owner()
    async def slash_ping(self, interaction: discord.Interaction) -> None:
        # Credits go to https://discord.com/channels/336642139381301249/1080409171050115092
        # Modified their code to fit my needs

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

        # get worst color (highest int)
        colors = [i[1] for i in results]
        colors.sort(reverse=True)
        color = colors[0]

        colored_websocket, _ = results[0]
        colored_api_response, _ = results[1]
        colored_database, _ = results[2]

        embed = discord.Embed(
            title=":ping_pong: Pong!",
            color=color,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        ).add_field(
            name="Websocket", value=f"{colored_websocket}{latency} ms {END_CODEBLOCK}",
            inline=False
        ).add_field(
            name="Response", value=f"{colored_api_response}{response} ms {END_CODEBLOCK}",
            inline=False
        ).add_field(
            name="Database", value=f"{colored_database}{database} ms {END_CODEBLOCK}",
            inline=False
        )

        await interaction.followup.send(embed=embed)


    @app_commands.command( name="performance", description="Show bot's Performance (Bot developer only)")
    async def performance(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="Performance",
            color=0,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

        worst_color = 0

        field_names = [
            "Cpu %",
            "Memory %",
            "Bytes Sent",
            "Bytes Received",
            "Packets Sent",
            "Packets Received",
        ]

        net_counters = psutil.net_io_counters()

        for i, value in enumerate([
            psutil.cpu_percent(),
            psutil.virtual_memory().percent,
            net_counters.bytes_sent,
            net_counters.bytes_recv,
            net_counters.packets_sent,
            net_counters.packets_recv,
        ]):
            self.logger.debug(f"{i=}, {value=}")
            if i < 2:
                ansi_color, color = self.get_colors(value, max_amount=100)
            elif i < 4:
                ansi_color, color = self.get_colors(value, max_amount=10_000_000_000)
            elif i < 6:
                ansi_color, color = self.get_colors(value, max_amount=1_000_000_000)

            # get worst color (highest int)
            colors = [worst_color, color]
            colors.sort(reverse=True)
            worst_color = colors[0]

            embed.add_field(
                name=f"{field_names[i]}", value=f"{ansi_color} {value} {END_CODEBLOCK}",
                inline=False
            )
        embed.color = worst_color
        await interaction.response.send_message(embed=embed)


    @commands.is_owner()
    @app_commands.command(name="performance_graph", description="Show bot's Performance (Bot developer only)")
    async def slash_performance_graph(self, interaction: discord.Interaction) -> None:
        self.gather_system_metrics()
        self.plot_system_metrics()

        try:
            file = discord.File(METRICS_FILE)
        except Exception:
            file = None
        await interaction.response.send_message(file=file)  # embed=embed,

    @staticmethod
    def get_colors(value: int, max_amount: int) -> tuple[str, int]:
        """Get colors based on given max value, with predefined percentages"""
        if value < max_amount * 0.4:
            ansi_start = "```ansi\n\x1b[2;32m"
            color = 1179392
        elif value < max_amount * 0.45:
            ansi_start = "```ansi\n\x1b[2;33m"
            color = 14548736
        elif value < max_amount * 0.6:
            ansi_start = "```ansi\n\x1b[2;33m"
            color = 16746496
        elif value < max_amount * 0.8:
            ansi_start = "```ansi\n\x1b[2;31m"
            color = 16729088
        else:
            ansi_start = "```ansi\n\x1b[2;31m"
            color = 16711680
        return (ansi_start, color)

    @classmethod
    def get_latency_colors(cls, latency) -> tuple[str, int]:
        return cls.get_colors(latency, 1000)

    @classmethod
    def get_percentage_colors(cls, percentage) -> tuple[str, int]:
        return cls.get_colors(percentage, 100)

    @classmethod
    def get_bytes_colors(cls, bytes_count) -> tuple[str, int]:
        return cls.get_colors(bytes_count, 10000000000)

    @classmethod
    def get_packets_colors(cls, packets_count) -> tuple[str, int]:
        return cls.get_colors(packets_count, 1000000000)


    # Switch to minutes for production
    # @tasks.loop(minutes=10)
    @tasks.loop(seconds=1)
    async def gather_metrics_loop(self) -> None:
        self.gather_system_metrics()


    def gather_system_metrics(self) -> None:
        # Get the current timestamp
        timestamp = time.time()
        self.timestamps.append(timestamp)

        # Get the CPU usage percentage
        cpu_percent = psutil.cpu_percent()
        self.cpu_percentages.append(cpu_percent)

        # Get the network I/O counters
        net_io = psutil.net_io_counters()
        self.net_io_counters.append(net_io)

        # Get the RAM percentage
        ram_percent = psutil.virtual_memory().percent
        self.ram_percentages.append(ram_percent)

        # Get the bytes sent and received
        bytes_sent_value = net_io.bytes_sent
        self.bytes_sent.append(bytes_sent_value)
        bytes_received_value = net_io.bytes_recv
        self.bytes_received.append(bytes_received_value)

        # Get the packets sent and received
        packets_sent_value = net_io.packets_sent
        packets_received_value = net_io.packets_recv
        self.packets_sent.append(packets_sent_value)
        self.packets_received.append(packets_received_value)

        # Check if an hour has passed and update the data for the last hour
        if timestamp - self.timestamps[0] > 3600:
            self._remove_oldest_system_metrics()


    def plot_system_metrics(self) -> None:
        plt.plot(
            self.timestamps,
            [net_io.bytes_sent for net_io in self.net_io_counters],
            label="Bytes Sent",
        )
        plt.plot(
            self.timestamps,
            [net_io.bytes_recv for net_io in self.net_io_counters],
            label="Bytes Received",
        )
        plt.plot(
            self.timestamps,
            [net_io.packets_sent for net_io in self.net_io_counters],
            label="Packets Sent",
        )
        plt.plot(
            self.timestamps,
            [net_io.packets_recv for net_io in self.net_io_counters],
            label="Packets Received",
        )

        # Make the cpu and ram % fit the full scale of the plot/graph
        values = []
        for net_io in self.net_io_counters:
            values.extend((
                net_io.bytes_sent,
                net_io.bytes_recv,
                net_io.packets_sent,
                net_io.packets_recv,
            ))
        max_scaler = max(values)

        plt.plot(
            self.timestamps,
            [max_scaler * (i / 100) for i in self.cpu_percentages],
            label="CPU Usage (%)",
        )
        plt.plot(
            self.timestamps,
            [max_scaler * (i / 100) for i in self.ram_percentages],
            label="RAM Usage (%)",
        )

        plt.xlabel("Time (seconds)")
        plt.ylabel("Value")
        plt.title("System Metrics Over Time")
        plt.legend()
        os.makedirs(IMG_DIR, exist_ok=True)
        plt.savefig(METRICS_FILE)
        plt.clf()

    def _remove_oldest_system_metrics(self) -> None:
        self.timestamps.pop(0)
        self.cpu_percentages.pop(0)
        self.net_io_counters.pop(0)
        self.ram_percentages.pop(0)
        self.bytes_sent.pop(0)
        self.bytes_received.pop(0)
        self.packets_sent.pop(0)
        self.packets_received.pop(0)

    @gather_metrics_loop.before_loop
    @activity_switch.before_loop
    async def before_update(self) -> None:
        self.logger.info("Waiting until bot is online")
        await self.bot.wait_until_ready()



async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BotC(bot))