import datetime
import logging
import os
import pickle
import random
import subprocess

import discord  # type: ignore
import psutil
from discord import app_commands
from discord.ext import commands

import config
from rainbow import RAINBOW
from tools import dragon_database


# TODO:
# Track inactivity and shutdown after 15 minutes. Mention servers statuses in channel.
# automatically shutdown (most if not all) when empty for ~15mins

# FIXME: 
# Starts Conan Exiles on foreground (like starting normally / double click on exe)


@app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
class GameServers(commands.GroupCog):
    running_PIDS = {}

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(
            f"{config.Main.BOT_NAME}.{self.__class__.__name__}"
        )
        self.data = None
        self.DATABASE_NAME = self.__class__.__name__
        self.SERVER_LIST = {
                "SCP: Secret Laboratory": self.handle_scp_sl,
                "Conan Exiles": self.handle_conan,
                "Minecraft: Cryptopolis": self.handle_mc_cryptopolis,
            }
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

    def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = db.get_data(self.DATABASE_NAME)
        elif os.path.getsize(self.DBLocation) > 0:
            with open(self.DBLocation, "rb") as f:
                data = pickle.load(f)
        return data

    def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "wb") as f:
                pickle.dump(data, f)

    async def cog_load(self) -> None:
        self.data = self.get_data()

    async def cog_unload(self) -> None:
        for process in self.running_PIDS:
            await self.stop_generic(interaction=None, server=process)
        self.set_data(self.data)

    def check_usable(self, interaction: discord.Interaction) -> None:
        self.logger.warning(f"{interaction.user} used {interaction.command.name}")
        if interaction.user.id not in config.Gameservers.ALLOWED:
            raise commands.NotOwner


    @app_commands.command(name="start", description="Start a specific self-hosted server")
    async def slash_start(self, interaction: discord.Interaction, server: str) -> None:
        """Command that handles all starting of self-hosted servers"""
        self.check_usable(interaction)
        if server not in self.SERVER_LIST:
            await interaction.response.send_message(f"Server {server} not found, use one from the following list:\n{self.SERVER_LIST}", ephemeral=True)
            return
        if server in self.running_PIDS:
            await interaction.response.send_message(content=f"Server already running, {self.running_PIDS[server]}", ephemeral=True)
            return
        await interaction.response.send_message(f"Starting {server}...", ephemeral=True)
        return await self.SERVER_LIST[server](interaction, server_name=server)


    @app_commands.command(name="status", description="get the status a specific self-hosted server")
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
                    
                    embed.add_field(name=server, value="```ansi\n[2;31m[2;32mRunning\n[0m[2;31m[2;32m[0m[2;31m[0m\n```")
                else:
                    embed.add_field(name=server, value="```ansi\n[2;31mStopped\n[0m```")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if server in self.running_PIDS:
            await interaction.response.send_message(f"{server} is Running", ephemeral=True)
        else:
            await interaction.response.send_message(f"{server} is Stopped", ephemeral=True)


    @app_commands.command(name="stop", description="Stop a specific self-hosted server")
    async def slash_stop(self, interaction: discord.Interaction, server: str) -> None:
        """Command that handles all stopping of self-hosted servers"""
        self.check_usable(interaction)
        if server not in self.running_PIDS:
            await interaction.response.send_message(f"Server {server} is not running", ephemeral=True)
        else:
            await interaction.response.send_message(f"Stopping {server}...", ephemeral=True)
            return await self.SERVER_LIST[server](interaction, server_name=server, stop=True)


    @slash_status.autocomplete("server")
    @slash_start.autocomplete("server")
    async def gameserver_stop_autocoplete_server(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=i, value=i)
            for i in self.SERVER_LIST
            if current.lower() in i.lower()
        ]

    @slash_stop.autocomplete("server")
    async def stop_gameserver_autocoplete_server(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=i, value=i)
            for i in self.running_PIDS
            if current.lower() in i.lower()
        ]


    async def handle_mc_cryptopolis(self, interaction: discord.Interaction, server_name: str, stop: bool=False) -> None:
        """Handles Minecraft server start/stop"""
        if stop:
            await self.stop_generic(interaction, server_name)
        else:
            MC_PATH = "C:\\Users\\marti\\curseforge\\minecraft\\Servers\\Cryptopolis_server_pack"
            await self.start_generic(
                interaction,
                server_name,
                exe_path = f"{MC_PATH}\\start.ps1",
                exe_args = ""
            )

    async def handle_scp_sl(self, interaction: discord.Interaction, server_name: str, stop: bool=False) -> None:
        """Handles SCP: Secret Laboratory server start/stop"""
        if stop:
            await self.stop_generic(interaction, server_name)
        else:
            await self.start_generic(
                interaction,
                server_name,
                exe_path = "C:\\Users\\marti\\Documents\\GitHub\\SteamCmd\\steamapps\\common\\SCP Secret Laboratory Dedicated Server\\LocalAdmin.exe",
                exe_args = "7777" #  --id27576 --SCPSL.exe --batchmode --nographics --nodedicateddelete --port7777 --console23082 --disableAnsiColors --heartbeat
            )


    async def handle_conan(self, interaction: discord.Interaction, server_name: str, stop: bool=False) -> None:
        """Handles Conan Exiles server start/stop"""
        if stop:
            await self.stop_generic(interaction, server_name)
        else:
            await self.start_generic(
                interaction = interaction,
                server_name = server_name,
                exe_path = "C:\\Users\\marti\\Desktop\\Folders\\ConanExilesServer\\DedicatedServerLauncher1508.exe",
                exe_args = "",
            )


    async def handle_generic(
            self,
            interaction: discord.Interaction,
            server_name: str,
            exe_path: str, 
            exe_args: str,
            stop: bool=False
        ) -> None:
        """Handles generic server start/stop"""
        self.logger.debug(f"Handling {server_name}")
        if stop:
            await self.stop_generic(interaction, server_name)
        else:
            await self.start_generic(interaction, server_name, exe_path, exe_args)


    async def start_generic(
            self,
            interaction: discord.Interaction,
            server_name: str,
            exe_path: str,
            exe_args: str
        ) -> None:
        """Starts a server"""
        self.logger.info(f"Starting {server_name}")
        try:
            running_server = await self.run_exe(exe_path, exe_args)
        except OSError:
            # if e.errno == errno. # should check for OSError: [WinError 193] %1 is not a valid Win32 application",)
            running_server = await self.run_from_powershell(exe_path, exe_args)
        self.running_PIDS = {server_name : running_server.pid}
        self.logger.debug(f"{self.running_PIDS=}")
        await interaction.edit_original_response(content=f"Started {server_name}")


    async def run_exe(
            self,
            exe_path: str,
            exe_args: str
        ) -> subprocess.Popen:
        # TODO: add seperate logging maybe
        if config.Gameservers.BACKGROUND:
            return subprocess.Popen(f'"{exe_path}" "{exe_args}', creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            return subprocess.Popen(f'"{exe_path}" "{exe_args}')

    async def run_from_powershell(
            self,
            exe_path: str,
            exe_args: str
        ) -> subprocess.Popen:
        # TODO: add seperate logging maybe
        if config.Gameservers.BACKGROUND:
            return subprocess.Popen(["powershell.exe", f"{exe_path} {exe_args}"], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            return subprocess.Popen(["powershell.exe", f"{exe_path} {exe_args}"])


    async def stop_generic(self, interaction: discord.Interaction, server: str) -> None:
        """Stops a server using Ctrl-C"""
        self.logger.info(f"Stopping {server}")
        if interaction:
            pid = self.running_PIDS[server]
        elif interaction is None:
            pid = server
        self.logger.debug(f"{pid}")
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)

        for child in children:
            self.logger.debug(f"terminating {child}")
            child.terminate() # kill child friendly
        parent.terminate() # kill parent friendly

        _, still_alive_children = psutil.wait_procs(children, timeout=3)
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
    await bot.add_cog(GameServers(bot))  # type: ignore
