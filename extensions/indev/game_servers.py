"""
Using SteamCmd allow users/admins to create/manage servers from SteamCmd
"""

import asyncio
from datetime import datetime, timedelta
import os
import random
import subprocess
from typing import Any, Generator, TypedDict

import discord
from discord import app_commands
from discord.ext import tasks

from _types.bot import WinterDragon
from _types.cogs import GroupCog  # , Cog
from tools.config_reader import config


STEAM_CMD_DIR = "./steam_cmd"
INSTALLED_SERVERS = f"{STEAM_CMD_DIR}/steamapps/common"
STEAM_SERVER_STORAGE = f"{STEAM_CMD_DIR}/steam_cmd/steamapps"
STEAM_DB_LIST = "SteamDb Servers.txt"


if os.name == "nt":
    WINGET_SteamCMD = "Valve.SteamCMD"
    DOWNLOADER = "bitsadmin"
    TEMP_FILE = r"c:\temp\Winget.msixbundle"
    WINGET_INSTALLER = "https://github.com/microsoft/winget-cli/releases/download/v1.5.2201/Microsoft.DesktopAppInstaller_8wekyb3d8bbwe.msixbundle"
    BITSADMIN_ARGS_WINGET = f"/transfer Winget /download {WINGET_INSTALLER} {TEMP_FILE}"
    INSTALLER_CMD = f"start {TEMP_FILE}"
elif os.name == "posix":
    """
    Find possible package managers installed on system, download using that
    """


class Server(TypedDict):
    id: int
    name: str
    type: str
    last_update: str


class DisabledError(Exception):
    pass


def get_all_servers() -> list[Server]:
    """
    Creates a :class:`TypedDict` form a list of servers from a txt file
    
    
    Returns
    -------
    :class:`Servers`
        a :class:`dict` with iteration numbers and a :class:`TypedDict` that contains server info
    """
    with open(STEAM_DB_LIST, "r", encoding="utf8") as f:
        servers: list[Server] = []
        for line in f:
            server = {}
            for pairs in [i.split(":") for i in line.split(",")]:
                name = pairs[0]
                # join values when names are separated with `,`
                value = "".join(pairs[1:]) 
                server[f"{name}"] = value
            servers.append(server)
        return servers


