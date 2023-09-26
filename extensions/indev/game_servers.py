"""
Using SteamCmd allow users/admins to create/manage servers from SteamCmd
"""

import os
import random
import subprocess
from typing import Any, TypedDict
import discord
from discord import app_commands
from discord.ext import tasks

from tools.config_reader import config
from _types.cogs import GroupCog #, Cog
from _types.bot import WinterDragon

STEAM_CMD_DIR = "./steam_cmd"
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

os.makedirs(STEAM_CMD_DIR, exist_ok=True)

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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.server_list = get_all_servers()


    async def cog_load(self) -> None:
        self.test_steamcmd.start()


    def find_download_job(self):
        # TODO: find the "Winget" download, and wait for it, or cancel it
        
        subprocess.Popen(["bitsadmin"], ["/monitor"])
        # Send ctrl + c, read output as strings
        # find "Winget"


    def download_winget(self):
        self.logger.debug("Downloading Winget")
        if not config.getboolean("SteamCMD", "download_winget"):
            raise ValueError("download_winget is set to False.")
        
        try:
            subprocess.Popen(["bitsadmin", BITSADMIN_ARGS_WINGET]).wait()
            subprocess.Popen(["cmd", INSTALLER_CMD])
        except Exception as e:
            self.logger.exception(f"error when downloading Winget {e}")
            return None


    def download_steamcmd(self):
        self.logger.debug("Downloading SteamCMD")
        if not config.getboolean("SteamCMD", "download_steamcmd"):
            raise ValueError("download_steamcmd is set to False.")
        
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

    @test_steamcmd.before_loop
    async def before_test(self) -> None:
        self.logger.info("Waiting until bot is online")
        await self.bot.wait_until_ready()


    async def update_steamcmd_server(self, server_id: int, interaction: discord.Interaction) -> None:
        self.logger.debug(f"starting SteamCMD server {server_id}")

        # TODO: catch steamcmd warnings, and push those to the message when it fails
        try:
            subprocess.Popen([
                f"{os.path.abspath(f'{STEAM_CMD_DIR}/steamcmd.exe')}",
                "+login anonymous",
                f"+app_update {server_id}",
                "+quit"
            ]).wait()
        except FileNotFoundError as e:
            self.logger.exception(f"error when starting {server_id} {e}")
        except Exception as e:
            self.logger.exception(f"error when starting {server_id} {e}")
            await interaction.followup.edit_message("Could not start server")


    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="update", description="Install or update steam server")
    async def slash_server_update(self, interaction: discord.Interaction, server_name: str) -> None:
        await interaction.response.defer()

        for server in self.server_list:
            if server["name"] == server_name:
                await interaction.followup.send(f"Starting {server_name}...")
                await self.update_steamcmd_server(server["id"], interaction)
                await interaction.followup.edit_message(f"{server_name} has started")
                break
        else:
            await interaction.followup.edit_message(f"{server_name} could not be found")


    @slash_server_update.autocomplete("server_name")
    async def activity_autocomplete_server(
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


    async def start_steamcmd_server(self, server_name: str, interaction: discord.Interaction):
        # TODO: find server in STEAM_SERVER_STORAGE, find / execute exe.
        # TODO: create script that adds a easy interface to run steam servers
        # TODO: send warning when not found
        # Add auto_complete
        pass


    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="start", description="Start a steam server")
    async def slash_server_start(self, interaction: discord.Interaction, server_name: str) -> None:
        await interaction.response.defer()

        for server in self.server_list:
            if server["name"] == server_name:
                await interaction.followup.send(f"Starting {server_name}...")
                await self.start_steamcmd_server(server["name"], interaction)
                await interaction.followup.edit_message(f"{server_name} has started")
                break
        else:
            await interaction.followup.edit_message(f"{server_name} could not be found")

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


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(SteamServers(bot))