"""Cog for managing command enablement/disablement with interactive UI."""

import discord
from discord import Guild, Interaction, app_commands
from discord.ext import commands
from sqlmodel import Session, select

from winter_dragon.bot.core.cogs import Cog
from winter_dragon.bot.ui.button import ToggleButton
from winter_dragon.bot.ui.paginator import PageSource, Paginator
from winter_dragon.bot.ui.view import View
from winter_dragon.database.tables.command import Commands
from winter_dragon.database.tables.disabled_commands import DisabledCommands

from .sync import LenFixer


class CommandToggleButton(ToggleButton):
    """A button to toggle a command's enabled/disabled state."""

    def __init__(
        self,
        command_name: str,
        **kwargs,  # noqa: ANN003
    ) -> None:
        """Initialize the toggle button for a command."""
        self.command_name = command_name
        super().__init__(**kwargs)


class CommandManagementPageSource(PageSource[list[tuple[str, bool]]]):
    """Page source for displaying commands with toggle buttons."""

    def __init__(
        self,
        commands_list: list,
        view: "CommandManagementView",
        title: str = "Manage Commands",
    ) -> None:
        """Initialize the command management page source."""
        self.commands_data = sorted([cmd for cmd in commands_list if hasattr(cmd, "name")], key=lambda c: c.name)
        self.items_per_page = 5
        self.title = title
        self.view = view

    async def get_page(self, page_number: int) -> list[tuple[str, bool]]:
        """Get a page of commands with their toggle states."""
        start = page_number * self.items_per_page
        end = start + self.items_per_page
        page_commands = self.commands_data[start:end]

        return [(cmd.name, self.view.get_command_state(cmd.name)) for cmd in page_commands]

    async def get_page_count(self) -> int:
        """Get total page count."""
        return (len(self.commands_data) + self.items_per_page - 1) // self.items_per_page

    async def format_page(
        self,
        page_data: list[tuple[str, bool]],
        page_number: int,
    ) -> tuple[str, discord.Embed]:
        """Format the page as an embed with command toggles."""
        total_pages = await self.get_page_count()
        total_commands = len(self.commands_data)

        embed = discord.Embed(
            title=self.title,
            description=f"Toggle commands to disable them for this guild\nPage {page_number + 1}/{total_pages}",
            colour=discord.Colour.blurple(),
        )

        for cmd_name, is_enabled in page_data:
            status = "✅ Enabled" if is_enabled else "❌ Disabled"
            embed.add_field(
                name=f"/{cmd_name}",
                value=status,
                inline=False,
            )

        embed.set_footer(text=f"Total: {total_commands} commands")

        return "", embed


