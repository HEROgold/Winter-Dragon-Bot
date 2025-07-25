"""Tournament management extension for the Winter Dragon Bot."""
from __future__ import annotations

import asyncio
from typing import Unpack

import discord
from discord import app_commands
from sqlmodel import select
from winter_dragon.bot._types.kwargs import BotKwarg
from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.database.tables import (
    Tournament,
    TournamentPlayer,
    TournamentSpectator,
    TournamentTeam,
    Users,
)
from winter_dragon.database.tables.tournament import TournamentStatus, TournamentType

from .strategies.round_robin import RoundRobinStrategy
from .strategies.single_elimination import SingleEliminationStrategy


class TournamentManager(GroupCog):
    """Tournament management system for Discord servers."""
    
    def __init__(self, **kwargs: Unpack[BotKwarg]) -> None:
        """Initialize the tournament manager."""
        super().__init__(**kwargs)
        self.strategies = {
            TournamentType.SINGLE_ELIMINATION: SingleEliminationStrategy,
            TournamentType.ROUND_ROBIN: RoundRobinStrategy,
            # TODO: Add other strategies
        }
    
    @app_commands.command(name="create", description="Create a new tournament")
    @app_commands.describe(
        name="Tournament name",
        tournament_type="Type of tournament",
        max_players="Maximum number of players (optional)",
        team_size="Number of players per team",
        description="Tournament description"
    )
    async def create_tournament(
        self,
        interaction: discord.Interaction,
        name: str,
        tournament_type: TournamentType,
        team_size: int = 1,
        max_players: int | None = None,
        description: str | None = None
    ) -> None:
        """Create a new tournament."""
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        
        # Validate inputs
        if team_size < 1:
            await interaction.response.send_message("Team size must be at least 1.", ephemeral=True)
            return
        
        if max_players is not None and max_players < 2:
            await interaction.response.send_message("Maximum players must be at least 2.", ephemeral=True)
            return
        
        # Check if tournament name already exists in this guild
        existing = self.session.exec(
            select(Tournament).where(
                Tournament.guild_id == interaction.guild.id,
                Tournament.name == name,
                Tournament.status != TournamentStatus.COMPLETED,
                Tournament.status != TournamentStatus.CANCELLED
            )
        ).first()
        
        if existing:
            await interaction.response.send_message(
                f"A tournament named '{name}' already exists in this server.", 
                ephemeral=True
            )
            return
        
        # Create tournament
        tournament = Tournament(
            name=name,
            description=description,
            tournament_type=tournament_type,
            status=TournamentStatus.PLANNED,
            guild_id=interaction.guild.id,
            creator_id=interaction.user.id,
            max_players=max_players,
            team_size=team_size
        )
        
        self.session.add(tournament)
        self.session.commit()
        
        embed = discord.Embed(
            title="Tournament Created",
            description=f"Tournament '{name}' has been created!",
            color=discord.Color.green()
        )
        embed.add_field(name="Type", value=tournament_type.value.replace("_", " ").title(), inline=True)
        embed.add_field(name="Team Size", value=str(team_size), inline=True)
        if max_players:
            embed.add_field(name="Max Players", value=str(max_players), inline=True)
        if description:
            embed.add_field(name="Description", value=description, inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="register", description="Register for a tournament")
    @app_commands.describe(tournament_name="Name of the tournament to register for")
    async def register_tournament(
        self,
        interaction: discord.Interaction,
        tournament_name: str
    ) -> None:
        """Register for a tournament."""
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        
        # Find tournament
        tournament = self.session.exec(
            select(Tournament).where(
                Tournament.guild_id == interaction.guild.id,
                Tournament.name == tournament_name,
                Tournament.status.in_([TournamentStatus.PLANNED, TournamentStatus.REGISTRATION_OPEN])
            )
        ).first()
        
        if not tournament:
            await interaction.response.send_message(
                f"No active tournament named '{tournament_name}' found.", 
                ephemeral=True
            )
            return
        
        # Check if already registered
        existing_registration = self.session.exec(
            select(TournamentPlayer).where(
                TournamentPlayer.tournament_id == tournament.id,
                TournamentPlayer.user_id == interaction.user.id
            )
        ).first()
        
        if existing_registration:
            await interaction.response.send_message(
                "You are already registered for this tournament.", 
                ephemeral=True
            )
            return
        
        # Check player limit
        if tournament.max_players:
            current_players = len(self.session.exec(
                select(TournamentPlayer).where(TournamentPlayer.tournament_id == tournament.id)
            ).all())
            
            if current_players >= tournament.max_players:
                await interaction.response.send_message(
                    "This tournament is full.", 
                    ephemeral=True
                )
                return
        
        # Ensure user exists in database
        Users.fetch(interaction.user.id)
        
        # Register player
        player = TournamentPlayer(
            tournament_id=tournament.id,
            user_id=interaction.user.id
        )
        
        self.session.add(player)
        self.session.commit()
        
        embed = discord.Embed(
            title="Registration Successful",
            description=f"You have been registered for tournament '{tournament_name}'!",
            color=discord.Color.green()
        )
        
        # Show current player count
        total_players = len(self.session.exec(
            select(TournamentPlayer).where(TournamentPlayer.tournament_id == tournament.id)
        ).all())
        
        if tournament.max_players:
            embed.add_field(
                name="Players", 
                value=f"{total_players}/{tournament.max_players}", 
                inline=True
            )
        else:
            embed.add_field(name="Players", value=str(total_players), inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="spectate", description="Join as a spectator for a tournament")
    @app_commands.describe(tournament_name="Name of the tournament to spectate")
    async def spectate_tournament(
        self,
        interaction: discord.Interaction,
        tournament_name: str
    ) -> None:
        """Join as a spectator for a tournament."""
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        
        # Find tournament
        tournament = self.session.exec(
            select(Tournament).where(
                Tournament.guild_id == interaction.guild.id,
                Tournament.name == tournament_name
            )
        ).first()
        
        if not tournament:
            await interaction.response.send_message(
                f"No tournament named '{tournament_name}' found.", 
                ephemeral=True
            )
            return
        
        # Check if already a player
        existing_player = self.session.exec(
            select(TournamentPlayer).where(
                TournamentPlayer.tournament_id == tournament.id,
                TournamentPlayer.user_id == interaction.user.id
            )
        ).first()
        
        if existing_player:
            await interaction.response.send_message(
                "You are registered as a player in this tournament.", 
                ephemeral=True
            )
            return
        
        # Check if already a spectator
        existing_spectator = self.session.exec(
            select(TournamentSpectator).where(
                TournamentSpectator.tournament_id == tournament.id,
                TournamentSpectator.user_id == interaction.user.id
            )
        ).first()
        
        if existing_spectator:
            await interaction.response.send_message(
                "You are already registered as a spectator for this tournament.", 
                ephemeral=True
            )
            return
        
        # Ensure user exists in database
        Users.fetch(interaction.user.id)
        
        # Register spectator
        spectator = TournamentSpectator(
            tournament_id=tournament.id,
            user_id=interaction.user.id
        )
        
        self.session.add(spectator)
        self.session.commit()
        
        embed = discord.Embed(
            title="Spectator Registration Successful",
            description=f"You are now registered as a spectator for tournament '{tournament_name}'!",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="list", description="List all tournaments in this server")
    async def list_tournaments(self, interaction: discord.Interaction) -> None:
        """List all tournaments in this server."""
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        
        tournaments = self.session.exec(
            select(Tournament).where(Tournament.guild_id == interaction.guild.id)
        ).all()
        
        if not tournaments:
            await interaction.response.send_message("No tournaments found in this server.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Tournaments",
            description=f"All tournaments in {interaction.guild.name}",
            color=discord.Color.blue()
        )
        
        for tournament in tournaments:
            player_count = len(self.session.exec(
                select(TournamentPlayer).where(TournamentPlayer.tournament_id == tournament.id)
            ).all())
            
            status_emoji = {
                TournamentStatus.PLANNED: "📋",
                TournamentStatus.REGISTRATION_OPEN: "📝",
                TournamentStatus.REGISTRATION_CLOSED: "🔒",
                TournamentStatus.IN_PROGRESS: "🎮",
                TournamentStatus.COMPLETED: "🏆",
                TournamentStatus.CANCELLED: "❌"
            }
            
            players_text = f"{player_count}"
            if tournament.max_players:
                players_text += f"/{tournament.max_players}"
            
            embed.add_field(
                name=f"{status_emoji.get(tournament.status, '❓')} {tournament.name}",
                value=f"Type: {tournament.tournament_type.value.replace('_', ' ').title()}\n"
                      f"Status: {tournament.status.value.replace('_', ' ').title()}\n"
                      f"Players: {players_text}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)
    
    @register_tournament.autocomplete("tournament_name")
    @spectate_tournament.autocomplete("tournament_name")
    async def tournament_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for tournament names."""
        if not interaction.guild:
            return []
        
        tournaments = self.session.exec(
            select(Tournament).where(
                Tournament.guild_id == interaction.guild.id,
                Tournament.status != TournamentStatus.CANCELLED
            )
        ).all()
        
        choices = []
        for tournament in tournaments:
            if current.lower() in tournament.name.lower():
                choices.append(app_commands.Choice(name=tournament.name, value=tournament.name))
        
        return choices[:25]  # Discord limit


async def setup(bot) -> None:
    """Setup function for the tournament manager cog."""
    await bot.add_cog(TournamentManager(bot=bot))