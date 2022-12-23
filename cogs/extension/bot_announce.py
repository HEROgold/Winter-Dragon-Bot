import discord
from discord.ext import commands
from discord import app_commands
from config import main as config

class Bot_announce(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot

    @app_commands.command(name="bot_announce", description="Announce important messages on all servers the bot runs on")
    async def slash_global_announce(self, interaction: discord.Interaction, msg:str):
        if interaction.user.id != config.owner_id and not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("Not enough permissions to run this command", ephemeral=True)
            return
        for guild in self.bot.guilds:
            await self.bot.get_channel(guild.public_updates_channel.id).send(msg)
            await interaction.response.send_message("Message send to all update channels on all servers!", ephemeral=True, delete_after=10)

async def setup(bot:commands.Bot):
	await bot.add_cog(Bot_announce(bot))