class CommandManagementView(View):
    """View for managing command enablement with toggle buttons and apply button."""

    def __init__(
        self,
        commands_list: list,
        guild: Guild,
        session: Session,
        timeout: float = 600.0,
    ) -> None:
        """Initialize the command management view."""
        super().__init__(timeout=timeout)
        self.commands_list = commands_list
        self.guild = guild
        self.session = session
        # Track toggled state: command_name -> is_enabled
        self.command_states: dict[str, bool] = {cmd.name: True for cmd in commands_list}
        self.message: discord.Message | None = None

    def get_command_state(self, command_name: str) -> bool:
        """Get the current state of a command."""
        return self.command_states.get(command_name, True)

    def set_command_state(self, command_name: str, *, state: bool) -> None:
        """Set the state of a command."""
        self.command_states[command_name] = state

    async def on_paginator_page_change(self, current_page: int) -> None:
        """Paginator page changed."""
        if not self.message:
            return

        # Rebuild the view with toggle buttons for the current page
        await self._update_page_buttons(current_page)

    async def _update_page_buttons(self, page_number: int) -> None:
        """Update buttons for a specific page."""
        # Clear existing items except paginator buttons
        paginator_button_ids = ("paginator_prev", "paginator_info", "paginator_next")
        items_to_remove = [
            item
            for item in self.children
            if not isinstance(item, discord.ui.Button) or item.custom_id not in paginator_button_ids
        ]
        for item in items_to_remove:
            self.remove_item(item)

        # Get commands for this page
        start = page_number * 5
        end = start + 5
        page_commands = self.commands_list[start:end]

        # Add toggle buttons for each command
        for idx, cmd in enumerate(page_commands):
            is_enabled = self.get_command_state(cmd.name)
            button = CommandToggleButton(
                command_name=cmd.name,
                label=f"/{cmd.name}",
                emoji=("✅", "❌")[not is_enabled],
                style=discord.ButtonStyle.success if is_enabled else discord.ButtonStyle.danger,
                custom_id=f"cmd_toggle_{cmd.name}",
                row=idx,
            )
            self.add_item(button)

        # Add apply button on the last row
        apply_button = discord.ui.Button(
            label="Apply Changes",
            emoji="💾",
            style=discord.ButtonStyle.blurple,
            custom_id="cmd_apply",
            row=4,
        )
        apply_button.callback = self._on_apply  # type: ignore[assignment]
        self.add_item(apply_button)

    async def _on_apply(self, interaction: Interaction) -> None:
        """Handle the apply button click."""
        await interaction.response.defer(ephemeral=True)

        # Get disabled commands (those with state False)
        disabled_command_names = [name for name, state in self.command_states.items() if not state]

        if not disabled_command_names:
            await interaction.followup.send("No changes to apply.", ephemeral=True)
            return

        # Store disabled commands in database
        for cmd_name in disabled_command_names:
            # Find or create command in database
            db_cmd = self.session.exec(select(Commands).where(Commands.qual_name == cmd_name)).first()

            if not db_cmd:
                db_cmd = Commands(qual_name=cmd_name, call_count=0)
                self.session.add(db_cmd)
                self.session.commit()

            # Check if already disabled
            existing = self.session.exec(
                select(DisabledCommands).where(
                    DisabledCommands.command_id == db_cmd.id,
                    DisabledCommands.guild_id == self.guild.id,
                )
            ).first()

            if not existing and db_cmd.id is not None:
                disabled = DisabledCommands(
                    command_id=db_cmd.id,
                    guild_id=self.guild.id,
                )
                self.session.add(disabled)

        self.session.commit()

        await interaction.followup.send(
            f"✅ Applied changes! Disabled {len(disabled_command_names)} command(s).",
            ephemeral=True,
        )


class CommandManager(Cog, auto_load=True):
    """Cog for managing command enablement/disablement with interactive UI."""

    @app_commands.command(name="manage-commands", description="Manage which commands are enabled for this guild")
    @app_commands.guild_only()
    async def manage_commands(self, interaction: Interaction) -> None:
        """Open the command manager to enable/disable commands for the guild."""
        await interaction.response.defer(ephemeral=True)

        user = interaction.user
        is_allowed = await self.bot.is_owner(user)

        if not is_allowed:
            msg = "You are not allowed to manage commands"
            self.logger.warning(f"{user} tried to manage commands, but is not allowed.")
            raise commands.NotOwner(msg)

        guild = interaction.guild
        if guild is None:
            msg = "This command can only be used in a guild."
            self.logger.warning(f"{user} tried to manage commands outside a guild.")
            raise commands.NoPrivateMessage(msg)

        # Get all commands that would be synced to this guild
        with LenFixer(self.bot.tree, guild=guild):
            commands_list = self.bot.tree.get_commands(guild=guild)

        if not commands_list:
            await interaction.followup.send("No commands available to manage.", ephemeral=True)
            return

        # Create the management view
        management_view = CommandManagementView(
            commands_list,
            guild,
            self.session,
        )

        # Create a custom paginator with the management view
        class ManagementPageSource(CommandManagementPageSource):
            """Custom page source that uses the management view."""

            async def format_page(
                self,
                page_data: list[tuple[str, bool]],
                page_number: int,
            ) -> tuple[str, discord.Embed]:
                """Format the page and update buttons."""
                # We access _update_page_buttons as it's internal to the view hierarchy
                await management_view._update_page_buttons(page_number)  # noqa: SLF001
                return await super().format_page(page_data, page_number)

        page_source = ManagementPageSource(
            commands_list,
            management_view,
            title=f"Manage Commands - {guild.name}",
        )

        paginator = Paginator(
            page_source,
            on_page_change=management_view.on_paginator_page_change,
        )

        message = await paginator.start(interaction)
        management_view.message = message
