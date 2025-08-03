"""Module for tournament commands accessible by users."""

from discord import Interaction, app_commands
from winter_dragon.bot.core.cogs import GroupCog


class TournamentCommands(GroupCog):
    """Commands for users to interact with tournaments."""

    @app_commands.command(name="join", description="Join a tournament")
    async def slash_join(self, interaction: Interaction) -> None:
        """Join a tournament."""

    @app_commands.command(name="leave", description="Leave a tournament")
    async def slash_leave(self, interaction: Interaction) -> None:
        """Leave a tournament."""

    @app_commands.command(name="list", description="List all tournaments")
    async def slash_list(self, interaction: Interaction) -> None:
        """List all tournaments."""

    @app_commands.command(name="info", description="Get information about a tournament")
    async def slash_info(self, interaction: Interaction) -> None:
        """Get information about a tournament."""

    @app_commands.command(name="spectate", description="Spectate a tournament")
    async def slash_spectate(self, interaction: Interaction) -> None:
        """Spectate a tournament."""
