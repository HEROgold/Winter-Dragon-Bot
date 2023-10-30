import discord  # type: ignore
from discord import app_commands

from _types.cogs import GroupCog
from _types.bot import WinterDragon


MemberRole = discord.Role | discord.Member


@app_commands.guild_only()
class ChannelUtils(GroupCog):
    categories = app_commands.Group(name="categories", description="Manage your categories")

    @app_commands.checks.has_permissions(manage_channels=True)
    @categories.command(name="delete", description="Delete a category and ALL channels inside.")
    async def slash_cat_delete(self, interaction: discord.Interaction, category: discord.CategoryChannel) -> None:
        await interaction.response.defer(ephemeral=True)
        # _, cmd_mention = await self.act.get_app_sub_command(self.slash_cat_delete)
        for channel in category.channels:
            await channel.delete(reason=f"Deleted by {interaction.user.mention} using /channel-utils categories delete") # {cmd_mention}
        await category.delete(reason=f"Deleted by {interaction.user.mention} using /channel-utils categories delete") # {cmd_mention}
        try:
            await interaction.followup.send("Channel's removed", ephemeral=True)
        except discord.NotFound:
            pass

    @app_commands.command(name="lock", description="Lock a channel")
    @app_commands.describe(target="Optional role or member to lock out of this channel")
    async def slash_lock(self, interaction: discord.Interaction, target: MemberRole=None):
        """Lock a channel"""
        role_perms = interaction.channel.permissions_for(target)
        role_perms.send_messages = False
        await interaction.channel.set_permissions(
            target=target,
            permissions=role_perms,
            reason=f"Channel locked for {target} by {interaction.user.mention}"
        )
        await interaction.response.send_message(f"Locked this channel for {target.mention}", ephemeral=True)


    @app_commands.command(name="unlock", description="Lock a channel")
    @app_commands.describe(target="Optional role or member to unlock this channel")
    async def slash_unlock(self, interaction: discord.Interaction, target: MemberRole=None):
        """unLock a channel"""
        role_perms = interaction.channel.permissions_for(target)
        role_perms.send_messages = True
        await interaction.channel.set_permissions(
            target=target,
            permissions=role_perms,
            reason=f"Channel locked for {target} by {interaction.user.mention}"
        )
        await interaction.response.send_message(f"UnLocked this channel for {target.mention}", ephemeral=True)


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(ChannelUtils(bot)) # type: ignore
