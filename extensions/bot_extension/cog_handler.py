import datetime
import os
from typing import Any, TypedDict

import discord
from discord import NotFound, app_commands
from discord.ext import commands, tasks

from tools.config_reader import config
from _types.cogs import Cog, GroupCog
from _types.bot import WinterDragon


class FileData(TypedDict):
    filepath: str
    cog_path: str
    edit_time: float


class CogData(TypedDict):
    timestamp: float
    files: dict[str, FileData]
    edited: dict[str, FileData]


class AutoCogReloader(Cog):
    data: CogData


    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.data = {
            "timestamp": datetime.datetime.now().timestamp(),
            "files": {},
            "edited" : {}
        }


    async def cog_load(self) -> None:
        if not self.data["files"]:
            self.logger.info("Starting Auto Reloader.")
            self.auto_reload.start()


    def get_cog_data(self) -> None:
        for root, _, files in os.walk("extensions"):
            for file in files:
                if not file.endswith(".py"):
                    continue
                if file == os.path.basename(__file__):
                    # self.logger.debug(f"Skipping {file} (myself/itself)")
                    continue
                # self.logger.debug(f"Getting data from {file}")
                file_path = os.path.join(root, file)
                cog_path = os.path.join(root, file[:-3]).replace("/", ".").replace("\\", ".")
                with open(file_path, "r") as f:
                    edit_timestamp = os.path.getmtime(file_path)
                    self.data["files"][file] = {
                        "filepath": f.name,
                        "cog_path": cog_path,
                        "edit_time": edit_timestamp,
                    }


    def check_edits(self) -> None:
        files = self.data["files"]
        self.get_cog_data()

        start_time = self.data["timestamp"]
        for file in files:
            edit_time = self.data["files"][file]["edit_time"]
            if start_time < edit_time:
                if file in self.data["edited"]:
                    continue
                self.logger.info(f"{file} has been edited!")
                self.data["edited"][file] = self.data["files"][file]


    @tasks.loop(seconds=5)
    async def auto_reload(self) -> None:
        if not self.data["edited"]:
            self.check_edits()
        for file_name, file_data in list(self.data["edited"].items()):
            try:
                self.logger.debug(f"before reloading: {file_data=}")
                await self.bot.reload_extension(file_data["cog_path"])
                self.logger.info(f"Automatically reloaded {file_name}")
            except commands.errors.ExtensionNotLoaded:
                self.logger.warning(f"Cannot reload {file_name}, it's not loaded")
            del self.data["edited"][file_name]
        self.data["timestamp"] = datetime.datetime.now().timestamp()


