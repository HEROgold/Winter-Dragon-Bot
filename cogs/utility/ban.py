import datetime
import pickle
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
from tools import dragon_database

class Ban(commands.Cog):
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

    async def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = await db.get_data(self.DATABASE_NAME)
        elif os.path.getsize(self.DBLocation) > 0:
            with open(self.DBLocation, "rb") as f:
                data = pickle.load(f)
        return data

    async def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "wb") as f:
                pickle.dump(data, f)

    async def cog_load(self) -> None:
        if not self.data:
            self.data = await self.get_data()
        self.unban_check.start()

    async def cog_unload(self) -> None:
        await self.set_data(self.data)

    @tasks.loop(seconds=3600)
    async def unban_check(self) -> None:
        if not self.data:
            return
        self.logger.debug("Checking unban states")
        to_delete = []
        for member_id, d_data in list(self.data.items()):
            ban_time = d_data["Epoch_unban"]
            if datetime.datetime.now().timestamp() >= ban_time:
                guild_id = d_data["guild_id"]
                member = discord.utils.get(self.bot.get_all_members(), id=int(member_id))
                guild = discord.utils.get(self.bot.guilds, id=guild_id)
                self.logger.info(f"Unbanning {d_data['Name']} for guild {guild_id}")
                await self.unban_member(member=member, guild=guild)
                to_delete.append(member_id)
        for id in to_delete:
            del self.data[str(id)]
        await self.set_data(data=self.data)

    async def unban_member(self, member:discord.Member, guild:discord.Guild) -> None:
        if not self.data:
            self.data = await self.get_data()
        banned_role = discord.utils.get(guild.roles, name="Banned")
        await member.remove_roles(banned_role, reason=f"Unbanning {member.name}")
        for role_id in self.data[str(member.id)]["Roles"]:
            role = discord.utils.get(guild.roles, id=role_id)
            await member.add_roles(role)

    def get_seconds(self, seconds, minutes, hours, days) -> int:
        hours += days*24
        minutes += hours*60
        seconds += minutes*60
        return seconds

    async def create_banned_role(self, guild:discord.Guild) -> discord.Role:
        return await guild.create_role(name="Banned", permissions=discord.Permissions.none())

    @app_commands.command(name="temp_ban", description="Ban members temporarily")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(ban_members=True)
    async def slash_ban(
        self,
        interaction:discord.Interaction,
        member:discord.Member,
        seconds:int=0,
        minutes:int=0,
        hours:int=0,
        days:int=0,
        reason:str=None
    ) -> None:
        if (seconds and minutes and hours and days) == 0:
            seconds = config.Ban.DEFAULT_BANTIME
        if not self.data:
            self.data = await self.get_data()
        # member = discord.utils.get(interaction.guild.members, id=int(member_id))
        member_id = str(member.id)
        # member_id = str(member.id)
        if member_id in self.data:
            epoch_unban = int(self.data[member_id]["Epoch_unban"])
            await interaction.response.send_message(f"{member.mention} is already banned. Unbanning in <t:{epoch_unban}:R>", ephemeral=True)
            return
        if reason is None:
            reason_msg = f"{interaction.user.mention} Did not specify a reason."
        else:
            reason_msg = f"{interaction.user.mention}: {reason}"
        time = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=self.get_seconds(seconds, minutes, hours, days))).timestamp()
        epoch = int(time)
        roles = [role.id for role in member.roles]
        self.data[member.id]= {"Name" : member.name, "Roles": roles, "Epoch_unban" : epoch, "Reason" : reason_msg, "guild_id" : interaction.guild.id}
        await self.set_data(data=self.data)

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

async def setup(bot:commands.Bot) -> None:
    await bot.add_cog(Ban(bot))
