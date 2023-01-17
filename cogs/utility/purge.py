import logging

import discord
from discord import app_commands
from discord.ext import commands

import config


class Purge(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot

    @app_commands.command(name="purge", description="Purge X amount of messages")
    @app_commands.guild_only()
    async def slash_purge(self, interaction:discord.Interaction, count:int):
        await interaction.response.defer(ephemeral=True)
        if count == -1:
            count = config.Purge.LIMIT
        if count <= config.Purge.LIMIT:
            if config.Purge.USE_HISTORY:
                messages = await self.history_delete(interaction=interaction, count=count)
                await interaction.followup.send(f"Killed {len(messages)} Messages.", ephemeral=True)
                return
            else:
                if interaction.channel.type == discord.ChannelType.private:
                    await interaction.followup.send("Cannot use purge in DM Channels!")
                    return
                await interaction.channel.purge(limit=count)
                await interaction.followup.send(f"Killed {count} Messages", ephemeral=True)
        else:
            await interaction.followup.send(f"Too many message to kill! The limit is set to {config.Purge.LIMIT}", ephemeral=True)

    async def history_delete(self, interaction:discord.Interaction, count:int) -> list[discord.Message]:
        messages = []
        async for message in interaction.channel.history(limit=count):
            message:discord.Message
            await message.delete()
            messages.append(message)
        return messages

async def setup(bot:commands.Bot):
	await bot.add_cog(Purge(bot))