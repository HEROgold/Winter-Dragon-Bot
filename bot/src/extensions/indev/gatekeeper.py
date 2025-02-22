"""
"""

import discord
from discord import ButtonStyle, Guild, Interaction, Member, Permissions, Role, app_commands
from discord.ui import Button, View

from core.bot import WinterDragon
from core.cogs import Cog, GroupCog


@app_commands.guild_only()
class Gatekeeper(GroupCog):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    @app_commands.command(name="enable", description="Enables the gatekeeper system.")
    async def slash_enable_gatekeeper(self, interaction: Interaction) -> None:
        with self.session:
            # Use database to store if enabled or not
            pass
        # if first time using, ask to use command
        await interaction.response.send_message(f"Please use {self.get_command_mention(self.slash_setup)} first.", ephemeral=True)


    @app_commands.command(name="disable", description="Disables the gatekeeper system.")
    async def slash_disable_gatekeeper(self, interaction: Interaction) -> None:
        pass

    @app_commands.command(name="setup", description="Sets up the roles for the gatekeeper system.")
    async def slash_setup(self, interaction: Interaction, member_role: Role | None = None) -> None:
        guild = interaction.guild
        if not guild:
            self.logger.warning("Guild not found for setup")
            return
        await self.setup_roles(guild, member_role)
        await interaction.response.send_message(f"Roles have been setup. You can now use {self.get_command_mention(self.slash_enable_gatekeeper)}", ephemeral=True)


    async def setup_roles(self, guild: Guild, member_role: Role | None = None) -> None:
        """Copies the default role permissions to the member role and removes all permissions from the default role.

        Parameters
        ----------
        :param:`guild`: :class:`Guild`
            The guild to setup the roles in.
        :param:`member_role`: :class:`Role | None`, optional
            A existing role, if any. by default None, and a new role will be created.

        """
        base_role = guild.default_role
        role = member_role or await guild.create_role(name="Member", permissions=base_role.permissions)
        await role.edit(permissions=base_role.permissions)
        await base_role.edit(permissions=Permissions.none())


    @Cog.listener()
    async def on_member_join(self, member: Member) -> None:
        if self.check_user_accepted_rules(member):
            await self.send_verification_message(member)

    async def send_verification_message(self, member: Member) -> None:
        verify_button = Button(label="Accept Rules", style=ButtonStyle.green)

        async def button_callback(interaction: Interaction) -> None:
            member_role = discord.utils.get(member.guild.roles, name="Member")
            if member_role:
                await member.add_roles(member_role)
                await interaction.response.send_message("Welcome! You now have access to the guild.", ephemeral=True)

        verify_button.callback = button_callback

        view = View()
        view.add_item(verify_button)
        await member.send("Please accept the rules to gain access to the guild.", view=view)

    def check_user_accepted_rules(self, _member: discord.Member) -> bool:
        # Implement your logic to check if the user has accepted the rules
        # This is just a placeholder function
        return True


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Gatekeeper(bot))
