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
    TournamentMatch,
    TournamentPlayer,
    TournamentSpectator,
    TournamentTeam,
    Users,
)
from winter_dragon.database.tables.tournament import TournamentStatus, TournamentType

from .strategies.double_elimination import DoubleEliminationStrategy
from .strategies.ffa import FFAStrategy
from .strategies.round_robin import RoundRobinStrategy
from .strategies.single_elimination import SingleEliminationStrategy


class TournamentManager(GroupCog):
    """Tournament management system for Discord servers."""
    
    def __init__(self, **kwargs: Unpack[BotKwarg]) -> None:
        """Initialize the tournament manager."""
        super().__init__(**kwargs)
        self.strategies = {
            TournamentType.SINGLE_ELIMINATION: SingleEliminationStrategy,
            TournamentType.DOUBLE_ELIMINATION: DoubleEliminationStrategy,
            TournamentType.ROUND_ROBIN: RoundRobinStrategy,
            TournamentType.FFA: FFAStrategy,
            # TODO: Add Swiss, Race, Group Stages strategies
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
    
    @app_commands.command(name="assign-teams", description="Assign players to teams (admin only)")
    @app_commands.describe(
        tournament_name="Name of the tournament",
        auto_assign="Automatically assign players to teams evenly"
    )
    async def assign_teams(
        self,
        interaction: discord.Interaction,
        tournament_name: str,
        auto_assign: bool = True
    ) -> None:
        """Assign players to teams."""
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        
        # Check permissions (admin or tournament creator)
        if not (interaction.user.guild_permissions.administrator or await self._is_tournament_creator(interaction.user.id, tournament_name, interaction.guild.id)):
            await interaction.response.send_message("You don't have permission to manage this tournament.", ephemeral=True)
            return
        
        # Find tournament
        tournament = self.session.exec(
            select(Tournament).where(
                Tournament.guild_id == interaction.guild.id,
                Tournament.name == tournament_name
            )
        ).first()
        
        if not tournament:
            await interaction.response.send_message(f"Tournament '{tournament_name}' not found.", ephemeral=True)
            return
        
        # Get all registered players
        players = self.session.exec(
            select(TournamentPlayer).where(TournamentPlayer.tournament_id == tournament.id)
        ).all()
        
        if len(players) < tournament.min_players:
            await interaction.response.send_message(
                f"Not enough players registered. Need at least {tournament.min_players}, have {len(players)}.",
                ephemeral=True
            )
            return
        
        if auto_assign:
            await self._auto_assign_teams(tournament, players)
            embed = discord.Embed(
                title="Teams Assigned",
                description=f"Players have been automatically assigned to teams for '{tournament_name}'!",
                color=discord.Color.green()
            )
        else:
            # Manual assignment would require additional UI
            embed = discord.Embed(
                title="Manual Assignment",
                description="Manual team assignment is not yet implemented. Use auto-assign for now.",
                color=discord.Color.orange()
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="create-channels", description="Create channels and categories for teams (admin only)")
    @app_commands.describe(
        tournament_name="Name of the tournament",
        use_roles="Whether to create temporary roles for permission management"
    )
    async def create_channels(
        self,
        interaction: discord.Interaction,
        tournament_name: str,
        use_roles: bool = True
    ) -> None:
        """Create Discord channels and categories for tournament teams."""
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        
        # Check permissions
        if not (interaction.user.guild_permissions.administrator or await self._is_tournament_creator(interaction.user.id, tournament_name, interaction.guild.id)):
            await interaction.response.send_message("You don't have permission to manage this tournament.", ephemeral=True)
            return
        
        # Find tournament
        tournament = self.session.exec(
            select(Tournament).where(
                Tournament.guild_id == interaction.guild.id,
                Tournament.name == tournament_name
            )
        ).first()
        
        if not tournament:
            await interaction.response.send_message(f"Tournament '{tournament_name}' not found.", ephemeral=True)
            return
        
        # Get teams
        teams = self.session.exec(
            select(TournamentTeam).where(TournamentTeam.tournament_id == tournament.id)
        ).all()
        
        if not teams:
            await interaction.response.send_message("No teams found. Please assign teams first.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Create main tournament category if it doesn't exist
            if not tournament.category_id:
                category = await interaction.guild.create_category(
                    name=f"🏆 {tournament.name}",
                    reason=f"Tournament category for {tournament.name}"
                )
                tournament.category_id = category.id
            else:
                category = interaction.guild.get_channel(tournament.category_id)
            
            # Create scoreboard channel if it doesn't exist
            if not tournament.scoreboard_channel_id:
                scoreboard_channel = await interaction.guild.create_text_channel(
                    name="📊-scoreboard",
                    category=category,
                    reason=f"Scoreboard for tournament {tournament.name}"
                )
                tournament.scoreboard_channel_id = scoreboard_channel.id
            
            # Create stage channel for spectators if it doesn't exist
            if not tournament.stage_channel_id:
                stage_channel = await interaction.guild.create_stage_channel(
                    name="🎪-tournament-stage",
                    category=category,
                    reason=f"Stage channel for tournament {tournament.name}"
                )
                tournament.stage_channel_id = stage_channel.id
            
            # Create team channels and roles
            created_count = 0
            for team in teams:
                if not team.text_channel_id or not team.voice_channel_id:
                    await self._create_team_channels(interaction.guild, tournament, team, category, use_roles)
                    created_count += 1
            
            # Update tournament settings
            tournament.use_temporary_roles = use_roles
            self.session.add(tournament)
            self.session.commit()
            
            embed = discord.Embed(
                title="Channels Created",
                description=f"Created channels for {created_count} teams in tournament '{tournament.name}'!",
                color=discord.Color.green()
            )
            embed.add_field(name="Category", value=category.mention if category else "Error", inline=True)
            if tournament.scoreboard_channel_id:
                scoreboard = interaction.guild.get_channel(tournament.scoreboard_channel_id)
                embed.add_field(name="Scoreboard", value=scoreboard.mention if scoreboard else "Error", inline=True)
            if tournament.stage_channel_id:
                stage = interaction.guild.get_channel(tournament.stage_channel_id)
                embed.add_field(name="Stage", value=stage.mention if stage else "Error", inline=True)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error creating channels: {e}")
            await interaction.followup.send(
                "An error occurred while creating channels. Please check bot permissions.",
                ephemeral=True
            )
    
    async def _is_tournament_creator(self, user_id: int, tournament_name: str, guild_id: int) -> bool:
        """Check if user is the creator of the tournament."""
        tournament = self.session.exec(
            select(Tournament).where(
                Tournament.guild_id == guild_id,
                Tournament.name == tournament_name,
                Tournament.creator_id == user_id
            )
        ).first()
        return tournament is not None
    
    async def _auto_assign_teams(self, tournament: Tournament, players: list[TournamentPlayer]) -> None:
        """Automatically assign players to teams."""
        import random
        
        # Shuffle players for random assignment
        shuffled_players = players.copy()
        random.shuffle(shuffled_players)
        
        # Calculate number of teams needed
        total_players = len(players)
        team_size = tournament.team_size
        num_teams = (total_players + team_size - 1) // team_size  # Ceiling division
        
        # Clear existing teams
        existing_teams = self.session.exec(
            select(TournamentTeam).where(TournamentTeam.tournament_id == tournament.id)
        ).all()
        for team in existing_teams:
            self.session.delete(team)
        
        # Create teams and assign players
        for team_num in range(num_teams):
            team = TournamentTeam(
                tournament_id=tournament.id,
                name=f"Team {team_num + 1}"
            )
            self.session.add(team)
            self.session.flush()  # Get the team ID
            
            # Assign players to this team
            start_idx = team_num * team_size
            end_idx = min(start_idx + team_size, total_players)
            
            for i in range(start_idx, end_idx):
                shuffled_players[i].team_id = team.id
                if i == start_idx:  # First player becomes captain
                    team.captain_id = shuffled_players[i].user_id
        
        self.session.commit()
    
    async def _create_team_channels(
        self,
        guild: discord.Guild,
        tournament: Tournament,
        team: TournamentTeam,
        category: discord.CategoryChannel,
        use_roles: bool
    ) -> None:
        """Create channels for a specific team."""
        # Get team players
        team_players = self.session.exec(
            select(TournamentPlayer).where(TournamentPlayer.team_id == team.id)
        ).all()
        
        team_members = []
        for player in team_players:
            member = guild.get_member(player.user_id)
            if member:
                team_members.append(member)
        
        # Create role if using role-based permissions
        role = None
        if use_roles:
            role = await guild.create_role(
                name=f"{tournament.name} - {team.name}",
                reason=f"Team role for {team.name} in tournament {tournament.name}"
            )
            team.role_id = role.id
            
            # Assign role to team members
            for member in team_members:
                try:
                    await member.add_roles(role, reason=f"Added to team {team.name}")
                except discord.HTTPException:
                    self.logger.warning(f"Failed to assign role to {member}")
        
        # Set up permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False)
        }
        
        if use_roles and role:
            overwrites[role] = discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                connect=True,
                speak=True
            )
        else:
            # User-based permissions
            for member in team_members:
                overwrites[member] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    connect=True,
                    speak=True
                )
        
        # Create text channel
        if not team.text_channel_id:
            text_channel = await guild.create_text_channel(
                name=f"{team.name.lower().replace(' ', '-')}-chat",
                category=category,
                overwrites=overwrites,
                reason=f"Team text channel for {team.name}"
            )
            team.text_channel_id = text_channel.id
        
        # Create voice channel
        if not team.voice_channel_id:
            voice_channel = await guild.create_voice_channel(
                name=f"{team.name} Voice",
                category=category,
                overwrites=overwrites,
                reason=f"Team voice channel for {team.name}"
            )
            team.voice_channel_id = voice_channel.id
        
        self.session.add(team)
        self.session.commit()
    
    @assign_teams.autocomplete("tournament_name")
    @create_channels.autocomplete("tournament_name")
    async def admin_tournament_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for tournament names (admin commands)."""
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
    
    @app_commands.command(name="scoreboard", description="Show tournament scoreboard")
    @app_commands.describe(tournament_name="Name of the tournament")
    async def show_scoreboard(
        self,
        interaction: discord.Interaction,
        tournament_name: str
    ) -> None:
        """Display the tournament scoreboard."""
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
            await interaction.response.send_message(f"Tournament '{tournament_name}' not found.", ephemeral=True)
            return
        
        # Get teams and matches
        teams = self.session.exec(
            select(TournamentTeam).where(TournamentTeam.tournament_id == tournament.id)
        ).all()
        
        if not teams:
            await interaction.response.send_message("No teams found in this tournament.", ephemeral=True)
            return
        
        # Get tournament strategy and standings
        strategy_class = self.strategies.get(tournament.tournament_type)
        if not strategy_class:
            await interaction.response.send_message("Tournament type not supported yet.", ephemeral=True)
            return
        
        strategy = strategy_class(tournament)
        matches = self.session.exec(
            select(TournamentMatch).where(TournamentMatch.tournament_id == tournament.id)
        ).all()
        
        standings = strategy.get_standings(teams, matches)
        
        embed = discord.Embed(
            title=f"🏆 {tournament.name} Scoreboard",
            color=discord.Color.gold()
        )
        
        if tournament.tournament_type == TournamentType.ROUND_ROBIN:
            # Round robin standings with points
            standings_text = ""
            for i, team in enumerate(standings, 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                standings_text += f"{emoji} **{team.name}** - {team.points} pts ({team.wins}W-{team.draws}D-{team.losses}L)\n"
            
            embed.add_field(name="Standings", value=standings_text or "No matches completed", inline=False)
        
        else:
            # Elimination tournament standings
            standings_text = ""
            for i, team in enumerate(standings, 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                if team.status.value == "eliminated":
                    status = "❌"
                elif team.status.value == "active":
                    status = "✅"
                else:
                    status = "⚪"
                standings_text += f"{emoji} {status} **{team.name}** ({team.wins}W-{team.losses}L)\n"
            
            embed.add_field(name="Standings", value=standings_text or "No teams", inline=False)
        
        # Add tournament info
        embed.add_field(
            name="Tournament Info",
            value=f"Type: {tournament.tournament_type.value.replace('_', ' ').title()}\n"
                  f"Status: {tournament.status.value.replace('_', ' ').title()}\n"
                  f"Teams: {len(teams)}",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)
    
    @show_scoreboard.autocomplete("tournament_name")
    async def scoreboard_tournament_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for tournament names."""
        return await self.tournament_autocomplete(interaction, current)
    
    @app_commands.command(name="start", description="Start a tournament and generate matches (admin only)")
    @app_commands.describe(tournament_name="Name of the tournament to start")
    async def start_tournament(
        self,
        interaction: discord.Interaction,
        tournament_name: str
    ) -> None:
        """Start a tournament and generate initial matches."""
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        
        # Check permissions
        if not (interaction.user.guild_permissions.administrator or await self._is_tournament_creator(interaction.user.id, tournament_name, interaction.guild.id)):
            await interaction.response.send_message("You don't have permission to start this tournament.", ephemeral=True)
            return
        
        # Find tournament
        tournament = self.session.exec(
            select(Tournament).where(
                Tournament.guild_id == interaction.guild.id,
                Tournament.name == tournament_name
            )
        ).first()
        
        if not tournament:
            await interaction.response.send_message(f"Tournament '{tournament_name}' not found.", ephemeral=True)
            return
        
        if tournament.status not in [TournamentStatus.PLANNED, TournamentStatus.REGISTRATION_CLOSED]:
            await interaction.response.send_message(
                f"Tournament cannot be started. Current status: {tournament.status.value}",
                ephemeral=True
            )
            return
        
        # Get teams
        teams = self.session.exec(
            select(TournamentTeam).where(TournamentTeam.tournament_id == tournament.id)
        ).all()
        
        if not teams:
            await interaction.response.send_message("No teams found. Please assign teams first.", ephemeral=True)
            return
        
        if len(teams) < tournament.min_players:
            await interaction.response.send_message(
                f"Not enough teams to start. Need at least {tournament.min_players}, have {len(teams)}.",
                ephemeral=True
            )
            return
        
        # Get tournament strategy
        strategy_class = self.strategies.get(tournament.tournament_type)
        if not strategy_class:
            await interaction.response.send_message("Tournament type not supported yet.", ephemeral=True)
            return
        
        strategy = strategy_class(tournament)
        
        # Validate team count for this tournament type
        if not strategy.validate_team_count(len(teams)):
            await interaction.response.send_message(
                f"Invalid number of teams ({len(teams)}) for {tournament.tournament_type.value.replace('_', ' ')} tournament.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Generate initial matches
            matches = await strategy.generate_matches(teams)
            
            # Save matches to database
            for match in matches:
                self.session.add(match)
            
            # Update tournament status
            tournament.status = TournamentStatus.IN_PROGRESS
            tournament.tournament_start = discord.utils.utcnow()
            self.session.add(tournament)
            
            self.session.commit()
            
            embed = discord.Embed(
                title="Tournament Started!",
                description=f"Tournament '{tournament_name}' has been started with {len(matches)} initial matches!",
                color=discord.Color.green()
            )
            embed.add_field(name="Teams", value=str(len(teams)), inline=True)
            embed.add_field(name="Matches Generated", value=str(len(matches)), inline=True)
            embed.add_field(name="Type", value=tournament.tournament_type.value.replace("_", " ").title(), inline=True)
            
            # Show first few matches
            if matches:
                match_list = ""
                for i, match in enumerate(matches[:5]):
                    team1 = next((t for t in teams if t.id == match.team1_id), None)
                    team2 = next((t for t in teams if t.id == match.team2_id), None)
                    if team1 and team2:
                        match_list += f"**{team1.name}** vs **{team2.name}**\n"
                
                if len(matches) > 5:
                    match_list += f"... and {len(matches) - 5} more matches"
                
                embed.add_field(name="First Matches", value=match_list, inline=False)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error starting tournament: {e}")
            await interaction.followup.send(
                "An error occurred while starting the tournament.",
                ephemeral=True
            )
    
    @start_tournament.autocomplete("tournament_name")
    async def start_tournament_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for tournament names (start command)."""
        return await self.admin_tournament_autocomplete(interaction, current)


async def setup(bot) -> None:
    """Setup function for the tournament manager cog."""
    await bot.add_cog(TournamentManager(bot=bot))