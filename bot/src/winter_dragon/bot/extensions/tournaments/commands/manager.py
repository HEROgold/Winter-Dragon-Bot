"""Module for tournament management commands accessible by admins and tournament managers."""

from discord import Interaction, app_commands
from winter_dragon.bot.core.cogs import GroupCog


TOURNAMENT_MANAGER = "Tournament Manager"


@app_commands.guild_only()
class TournamentManager(GroupCog):
    """Commands for managing tournaments, accessible only to admins."""

    @app_commands.checks.has_permissions(Administrator=True)
    @app_commands.command(name="setup", description="Setup the tournament system (admin only)")
    async def slash_setup(self, interaction: Interaction) -> None:
        """Add the tournament system to the server."""
        # If already set up, mention that.
        # If not, set up the tournament system. and track it in the database.
        # Sync the TournamentCommands cog to the server. (so users can use the commands)

    @app_commands.checks.has_permissions(Administrator=True)
    @app_commands.command(name="remove", description="Remove the tournament system (admin only)")
    async def slash_remove(self, interaction: Interaction) -> None:
        """Remove the tournament system."""
        # If not, mention that it is not set up. mention how to set it up.
        # If the tournament system is set up, remove it from the database.
        # Sync the TournamentCommands cog to the server. (so users can no longer use the commands)

    @app_commands.checks.has_role(TOURNAMENT_MANAGER)
    @app_commands.command(name="create", description="Manage tournaments")
    async def slash_create(self, interaction: Interaction) -> None:
        """Create a new tournament or manage an existing one."""

    @app_commands.checks.has_role(TOURNAMENT_MANAGER)
    @app_commands.command(name="cancel", description="Cancel a tournament")
    async def slash_cancel(self, interaction: Interaction) -> None:
        """Cancel a tournament that is currently running or scheduled."""
