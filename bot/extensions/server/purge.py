import discord
from discord import app_commands

from bot import WinterDragon
from bot._types.cogs import Cog
from bot.config import config


@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_messages=True)
class Purge(Cog):
    @app_commands.command(name="purge", description="Purge X amount of messages, use history to delete older messages.")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.bot_has_permissions(manage_messages=True)
    async def slash_purge(self, interaction: discord.Interaction, count: int, use_history: bool = False) -> None:
        if count == -1:
            count = config.getint("Purge", "limit")
        if count <= config.getint("Purge", "limit"):
            await interaction.response.defer()
            history_messages_count = 0
            purged_count = 0
            purged = await interaction.channel.purge(limit=count)
            purged_count = len(purged)
            self.logger.debug(f"Purged: {purged_count}")
            if (
                purged_count < count
                and config.getboolean("Purge", "use_history")
                and use_history
            ):
                history_messages = await self.history_delete(interaction=interaction, count=(count - purged_count))
                history_messages_count = len(history_messages)
                self.logger.debug(f"History killed: {history_messages_count}")
            await interaction.followup.send(f"{interaction.user.mention} Killed {history_messages_count + purged_count} Messages")
        else:
            await interaction.response.send_message(f"Too many message to kill! The limit is {config['Purge']['LIMIT']}", ephemeral=True)


    async def history_delete(self, interaction: discord.Interaction, count: int) -> list[discord.Message]:
        messages = []
        async for message in interaction.channel.history(limit=count):
            message: discord.Message
            try:
                await message.delete()
            except discord.NotFound:
                pass
            messages.append(message)
        return messages


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Purge(bot))
