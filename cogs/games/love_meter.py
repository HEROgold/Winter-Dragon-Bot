import discord
import random
from discord.ext import commands
from discord import app_commands


class Love(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot:commands.Bot = bot

    @app_commands.command(
        name="love",
        description="Find out if another person is compatible with you"
    )
    async def love(self, interaction:discord.Interaction, member:discord.Member) -> None:
        user = interaction.user
        # Check if bot is mentioned and skip it
        emb = discord.Embed(
            title="Love Meter",
            description=" ",
            color=0xFF0000,
        )
        random.seed((user.id + member.id))
        emb.add_field(
            name=f"{member.display_name}",
            value=f"Your compatibility with {member.display_name} is {random.randint(0,100)}%",
            inline=True,
        )
        await interaction.response.send_message(embed=emb)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Love(bot))