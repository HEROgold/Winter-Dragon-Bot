import discord
import logging
import os
import json
import datetime
from discord.ext import commands
from discord import app_commands
import asyncio

class Reminder(commands.Cog):
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot:commands.Bot = bot
        self.DBLocation = "./Database/Reminder.json"
        self.setup_db()

    def setup_db(self):
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                logging.info("Reminder Json Created.")
        else:
            logging.info("Reminder Json Loaded.")

    async def get_data(self) -> dict[str, list[dict[str, str|int]]]:
        with open(self.DBLocation, 'r') as f:
            data = json.load(f)
        return data

    async def set_data(self, data) -> None:
        with open(self.DBLocation,'w') as f:
            json.dump(data, f)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.send_reminder()
        await asyncio.sleep(60)
        await self.on_ready()

    async def send_reminder(self):
        data = await self.get_data()
        for member_id, remind_list in list(data.items()):
            for i, remind_data in enumerate(remind_list):
                if remind_data["unix_time"] <= datetime.datetime.now(datetime.timezone.utc).timestamp():
                    member:discord.Member = discord.utils.get(self.bot.users, id=int(member_id))
                    dm = await member.create_dm()
                    reminder = remind_data["reminder"]
                    await dm.send(f"I'm here to remind you about\n{reminder}")
                    del remind_list[i]
                    logging.info(f"Reminded {member}, and removed it.")
            if not remind_list:
                del data[member_id]
                logging.info(f"Removing empty reminder for id {member_id}")
        await self.set_data(data)

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
        member = interaction.user
        data = await self.get_data()
        time = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds)).timestamp()
        epoch = int(time)
        member_id = str(member.id)
        try:
            reminders = data[member_id]
            reminders.append({"reminder": reminder, "unix_time": epoch})
        except KeyError:
            reminders = data[member_id] = [{"reminder": reminder, "unix_time": epoch}]
        await self.set_data(data)
        await interaction.response.send_message(f"at <t:{epoch}> I will remind you of \n`{reminder}`", ephemeral=True)

    def get_seconds(self, seconds, minutes, hours, days) -> int:
        hours += days * 24
        minutes += hours * 60
        seconds += minutes * 60
        return seconds

async def setup(bot:commands.Bot):
	await bot.add_cog(Reminder(bot))