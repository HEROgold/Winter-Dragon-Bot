import discord
from discord import app_commands
from discord.ext import commands


class Invite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="invite",
        description="Invite this bot to your own server!",
        )
    @commands.has_permissions()
    async def invite(self, interaction:discord.Interaction):
        await interaction.response.send_message("https://discord.com/api/oauth2/authorize?client_id=742777596734996582&permissions=4398046511095&scope=bot", ephemeral=True)

async def setup(bot:commands.Bot):
	await bot.add_cog(Invite(bot))
