
from typing import Protocol

from discord import Interaction, app_commands
from discord.ext import commands

from winter_dragon.bot.core.cogs import GroupCog

from .settings import Settings


class SupportsString(Protocol):
    """A protocol for objects that can be converted to strings."""

    def __str__(self) -> str:  # pyright: ignore[reportReturnType]
        """Return a string representation of the object."""

def codeblock(language: str, text: SupportsString) -> str:
    """Format a string as a code block with syntax highlighting."""
    return f"```{language}\n{text}\n```"


# TODO: rewrite to be a CogManager.
@app_commands.guilds(Settings.support_guild_id)
class ExtensionManager(GroupCog, auto_load=True):
    """Commands to manage extensions."""

    async def mass_reload(self, interaction: Interaction) -> None:
        """Reload all previously loaded extensions."""
        await interaction.response.defer(ephemeral=True)
        reload_message = ""
        for extension in await self.bot.get_extensions():
            try:
                await self.bot.reload_extension(extension)
            except commands.errors.ExtensionNotLoaded:
                self.logger.exception(f"Cog not loaded {extension}")
            except commands.errors.NoEntryPointError as e:
                await interaction.response.send_message(
                    f"Could not load {extension}, it has no setup function.",
                    ephemeral=True,
                )
                self.logger.warning(e)
            except commands.errors.ExtensionAlreadyLoaded as e:
                await interaction.response.send_message(
                    f"Could not load {extension}, it is already loaded",
                    ephemeral=True,
                )
                self.logger.warning(e)
            except commands.errors.ExtensionFailed as e:
                await interaction.response.send_message(
                    f"Could not load {extension}, {e}",
                    ephemeral=True,
                )
                self.logger.exception(f"Could not load {extension}")
            except ModuleNotFoundError as e:
                await interaction.response.send_message(
                    f"Could not find {extension}, {e}",
                    ephemeral=True,
                )
                self.logger.warning(e)
            except Exception as e:
                self.logger.exception(f"unable to unload {extension}")
                await interaction.response.send_message(
                    f"Unable to load {extension}, {e}",
                    ephemeral=True,
                )
            self.logger.info(f"Reloaded {extension}")
            reload_message += f"Reloaded {extension}\n"
        await interaction.followup.send(f"{reload_message}Restart complete.")


    @app_commands.command(name="crash", description="Raise a random Exception (Bot Dev only)")
    @commands.is_owner()
    async def slash_crash(self, interaction: discord.Interaction) -> None:
        """Raise a CommandInvoke Exception."""
        await interaction.response.send_message("Crashing with discord.app_commands.errors.CommandInvokeError")
        msg = "Test Exception"
        raise commands.CommandInvokeError(Exception(msg))


    @commands.is_owner()
    @app_commands.command(name = "show", description = "Show loaded extensions (For bot developer only)")
    async def slash_show(self, interaction: discord.Interaction) -> None:
        """Show all loaded extensions."""
        extensions = await self.bot.get_extensions()
        self.logger.debug(f"Showing {extensions} to {interaction.user}")
        await interaction.response.send_message(f"{extensions}", ephemeral=True)


    @commands.is_owner()
    @app_commands.command(
        name = "reload",
        description = "Reload a specified or all available extensions (For bot developer only)",
    )
    async def slash_restart(self, interaction: discord.Interaction, extension: str = "") -> None:
        """Reload a specified or all available extensions."""
        self.logger.info(f"{interaction.user} used /reload")
        if not extension:
            self.logger.warning("Reloading all extensions")
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
            except Exception:
                self.logger.exception(f"unable to re-load {extension}")
                await interaction.response.send_message(
                    f"error reloading {extension}",
                    ephemeral=True,
                )


    @app_commands.command(
        name = "unload",
        description = "Unload a specified cog (For bot developer only)",
    )
    @commands.is_owner()
    async def slash_unload(self, interaction: discord.Interaction, extension: str) -> None:
        """Unload a specified extension."""
        try:
            self.logger.info(f"Unloaded {extension}")
            await self.bot.unload_extension(extension)
        except NotFound:
            pass
        except Exception:
            self.logger.critical("REMOVE `except Exception`!")
            self.logger.exception(f"unable to unload {extension}")
        await interaction.response.send_message(f"Unloaded {extension}", ephemeral=True)


    @slash_restart.autocomplete("extension")
    @slash_unload.autocomplete("extension")
    async def autocomplete_extension(
        self,
        _interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete extension names."""
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
        description = "Load a specified or all available extensions (For bot developer only)",
    )
    @commands.is_owner()
    async def slash_load(self, interaction: discord.Interaction, extension: str) -> None:
        """Load a specified extension or all available extensions."""
        try:
            await self.bot.load_extension(extension)
            self.logger.info(f"Loaded {extension}")
            await interaction.response.send_message(f"Loaded {extension}", ephemeral=True)
        except commands.errors.NoEntryPointError as e:
            await interaction.response.send_message(
                f"Could not oad {extension}, it has no setup function.",
                ephemeral=True,
            )
            self.logger.warning(e)
        except commands.errors.ExtensionAlreadyLoaded as e:
            await interaction.response.send_message(
                f"Could not load {extension}, it is already loaded",
                ephemeral=True,
            )
            self.logger.warning(e)
        except commands.errors.ExtensionFailed as e:
            await interaction.response.send_message(
                f"Could not load {extension}, {e}",
                ephemeral=True,
            )
            self.logger.exception(f"Could not load {extension}")
        except Exception:
            self.logger.exception(f"unable to unload {extension}")
            await interaction.response.send_message(f"Unable to load {extension}", ephemeral=True)


    @slash_load.autocomplete("extension")
    async def load_autocomplete_extension(
        self,
        _interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete extension names."""
        extensions = await self.bot.get_extensions()
        return [
            app_commands.Choice(name=extension, value=extension)
            for extension in extensions
            if current.lower() in extension.lower()
        ] or [
            app_commands.Choice(name=extension, value=extension)
            for extension in extensions
        ]