@app_commands.guilds(config.getint("Main", "support_guild_id"))
class CogsC(GroupCog):

    @staticmethod
    def get_extensions() -> list[str]:
        extensions = []
        for root, _, files in os.walk("extensions"):
            extensions.extend(
                os.path.join(root, file[:-3]).replace("/", ".").replace("\\", ".")
                for file in files
                if file.endswith(".py")
            )
        return extensions


    async def mass_reload(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        reload_message = ""
        for extension in self.get_extensions():
            try:
                await self.bot.reload_extension(extension)
            except commands.errors.ExtensionNotLoaded as e:
                self.logger.exception(f"Cog not loaded {extension}, {e}")
            except commands.errors.NoEntryPointError as e:
                await interaction.response.send_message(
                    f"Could not oad {extension}, it has no setup function.",
                    ephemeral=True
                )
                self.logger.warning(e)
            except commands.errors.ExtensionAlreadyLoaded as e:
                await interaction.response.send_message(
                    f"Could not load {extension}, it is already loaded",
                    ephemeral=True
                )
                self.logger.warning(e)
            except commands.errors.ExtensionFailed as e:
                await interaction.response.send_message(
                    f"Could not load {extension}, {e}",
                    ephemeral=True
                )
                self.logger.exception(e)
            except ModuleNotFoundError as e:
                await interaction.response.send_message(
                    f"Could not find {extension}, {e}",
                    ephemeral=True
                )
                self.logger.warning(e)
            except Exception as e:
                self.logger.exception(f"unable to unload {extension}, {e}")
                await interaction.response.send_message(
                    f"Unable to load {extension}",
                    ephemeral=True
                )
            self.logger.info(f"Reloaded {extension}")
            reload_message += f"Reloaded {extension}\n"
        await interaction.followup.send(f"{reload_message}Restart complete.")


    @app_commands.command(name="crash", description="Raise a random Exception (Bot Dev only)")
    @commands.is_owner()
    async def slash_crash(self, interaction:discord.Interaction) -> None:
        await interaction.response.send_message("Crashing with discord.app_commands.errors.CommandInvokeError")
        raise commands.CommandInvokeError("Test Exception")


    @commands.is_owner()
    @app_commands.command(name = "show", description = "Show loaded extensions (For bot developer only)")
    async def slash_show(self, interaction: discord.Interaction) -> None:
        extensions = self.get_extensions()
        self.logger.debug(f"Showing {extensions} to {interaction.user}")
        await interaction.response.send_message(f"{extensions}", ephemeral=True)


    @commands.is_owner()
    @app_commands.command(
        name = "reload",
        description = "Reload a specified or all available extensions (For bot developer only)"
    )
    async def slash_restart(self, interaction: discord.Interaction, extension: str = None) -> None:
        self.logger.info(f"{interaction.user} used /reload")
        if extension is None:
            self.logger.warning("Reloaded all extensions")
            await self.mass_reload(interaction)
        else:
            try:
                await self.bot.reload_extension(extension)
                self.logger.info(f"Reloaded {extension}")
                await interaction.response.send_message(f"Reloaded {extension}", ephemeral=True)
            except commands.ExtensionNotLoaded:
                await interaction.response.send_message(
                    f"Cannot load {extension} is not loaded",
                )
            except Exception as e:
                self.logger.exception(f"unable to re-load {extension}, {e}")
                await interaction.response.send_message(
                    f"error reloading {extension}",
                    ephemeral=True
                )


    @app_commands.command(
        name = "unload",
        description = "Unload a specified cog (For bot developer only)"
    )
    @commands.is_owner()
    async def slash_unload(self, interaction: discord.Interaction, extension: str) -> None:
        try:
            self.logger.info(f"Unloaded {extension}")
            await self.bot.unload_extension(extension)
        except NotFound:
            pass
        except Exception as e:
            self.logger.critical("REMOVE `except Exception`!")
            self.logger.exception(f"unable to unload {extension}, {e}")
        await interaction.response.send_message(f"Unloaded {extension}", ephemeral=True)


    @slash_restart.autocomplete("extension")
    @slash_unload.autocomplete("extension")
    async def autocomplete_extension(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=extension, value=extension)
            for extension in self.bot.extensions
            if current.lower() in extension.lower()
        ] or [
            app_commands.Choice(name=extension, value=extension)
            for extension in self.bot.extensions
        ]


    @app_commands.command(
        name = "load",
        description = "Load a specified or all available extensions (For bot developer only)"
    )
    @commands.is_owner()
    async def slash_load(self, interaction: discord.Interaction, extension: str) -> None:
        try:
            await self.bot.load_extension(extension)
            self.logger.info(f"Loaded {extension}")
            await interaction.response.send_message(f"Loaded {extension}", ephemeral=True)
        except commands.errors.NoEntryPointError as e:
            await interaction.response.send_message(
                f"Could not oad {extension}, it has no setup function.",
                ephemeral=True
            )
            self.logger.warning(e)
        except commands.errors.ExtensionAlreadyLoaded as e:
            await interaction.response.send_message(
                f"Could not load {extension}, it is already loaded",
                ephemeral=True
            )
            self.logger.warning(e)
        except commands.errors.ExtensionFailed as e:
            await interaction.response.send_message(
                f"Could not load {extension}, {e}",
                ephemeral=True
            )
            self.logger.exception(e)
        except Exception as e:
            self.logger.exception(f"unable to unload {extension}, {e}")
            await interaction.response.send_message(f"Unable to load {extension}", ephemeral=True)


    @slash_load.autocomplete("extension")
    async def load_autocomplete_extension(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        extensions = self.get_extensions()
        return [
            app_commands.Choice(name=extension, value=extension)
            for extension in extensions
            if current.lower() in extension.lower()
        ] or [
            app_commands.Choice(name=extension, value=extension)
            for extension in extensions
        ]


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(AutoCogReloader(bot))
    await bot.add_cog(CogsC(bot))