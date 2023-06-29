import datetime
import logging

import discord  # type: ignore
from discord import app_commands
from discord.ext import commands

import config
from tools.database_tables import Session, engine, Presence


class Uptime(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")


    @app_commands.command(name="bot", description="Show bot's current uptime")
    async def slash_uptime_bot(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"Bot uptime: {datetime.datetime.now(datetime.timezone.utc) - self.bot.launch_time}")


    @app_commands.command(name="user", description="Show a users's current uptime/online time")
    async def slash_uptime_user(self, interaction: discord.Interaction) -> None:
        with Session(engine) as session:
            member = interaction.user
            db_presences = session.query(Presence).where(Presence.user_id == member.id).order_by(Presence.date_time.desc()).all()
            now = datetime.datetime.now(datetime.timezone.utc)
            last_time = datetime.datetime.fromtimestamp(0)
            for presence in db_presences:
                time_difference = (now - last_time)
                self.logger.debug(f"{time_difference=}, {last_time=}")
                last_time = presence.date_time
            session.commit()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Uptime(bot))

