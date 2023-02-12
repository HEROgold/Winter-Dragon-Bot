import asyncio
import datetime
import json
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

import config
import dragon_database


class Reminder(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot:commands.Bot = bot
        self.data = None
        self.database_name = "Reminder"
        self.logger = logging.getLogger("winter_dragon.reminder")
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.database_name}.json"
            self.setup_json()

    def setup_json(self):
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                self.logger.info(f"{self.database_name} Json Created.")
        else:
            self.logger.info(f"{self.database_name} Json Loaded.")

    async def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data:dict = await db.get_data(self.database_name)
        else:
            with open(self.DBLocation, 'r') as f:
                data = json.load(f)
        return data

    async def set_data(self, data):
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.database_name, data=data)
        else:
            with open(self.DBLocation,'w') as f:
                json.dump(data, f)

    async def cog_load(self):
        self.data = await self.get_data()
        await self.send_reminder()
        # seconds > minutes > hours
        await asyncio.sleep(60)
        await self.cog_load()

    async def cog_unload(self):
        await self.set_data(self.data)

    async def send_reminder(self):
        if not self.data:
            self.data = await self.get_data()
        if not self.data:
            return
        for member_id, remind_list in list(self.data.items()):
            for i, remind_data in enumerate(remind_list):
                if remind_data["unix_time"] <= datetime.datetime.now(datetime.timezone.utc).timestamp():
                    member:discord.Member = discord.utils.get(self.bot.users, id=int(member_id))
                    dm = await member.create_dm()
                    reminder = remind_data["reminder"]
                    await dm.send(f"I'm here to remind you about\n{reminder}")
                    del remind_list[i]
                    self.logger.debug(f"Reminded {member}, and removed it.")
            if not remind_list:
                del self.data[member_id]
                self.logger.debug(f"Removing empty reminder for id {member_id}")
        await self.set_data(self.data)

    @app_commands.command(
        name="remind",
        description = "Set a reminder for yourself!",
        )
    async def slash_reminder(self, interaction:discord.Interaction, reminder:str, minutes:int=0, hours:int=0, days:int=0):
        if minutes == 0 and hours == 0 and days == 0:
            await interaction.response.send_message("Give me a time so i can remind you!", ephemeral=True)
            return
        else:
            seconds = self.get_seconds(seconds=0, minutes=minutes, hours=hours, days=days)
        if not self.data:
            self.data = await self.get_data()
        member = interaction.user
        time = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds)).timestamp()
        epoch = int(time)
        member_id = str(member.id)
        try:
            reminders = self.data[member_id]
            reminders.append({"reminder": reminder, "unix_time": epoch})
        except KeyError:
            self.data[member_id] = [{"reminder": reminder, "unix_time": epoch}]
        await self.set_data(self.data)
        await interaction.response.send_message(f"at <t:{epoch}> I will remind you of \n`{reminder}`", ephemeral=True)

    def get_seconds(self, seconds, minutes, hours, days) -> int:
        hours += days * 24
        minutes += hours * 60
        seconds += minutes * 60
        return seconds

async def setup(bot:commands.Bot):
	await bot.add_cog(Reminder(bot))