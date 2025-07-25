"""Gatekeeper cog for managing server roles and permissions, liming the amount of bot/spam users that can join."""

import discord
from discord import ButtonStyle, Guild, Interaction, Member, Permissions, Role, app_commands
from discord.ui import Button, View
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import Cog, GroupCog


@app_commands.guild_only()
class Gatekeeper(GroupCog):
    """Gatekeeper cog for limiting the amount of bot/spam users that can join."""

    @app_commands.command(name="enable", description="Enables the gatekeeper system.")
    async def slash_enable_gatekeeper(self, interaction: Interaction) -> None:
        """Enable the gatekeeper system. for the guild."""
        # Use database to store if enabled or not
        # if first time using, ask to use command
        msg = f"Please use {self.get_command_mention(self.slash_setup)} first."
        await interaction.response.send_message(msg, ephemeral=True)


    @app_commands.command(name="disable", description="Disables the gatekeeper system.")
    async def slash_disable_gatekeeper(self, interaction: Interaction) -> None:
        """Disable the gatekeeper system. for the guild."""
        # Use database to store if enabled or not
        # if first time using, ask to use command
        msg = f"Please use {self.get_command_mention(self.slash_setup)} first."
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="setup", description="Sets up the roles for the gatekeeper system.")
    async def slash_setup(self, interaction: Interaction, member_role: Role | None = None) -> None:
        """Set up the roles for the gatekeeper system."""
        guild = interaction.guild
        if not guild:
            self.logger.warning("Guild not found for setup")
            return
        await self.setup_roles(guild, member_role)
        msg = f"Roles have been setup. You can now use {self.get_command_mention(self.slash_enable_gatekeeper)}"
        await interaction.response.send_message(msg, ephemeral=True)


    async def setup_roles(self, guild: Guild, member_role: Role | None = None) -> None:
        """Copy the default role permissions to the member role and removes all permissions from the default role."""
        base_role = guild.default_role
        role = member_role or await guild.create_role(name="Member", permissions=base_role.permissions)
        await role.edit(permissions=base_role.permissions)
        await base_role.edit(permissions=Permissions.none())


    @Cog.listener()
    async def on_member_join(self, member: Member) -> None:
        """When a member joins, check if they have accepted the rules and send them a message if not."""
        # Use database to check if enabled or not
        if not self.check_user_accepted_rules(member):
            await self.send_verification_message(member)

    async def send_verification_message(self, member: Member) -> None:
        """Send a verification message to the member."""
        view = View()
        verify_button = Button[view](label="Accept Rules", style=ButtonStyle.green)
        view.add_item(verify_button)

        async def button_callback(interaction: Interaction) -> None:
            member_role = discord.utils.get(member.guild.roles, name="Member")
            if member_role:
                await member.add_roles(member_role)
                await interaction.response.send_message("Welcome! You now have access to the guild.", ephemeral=True)

        verify_button.callback = button_callback

        await member.send("Please accept the rules to gain access to the guild.", view=view)

    def check_user_accepted_rules(self, _member: discord.Member) -> bool:
        """Check if the user has accepted the rules."""
        msg = "This method should check if the user has accepted the rules."
        raise NotImplementedError(msg)


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    # await bot.add_cog(Gatekeeper(bot=bot))
