"""Handle voting using dropdowns.

Users may only vote on a game once.
When a vote is concluded, players may press a button to enter that game.

Some games support different tournament brackets, or custom settings.
In those cases, players will be able to vote on their desired bracket and settings after voting.

All players will be distributed into teams and brackets will be generated.
The bracket generation process will take into account winrate across the team and individual players,
trying to balance out the teams as much as possible.
The matchmaking system will try to avoid putting players that have great synergy together.
The system takes into account the selected bracket format, and settings on the game.
"""

import discord
from discord import Interaction, app_commands
from discord.ext import commands
from herogold.log import LoggerMixin

from winter_dragon.bot.core.cogs import Cog
from winter_dragon.bot.extensions.tournament.matchmaking import MatchmakingSystem
from winter_dragon.bot.extensions.tournament.models import TournamentVote
from winter_dragon.bot.extensions.tournament.views import TournamentVotingView
from winter_dragon.database.tables.game import Games
from winter_dragon.database.tables.user import Users


class TournamentVoting(Cog, LoggerMixin):
    """Cog for handling tournament voting and matchmaking."""

    def __init__(self, bot: commands.Bot, **kwargs) -> None:
        """Initialize the tournament voting cog.

        Args:
        ----
            bot: Discord bot instance
            **kwargs: Additional arguments for Cog initialization

        """
        super().__init__(bot=bot, **kwargs)
        self.matchmaking = MatchmakingSystem()
        self.active_votes: dict[int, TournamentVote] = {}  # message_id -> TournamentVote

        self.logger.info("TournamentVoting cog initialized")
        self.logger.debug(f"Active votes tracker initialized: {len(self.active_votes)} votes")

    async def cog_load(self) -> None:
        """Called when the cog is loaded."""
        self.logger.info("TournamentVoting cog loaded and ready")

    async def cog_unload(self) -> None:
        """Called when the cog is unloaded."""
        self.logger.info(f"TournamentVoting cog unloading... {len(self.active_votes)} active votes will be cleared")
        self.active_votes.clear()
        self.logger.info("TournamentVoting cog unloaded")

    @app_commands.command(
        name="start_tournament",
        description="Start a tournament vote for game selection",
    )
    @app_commands.describe(
        games="Comma-separated list of games to vote on (e.g., 'League of Legends, CS:GO, Rocket League')",
        formats="Optional comma-separated list of bracket formats (e.g., '2v2, 3v3, 4v4')",
    )
    async def start_tournament(
        self,
        interaction: Interaction,
        games: str,
        formats: str | None = None,
    ) -> None:
        """Start a tournament voting session.

        Args:
        ----
            interaction: Discord interaction
            games: Comma-separated list of games
            formats: Optional comma-separated list of formats

        """
        self.logger.info(f"User {interaction.user.id} starting tournament vote")

        # Parse games
        game_list = [g.strip() for g in games.split(",")]
        if not game_list:
            await interaction.response.send_message(
                "❌ You must provide at least one game!",
                ephemeral=True,
            )
            return

        # Parse formats if provided
        format_list = None
        if formats:
            format_list = [f.strip() for f in formats.split(",")]

        self.logger.debug(f"Starting vote with games: {game_list}, formats: {format_list}")

        # Create vote tracker
        vote_tracker = TournamentVote()

        # Create view with callback
        view = TournamentVotingView(
            vote_tracker=vote_tracker,
            available_games=game_list,
            available_formats=format_list,
            admin_id=interaction.user.id,
            on_tournament_start=lambda i: self._generate_teams(i, vote_tracker),
        )

        # Create initial embed
        embed = view._create_vote_embed()

        await interaction.response.send_message(
            embed=embed,
            view=view,
        )

        # Store vote tracker for reference
        message = await interaction.original_response()
        self.active_votes[message.id] = vote_tracker

        self.logger.info(f"Tournament vote started (message ID: {message.id})")

    async def _generate_teams(
        self,
        interaction: Interaction,
        vote_tracker: TournamentVote,
    ) -> None:
        """Generate balanced teams for the tournament.

        Args:
        ----
            interaction: Discord interaction
            vote_tracker: Vote tracking object

        """
        self.logger.info(f"Generating teams for {len(vote_tracker.participants)} participants")

        # Ensure all users exist in database
        for user_id in vote_tracker.participants:
            Users.fetch(user_id)

        # Determine bracket format
        if vote_tracker.winning_format:
            bracket_format = vote_tracker.winning_format
        else:
            # Auto-determine based on participant count
            num_participants = len(vote_tracker.participants)
            if num_participants == 2:
                bracket_format = "1v1"
            elif num_participants == 4:
                bracket_format = "2v2"
            elif num_participants == 6:
                bracket_format = "3v3"
            elif num_participants == 8:
                bracket_format = "4v4"
            else:
                # Default to teams that fit the number
                team_size = 2
                while num_participants % (team_size * 2) != 0 and team_size < 5:
                    team_size += 1
                bracket_format = f"{team_size}v{team_size}"

        self.logger.debug(f"Using bracket format: {bracket_format}")

        try:
            # Generate balanced teams
            teams = self.matchmaking.create_balanced_teams(
                game_name=vote_tracker.winning_game,
                player_ids=vote_tracker.participants,
                bracket_format=bracket_format,
                avoid_synergy=True,
            )

            self.logger.info(f"Teams generated successfully: {len(teams)} teams")

            # Create embed with team assignments
            embed = discord.Embed(
                title=f"🏆 {vote_tracker.winning_game} Tournament",
                description=f"**Format:** {bracket_format}\n**Players:** {len(vote_tracker.participants)}\n\n"
                "Teams have been balanced based on player skill and synergy!",
                color=discord.Color.gold(),
            )

            # Add team information
            for i, team in enumerate(teams, 1):
                team_members = [f"<@{uid}>" for uid in team]
                embed.add_field(
                    name=f"Team {i}",
                    value="\n".join(team_members),
                    inline=True,
                )

            embed.set_footer(text="Use /record_match to save match results after playing!")

            await interaction.followup.send(embed=embed)

            self.logger.info("Team assignments sent")

        except ValueError as e:
            self.logger.exception(f"Failed to generate teams: {e}")
            await interaction.followup.send(
                f"❌ Failed to generate teams: {e}",
                ephemeral=True,
            )
        except Exception as e:
            self.logger.exception(f"Unexpected error generating teams: {e}")
            await interaction.followup.send(
                f"❌ An unexpected error occurred: {e}",
                ephemeral=True,
            )

    @app_commands.command(
        name="record_match",
        description="Record the results of a tournament match",
    )
    @app_commands.describe(
        game="Name of the game played",
        format="Bracket format (e.g., 2v2, 3v3)",
        team1="Comma-separated user IDs for team 1",
        team2="Comma-separated user IDs for team 2",
        winner="Which team won (1 or 2)",
        team1_score="Optional: Team 1's score",
        team2_score="Optional: Team 2's score",
        duration="Optional: Match duration in minutes",
    )
    async def record_match(
        self,
        interaction: Interaction,
        game: str,
        format: str,
        team1: str,
        team2: str,
        winner: int,
        team1_score: int | None = None,
        team2_score: int | None = None,
        duration: int | None = None,
    ) -> None:
        """Record match results and update player statistics.

        Args:
        ----
            interaction: Discord interaction
            game: Game name
            format: Bracket format
            team1: Team 1 player IDs
            team2: Team 2 player IDs
            winner: Winning team (1 or 2)
            team1_score: Optional team 1 score
            team2_score: Optional team 2 score
            duration: Optional match duration in minutes

        """
        self.logger.info(f"User {interaction.user.id} recording match for {game}")

        await interaction.response.defer()

        try:
            # Parse teams
            team1_ids = [int(uid.strip()) for uid in team1.split(",")]
            team2_ids = [int(uid.strip()) for uid in team2.split(",")]
            teams = [team1_ids, team2_ids]

            self.logger.debug(f"Teams parsed: {teams}")

            # Validate winner
            if winner not in [1, 2]:
                await interaction.followup.send(
                    "❌ Winner must be 1 or 2!",
                    ephemeral=True,
                )
                return

            # Ensure all users exist
            for user_id in team1_ids + team2_ids:
                Users.fetch(user_id)

            # Build scores if provided
            team_scores = None
            if team1_score is not None and team2_score is not None:
                team_scores = [team1_score, team2_score]

            # Convert duration to seconds
            duration_seconds = None
            if duration is not None:
                duration_seconds = duration * 60

            # Record match
            match = self.matchmaking.record_match_result(
                game_name=game,
                teams=teams,
                winning_team_idx=winner - 1,  # Convert to 0-based
                bracket_format=format,
                team_scores=team_scores,
                duration_seconds=duration_seconds,
            )

            self.logger.info(f"Match recorded successfully (ID: {match.id})")

            # Create confirmation embed
            embed = discord.Embed(
                title="✅ Match Recorded",
                description=f"Match results have been saved for **{game}**",
                color=discord.Color.green(),
            )

            embed.add_field(
                name="Format",
                value=format,
                inline=True,
            )
            embed.add_field(
                name="Match ID",
                value=str(match.id),
                inline=True,
            )

            # Show teams
            winner_mark = " 🏆" if winner == 1 else ""
            team1_display = ", ".join(f"<@{uid}>" for uid in team1_ids)
            embed.add_field(
                name=f"Team 1{winner_mark}",
                value=team1_display,
                inline=False,
            )

            winner_mark = " 🏆" if winner == 2 else ""
            team2_display = ", ".join(f"<@{uid}>" for uid in team2_ids)
            embed.add_field(
                name=f"Team 2{winner_mark}",
                value=team2_display,
                inline=False,
            )

            if team_scores:
                embed.add_field(
                    name="Score",
                    value=f"{team_scores[0]} - {team_scores[1]}",
                    inline=True,
                )

            embed.set_footer(text="Player ratings and statistics have been updated!")

            await interaction.followup.send(embed=embed)

        except ValueError as e:
            self.logger.exception(f"Invalid input: {e}")
            await interaction.followup.send(
                f"❌ Invalid input: {e}",
                ephemeral=True,
            )
        except Exception as e:
            self.logger.exception(f"Failed to record match: {e}")
            await interaction.followup.send(
                f"❌ Failed to record match: {e}",
                ephemeral=True,
            )

    @app_commands.command(
        name="player_stats",
        description="View player statistics for a specific game",
    )
    @app_commands.describe(
        game="Name of the game",
        player="The player to view stats for (leave empty for yourself)",
    )
    async def player_stats(
        self,
        interaction: Interaction,
        game: str,
        player: discord.User | None = None,
    ) -> None:
        """Display player statistics for a game.

        Args:
        ----
            interaction: Discord interaction
            game: Game name
            player: Optional player to view (defaults to command user)

        """
        target_user = player or interaction.user
        self.logger.info(f"Fetching stats for user {target_user.id} in {game}")

        await interaction.response.defer()

        try:
            game_obj = Games.fetch_game_by_name(game)

            from sqlmodel import select

            from winter_dragon.database.tables.matchmaking.player_game_stats import PlayerGameStats

            stats = self.matchmaking.session.exec(
                select(PlayerGameStats)
                .where(PlayerGameStats.user_id == target_user.id)
                .where(PlayerGameStats.game_id == game_obj.id)
            ).first()

            if not stats:
                await interaction.followup.send(
                    f"No statistics found for {target_user.mention} in **{game}**",
                    ephemeral=True,
                )
                return

            # Create stats embed
            embed = discord.Embed(
                title=f"📊 {target_user.display_name}'s Stats",
                description=f"Statistics for **{game}**",
                color=discord.Color.blue(),
            )

            embed.set_thumbnail(url=target_user.display_avatar.url)

            embed.add_field(
                name="Matches Played",
                value=str(stats.total_matches),
                inline=True,
            )
            embed.add_field(
                name="Record",
                value=f"{stats.total_wins}W - {stats.total_losses}L",
                inline=True,
            )
            embed.add_field(
                name="Win Rate",
                value=f"{stats.win_rate * 100:.1f}%",
                inline=True,
            )
            embed.add_field(
                name="Skill Rating",
                value=f"{stats.skill_rating:.0f}",
                inline=True,
            )
            embed.add_field(
                name="Avg Score",
                value=f"{stats.avg_score:.1f}",
                inline=True,
            )

            await interaction.followup.send(embed=embed)

            self.logger.info(f"Stats displayed for user {target_user.id}")

        except Exception as e:
            self.logger.exception(f"Failed to fetch stats: {e}")
            await interaction.followup.send(
                f"❌ Failed to fetch statistics: {e}",
                ephemeral=True,
            )

    @app_commands.command(
        name="leaderboard",
        description="View the top players for a game",
    )
    @app_commands.describe(
        game="Name of the game",
        limit="Number of players to show (default: 10)",
    )
    async def leaderboard(
        self,
        interaction: Interaction,
        game: str,
        limit: int = 10,
    ) -> None:
        """Display leaderboard for a game.

        Args:
        ----
            interaction: Discord interaction
            game: Game name
            limit: Number of players to show

        """
        self.logger.info(f"Fetching leaderboard for {game}")

        await interaction.response.defer()

        try:
            game_obj = Games.fetch_game_by_name(game)

            from sqlmodel import select

            from winter_dragon.database.tables.matchmaking.player_game_stats import PlayerGameStats

            top_players = self.matchmaking.session.exec(
                select(PlayerGameStats)
                .where(PlayerGameStats.game_id == game_obj.id)
                .order_by(PlayerGameStats.skill_rating.desc())
                .limit(limit)
            ).all()

            if not top_players:
                await interaction.followup.send(
                    f"No statistics found for **{game}**",
                    ephemeral=True,
                )
                return

            # Create leaderboard embed
            embed = discord.Embed(
                title=f"🏆 {game} Leaderboard",
                description=f"Top {len(top_players)} players by skill rating",
                color=discord.Color.gold(),
            )

            leaderboard_text = ""
            for rank, stats in enumerate(top_players, 1):
                medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
                leaderboard_text += (
                    f"{medal} <@{stats.user_id}> - **{stats.skill_rating:.0f}** ({stats.total_wins}W-{stats.total_losses}L)\n"
                )

            embed.description = leaderboard_text

            await interaction.followup.send(embed=embed)

            self.logger.info(f"Leaderboard displayed for {game}")

        except Exception as e:
            self.logger.exception(f"Failed to fetch leaderboard: {e}")
            await interaction.followup.send(
                f"❌ Failed to fetch leaderboard: {e}",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    """Set up the tournament voting cog.

    Args:
    ----
        bot: Discord bot instance

    """
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Loading TournamentVoting extension...")
    try:
        await bot.add_cog(TournamentVoting(bot))
        logger.info("TournamentVoting extension loaded successfully")
    except Exception as e:
        logger.exception(f"Failed to load TournamentVoting: {e}")
        raise
