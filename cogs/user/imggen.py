import asyncio
import logging
import os
import random

import discord
from craiyon import Craiyon
from discord import app_commands
from discord.ext import commands, tasks

import config
import rainbow


class Image(commands.GroupCog):
    def __init__(self, bot:commands.Bot) -> None:
        self.CrAIyonDataBase = "./Database/crAIyon/"
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")

    async def cog_load(self) -> None:
        self.image_watcher.start()

    def cog_unload(self) -> None: # type: ignore
        self.image_watcher.cancel()

    @tasks.loop(seconds=10)
    async def image_watcher(self) -> None:
        for root, subdirs, files in os.walk(self.CrAIyonDataBase):
            if not files:
                continue
            self.logger.debug(f"Scanning files: {root}, {subdirs}, {files}")
            try:
                member = self.bot.get_user(int(root[19:])) or await self.bot.fetch_user(int(root[19:]))
            except ValueError:
                continue
            dm = await member.create_dm()
            self.logger.debug(f"sending images to {member.mention}")
            embed = discord.Embed(title="AI Generated Image's", color=random.choice(rainbow.RAINBOW))
            embed.set_footer(text="These results come from an API, the results are from www.craiyon.com")
            dc_files = []
            dc_files.extend(discord.File(os.path.join(root, file)) for file in files)
            await dm.send(embed=embed, files=dc_files)
            for file in files:
                os.remove(os.path.join(root, file))
            os.rmdir(root)

    def generate_images(self, interaction:discord.Interaction, dm:discord.DMChannel, query:str) -> None:
        user_dir = f"{self.CrAIyonDataBase}/{interaction.user.id}"
        generator = Craiyon() # Instantiates the api wrapper
        result = generator.generate(query) # Generates 9 images by default and cannot change that
        os.makedirs(user_dir, exist_ok=True)
        result.save_images(user_dir)

    @app_commands.command(name = "generate",
                    description = "Request an AI to make an image, and when its done get it send to you")
    @app_commands.checks.cooldown(3, 360)
    async def slash_imggen(self, interaction:discord.Interaction, *, query:str) -> None:
        dm = await interaction.user.create_dm()
        await interaction.response.send_message("Creating images, please be patient.", ephemeral=True)
        self.logger.debug(f"Requesting images for {interaction.user} with query {query}")
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(loop.run_in_executor(None, self.generate_images, interaction, dm, query))

async def setup(bot:commands.Bot) -> None:
    await bot.add_cog(Image(bot))