class SteamServers(GroupCog):
    server_list: list[Server]
    processes: list[subprocess.Popen]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.server_list = get_all_servers()
        self.is_already_downloading()


    async def cog_load(self) -> None:
        self.test_steamcmd.start()


    def get_installed_servers(self) -> list[str]:
        servers = os.listdir(INSTALLED_SERVERS)
        self.logger.debug(f"{len(servers)=} {servers=}")
        return servers


    def is_already_downloading(self) -> bool:
        monitor = subprocess.check_output(["powershell.exe", "bitstransfer"])
        output = monitor.decode()
        self.logger.debug(f"{output=}")

        if "Winget" in output:
            self.logger.warning("Found Winget in bitsadmin monitor")
            return True
        return False


    def download_winget(self):
        self.logger.debug("Downloading Winget")
        
        if not config.getboolean("SteamCMD", "download_winget"):
            raise DisabledError("download_winget is set to False.")
        
        if self.is_already_downloading():
            # TODO: wait to finish
            return None

        try:
            subprocess.Popen(["bitsadmin", BITSADMIN_ARGS_WINGET]).wait()
            subprocess.Popen(["cmd", INSTALLER_CMD]).wait()
        except Exception as e:
            self.logger.exception(f"error when downloading Winget {e}")
            return None


    def download_steamcmd(self):
        self.logger.debug("Downloading SteamCMD")
        if not config.getboolean("SteamCMD", "download_steamcmd"):
            raise DisabledError("download_steamcmd is set to False.")
        
        try:
            subprocess.Popen([
                "winget", "install", WINGET_SteamCMD,
                "--location", os.path.abspath(STEAM_CMD_DIR),
                "--force"]
            ).wait()
        except Exception as e:
            self.logger.exception(f"error when downloading SteamCMD {e}")
            self.download_winget()


    @tasks.loop(count=1)
    async def test_steamcmd(self) -> None:
        self.logger.debug("starting SteamCMD")

        try:
            subprocess.Popen([
                f"{os.path.abspath(f'{STEAM_CMD_DIR}/steamcmd.exe')}",
                # "+login anonymous",
                "+quit"
            ]).wait()
        except FileNotFoundError as e:
            self.logger.exception(f"error when opening SteamCmd {e}")
            self.download_steamcmd()
        except DisabledError as e:
            self.logger.warning(f"User has disabled downloading: {e}")


    @test_steamcmd.before_loop
    async def before_test(self) -> None:
        self.logger.info("Waiting until bot is online")
        await self.bot.wait_until_ready()


    async def live_output(self, process: subprocess.Popen) -> Generator[str, str, None]:
        for line in iter(process.stdout.readline, ""):
            self.logger.debug(f"{line=}")
            yield line


    async def uninstall_steamcmd_server(self, server_id: int, interaction: discord.Interaction):
        self.logger.debug(f"starting SteamCMD server {server_id}")

        try:
            subprocess.Popen(
                [
                    f"{os.path.abspath(f'{STEAM_CMD_DIR}/steamcmd.exe')}",
                    "+login anonymous",
                    f"+app_uninstall {server_id}",
                    "+quit"
                ]
            ).wait()
        except FileNotFoundError as e:
            self.logger.exception(f"error when uninstalling {server_id} {e}")
        except Exception as e:
            self.logger.exception(f"error when uninstalling {server_id} {e}")
            await interaction.edit_original_response(content="Could not uninstall server")


    async def update_steamcmd_server(
        self,
        server_id: int,
        interaction: discord.Interaction,
        install: bool=False
    ) -> None:
        self.logger.debug(f"starting SteamCMD server {server_id}")

        # TODO: catch steamcmd warnings, and push those to the message when it fails
        try:
            process = subprocess.Popen(
                [
                    f"{os.path.abspath(f'{STEAM_CMD_DIR}/steamcmd.exe')}",
                    "+login anonymous",
                    f"+app_update {server_id}",
                    "+quit"
                ],
                stdout=subprocess.PIPE,
                universal_newlines=True
            )

            status = "installing" if install else "updating"
            last_update = datetime.now()

            async for line in self.live_output(process):
                if "progress" in line:
                    l_index = line.index("progress")

                    if last_update < datetime.now() - timedelta(seconds=15):
                        await interaction.edit_original_response(content=f"{status} {line[l_index:]}")
                if "already up to date" in line:
                    await interaction.edit_original_response(content="Already up to date.")

        except FileNotFoundError as e:
            self.logger.exception(f"error when starting {server_id} {e}")
        except Exception as e:
            self.logger.exception(f"error when starting {server_id} {e}")
            await interaction.edit_original_response(content="Could not start server")


    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="install", description="Install a steam server")
    async def slash_server_install(self, interaction: discord.Interaction, server_name: str) -> None:
        await interaction.response.defer()

        for server in self.server_list:
            if server["name"] == server_name:
                # TODO: find out if server is installed, change message based on that
                await interaction.followup.send(f"Installing {server_name}...")
                await self.update_steamcmd_server(server["id"], interaction)
                await interaction.edit_original_response(content=f"{server_name} has started")
                break
        else:
            await interaction.edit_original_response(content=f"{server_name} could not be found")


    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="uninstall", description="UnInstall a installed steam server")
    async def slash_server_uninstall(self, interaction: discord.Interaction, server_name: str) -> None:
        await interaction.response.defer()

        for server in self.server_list:
            if server["name"] == server_name:
                await interaction.followup.send(f"UnInstalling {server_name}...")
                await self.uninstall_steamcmd_server(server["id"], interaction)
                await interaction.edit_original_response(content=f"{server_name} has been removed")
                break
        else:
            await interaction.edit_original_response(f"{server_name} could not be found")


    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="update", description="Update a steam server")
    async def slash_server_update(self, interaction: discord.Interaction, server_name: str) -> None:
        await interaction.response.defer()

        for server in self.server_list:
            if server["name"] == server_name:
                if server_name in self.get_installed_servers():
                    self.logger.debug("Server is installed")

                # TODO: find out if server is installed, change message based on that
                await interaction.followup.send(f"Updating {server_name}...")
                await self.update_steamcmd_server(server["id"], interaction)
                await interaction.edit_original_response(content=f"{server_name} has started")
                break
        else:
            await interaction.edit_original_response(content=f"{server_name} could not be found")

    def get_server_executable_path(self) -> str:
        # TODO: find if servers file contains .bat, .exe or any other executables.
        pass


    async def start_steamcmd_server(self, server_name: str, interaction: discord.Interaction):
        servers = self.get_installed_servers()
        if server_name in servers:
            self.get_server_executable_path()
        # TODO: create script that adds a easy interface to run steam servers
        # TODO: send warning when not found
        # Add auto_complete


    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="start", description="Start a steam server")
    async def slash_server_start(self, interaction: discord.Interaction, server_name: str) -> None:
        await interaction.response.defer()

        for server in self.server_list:
            if server["name"] == server_name:
                await interaction.followup.send(f"Starting {server_name}...")
                await self.start_steamcmd_server(server["name"], interaction)
                await interaction.edit_original_response(content=f"{server_name} has started")
                break
        else:
            await interaction.edit_original_response(content=f"{server_name} could not be found")

#
# AutoCompletes
#

    @slash_server_start.autocomplete("server_name")
    @slash_server_update.autocomplete("server_name")
    @slash_server_uninstall.autocomplete("server_name")
    async def start_autocomplete_server(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        options = [
            app_commands.Choice(name=i, value=i)
            for i
            in self.get_installed_servers()
        ]

        if len(options) >= 24:
            randomized = random.choices(options, k=25)
            self.logger.debug(f"{randomized=}")
            return randomized
        return options


    @slash_server_install.autocomplete("server_name")
    async def install_autocomplete_server(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        options = [
            app_commands.Choice(name=server["name"], value=server["name"]) 
            for server in self.server_list
            if current.lower() in server["name"].lower()
        ]
        self.logger.debug(len(options))
        if len(options) >= 24:
            randomized = random.choices(options, k=25)
            self.logger.debug(f"{randomized=}")
            return randomized
        return options


## STEAM USAGE
# Usage:  steamcmd ["+COMMAND [ARG]..."]...
#   or:   steamcmd +runscript SCRIPTFILE

# Help topics - type "help <topic>" or run with "--help <topic>" for more information:

#                login : Logging in to Steam
#              scripts : Executing a sequence of commands via a script file
#          commandline : Executing commands directly via the OS command line
#              convars : Options and settings that affect this program session
#            app_build : Building Steam application content (only for licensed Steam application developers)
#           app_update : Installing/updating a Steam application on the local filesystem (EG dedicated servers)


# You can also type "find <string>" to see a list of all commands and convars that contain or reference <string>.


def main() -> None:
    os.makedirs(STEAM_CMD_DIR, exist_ok=True)


async def setup(bot: WinterDragon) -> None:
    return
    main()
    await bot.add_cog(SteamServers(bot))
