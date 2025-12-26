"""Module to hold welcoming cogs."""

import discord
from discord import app_commands
from sqlmodel import select

from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.bot.core.config import Config
from winter_dragon.database.tables import Welcome as WelcomeDb


@app_commands.guild_only()
@app_commands.checks.has_permissions(administrator=True)
class Welcome(GroupCog, auto_load=True):
    """Cog containing the welcome commands."""

    allowed_welcome_dm = Config(default=True)

    @GroupCog.listener()
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
            self.logger.warning("sending welcome to guilds system_channel")
            if message:
                await channel.send(message)
            else:
                await channel.send(default_message)
        elif channel is not None and self.allowed_welcome_dm is True and member.bot is False:
            self.logger.warning("sending welcome to user's dm")
            if message:
                await member.send(message)
            else:
                await member.send(default_message)
        else:
            self.logger.warning("No system_channel to welcome user to, and dm is disabled.")

    @app_commands.command(name="enable", description="Enable welcome message")
    async def slash_enable(self, interaction: discord.Interaction) -> None:
        """Enable the welcome msg."""
        await self.update_data(interaction, enabled=True)
        await interaction.response.send_message("Enabled welcome message.", ephemeral=True)

    @app_commands.command(name="disable", description="Disable welcome message")
    async def slash_disable(self, interaction: discord.Interaction) -> None:
        """Disable the welcome msg."""
        await self.update_data(interaction, enabled=False)
        await interaction.response.send_message("Disabled welcome message.", ephemeral=True)

    @app_commands.command(name="message", description="Change the welcome message")
    async def slash_set_msg(self, interaction: discord.Interaction, message: str) -> None:
        """Set the welcome msg."""
        await self.update_data(interaction, message)
        await interaction.response.send_message(f"changed message to {message}")

    async def update_data(
        self,
        interaction: discord.Interaction,
        message: str | None = None,
        channel_id: int | None = None,
        *,
        enabled: bool | None = None,
    ) -> None:
        """Update the welcome message in the database."""
        self.logger.debug(f"updating {WelcomeDb} for {interaction.guild} to {message=}, {enabled=}, {channel_id=}")
        if interaction.guild is None:
            msg = "Guild is None"
            await interaction.response.send_message(msg)
            raise ValueError(msg)
        if interaction.guild.system_channel is None:
            msg = "Guild has no system channel"
            await interaction.response.send_message(msg)
            raise ValueError(msg)

        if channel_id is None:
            channel_id = interaction.guild.system_channel.id

        data = self.session.exec(select(WelcomeDb).where(WelcomeDb.guild_id == interaction.guild.id)).first()
        if enabled is None:
            enabled = data.enabled if data else False
        if message is None:
            message = data.message if data else f"Welcome to {interaction.guild.name}"
        if data is None:
            self.session.add(
                WelcomeDb(
                    guild_id=interaction.guild.id,
                    channel_id=channel_id,
                    message=message,
                    enabled=enabled,
                ),
            )
        else:
            data.channel_id = channel_id
            data.message = message
            data.enabled = enabled
        self.session.commit()
