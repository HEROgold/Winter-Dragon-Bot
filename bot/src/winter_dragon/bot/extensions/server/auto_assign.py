"""Cog for automatically assigning roles to new members."""
import discord
from discord import app_commands
from sqlmodel import select
from winter_dragon.bot.constants import AUTO_ASSIGN_REASON
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import Cog, GroupCog
from winter_dragon.database.tables import AutoAssignRole
from winter_dragon.database.tables import Roles as DbRole


class AutoAssign(GroupCog):
    """Cog for automatically assigning roles to new members."""

    @app_commands.command(name="show", description="Show the current auto assign role")
    async def slash_assign_show(self, interaction: discord.Interaction) -> None:
        """Show the current auto assign role."""
        if interaction.guild is None:
            self.logger.warning("AutoAssign command was not used in a guild")
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        with self.session as session:
            aar = session.exec(
                select(AutoAssignRole)
                .where(AutoAssignRole.guild_id == interaction.guild.id)).first()
        if aar is None:
            self.logger.warning("AutoAssign command didn't find any assignable roles")
            await interaction.response.send_message("No auto assign role is set.", ephemeral=True)
            return
        role = interaction.guild.get_role(aar.role_id)
        if role is None:
            self.logger.warning("AutoAssign command didn't find the role in the guild")
            await interaction.response.send_message("No auto assign role is set.", ephemeral=True)
            return
        await interaction.response.send_message(role.mention, ephemeral=True)

    @app_commands.command(name="add", description="Automatically give a new user the selected role when they join")
    async def slash_assign_add(self, interaction: discord.Interaction, role: discord.Role) -> None:
        """Add a role to the list of roles to be assigned to new members."""
        self.logger.info(f"Adding AutoAssign role {role} to database")
        with self.session as session:
            if session.exec(select(AutoAssignRole).where(AutoAssignRole.role_id == role.id)).first():
                await interaction.response.send_message(f"Role {role.mention} is already registered.", ephemeral=True)
                return
            if not session.exec(select(DbRole).where(DbRole.id == role.id)).first():
                session.add(DbRole(id=role.id, name=role.name))
            session.add(AutoAssignRole(role_id=role.id, guild_id=role.guild.id))
            session.commit()

        await interaction.response.send_message(f"Adding {role.mention} when a new member joins", ephemeral=True)


    @app_commands.command(name="remove", description="Stop AutoAssigning role(s) to new members")
    async def slash_assign_remove(self, interaction: discord.Interaction, role: discord.Role | None = None) -> None:
        """Remove a role from the list of roles to be assigned to new members."""
        if role:
            await self.remove_specified_role(interaction, role)
            await interaction.response.send_message(f"I will not add {role.mention} to new members", ephemeral=True)
            return

        await self.remove_all_roles(interaction)
        await interaction.response.send_message("I will not be adding any roles to new members", ephemeral=True)


    async def remove_specified_role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        """Remove a specific role from the list of roles to be assigned to new members."""
        self.logger.info(f"Removing AutoAssign role {role} from {interaction.guild=}")
        if interaction.guild is None:
            self.logger.warning("AutoAssign command was not used in a guild")
            return
        with self.session as session:
            if auto_assign := session.exec(select(AutoAssignRole).where(
                AutoAssignRole.guild_id == interaction.guild.id,
                AutoAssignRole.role_id == role.id,
            )).first():
                session.delete(auto_assign)
            session.commit()


    async def remove_all_roles(self, interaction: discord.Interaction) -> None:
        """Remove all roles from the list of roles to be assigned to new members."""
        if interaction.guild is None:
            self.logger.warning("AutoAssign command was not used in a guild")
            return
        self.logger.info(f"Removing all AutoAssign roles from {interaction.guild=}")
        with self.session as session:
            for auto_assign in session.exec(
                select(AutoAssignRole)
                .where(AutoAssignRole.guild_id == interaction.guild.id)).all():
                session.delete(auto_assign)
            session.commit()


    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Automatically assign roles to new members."""
        with self.session as session:
            for auto_assign in session.exec(select(AutoAssignRole).where(AutoAssignRole.guild_id == member.guild.id)).all():
                if role := member.guild.get_role(auto_assign.role_id):
                    await member.add_roles(role, reason=AUTO_ASSIGN_REASON)
                    self.logger.debug(f"Added AutoAssign role {role} to new member {member.mention}")


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(AutoAssign(bot))
