import contextlib

import discord
from discord import DMChannel, GroupChannel, PermissionOverwrite, Permissions, Thread, app_commands
from winter_dragon.bot._types.aliases import MemberRole
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import GroupCog


@app_commands.guild_only()
class ChannelUtils(GroupCog):
    """Utility commands for managing channels."""

    categories = app_commands.Group(name="categories", description="Manage your categories")

    @app_commands.checks.has_permissions(manage_channels=True)
    @categories.command(name="delete", description="Delete a category and ALL channels inside.")
    async def slash_cat_delete(self, interaction: discord.Interaction, category: discord.CategoryChannel) -> None:
        """Delete a discord category with all channels inside."""
        await interaction.response.defer(ephemeral=True)
        cmd_mention = self.get_command_mention(self.slash_cat_delete)

        for channel in category.channels:
            await channel.delete(reason=f"Deleted by {interaction.user.mention} using {cmd_mention}")
        await category.delete(reason=f"Deleted by {interaction.user.mention} using {cmd_mention}")

        with contextlib.suppress(discord.NotFound):
            await interaction.followup.send("Channels removed", ephemeral=True)

    async def _set_channel_lock_state(self, interaction: discord.Interaction, target: MemberRole, *, lock: bool) -> None:
        """Set a lock state on a channel."""
        if not interaction.channel:
            await interaction.response.send_message("This command can only be used in a channel.", ephemeral=True)
            return
        if isinstance(interaction.channel, (Thread, DMChannel, GroupChannel)):
            await interaction.response.send_message("You cannot lock or unlock this channel.", ephemeral=True)
            return

        role_perms = interaction.channel.permissions_for(target)
        role_perms.send_messages = not lock
        await interaction.channel.set_permissions(
            target=target,
            overwrite=PermissionOverwrite().from_pair(role_perms, Permissions()),
            reason=f"Channel {'locked' if lock else 'unlocked'} for {target} by {interaction.user.mention}",
        )
        await interaction.response.send_message(
            f"{'Locked' if lock else 'Unlocked'} this channel for {target.mention}", ephemeral=True,
        )

    @app_commands.command(name="lock", description="Lock a channel")
    @app_commands.describe(target="Optional role or member to lock out of this channel")
    async def slash_lock(self, interaction: discord.Interaction, target: MemberRole) -> None:
        """Lock a channel."""
        await self._set_channel_lock_state(interaction, target, lock=True)

    @app_commands.command(name="unlock", description="Unlock a channel")
    @app_commands.describe(target="Optional role or member to unlock this channel")
    async def slash_unlock(self, interaction: discord.Interaction, target: MemberRole) -> None:
        """Unlock a channel."""
        await self._set_channel_lock_state(interaction, target, lock=False)


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(ChannelUtils(bot))
