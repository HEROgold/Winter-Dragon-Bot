import random

import discord
from discord import app_commands

from bot import WinterDragon
from bot._types.cogs import Cog


class Love(Cog):
    @app_commands.command(name = "love", description = "Find out if another person is compatible with you")
    async def love(self, interaction: discord.Interaction, member: discord.Member) -> None:
        user = interaction.user
        emb = discord.Embed(
            title = "Love Meter",
            description = " ",
            color = 0xFF0000,
        )
        random.seed(user.id + member.id)
        emb.add_field(
            name = f"{member.display_name}",
            value = f"Your compatibility with {member.display_name} is {random.randint(0,100)}%",
            inline = True,
        )
        await interaction.response.send_message(embed=emb)


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Love(bot))
