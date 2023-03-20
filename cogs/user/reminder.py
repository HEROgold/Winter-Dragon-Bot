import datetime
import logging
import os
import pickle

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
from tools import dragon_database


class Reminder(commands.Cog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        self.data = None
        self.DATABASE_NAME = self.__class__.__name__
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.DATABASE_NAME}.pkl"
            self.setup_db_file()

    def setup_db_file(self) -> None:
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "wb") as f:
                data = self.data
                pickle.dump(data, f)
                f.close
                self.logger.info(f"{self.DATABASE_NAME}.pkl Created.")
        else:
            self.logger.info(f"{self.DATABASE_NAME}.pkl File Exists.")

    def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = db.get_data(self.DATABASE_NAME)
        elif os.path.getsize(self.DBLocation) > 0:
            with open(self.DBLocation, "rb") as f:
                data = pickle.load(f)
        return data

    def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "wb") as f:
                pickle.dump(data, f)

    async def cog_load(self) -> None:
        self.data = self.get_data()

    async def cog_unload(self) -> None:
        self.set_data(self.data)

    @tasks.loop(hours=1)
    async def update_database(self) -> None:
        self.set_data(self.data)

    @tasks.loop(seconds=60)
    async def send_reminder(self) -> None:
        if not self.data:
            self.data = self.get_data()
        if not self.data:
            self.logger.warning("Could not get data.")
            return
        for member_id, remind_list in list(self.data.items()):
            for i, remind_data in enumerate(remind_list):
                if remind_data["unix_time"] <= datetime.datetime.now(datetime.timezone.utc).timestamp():
                    member:discord.Member = discord.utils.get(self.bot.users, id=int(member_id)) # type: ignore
                    dm = await member.create_dm()
                    reminder = remind_data["reminder"]
                    await dm.send(f"I'm here to remind you about\n{reminder}")
                    del remind_list[i]
                    self.logger.debug(f"Reminded {member}, and removed it.")
            if not remind_list:
                del self.data[member_id]
                self.logger.debug(f"Removing empty reminder(s) for id=`{member_id}`")

    @app_commands.command(
        name="remind",
        description = "Set a reminder for yourself!",
        )
    async def slash_reminder(self, interaction:discord.Interaction, reminder:str, minutes:int=0, hours:int=0, days:int=0) -> None:
        if minutes == 0 and hours == 0 and days == 0:
            await interaction.response.send_message("Give me a time so i can remind you!", ephemeral=True)
            return
        else:
            seconds = self.get_seconds(seconds=0, minutes=minutes, hours=hours, days=days)
        if not self.data:
            self.data = self.get_data()
        member = interaction.user
        time = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds)).timestamp()
        epoch = int(time)
        member_id = str(member.id)
        try:
            reminders = self.data[member_id]
            reminders.append({"reminder": reminder, "unix_time": epoch})
        except KeyError:
            self.data[member_id] = [{"reminder": reminder, "unix_time": epoch}]
        await interaction.response.send_message(f"at <t:{epoch}> I will remind you of \n`{reminder}`", ephemeral=True)

    def get_seconds(self, seconds:int=0, minutes:int=0, hours:int=0, days:int=0) -> int:
        hours += days * 24
        minutes += hours * 60
        seconds += minutes * 60
        return seconds

async def setup(bot:commands.Bot) -> None:
	await bot.add_cog(Reminder(bot))