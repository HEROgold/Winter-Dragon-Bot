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


class Ban(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot:commands.Bot = bot
        self.database_name = "Ban"
        self.logger = logging.getLogger("winter_dragon.ban")
        if not config.main.use_database:
            self.DBLocation = f"./Database/{self.database_name}.json"
            self.setup_json()

    def setup_json(self):
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                self.logger.debug(f"{self.database_name} Json Created.")
        else:
            self.logger.debug(f"{self.database_name} Json Loaded.")

    async def get_data(self) -> dict[str,int|dict[str, str]]:
        if config.main.use_database:
            db = dragon_database.Database()
            data = await db.get_data(self.database_name)
        else:
            with open(self.DBLocation, 'r') as f:
                data = json.load(f)
        return data

    async def set_data(self, data):
        if config.main.use_database:
            db = dragon_database.Database()
            await db.set_data(self.database_name, data=data)
        else:
            with open(self.DBLocation,'w') as f:
                json.dump(data, f)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.unban_check()

    async def unban_check(self):
        data = await self.get_data()
        self.logger.debug("Checkin unban states")
        to_delete = []
        for member_id, d_data in list(data.items()):
            ban_time = d_data["Epoch_unban"]
            if datetime.datetime.now().timestamp() >= ban_time:
                guild_id = d_data["guild_id"]
                member = discord.utils.get(self.bot.get_all_members(), id=int(member_id))
                guild = discord.utils.get(self.bot.guilds, id=guild_id)
                self.logger.debug(f"Unbanning {d_data['Name']} for guild {guild_id}")
                await self.unban_member(member=member, guild=guild)
                to_delete.append(member_id)
        for id in to_delete:
            del data[str(id)]
        await self.set_data(data=data)
        # seconds > minuts > hours
        await asyncio.sleep(60*60*1)
        if config.database.PERIODIC_CLEANUP:
            await self.unban_check()

    async def unban_member(self, member:discord.Member, guild:discord.Guild):
        data = await self.get_data()
        banned_role = discord.utils.get(guild.roles, name="Banned")
        await member.remove_roles(banned_role, reason=f"Unbanning {member.name}")
        for role_id in data[str(member.id)]["Roles"]:
            role = discord.utils.get(guild.roles, id=role_id)
            try:
                await member.add_roles(role)
            except Exception as e:
                self.logger.exception(f"Trying to add role {role.name} got error: {e}")

    def get_seconds(self, seconds, minutes, hours, days) -> int:
        hours += days*24
        minutes += hours*60
        seconds += minutes*60
        return seconds

    async def create_banned_role(self, guild:discord.Guild) -> discord.Role:
        return await guild.create_role(name="Banned", permissions=discord.Permissions.none())

    @app_commands.command(name="temp_ban", description="Ban members temporarily")
    @app_commands.guild_only()
    async def slash_ban(self, interaction:discord.Interaction, member_id:str, seconds:int=0, minutes:int=0, hours:int=0, days:int=0, reason:str=None):
        await interaction.response.defer(ephemeral=True)
        if (seconds and minutes and hours and days) == 0:
            seconds = config.ban.default_bantime
        data = await self.get_data()
        member = discord.utils.get(interaction.guild.members, id=int(member_id))
        # member_id = str(member.id)
        if member_id in data:
            epoch_unban = int(data[member_id]["Epoch_unban"])
            await interaction.followup.send(f"{member.mention} is already banned. Unbanning in <t:{epoch_unban}:R>", ephemeral=True)
            return
        if reason is None:
            reason_msg = f"{interaction.user.mention} Did not specify a reason."
        else:
            reason_msg = f"{interaction.user.mention}: {reason}"
        time = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=self.get_seconds(seconds, minutes, hours, days))).timestamp()
        epoch = int(time)
        roles = [role.id for role in member.roles]
        data[member.id]= {"Name" : member.name, "Roles": roles, "Epoch_unban" : epoch, "Reason" : reason_msg, "guild_id" : interaction.guild.id}
        await self.set_data(data=data)

        banned_role = discord.utils.get(interaction.guild.roles, name="Banned")
        if banned_role is None:
            banned_role = await self.create_banned_role(interaction.guild)

        await interaction.followup.send(f"Banning {member.mention}", ephemeral=True)
        await member.remove_roles(reason=reason_msg)
        await member.add_roles(banned_role)

    @slash_ban.autocomplete("seconds")
    async def ban_autocompletion_time(self, interaction:discord.Interaction, current:str) -> list[app_commands.Choice[str]]:
        times = ["5", "10", "30", "60"]
        return [
            app_commands.Choice(name=time, value=time)
            for time in times if current.lower() in time.lower()
        ]

    @slash_ban.autocomplete("minutes")
    async def ban_autocompletion_time(self, interaction:discord.Interaction, current:str) -> list[app_commands.Choice[str]]:
        times = ["5", "10", "30", "60"]
        return [
            app_commands.Choice(name=time, value=time)
            for time in times if current.lower() in time.lower()
        ]

    @slash_ban.autocomplete("hours")
    async def ban_autocompletion_time(self, interaction:discord.Interaction, current:str) -> list[app_commands.Choice[str]]:
        times = ["5", "10", "30", "60"]
        return [
            app_commands.Choice(name=time, value=time)
            for time in times if current.lower() in time.lower()
        ]

    @slash_ban.autocomplete("days")
    async def ban_autocompletion_time(self, interaction:discord.Interaction, current:str) -> list[app_commands.Choice[str]]:
        times = ["5", "10", "30", "60"]
        return [
            app_commands.Choice(name=time, value=time)
            for time in times if current.lower() in time.lower()
        ]

async def setup(bot:commands.Bot):
    await bot.add_cog(Ban(bot))
