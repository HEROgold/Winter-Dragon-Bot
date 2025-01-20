import asyncio

import discord
from discord.ext import commands
from core.bot import WinterDragon


class Updater(commands.Cog):
    def __init__(self, bot: WinterDragon) -> None:
        self.bot = bot

    @commands.is_owner()
    @discord.app_commands.command(name="update", description="Update the bot from the configured .git URL")
    async def update(self, interaction: discord.Interaction) -> None:
        """Update the bot from the configured .git URL."""
        await interaction.response.send_message("Updating the bot...", ephemeral=True)

        # Pull the latest changes from the git repository
        process = await asyncio.create_subprocess_exec(
            "git", "pull",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode == 0:
            await interaction.followup.send("Bot updated successfully.")
        else:
            await interaction.followup.send(f"Failed to update the bot:\n{stderr.decode()}")


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Updater(bot))
