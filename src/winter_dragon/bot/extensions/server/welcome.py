"""Module to hold welcoming cogs."""

import discord
from discord import Interaction, app_commands
from sqlmodel import Session, col, select
from winter_dragon.database.constants import SessionMixin
from winter_dragon.database.tables import Welcome as WelcomeDb

from winter_dragon.bot.core.cogs import Cog
from winter_dragon.bot.ui import Menu, Modal
from winter_dragon.bot.ui.button import Button, ToggleButton
from winter_dragon.config import Config


class WelcomeMenu(Menu, SessionMixin):
    """Menu for configuring welcome settings."""

    def __init__(self, interaction: discord.Interaction, timeout: float = 300.0) -> None:
        """Initialize the welcome menu."""
        super().__init__(timeout=timeout)
        if not interaction.guild:
            msg = "Interaction must have a guild before initializing WelcomeMenu"
            raise ValueError(msg)

        self.guild = interaction.guild
        self.interaction = interaction
        welcome = WelcomeDb.from_(col(WelcomeDb.guild_id), interaction.guild.id, self.session).first()
        if not welcome:
            msg = f"No welcome data found for guild {interaction.guild.id}"
            raise ValueError(msg)

        self.welcome = welcome
        toggle_button = ToggleButton()
        toggle_button.state = self.welcome.enabled

        async def on_toggle(_: discord.Interaction) -> None:
            self.welcome.enabled = not self.welcome.enabled
            self.session.add(self.welcome)
            self.session.commit()

        toggle_button.on_interact = on_toggle

        async def on_edit_message(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(WelcomeMessageModal(self.welcome, interaction, self.session))

        edit_button = Button(
            label="Edit Message",
            style=discord.ButtonStyle.primary,
            emoji="✏️",
            on_interact=on_edit_message,
            row=0,
        )

        self.add_item(toggle_button)
        self.add_item(edit_button)

    def embed(self) -> discord.Embed:
        """Build the welcome settings embed."""
        embed = discord.Embed(
            title="Welcome Message Settings",
            description="Configure how new members are greeted",
            colour=discord.Colour.blurple(),
        )

        embed.add_field(name="Status", value="✅ Enabled" if self.welcome.enabled else "❌ Disabled", inline=False)

        embed.add_field(
            name="Current Message",
            value=f"```\n{self.welcome.message}\n```",
            inline=False,
        )

        if channel := self.guild.system_channel:
            embed.add_field(
                name="Channel",
                value=f"{channel.mention}",
                inline=False,
            )

        return embed


class WelcomeMessageModal(Modal):
    """Modal for editing the welcome message."""

    message_input = discord.ui.TextInput(
        label="Welcome Message",
        placeholder="Enter the welcome message",
        style=discord.TextStyle.long,
        max_length=2000,
    )

    def __init__(self, entry: WelcomeDb, interaction: Interaction, session: Session) -> None:
        """Initialize the modal with the current message."""
        super().__init__(title="Edit Welcome Message", custom_id="welcome_message_modal")
        if not interaction.guild or not interaction.channel:
            msg = "Interaction must have a guild and a channel"
            raise ValueError(msg)
        self.message_input.default = entry.message
        self.channel = interaction.channel
        self.guild = interaction.guild
        self.session = session
        self.entry = entry

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handle modal submission and update the database."""
        await interaction.response.defer()

        # At this point a WelcomeDb entry should exist. Created in `/welcome` command.
        if data := self.session.exec(select(WelcomeDb).where(WelcomeDb.guild_id == self.guild.id)).first():
            data.message = self.message_input.value
            self.session.commit()
            self.logger.info(f"Welcome message updated for {self.guild=} by {interaction.user=})")
        else:
            msg = f"No welcome data found for guild {self.guild.id}"
            self.logger.error(msg)
            await interaction.followup.send(msg, ephemeral=True)
            return


@app_commands.guild_only()
@app_commands.checks.has_permissions(administrator=True)
class Welcome(Cog, auto_load=True):
    """Cog containing the welcome commands."""

    allowed_welcome_dm = Config(default=True)

    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Send a welcome message to the user when they join the server."""
        self.logger.debug(f"{member} joined {member.guild}")
        welcome = self.session.exec(select(WelcomeDb).where(WelcomeDb.guild_id == member.guild.id)).first()
        message = welcome.message if welcome else None
        channel = member.guild.system_channel
        cmd = self.get_app_command("help")
        mention = cmd.mention if cmd else "the help command"
        default_message = f"Welcome {member.mention} to {member.guild},\nyou may use {mention} to see what commands I have!"
        if channel is not None and self.allowed_welcome_dm is False:
            self.logger.warning(f"Sending welcome message to channel {channel.id} for {member} in guild {member.guild.id}")
            if message:
                await channel.send(message)
                self.logger.info(f"Sent custom welcome message to {channel.id} for new member {member}")
            else:
                await channel.send(default_message)
                self.logger.info(f"Sent default welcome message to {channel.id} for new member {member}")
        elif channel is not None and self.allowed_welcome_dm is True and member.bot is False:
            self.logger.warning(f"Sending welcome message to DM for {member} (ID: {member.id})")
            if message:
                await member.send(message)
                self.logger.info(f"Sent custom welcome message via DM to new member {member}")
            else:
                await member.send(default_message)
                self.logger.info(f"Sent default welcome message via DM to new member {member}")
        else:
            self.logger.warning(f"Welcome failed for {member=}: {channel=}, {self.allowed_welcome_dm=}, {member.bot=}")

    @app_commands.command(name="welcome", description="Configure welcome messages")
    async def slash_welcome(self, interaction: discord.Interaction) -> None:
        """Configure welcome message settings with an interactive menu."""
        if interaction.guild is None:
            msg = "Guild is None"
            self.logger.error(f"Welcome command failed: {msg} for user {interaction.user}")
            await interaction.response.send_message(msg, ephemeral=True)
            return

        if interaction.guild.system_channel is None:
            msg = "Guild has no system channel"
            self.logger.warning(f"Welcome command in guild {interaction.guild.id} - {msg}")
            await interaction.response.send_message(msg, ephemeral=True)
            return

        welcome = self.session.exec(select(WelcomeDb).where(WelcomeDb.guild_id == interaction.guild.id)).first()
        if not welcome:
            self.logger.info(f"No welcome data found for guild {interaction.guild.id}, creating default entry")
            welcome = WelcomeDb(
                guild_id=interaction.guild.id,
                channel_id=interaction.guild.system_channel.id,
                message=f"Welcome to {interaction.guild.name}",
                enabled=False,
            )
            self.session.add(welcome)
            self.session.commit()

        menu = WelcomeMenu(interaction)

        embed = menu.embed()
        embed.set_footer(text="Use the buttons below to modify settings")

        await interaction.response.send_message(embed=embed, view=menu, ephemeral=True)
