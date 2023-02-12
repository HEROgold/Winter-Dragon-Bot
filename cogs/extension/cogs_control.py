import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

import config

class CogsC(commands.GroupCog):
    def __init__(self, bot:commands.Bot):
        self.bot: commands.Bot = bot
        self.logger = logging.getLogger("winter_dragon.cogs")

    async def cog_load(self):
        await self.mass_load()

    async def cog_unload(self):
        await self.mass_unload()

    async def get_cogs(self) -> list[str]:
        extensions = []
        for root, subdirs, files in os.walk("cogs"):
            extensions.extend(
                os.path.join(root, file[:-3]).replace("\\", ".")
                for file in files
                if file.endswith(".py")
            )
        return extensions

    async def mass_load(self) -> None:
        cogs = await self.get_cogs()
        for cog in cogs:
            try:
                await self.bot.load_extension(cog)
                self.logger.info(f"Loaded {cog}")
            except Exception as e:
                if isinstance(e, commands.errors.ExtensionFailed):
                    continue
                self.logger.exception(f"Error while loading {cog}")
        if not (os.listdir("./cogs")):
            self.logger.warning("No Cogs Directory To Load!")

    async def mass_unload(self) -> None:
        cogs = await self.get_cogs()
        for cog in cogs:
            try:
                await self.bot.remove_cog(cog)
                self.logger.info(f"Unloaded {cog}")
            except Exception as e:
                self.logger.exception(f"Error while unloading {cog}")
        if not (os.listdir("./cogs")):
            self.logger.warning("No Cogs Directory To Unload!")

    async def mass_reload(self, interaction:discord.Interaction) -> None:
        reload_message = ""
        cogs = await self.get_cogs(self)
        for cog in cogs:
            try:
                self.bot.reload_extension(cog)
            except Exception as e:
                self.logger.exception(f"Error while reloading {cog}")
            self.logger.info(f"Reloaded {cog}")
            reload_message += f"Reloaded {cog}\n"
        await interaction.followup.send(f"{reload_message}Restart complete.")

    # @app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
    @app_commands.command(
        name = "show",
        description= "Show loaded cogs (For bot developer only)"
        )
    async def slash_show_cogs(self, interaction:discord.Interaction):
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        cogs = await self.get_cogs()
        self.logger.debug(f"Showing {cogs} to {interaction.user}")
        await interaction.response.send_message(f"{cogs}", ephemeral=True)

    # @app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
    @app_commands.command(
        name = "reload",
        description = "Reload a specified or all available cogs (For bot developer only)"
        )
    async def slash_restart(self, interaction:discord.Interaction, extension:str):
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        await interaction.response.defer()
        if extension is None :
            await self.mass_reload(interaction)
        else:
            try:
                await self.bot.reload_extension(extension)
                self.logger.info(f"Reloaded {extension}")
                await interaction.followup.send(f"Reloaded {extension}", ephemeral=True)
            except Exception:
                await interaction.followup.send(f"error reloading {extension}", ephemeral=True)

    @slash_restart.autocomplete("extension")
    async def restart_autocomplete_extension(self, interaction:discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=extension, value=extension)
            for extension in self.bot.extensions
            if current.lower() in extension.lower()
        ]

    # @app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
    @app_commands.command(
        name = "unload",
        description = "Unload a specified cog (For bot developer only)"
        )
    async def slash_unload(self, interaction:discord.Interaction, extension:str):
        if not self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        await interaction.response.defer(ephemeral=True)
        if extension is None:
            await interaction.followup.send("Please provide a cog to unload.", ephemeral=True)
        else:
            try:
                await self.bot.unload_extension(extension)
                self.logger.info(f"Unloaded {extension}")
                await interaction.followup.send(f"Unloaded {extension}", ephemeral=True)
            except Exception:
                self.logger.warning(f"unable to reload {extension}")
                await interaction.followup.send(f"Unable to reload {extension}", ephemeral=True)

    @slash_unload.autocomplete("extension")
    async def restart_autocomplete_extension(self, interaction:discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=extension, value=extension)
            for extension in self.bot.extensions
            if current.lower() in extension.lower()
        ]

    # @app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
    @app_commands.command(
        name = "load",
        description = "Load a specified or all available cogs (For bot developer only)"
        )
    async def slash_load(self, interaction:discord.Interaction, extension:str):
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        await interaction.response.defer(ephemeral=True)
        try:
            await self.bot.load_extension(extension)
            self.logger.info(f"Loaded {extension}")
            await interaction.followup.send(f"Loaded {extension}", ephemeral=True)
        except Exception:
            self.logger.warning(f"unable to load {extension}")
            await interaction.followup.send(f"Unable to load {extension}", ephemeral=True)
    
    @slash_load.autocomplete("extension")
    async def restart_autocomplete_extension(self, interaction:discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        cogs = await self.get_cogs()
        return [
            app_commands.Choice(name=extension, value=extension)
            for extension in cogs
            if current.lower() in extension.lower()
        ]

async def setup(bot:commands.Bot):
	await bot.add_cog(CogsC(bot))
