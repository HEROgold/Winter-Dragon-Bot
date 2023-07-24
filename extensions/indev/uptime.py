import datetime
import logging

import discord  # type: ignore
from discord import app_commands
from discord.ext import commands

from tools.config_reader import config
from tools.database_tables import Session, engine, Presence


class Uptime(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")


    @app_commands.command(name="bot", description="Show bot's current uptime")
    async def slash_uptime_bot(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"Bot uptime: {datetime.datetime.now(datetime.timezone.utc) - self.bot.launch_time}")


    @app_commands.command(name="user", description="Show a users's current uptime/online time (In development)")
    async def slash_uptime_user(self, interaction: discord.Interaction) -> None:
        with Session(engine) as session:
            member = interaction.user
            db_presences = session.query(Presence).where(Presence.user_id == member.id).order_by(Presence.date_time.desc()).all()
            now = datetime.datetime.now(datetime.timezone.utc)
            last_time = None
            for presence in db_presences:
                presence_date_time = presence.date_time.astimezone(datetime.timezone.utc)
                if last_time is not None:
                    time_difference = (now - last_time)
                    self.logger.debug(f"{time_difference=}, {last_time=}")
                if presence.status in ["online", "dnd", "do-not-disturb", "idle"]:
                    # TODO: create a pie chart
                    pass
                elif presence.status in ["offline", "invisible"]:
                    pass
                last_time = presence_date_time
            session.commit()
            await interaction.response.send_message(f"{last_time=}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Uptime(bot))