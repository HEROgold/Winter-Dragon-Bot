import datetime
import functools
import logging
import os
import random
import subprocess

import discord  # type: ignore
import psutil
from discord import app_commands
from discord.ext import commands

import config
from rainbow import RAINBOW
# from tools.database_tables import Server, Session, engine


# TODO:
# Track inactivity and shutdown after 15 minutes. Mention servers statuses in channel.
# automatically shutdown (most if not all) when empty for ~15mins

# Switch to using docker with shared files
# Add database table, add other statuses

# Add command to submit new servers
# Allow new suggestions using curseforge links, ftb app.


# FIXME:
# Conan log does't get pushed to file
# Conan doesn't run in background


# TODO: Change so it can work outside the docker container
# https://stackoverflow.com/questions/39468841/is-it-possible-to-start-a-stopped-container-from-another-container
@app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
class GameServers(commands.GroupCog):
    running_PIDS = {}


    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        # Return a function partially filled in, containing the starting script (powershell) 
        # or exe for that game server.
        self.SERVER_LIST = {
                "SCP: Secret Laboratory": functools.partial(
                    self.handle_generic_server,
                    exe_path = r"C:\Users\marti\Documents\GitHub\SteamCmd\steamapps\common\SCP Secret Laboratory Dedicated Server\start_server.ps1"
                ),
                "Conan Exiles": functools.partial(
                    self.handle_generic_server,
                    exe_path = r"C:\Users\marti\Desktop\Folders\ConanExilesServer\DedicatedServerLauncher\ConanExilesDedicatedServer\ConanSandboxServer.exe",
                    exe_args = "-log"
                ),
                "Minecraft: Cryptopolis": functools.partial(
                    self.handle_generic_server,
                    exe_path = r"C:\Users\marti\curseforge\minecraft\Servers\Cryptopolis_server_pack\start.ps1"
                ),
            }


    async def cog_unload(self) -> None:
        for process in self.running_PIDS:
            await self.stop_generic_server(interaction=None, server=process)


    async def check_usable(self, interaction: discord.Interaction) -> None:
        self.logger.warning(f"{interaction.user} used {interaction.command.name}")
        owner = await self.bot.is_owner(interaction.user)
        allowed = interaction.user.id in config.Gameservers.ALLOWED
        if not owner and not allowed:
            raise commands.NotOwner(f"may not use command: {interaction.user}")


    users = app_commands.Group(name="users", description="manage users command access")
    # TEMP_GROUP = app_commands.Group(name="TEMPGroup", description="TEMP")
    # Add- and remove-usable only work with config inside the bot's memory,
    # not the given config when starting


    @users.command(name="add", description="Start a specific self-hosted server")
    async def add_usable(self, interaction: discord.Interaction, member: discord.Member) -> None:
        await self.check_usable(interaction)

        config.Gameservers.ALLOWED.append(member.id)
        await interaction.response.send_message(f"Added {member} to list of allowed members.", ephemeral=True)


    @users.command(name="remove", description="Start a specific self-hosted server")
    async def remove_usable(self, interaction: discord.Interaction, member: discord.Member) -> None:
        await self.check_usable(interaction)

        config.Gameservers.ALLOWED.pop(member.id)
        await interaction.response.send_message(f"Removed {member} from list of allowed members.", ephemeral=True)


    @app_commands.command(name="start", description="Start a specific self-hosted server")
    async def slash_start(self, interaction: discord.Interaction, server: str) -> None:
        """Command that handles all starting of self-hosted servers"""
        await self.check_usable(interaction)
        if server not in self.SERVER_LIST:
            await interaction.response.send_message(f"Server {server} not found, use one from the following list:\n{self.SERVER_LIST}", ephemeral=True)
            return
        if server in self.running_PIDS:
            await interaction.response.send_message(content=f"Server already running, {self.running_PIDS[server]}")
            return
        await interaction.response.send_message(f"Starting {server}.")
        return await self.SERVER_LIST[server](interaction, server_name=server)


    @app_commands.checks.cooldown(3, 120)
    @app_commands.command(name="status", description="get the status a all or a specific self-hosted server")
    async def slash_status(self, interaction: discord.Interaction, server: str = None) -> None:
        """Command that handles showing status of self-hosted servers"""
        embed = discord.Embed(
            title="Server status",
            color=random.choice(RAINBOW),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        if server is None:
            for server in self.SERVER_LIST:
                if server in self.running_PIDS:
                    embed.add_field(name=server, value="```ansi\n[2;31m[2;32mRunning\n[0m```")
                else:
                    embed.add_field(name=server, value="```ansi\n[2;31mStopped\n[0m```")
            await interaction.response.send_message(embed=embed)
            return

        if server in self.running_PIDS:
            await interaction.response.send_message(f"{server} is Running", ephemeral=True)
        else:
            await interaction.response.send_message(f"{server} is Stopped", ephemeral=True)


    @app_commands.command(name="stop", description="Stop a specific self-hosted server")
    async def slash_stop(self, interaction: discord.Interaction, server: str) -> None:
        """Command that handles all stopping of self-hosted servers"""
        await self.check_usable(interaction)
        if server not in self.running_PIDS:
            await interaction.response.send_message(f"Server {server} is not running", ephemeral=True)
        else:
            await interaction.response.send_message(f"Stopping {server}.")
            await interaction.response.send_message(f"Stopping {server}.")
            return await self.SERVER_LIST[server](interaction, server_name=server, stop=True)


    @slash_status.autocomplete("server")
    @slash_start.autocomplete("server")
    async def gameserver_stop_autocomplete_server(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=i, value=i)
            for i in self.SERVER_LIST
            if current.lower() in i.lower()
        ]

    @slash_stop.autocomplete("server")
    async def stop_gameserver_autocomplete_server(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=i, value=i)
            for i in self.running_PIDS
            if current.lower() in i.lower()
        ]


    async def handle_generic_server(
        self,
        interaction: discord.Interaction,
        server_name: str,
        exe_path: str, 
        exe_args: str = "",
        stop: bool = False
    ) -> None:
        """Handles generic server start/stop"""
        self.logger.debug(f"Handling {server_name}")
        if stop:
            await self.stop_generic_server(interaction, server_name)
        else:
            await self.start_generic_server(interaction, server_name, exe_path, exe_args)


    async def start_generic_server(
        self,
        interaction: discord.Interaction,
        server_name: str,
        exe_path: str,
        exe_args: str = ""
    ) -> None:
        """Starts a server"""

        log_path = os.path.normpath(f"{server_name}.log")
        illegal_chars = r""""#%&{}\<>*?/$!'":@+`|= """
        for letter in log_path:
            if letter in illegal_chars:
                log_path = log_path.replace(letter, "")
        self.logger.debug(f"logging for: {server_name=} in: {log_path=}")

        self.logger.info(f"Starting {server_name}")
        try:
            running_server = await self.run_from_exe(exe_path, exe_args, log_path)
        except OSError:
            # if e.errno == errno. # should check for OSError: [WinError 193] %1 is not a valid Win32 application",)
            running_server = await self.run_from_powershell(exe_path, exe_args, log_path)
        self.running_PIDS = {server_name : running_server.pid}
        self.logger.debug(f"{self.running_PIDS=}")
        await interaction.edit_original_response(content=f"Started {server_name}")


    async def run_from_exe(
        self,
        exe_path: str,
        exe_args: str,
        log_path: str = None
    ) -> subprocess.Popen:
        with open(log_path, "w", encoding="utf-8") as logs:
            if config.Gameservers.BACKGROUND:
                return subprocess.Popen(f'"{exe_path}" "{exe_args}', stderr=logs, stdout=logs, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                return subprocess.Popen(f'"{exe_path}" "{exe_args}', stderr=logs, stdout=logs)


    async def run_from_powershell(
        self,
        exe_path: str,
        exe_args: str,
        log_path: str = None
    ) -> subprocess.Popen:
        if not exe_path.endswith(".ps1"):
            self.logger.warning(f"file not a powershell script skipping: {exe_path}")
            return
        with open(log_path, "w", encoding="utf-8") as logs:
            if config.Gameservers.BACKGROUND:
                # return subprocess.Popen(["powershell.exe", f'"{exe_path}" {exe_args}'], stderr=logs, stdout=logs, creationflags=subprocess.CREATE_NO_WINDOW)
                return subprocess.Popen(f'"powershell.exe" "{exe_path}" {exe_args}', stderr=logs, stdout=logs, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                # return subprocess.Popen(["powershell.exe", f'"{exe_path}" {exe_args}'], stderr=logs, stdout=logs)
                return subprocess.Popen(f'"powershell.exe" "{exe_path}" {exe_args}', stderr=logs, stdout=logs)


    async def log_watcher(self) -> None:
        """Watches logs from the spawned servers, to determine inactivity"""
        raise NotImplementedError


    async def stop_generic_server(self, interaction: discord.Interaction, server: str) -> None:
        """Stops a server using the equivalent of Ctrl-C, or with force after a delay"""
        self.logger.info(f"Stopping {server}")
        if interaction:
            pid = self.running_PIDS[server]
        elif interaction is None:
            pid = server
        self.logger.debug(f"{pid}")
        try:
            parent = psutil.Process(pid)
        except psutil.NoSuchProcess:
            await interaction.edit_original_response(content=f"{server} ({pid}) could not be found")
            return

        children = parent.children(recursive=True)

        for child in children:
            self.logger.debug(f"terminating {child}")
            child.terminate() # kill child friendly
        parent.terminate() # kill parent friendly

        _, still_alive_children = psutil.wait_procs(children, timeout=5)
        for child in still_alive_children:
            if len(still_alive_children) <= 0:
                break
            self.logger.debug(f"killing {child}")
            child.kill()  # kill child unfriendly
        else:
            try:
                parent.kill()
            except psutil.NoSuchProcess:
                pass

        del self.running_PIDS[server]
        self.logger.debug(f"{self.running_PIDS=}")
        
        if interaction is not None:
            await interaction.edit_original_response(content=f"Stopped {server}")


async def setup(bot: commands.Bot) -> None:
    # await bot.add_cog(GameServers(bot))  # type: ignore
    pass
