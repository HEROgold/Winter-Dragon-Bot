import logging
import discord
import os
import asyncio
import random
import rainbow
from craiyon import Craiyon
from discord.ext import commands
from discord import app_commands

class ImageGen(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.CrAIyonDataBase = "./Database/crAIyon/"
        self.bot:commands.Bot = bot

    async def generate_images(self, interaction:discord.Interaction, dm:discord.DMChannel, query:str) -> None:
        os.makedirs(f"{self.CrAIyonDataBase}/{interaction.user.id}", exist_ok=True)
        generator = Craiyon() # Instantiates the api wrapper
        result = generator.generate(query) # Generates 9 images by default and you cannot change that
        result.save_images(f"{self.CrAIyonDataBase}{interaction.user.id}")
        for i in range(9):
            embed=discord.Embed(title=f"AI Generated Image #{i}", color=random.choice(rainbow.RAINBOW))
            embed.set_footer(text="These results come from an API, the results are from www.craiyon.com")
            await dm.send(file=discord.File(f"{self.CrAIyonDataBase}{interaction.user.id}/image-{i+1}.png"), embed=embed)
            os.remove(f"{self.CrAIyonDataBase}{interaction.user.id}/image-{i+1}.png")
        os.rmdir(f"{self.CrAIyonDataBase}/{interaction.user.id}")
        logging.info(f"Removing {i} image from {interaction.user.id}")

    @app_commands.command(name = "image_gen",
                    description = "Request an AI to make an image, and when its done get it send to you")
    @app_commands.checks.cooldown(1, 3000)
    async def slash_imggen(self, interaction:discord.Interaction, *, query:str):
        dm = await interaction.user.create_dm()
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("Proccessing images, please be patient.", ephemeral=True)
        logging.info(f"Requesting images for {interaction.user} with query {query}")
        # Run in another thread, to not get blocked on waiting generation
        asyncio.new_event_loop().create_task(await self.generate_images(interaction, dm, query))

async def setup(bot:commands.Bot):
    await bot.add_cog(ImageGen(bot))
