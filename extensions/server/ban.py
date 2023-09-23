import datetime

import discord
from discord import app_commands
from discord.ext import tasks

from tools.config_reader import config# from tools.database_tables Session, engine
from _types.cogs import Cog
from _types.bot import WinterDragon
from tools.database_tables import Session, engine, SyncBan, SyncBanGuild


class TempBan(Cog):
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
            self.data = self.get_data()
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
            seconds = config["Ban"]["DEFAULT_BANTIME"]
        if not self.data:
            self.data = self.get_data()
        member_id = str(member.id)
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
        self.data[member.id] = {"Name" : member.name, "Roles": roles, "Epoch_unban" : epoch, "Reason" : reason_msg, "guild_id" : interaction.guild.id}
        await self.set_data(data=self.data)

        banned_role = discord.utils.get(interaction.guild.roles, name="Banned")
        if banned_role is None:
            banned_role = await self.create_banned_role(interaction.guild)

        await interaction.followup.send(f"Banning {member.mention}", ephemeral=True)
        await member.remove_roles(reason=reason_msg)
        await member.add_roles(banned_role)


    @slash_ban.autocomplete("days")
    @slash_ban.autocomplete("hours")
    @slash_ban.autocomplete("minutes")
    @slash_ban.autocomplete("seconds")
    async def ban_autocompletion_time(self, interaction:discord.Interaction, current:str) -> list[app_commands.Choice[str]]:
        times = ["5", "10", "30", "60"]
        return [
            app_commands.Choice(name=time, value=time)
            for time in times
            if current.lower() in time.lower()
        ] or [
            app_commands.Choice(name=time, value=time)
            for time in times
        ]


    @Cog.listener()
    async def on_ban(self, member: discord.Member):
        await self.synced_ban_sync(member)

    sync = app_commands.Group(name="sync", description="Synchronize bans across other servers")

    @sync.command(name="join", description="Start syncing ban's with this server")
    async def slash_synced_ban_join(self, interaction: discord.Interaction):
        guild = interaction.guild

        with Session(engine) as session:
            session.add(SyncBanGuild(
                guild_id = guild.id
            ))
            session.commit()

        await interaction.response.send_message("This guild will have ban's synced across this bot.", ephemeral=True)


    @sync.command(name="leave", description="Stop syncing ban's with this server")
    async def slash_synced_ban_leave(self, interaction: discord.Interaction):
        guild = interaction.guild

        with Session(engine) as session:
            session.delete(session.query(SyncBanGuild).where(SyncBanGuild.guild_id == guild.id).first())
            session.commit()

        await interaction.response.send_message("This guild will no longer have ban's synced across this bot.", ephemeral=True)


    async def synced_ban_sync(self, member: discord.Member):
        with Session(engine) as session:
            session.add(SyncBan(
                user_id = member.id
            ))

            for db_guild in session.query(SyncBanGuild).all():
                guild = self.bot.get_guild(db_guild.guild_id)
                await guild.ban(member, reason="Syncing bans")
            session.commit()


async def setup(bot: WinterDragon) -> None:
    return
    await bot.add_cog(TempBan(bot))
    # Removed since normal ban exist.
    # added since synced ban
