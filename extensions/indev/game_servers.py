"""
Using SteamCmd allow users/admins to create/manage servers from SteamCmd
# TODO
Currently this code is blocking, when installing, updating, uninstalling etc.
the whole bot waits for it to complete. find and implement a way to have it not block
"""

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
    TODO: Test code and find issues with this
    """
    def install_package(package_name):
        distributions = {
            "debian": "apt-get install -y",
            "ubuntu": "apt-get install -y",
            "centos": "yum install -y",
            "fedora": "dnf install -y",
            "opensuse": "zypper install",
            "arch": "pacman -S --noconfirm",
            "alpine": "apk add --no-cache"
        }

        distro = os.popen('awk -F= "/^NAME/{print $2}" /etc/os-release').read().strip().lower()

        for key in distributions:
            if key in distro:
                os.system(f"{distributions[key]} {package_name}")
                break
        else:
            print("Distro not supported")


class Server(TypedDict):
    id: int
    name: str
    type: str
    last_update: str


class DisabledError(Exception):
    pass

class ServerNotFound(Exception):
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


    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.server_list = get_all_servers()
        # self.is_already_downloading()


    async def cog_load(self) -> None:
        self.test_steamcmd.start()


    async def wait_on_process_finish(self, process: subprocess.Popen) -> None:
        process.wait()
        # while process.poll() is not None:
        #     await asyncio.sleep(0)


    def find_server(self, target: str | int) -> Server | None:
        """
        Find a server by name or id
        
        Parameters
        -----------
        :param:`target`: :class:`str` | :class:`int`
            Target server name
        
        Returns
        -------
        :class:`Server`
            Dict containing server info
        """
        if type(target) == str:
            return next(
                (
                    server
                    for server in self.server_list
                    if target.lower() in server["name"].lower()
                ),
                None,
            )
        elif type(target) == int:
            return next(
                (
                    server
                    for server in self.server_list
                    if target == server["id"]
                ),
                None,
            )


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


    async def download_winget(self):
        self.logger.debug("Downloading Winget")
        
        if not config.getboolean("SteamCMD", "download_winget"):
            raise DisabledError("download_winget is set to False.")
        
        if self.is_already_downloading():
            # TODO: wait to finish
            self.logger.debug("winget not finished downloading.")
            return None

        try:
            await self.wait_on_process_finish(subprocess.Popen(["bitsadmin", BITSADMIN_ARGS_WINGET]))
            await self.wait_on_process_finish(subprocess.Popen(["cmd", INSTALLER_CMD]))
        except Exception as e:
            self.logger.exception(f"error when downloading Winget {e}")
            return None


    async def download_steamcmd(self):
        self.logger.debug("Downloading SteamCMD")
        if not config.getboolean("SteamCMD", "download_steamcmd"):
            raise DisabledError("download_steamcmd is set to False.")
        
        try:
            await self.wait_on_process_finish(subprocess.Popen([
                "winget", "install", WINGET_SteamCMD,
                "--location", os.path.abspath(STEAM_CMD_DIR),
                "--force"]
            ))
        except Exception as e:
            self.logger.exception(f"error when downloading SteamCMD {e}")
            await self.download_winget()


    @tasks.loop(count=1)
    async def test_steamcmd(self) -> None:
        if os.name == "posix":
            self.logger.debug(f"{self.__class__.__name__} Disabled on Posix!")
            return

        self.logger.debug("starting SteamCMD")

        try:
            await self.wait_on_process_finish(subprocess.Popen([
                f"{os.path.abspath(f'{STEAM_CMD_DIR}/steamcmd.exe')}",
                # "+login anonymous",
                "+quit"
            ]))
        except FileNotFoundError as e:
            self.logger.exception(f"error when opening SteamCmd {e}")
            await self.download_steamcmd()
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


    async def login(self, process: subprocess.Popen, username: str, password: str):
        # TODO add processes with user logins at install, update. optionally uninstall?
        # wait for process to prompt password
        async for line in self.live_output(process):
            if line == f"Logging in user '{username}' to Steam Public...":
                process.communicate(password)
                break


    async def uninstall_steamcmd_server(self, target: int | str, interaction: discord.Interaction):
        server = self.find_server(target)
        self.logger.debug(f"starting SteamCMD server {server}")

        if server is None:
            self.logger.warning(f"Server not found when uninstalling {target=}")
            await interaction.edit_original_response("Server not found")
            return

        try:
            subprocess.Popen(
                [
                    f"{os.path.abspath(f'{STEAM_CMD_DIR}/steamcmd.exe')}",
                    "+login anonymous",
                    f"+app_uninstall {server['id']}",
                    "+quit"
                ]
            ).wait()

            os.rmdir(f"""{os.path.abspath(f'{INSTALLED_SERVERS}/{server["name"]}')}""")
        except FileNotFoundError as e:
            self.logger.exception(f"error when uninstalling {server} {e}")
        except Exception as e:
            self.logger.exception(f"error when uninstalling {server} {e}")
            await interaction.edit_original_response(content="Could not uninstall server")
        
        await interaction.edit_original_response(content=f"{server['name']} has been removed")


    async def update_steamcmd_server(
        self,
        server_id: int,
        interaction: discord.Interaction,
        install: bool=False
    ) -> None:
        server = self.find_server(server_id)
        self.logger.debug(f"starting SteamCMD server {server}")

        try:
            # await asyncio.create_subprocess_shell(
            #     cmd = "".join([
            #         f"{os.path.abspath(f'{STEAM_CMD_DIR}/steamcmd.exe')}",
            #         "+login anonymous",
            #         f"+app_update {server_id}",
            #         "+quit"
            #     ]),
            # )
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

            status = "unknown"
            last_update = datetime.now()

            async for line in self.live_output(process):
                if "ERROR!" in line:
                    await interaction.edit_original_response(content=line)
                    return
                if "already up to date" in line:
                    await interaction.edit_original_response(content="Already up to date.")
                    return
                if "downloading" in line:
                    status = "downloading"
                if "installing" in line:
                    status = "installing"
                if "updating" in line:
                    status = "updating"
                if (
                    "progress" in line
                    and last_update < datetime.now() - timedelta(seconds=15)
                ):
                    progress_len = len("progress: ")
                    l_index = line.index("progress")
                    percent = line[l_index+progress_len:l_index+progress_len+3]
                    bits = line[line[l_index:].index("(")+l_index:-1]

                    await interaction.edit_original_response(content=f"{status} {percent}% {bits} bytes") # {line[l_index:]}
                    last_update = datetime.now()

        except FileNotFoundError as e:
            self.logger.exception(f"error when starting {server} {e}")
        except Exception as e:
            self.logger.exception(f"error when starting {server} {e}")
            await interaction.edit_original_response(content="Could not start server")
        
        await interaction.edit_original_response(content=f"{server['name']} has been {'installed' if install else 'updated'}")


    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="install", description="Install a steam server")
    async def slash_server_install(self, interaction: discord.Interaction, server_name: str) -> None:
        await interaction.response.defer()

        for server in self.server_list:
            if server["name"] == server_name:
                if server_name in self.get_installed_servers():
                    await interaction.followup.send("Server already installed, please update instead.")
                    break
                await interaction.followup.send(f"Installing {server_name}...")
                await self.update_steamcmd_server(server["id"], interaction, install=True)
                break
        else:
            await interaction.edit_original_response(content=f"{server_name} could not be found")


    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="uninstall", description="UnInstall a installed steam server")
    async def slash_server_uninstall(self, interaction: discord.Interaction, server_name: str) -> None:
        await interaction.response.defer()

        for server in self.get_installed_servers():
            if server == server_name:
                await interaction.followup.send(f"UnInstalling {server_name}...")
                await self.uninstall_steamcmd_server(server, interaction)
                await interaction.edit_original_response(content=f"{server_name} has been removed")
                break
        else:
            await interaction.edit_original_response(content=f"{server_name} could not be found")


    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="update", description="Update or install a steam server")
    async def slash_server_update(self, interaction: discord.Interaction, server_name: str) -> None:
        await interaction.response.defer()

        for server in self.server_list:
            if server["name"] == server_name:
                if server_name in self.get_installed_servers():
                    self.logger.debug("Server is installed")
                    await interaction.followup.send(f"Updating {server_name}...")
                    await self.update_steamcmd_server(server["id"], interaction)
                else:
                    await interaction.followup.send(f"Installing {server_name}...")
                    await self.update_steamcmd_server(server["id"], interaction, install=True)
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
        await interaction.edit_original_response(content=f"{server_name} has started")


    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="start", description="Start a steam server")
    async def slash_server_start(self, interaction: discord.Interaction, server_name: str) -> None:
        await interaction.response.defer()

        for server in self.server_list:
            if server["name"] == server_name:
                await interaction.followup.send(f"Starting {server_name}...")
                await self.start_steamcmd_server(server["name"], interaction)
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
    main()
    await bot.add_cog(SteamServers(bot))
