"""Module for handling permission related things in Discord bot interactions."""

from collections.abc import Mapping

from discord import Interaction, Member, Object, PermissionOverwrite, Permissions, Role


type PermissionsOverwrites = Mapping[Role | Member | Object, PermissionOverwrite]


class PermissionsNotifier:
    """Notify users about missing permissions, roles or overwrites."""

    def __init__(self, interaction: Interaction, required_permissions: Permissions) -> None:
        """Initialize PermissionsNotifier with the interaction."""
        self.interaction = interaction
        self.required_permissions = required_permissions

    async def notify(self) -> None:
        """Notify the user about missing permissions, roles or overwrites."""
        if not isinstance(self.interaction.user, Member):
            return
        bot_permissions = self.interaction.app_permissions
        user_permissions = self.interaction.user.resolved_permissions
        if user_permissions is None:
            return

        user_missing_permissions = user_permissions & self.required_permissions
        bot_missing_permissions = bot_permissions & self.required_permissions

        msg = ""
        if user_missing_permissions:
            user_permission_names = [perm[0] for perm in user_missing_permissions]
            msg += f"You are missing the following permissions to execute this command: {user_permission_names}"
        if bot_missing_permissions:
            bot_permission_names = [perm[0] for perm in bot_missing_permissions]
            msg += f"The bot is missing the following permissions to execute this command: {bot_permission_names}"

        await self.interaction.response.send_message(
            msg,
            ephemeral=True,
        )
