import asyncio
import os
import random
from typing import Any

import discord
from craiyon import Craiyon
from discord import app_commands
from discord.ext import tasks

import tools.rainbow as rainbow
from _types.cogs import GroupCog
from _types.bot import WinterDragon


# FIXME: Find out what doesn't work
class Image(GroupCog):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.CrAIyonDataBase = "./database/crAIyon/"


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
            self.logger.debug("Creating embed")
            embed = discord.Embed(title="AI Generated Image's", color=random.choice(rainbow.RAINBOW))
            embed.set_footer(text="These results come from an API, the results are from www.craiyon.com")
            dc_files = []
            for file in files:
                img_path = os.path.join(root, file)
                self.logger.debug(f"Adding file {file} to send")
                # FIXME: Doesn't go past here.
                dc_files.extend(discord.File(img_path))
                self.logger.debug(f"Removing file {file}")
                os.remove(img_path)
            self.logger.debug(f"sending images to {member.mention}")
            await dm.send(embed=embed, files=dc_files)
            os.rmdir(root)


    def generate_images(self, interaction: discord.Interaction, dm: discord.DMChannel, query:str) -> None:
        user_dir = f"{self.CrAIyonDataBase}/{interaction.user.id}"
        generator = Craiyon() # Instantiates the api wrapper
        result = generator.generate(query) # Generates 9 images by default and cannot change that
        os.makedirs(user_dir, exist_ok=True)
        result.save_images(user_dir)


    @app_commands.checks.cooldown(3, 360)
    @app_commands.command(name = "generate",description = "Request an AI to make an image, and when its done get it send to you")
    async def slash_image_generate(self, interaction:discord.Interaction, *, query:str) -> None:
        dm = await interaction.user.create_dm()
        await interaction.response.send_message("Creating images, please be patient.", ephemeral=True)
        self.logger.debug(f"Requesting images for {interaction.user} with query {query}")
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(loop.run_in_executor(None, self.generate_images, interaction, dm, query))


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Image(bot))
