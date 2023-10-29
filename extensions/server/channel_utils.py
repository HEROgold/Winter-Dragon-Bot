import discord  # type: ignore
from discord import app_commands

from _types.cogs import GroupCog
from _types.bot import WinterDragon


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
    async def slash_lock(self, interaction: discord.Integration):
        """Lock a channel"""


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(ChannelUtils(bot)) # type: ignore
