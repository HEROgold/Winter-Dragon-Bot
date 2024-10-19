import discord
from discord import Role, app_commands

from bot import WinterDragon
from bot._types.cogs import Cog, GroupCog
from bot.constants import AUTO_ASSIGN_REASON
from database.tables import AutoAssignRole
from database.tables import Role as DbRole


class AutoAssign(GroupCog):
    @app_commands.command(name="show", description="Show the current auto assign role")
    async def slash_assign_show(self, interaction: discord.Interaction) -> None:
        with self.session as session:
            aar = session.query(AutoAssignRole).where(AutoAssignRole.guild_id == interaction.guild.id).first()
        role: Role = interaction.guild.get_role(aar.role_id) # type: ignore
        await interaction.response.send_message(role.mention, ephemeral=True)

    @app_commands.command(name="add", description="Automatically give a new user the selected role when they join")
    async def slash_assign_add(self, interaction: discord.Interaction, role: discord.Role) -> None:
        self.logger.info(f"Adding AutoAssign role {role} to database")
        with self.session as session:
            if session.query(AutoAssignRole).where(AutoAssignRole.role_id == role.id).first():
                await interaction.response.send_message(f"Role {role.mention} is already registered.", ephemeral=True)
                return
            if not session.query(DbRole).where(DbRole.id == role.id).first():
                session.add(DbRole(id=role.id, name=role.name))
            session.add(AutoAssignRole(role.id, guild_id=role.guild.id))
            session.commit()

        await interaction.response.send_message(f"Adding {role.mention} when a new member joins", ephemeral=True)


    @app_commands.command(name="remove", description="Stop AutoAssigning role(s) to new members")
    async def slash_assign_remove(self, interaction: discord.Interaction, role: discord.Role | None = None) -> None:
        if role:
            await self.remove_specified_role(interaction, role)
            await interaction.response.send_message(f"I will not add {role.mention} to new members", ephemeral=True)
            return

        await self.remove_all_roles(interaction)
        await interaction.response.send_message("I will not be adding any roles to new members", ephemeral=True)


    async def remove_specified_role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        self.logger.info(f"Removing AutoAssign role {role} from {interaction.guild=}")
        with self.session as session:
            if auto_assign := session.query(AutoAssignRole).where(
                AutoAssignRole.guild_id == interaction.guild.id,
                AutoAssignRole.role_id == role.id,
            ).first():
                session.delete(auto_assign)
            session.commit()


    async def remove_all_roles(self, interaction: discord.Interaction) -> None:
        self.logger.info(f"Removing all AutoAssign roles from {interaction.guild=}")
        with self.session as session:
            for auto_assign in session.query(AutoAssignRole).where(AutoAssignRole.guild_id == interaction.guild.id).all():
                session.delete(auto_assign)
            session.commit()


    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        with self.session as session:
            for auto_assign in session.query(AutoAssignRole).where(AutoAssignRole.guild_id == member.guild.id).all():
                role = member.guild.get_role(auto_assign.role_id) # type: ignore
                await member.add_roles(role, reason=AUTO_ASSIGN_REASON)
        self.logger.debug(f"Added AutoAssign role {role} to new member {member.mention}")


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(AutoAssign(bot))
