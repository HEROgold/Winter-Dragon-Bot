import discord
from discord.ext import commands
from discord import app_commands
import config

class Purge(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot

    @app_commands.command(name="purge", description="Purge X amount of messages")
    async def slash_purge(self, interaction:discord.Interaction, count:int):
        await interaction.response.defer(ephemeral=True)
        if count == -1:
            count = config.purge.limit
        if count <= config.purge.limit:
            # await interaction.channel.purge(limit=count)
            messages = await self.history_delete(interaction=interaction, count=count)
            await interaction.followup.send(f"Killed {len(messages)} Messages.", ephemeral=True)
        else:
            await interaction.followup.send(f"Too many message to kill! The limit is set to {config.purge.limit}", ephemeral=True)

    async def history_delete(self, interaction:discord.Interaction, count:int) -> list[discord.Message]:
        messages = []
        async for amount, message in enumerate(interaction.channel.history(limit=count)):
            message:discord.Message
            await message.delete()
            messages.append(message)
        return messages

async def setup(bot:commands.Bot):
	await bot.add_cog(Purge(bot))