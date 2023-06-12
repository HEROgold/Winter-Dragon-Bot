import logging

import discord
from discord import app_commands
from discord.ext import commands

import config


@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_messages=True)
class Purge(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")

    @app_commands.command(name="purge", description="Purge X amount of messages, use history to delete older messages.")
    @app_commands.checks.has_permissions(manage_messages=True, manage_channels=True)
    async def slash_purge(self, interaction:discord.Interaction, count:int, use_history:bool=False) -> None:
        if count == -1:
            count = config.Purge.LIMIT
        if count <= config.Purge.LIMIT:
            await interaction.response.defer()
            history_messages_count = 0
            purged_count = 0
            purged = await interaction.channel.purge(limit=count)
            purged_count = len(purged)
            self.logger.debug(f"Purged: {purged_count}")
            if (
                purged_count < count
                and config.Purge.USE_HISTORY == True
                and use_history
            ):
                history_messages = await self.history_delete(interaction=interaction, count=(count - purged_count))
                history_messages_count = len(history_messages)
                self.logger.debug(f"History killed: {history_messages_count}")
            await interaction.followup.send(f"{interaction.user.mention} Killed {history_messages_count + purged_count} Messages")
        else:
            await interaction.response.send_message(f"Too many message to kill! The limit is {config.Purge.LIMIT}", ephemeral=True)


    async def history_delete(self, interaction:discord.Interaction, count:int) -> list[discord.Message]:
        messages = []
        async for message in interaction.channel.history(limit=count):
            message:discord.Message
            await message.delete()
            messages.append(message)
        return messages

async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(Purge(bot))
