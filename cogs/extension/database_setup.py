import logging

import discord  # type: ignore
from discord import app_commands
from discord.ext import commands, tasks

import config
from tools.database_tables import Guild, User, Session, engine


@app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
class DatabaseSetup(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")


    async def cog_load(self) -> None:
        self.update.start()


    @tasks.loop(hours=1)
    async def update(self) -> None:
        with Session(engine) as session:
            for user in self.bot.users:
                if session.query(User).where(User.id == user.id).first() is None:
                    self.logger.debug(f"Adding new {user=} to Users table")
                    session.add(User(id = user.id))
            for guild in self.bot.guilds:
                if session.query(Guild).where(Guild.id == guild.id).first() is None:
                    self.logger.debug(f"Adding new {guild=} to Guild table")
                    session.add(Guild(id = guild.id))

            session.commit()

    @update.before_loop # type: ignore
    async def before_update(self) -> None:
        self.logger.info("Waiting until bot is online")
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DatabaseSetup(bot))  # type: ignore
