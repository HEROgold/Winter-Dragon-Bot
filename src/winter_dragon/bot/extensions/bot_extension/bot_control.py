"""Module that contains interfaces to control the bot using discord."""
import datetime
import random
import time
from typing import Unpack

import discord
import psutil
from discord import Guild, app_commands
from discord.ext import commands
from matplotlib import pyplot as plt
from psutil._common import snetio
from winter_dragon.bot._types.kwargs import BotArgs
from winter_dragon.bot.config import Config
from winter_dragon.bot.constants import METRICS_FILE
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.bot.core.tasks import loop
from winter_dragon.bot.enums.activity import ACTIVITY_TYPES, STATUS_TYPES, VALID_RNG_ACTIVITY, VALID_RNG_STATUS
from winter_dragon.bot.settings import Settings
from winter_dragon.bot.tools.strings import codeblock
from winter_dragon.database.tables.user import Users

# TODO: Split into metrics Cog and Activity Cog.

@app_commands.guilds(Settings.support_guild_id)
class BotC(GroupCog):
    """Cog to control the bot."""

    timestamps: list[float]
    cpu_percentages: list[float]
    net_io_counters: list[snetio]
    ram_percentages: list[float]
    bytes_sent: list[int]
    bytes_received: list[int]
    packets_sent: list[int]
    packets_received: list[int]

    random_activity = Config(default=True)
    periodic_change = Config(default=True)
    periodic_time = Config(180)
    gather_metrics_interval = Config(180)


    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the bot control cog."""
        super().__init__(**kwargs)
        self.timestamps = []
        self.cpu_percentages = []
        self.net_io_counters = []
        self.ram_percentages = []
        self.bytes_sent = []
        self.bytes_received = []
        self.packets_sent = []
        self.packets_received = []


    async def cog_load(self) -> None:
        """When the cog loads, start collecting metrics and activity statuses."""
        await super().cog_load()
        # Configure loop intervals from config
        self.gather_metrics_loop.change_interval(seconds=self.gather_metrics_interval)
        self.activity_switch.change_interval(seconds=self.periodic_time)
        self.activity_switch.start()
        self.gather_metrics_loop.start()


    @loop()
    async def activity_switch(self) -> None:
        """Switch the bot's activity and status periodically. Uses activity.periodic_time config."""
        if self.random_activity:
            self.activity_switch.stop()
            return
        status, activity = self.get_random_activity()

        await self.bot.change_presence(status=status, activity=activity)
        self.logger.debug(f"Activity and status set to {activity}")
        if not self.periodic_change:
            self.activity_switch.stop()
            return


    def get_random_activity(self) -> tuple[discord.Status, discord.Activity]:
        """Get a random valid activity and status."""
        status = random.choice(VALID_RNG_STATUS)  # noqa: S311
        activity_type = random.choice(VALID_RNG_ACTIVITY)  # noqa: S311

        activity = discord.Activity(
            type=activity_type,
            name=random.choice(Settings.bot_status_messages),  # noqa: S311
        )
        return status, activity


    async def _start_randomizer(self, interaction: discord.Interaction) -> None:
        self.periodic_change = True
        self.logger.info(f"Turned on periodic activity change by {interaction.user}")
        await interaction.response.send_message("I will randomly change my status and activity", ephemeral=True)
        self.activity_switch.start()


    @commands.is_owner()
    @app_commands.command(name="activity", description="change bot activity")
    async def slash_bot_activity(
        self,
        interaction: discord.Interaction,
        status: str,
        activity: str,
        msg: str = "",
    ) -> None:
        """Change the bot's activity and status."""
        status = status.lower()
        activity = activity.lower()
        statuses = ", ".join([i.name for i in STATUS_TYPES])
        activities = ", ".join([i.name for i in ACTIVITY_TYPES])

        if status not in [i.name.lower() for i in STATUS_TYPES]:
            await interaction.response.send_message(f"Status not found, can only be\n{statuses}", ephemeral=True)
            return

        if activity not in activities:
            await interaction.response.send_message(f"Activity not found, can only be\n{activities}", ephemeral=True)
            return

        if status == "random" and activity == "random":
            await self._start_randomizer(interaction)
            return

        if status == "random" or activity == "random":
            await interaction.response.send_message(
                "Both status and activity need to be random or not chosen.",
                ephemeral=True,
            )
            return

        status_attr = discord.Status[status] or discord.Status.online
        activity_type = discord.Status[activity] or discord.ActivityType.playing
        activity_obj = discord.Activity(type=activity_type, name=msg)

        await self.bot.change_presence(status=status_attr, activity=activity_obj)
        await interaction.response.send_message("Updated my activity!", ephemeral=True)
        self.logger.debug(f"Activity and status set to {activity} by {interaction.user}")
        self.logger.info(f"Turned off periodic activity change by {interaction.user}")

        self.periodic_change = False
        self.activity_switch.stop()
        return


    @slash_bot_activity.autocomplete("status")
    async def activity_autocomplete_status(
        self,
        interaction: discord.Interaction,  # noqa: ARG002
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for the status command."""
        statuses = [i.name for i in STATUS_TYPES]
        return [
            app_commands.Choice(name=stat, value=stat)
            for stat in statuses
            if current.lower() in stat.lower()
        ] or [app_commands.Choice(name=stat, value=stat) for stat in statuses]


    @slash_bot_activity.autocomplete("activity")
    async def activity_autocomplete_activity(
        self,
        interaction: discord.Interaction,  # noqa: ARG002
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for the activity command."""
        activities = [i.name for i in ACTIVITY_TYPES]
        return [
            app_commands.Choice(name=activity, value=activity)
            for activity in activities
            if current.lower() in activity.lower()
        ] or [app_commands.Choice(name=activity, value=activity) for activity in activities]


    @commands.is_owner()
    @app_commands.guild_only()
    @app_commands.command(name="announce", description="Announce important messages on all servers the bot runs on")
    async def slash_bot_announce(self, interaction: discord.Interaction, msg: str) -> None:
        """Announce a message to all servers the bot is in and allowed to."""
        for guild in self.bot.guilds:
            await self._send_announcement(msg, guild)

        await interaction.response.send_message(
            "Message send to all update channels on all servers!",
            ephemeral=True,
        )

    async def _send_announcement(self, msg: str, guild: Guild) -> None:
        if guild.public_updates_channel is None:
            self.logger.warning(f"Guild {guild.name} does not have a public updates channel")
            return
        await guild.public_updates_channel.send(msg)


    @app_commands.command(name="ping", description="show latency")
    @commands.is_owner()
    async def slash_ping(self, interaction: discord.Interaction) -> None:
        """Show the bot's latency."""
        # Credits go to https://discord.com/channels/336642139381301249/1080409171050115092
        # Modified their code to fit my needs

        latency, response, database = await self.gather_latency(interaction)
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
            timestamp=datetime.datetime.now(datetime.UTC),
        ).add_field(
            name="Websocket", value=codeblock(colored_websocket, f"{latency} ms"),
            inline=False,
        ).add_field(
            name="Response", value=codeblock(colored_api_response, f"{response} ms"),
            inline=False,
        ).add_field(
            name="Database", value=codeblock(colored_database, f"{database} ms"),
            inline=False,
        )

        await interaction.followup.send(embed=embed)

    async def gather_latency(self, interaction: discord.Interaction) -> tuple[int, int, int]:
        """Gather the latency, response time and database response time of the bot."""
        latency = round(self.bot.latency * 1000)

        start_time = time.time()
        await interaction.response.defer()
        measured_time = time.time() - start_time
        response = round(measured_time * 1000)

        start_time = time.time()
        Users.fetch(id_=interaction.user.id)
        measured_time = time.time() - start_time
        database = round(measured_time * 1000)
        return latency, response, database


    @app_commands.command( name="performance", description="Show bot's Performance (Bot developer only)")
    async def slash_performance(self, interaction: discord.Interaction) -> None:
        """Show the bot's performance."""
        embed = discord.Embed(
            title="Performance",
            color=0,
            timestamp=datetime.datetime.now(datetime.UTC),
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

        cpu_and_ram_idx = 2
        bytes_idx = 4
        packets_idx = 6

        for i, value in enumerate([
            psutil.cpu_percent(),
            psutil.virtual_memory().percent,
            net_counters.bytes_sent,
            net_counters.bytes_recv,
            net_counters.packets_sent,
            net_counters.packets_recv,
        ]):
            self.logger.debug(f"{i=}, {value=}")

            ansi_color, color = "", 0
            if i < cpu_and_ram_idx:
                ansi_color, color = self.get_colors(value, max_amount=100)
            elif i < bytes_idx:
                ansi_color, color = self.get_colors(value, max_amount=10_000_000_000)
            elif i < packets_idx:
                ansi_color, color = self.get_colors(value, max_amount=1_000_000_000)

            # get worst color (highest int)
            colors = [worst_color, color]
            colors.sort(reverse=True)
            worst_color = colors[0]

            embed.add_field(
                name=f"{field_names[i]}", value=codeblock(ansi_color, value),
                inline=False,
            )
        embed.color = worst_color
        await interaction.response.send_message(embed=embed)


    @commands.is_owner()
    @app_commands.command(name="performance_graph", description="Show bot's Performance (Bot developer only)")
    async def slash_performance_graph(self, interaction: discord.Interaction) -> None:
        """Show the bot's performance in a graph."""
        await interaction.response.defer(thinking=True)
        self.gather_system_metrics()
        self.plot_system_metrics()

        try:
            file = discord.File(METRICS_FILE)
            await interaction.followup.send(file=file)  # embed=embed,
        except Exception:
            self.logger.exception("Error when creating a graph.")
            file = None
            await interaction.followup.send("Could not make a graph to show.")


    @staticmethod
    def get_colors(value: float, max_amount: int) -> tuple[str, int]:
        """Get colors based on given max value, with predefined percentages."""
        if value < max_amount * 0.4:
            ansi_start = "ansi\n\x1b[2;32m"
            color = 1179392
        elif value < max_amount * 0.45:
            ansi_start = "ansi\n\x1b[2;33m"
            color = 14548736
        elif value < max_amount * 0.6:
            ansi_start = "ansi\n\x1b[2;33m"
            color = 16746496
        elif value < max_amount * 0.8:
            ansi_start = "ansi\n\x1b[2;31m"
            color = 16729088
        else:
            ansi_start = "ansi\n\x1b[2;31m"
            color = 16711680
        return (ansi_start, color)

    @classmethod
    def get_latency_colors(cls, latency: int) -> tuple[str, int]:
        """Get colors based on latency."""
        return cls.get_colors(latency, 1000)

    @classmethod
    def get_percentage_colors(cls, percentage: int) -> tuple[str, int]:
        """Get colors based on percentage."""
        return cls.get_colors(percentage, 100)

    @classmethod
    def get_bytes_colors(cls, bytes_count: int) -> tuple[str, int]:
        """Get colors based on bytes."""
        return cls.get_colors(bytes_count, 10000000000)

    @classmethod
    def get_packets_colors(cls, packets_count: int) -> tuple[str, int]:
        """Get colors based on packets."""
        return cls.get_colors(packets_count, 1000000000)


    @loop()
    async def gather_metrics_loop(self) -> None:
        """Gather system metrics every second."""
        self.gather_system_metrics()


    def gather_system_metrics(self) -> None:
        """Gather system metrics like cpu, ram and network traffic."""
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
        hour = 3600
        if timestamp - self.timestamps[0] > hour:
            self._remove_oldest_system_metrics()


    def plot_system_metrics(self) -> None:
        """Plot the system metrics on a graph."""
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
        values: list[int] = []
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
        """Wait until the bot is ready before starting the loops."""
        await self.bot.wait_until_ready()



async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(BotC(bot=bot))
