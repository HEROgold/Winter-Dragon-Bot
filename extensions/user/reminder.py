import datetime
import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from tools.config_reader import config
from tools.database_tables import Reminder as ReminderDb
from tools.database_tables import engine, Session


class Reminder(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")

    def get_seconds(self, seconds:int=0, minutes:int=0, hours:int=0, days:int=0) -> int:
        hours += days * 24
        minutes += hours * 60
        seconds += minutes * 60
        return seconds

    async def cog_load(self) -> None:
        self.send_reminder.start()


    @tasks.loop(seconds=60)
    async def send_reminder(self) -> None:
        # self.logger.debug("checking reminders")
        is_past_timestamp = datetime.datetime.now() >= ReminderDb.timestamp
        with Session(engine) as session:
            results = session.query(ReminderDb).where(is_past_timestamp)
            if not results.all():
                return
            for i in results.all():
                self.logger.debug(f"sending reminder {i.content=} to {i.user_id=}")
                member = discord.utils.get(self.bot.users, id=i.user_id)
                dm = await member.create_dm()
                await dm.send(f"I'm here to remind you about\n`{i.content}`")
                session.delete(i)
            session.commit()


    @send_reminder.before_loop # type: ignore
    async def before_send_reminder(self) -> None:
        self.logger.info("Waiting until bot is online")
        await self.bot.wait_until_ready()


    @app_commands.command(
        name="remind",
        description = "Set a reminder for yourself!",
        )
    async def slash_reminder(
        self,
        interaction: discord.Interaction,
        reminder: str,
        minutes: int = 0,
        hours: int = 0,
        days: int = 0
    ) -> None:
        if minutes == 0 and hours == 0 and days == 0:
            await interaction.response.send_message("Give me a time so i can remind you!", ephemeral=True)
            return
        else:
            seconds = self.get_seconds(seconds=0, minutes=minutes, hours=hours, days=days)
        member = interaction.user
        time = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds))
        with Session(engine) as session:
            session.add(ReminderDb(
                # id = None,
                content = reminder,
                user_id = member.id,
                timestamp = time,
            ))
            session.commit()
        epoch = int(time.timestamp())
        await interaction.response.send_message(f"at <t:{epoch}> I will remind you of \n`{reminder}`", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(Reminder(bot))