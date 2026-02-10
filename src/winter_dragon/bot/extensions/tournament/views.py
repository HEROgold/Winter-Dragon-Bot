"""Voting views and components for tournament system."""

from typing import TYPE_CHECKING

import discord
from discord import Interaction, SelectOption
from herogold.log import LoggerMixin

from winter_dragon.bot.ui.button import Button
from winter_dragon.bot.ui.select import Select
from winter_dragon.bot.ui.view import View


if TYPE_CHECKING:
    from winter_dragon.bot.extensions.tournament.models import TournamentVote


class GameVoteSelect(Select):
    """Select menu for voting on games."""

    def __init__(self, available_games: list[str], vote_tracker: "TournamentVote") -> None:
        """Initialize the game vote select menu.

        Args:
        ----
            available_games: List of game names to vote on
            vote_tracker: Vote tracking object

        """
        self.vote_tracker = vote_tracker

        options = [
            SelectOption(
                label=game,
                value=game,
                description=f"Vote for {game}",
            )
            for game in available_games
        ]

        super().__init__(
            placeholder="Select a game to vote for",
            options=options,
            min_values=1,
            max_values=1,
            on_interact=self._handle_vote,
        )

    async def _handle_vote(self, interaction: Interaction) -> None:
        """Handle game vote selection."""
        self.logger.info(f"User {interaction.user.id} voting for: {self.values[0]}")

        # Check if user already voted
        if interaction.user.id in self.vote_tracker.votes:
            await interaction.followup.send(
                "You have already voted! You can only vote once.",
                ephemeral=True,
            )
            return

        # Record vote
        game_name = self.values[0]
        self.vote_tracker.votes[interaction.user.id] = game_name
        self.vote_tracker.vote_counts[game_name] = self.vote_tracker.vote_counts.get(game_name, 0) + 1

        self.logger.debug(f"Vote recorded: {game_name} now has {self.vote_tracker.vote_counts[game_name]} votes")

        await interaction.followup.send(
            f"✅ Your vote for **{game_name}** has been recorded!",
            ephemeral=True,
        )

        # Update the embed to show current votes
        if self.view:
            await self.view.update_vote_display(interaction)


class BracketFormatSelect(Select):
    """Select menu for choosing bracket format."""

    def __init__(self, available_formats: list[str], vote_tracker: "TournamentVote") -> None:
        """Initialize the bracket format select menu.

        Args:
        ----
            available_formats: List of bracket formats ("2v2", "3v3", etc.)
            vote_tracker: Vote tracking object

        """
        self.vote_tracker = vote_tracker

        options = [
            SelectOption(
                label=format_,
                value=format_,
                description=f"Play in {format_} format",
            )
            for format_ in available_formats
        ]

        super().__init__(
            placeholder="Select bracket format",
            options=options,
            min_values=1,
            max_values=1,
            on_interact=self._handle_format_vote,
        )

    async def _handle_format_vote(self, interaction: Interaction) -> None:
        """Handle bracket format vote selection."""
        self.logger.info(f"User {interaction.user.id} voting for format: {self.values[0]}")

        # Check if user already voted
        if interaction.user.id in self.vote_tracker.format_votes:
            await interaction.followup.send(
                "You have already voted for a format!",
                ephemeral=True,
            )
            return

        # Record format vote
        format_choice = self.values[0]
        self.vote_tracker.format_votes[interaction.user.id] = format_choice
        self.vote_tracker.format_counts[format_choice] = self.vote_tracker.format_counts.get(format_choice, 0) + 1

        self.logger.debug(
            f"Format vote recorded: {format_choice} now has {self.vote_tracker.format_counts[format_choice]} votes"
        )

        await interaction.followup.send(
            f"✅ Your vote for **{format_choice}** format has been recorded!",
            ephemeral=True,
        )

        if self.view:
            await self.view.update_vote_display(interaction)


class JoinTournamentButton(Button):
    """Button for joining the tournament after voting concludes."""

    def __init__(self, vote_tracker: "TournamentVote") -> None:
        """Initialize the join tournament button.

        Args:
        ----
            vote_tracker: Vote tracking object

        """
        self.vote_tracker = vote_tracker

        super().__init__(
            style=discord.ButtonStyle.success,
            label="Join Tournament",
            emoji="🎮",
            disabled=True,  # Disabled until voting concludes
            on_interact=self._handle_join,
        )

    async def _handle_join(self, interaction: Interaction) -> None:
        """Handle user joining the tournament."""
        self.logger.info(f"User {interaction.user.id} joining tournament")

        # Check if user already joined
        if interaction.user.id in self.vote_tracker.participants:
            await interaction.followup.send(
                "You have already joined the tournament!",
                ephemeral=True,
            )
            return

        # Add participant
        self.vote_tracker.participants.append(interaction.user.id)

        self.logger.debug(f"Participant added: {interaction.user.id}. Total: {len(self.vote_tracker.participants)}")

        await interaction.followup.send(
            f"✅ You have joined the tournament! ({len(self.vote_tracker.participants)} players)",
            ephemeral=True,
        )

        if self.view:
            await self.view.update_vote_display(interaction)


class ConcludeVotingButton(Button):
    """Button for concluding the voting phase (admin only)."""

    def __init__(self, vote_tracker: "TournamentVote", admin_id: int) -> None:
        """Initialize the conclude voting button.

        Args:
        ----
            vote_tracker: Vote tracking object
            admin_id: User ID of the admin who can conclude voting

        """
        self.vote_tracker = vote_tracker
        self.admin_id = admin_id

        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Conclude Voting",
            emoji="✋",
            on_interact=self._handle_conclude,
        )

    async def _handle_conclude(self, interaction: Interaction) -> None:
        """Handle concluding the voting phase."""
        self.logger.info(f"User {interaction.user.id} attempting to conclude voting")

        # Check if user is authorized
        if interaction.user.id != self.admin_id:
            await interaction.followup.send(
                "❌ Only the tournament organizer can conclude voting!",
                ephemeral=True,
            )
            return

        # Determine winning game
        if not self.vote_tracker.vote_counts:
            await interaction.followup.send(
                "❌ No votes have been cast yet!",
                ephemeral=True,
            )
            return

        winning_game = max(self.vote_tracker.vote_counts, key=self.vote_tracker.vote_counts.get)
        winning_votes = self.vote_tracker.vote_counts[winning_game]

        self.vote_tracker.winning_game = winning_game
        self.vote_tracker.voting_concluded = True

        # Determine winning format if applicable
        if self.vote_tracker.format_counts:
            winning_format = max(self.vote_tracker.format_counts, key=self.vote_tracker.format_counts.get)
            self.vote_tracker.winning_format = winning_format

        self.logger.info(f"Voting concluded: {winning_game} won with {winning_votes} votes")

        # Disable voting, enable join button
        self.disabled = True
        if self.view:
            for child in self.view.children:
                if isinstance(child, (GameVoteSelect, BracketFormatSelect)):
                    child.disabled = True
                elif isinstance(child, JoinTournamentButton):
                    child.disabled = False

        await interaction.followup.send(
            f"🏆 Voting concluded! **{winning_game}** wins with {winning_votes} votes!\n"
            f"Players can now join the tournament by clicking the 'Join Tournament' button.",
        )

        if self.view:
            await self.view.update_vote_display(interaction)


class StartTournamentButton(Button):
    """Button for starting the tournament and generating brackets."""

    def __init__(self, vote_tracker: "TournamentVote", admin_id: int) -> None:
        """Initialize the start tournament button.

        Args:
        ----
            vote_tracker: Vote tracking object
            admin_id: User ID of the admin who can start tournament

        """
        self.vote_tracker = vote_tracker
        self.admin_id = admin_id

        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Start Tournament",
            emoji="🚀",
            disabled=True,  # Disabled until voting concludes
            on_interact=self._handle_start,
        )

    async def _handle_start(self, interaction: Interaction) -> None:
        """Handle starting the tournament."""
        self.logger.info(f"User {interaction.user.id} attempting to start tournament")

        # Check if user is authorized
        if interaction.user.id != self.admin_id:
            await interaction.followup.send(
                "❌ Only the tournament organizer can start the tournament!",
                ephemeral=True,
            )
            return

        # Check if voting has concluded
        if not self.vote_tracker.voting_concluded:
            await interaction.followup.send(
                "❌ Voting must be concluded before starting the tournament!",
                ephemeral=True,
            )
            return

        # Check minimum participants
        if len(self.vote_tracker.participants) < 2:
            await interaction.followup.send(
                f"❌ Need at least 2 participants to start! Currently have {len(self.vote_tracker.participants)}.",
                ephemeral=True,
            )
            return

        self.vote_tracker.tournament_started = True
        self.disabled = True

        self.logger.info(f"Tournament starting with {len(self.vote_tracker.participants)} participants")

        await interaction.followup.send(
            f"🎮 Tournament is starting! Generating balanced teams for {len(self.vote_tracker.participants)} players...",
        )

        # Trigger matchmaking callback if set
        if self.view and hasattr(self.view, "on_tournament_start"):
            await self.view.on_tournament_start(interaction)


class TournamentVotingView(View, LoggerMixin):
    """Main view for tournament voting and participant management."""

    def __init__(
        self,
        vote_tracker: "TournamentVote",
        available_games: list[str],
        available_formats: list[str] | None = None,
        admin_id: int = 0,
        on_tournament_start=None,
    ) -> None:
        """Initialize the tournament voting view.

        Args:
        ----
            vote_tracker: Vote tracking object
            available_games: List of games to vote on
            available_formats: Optional list of bracket formats
            admin_id: User ID of tournament organizer
            on_tournament_start: Callback for when tournament starts

        """
        super().__init__(timeout=None)  # No timeout for voting

        self.vote_tracker = vote_tracker
        self.admin_id = admin_id
        self.on_tournament_start = on_tournament_start

        # Add game voting dropdown
        self.add_item(GameVoteSelect(available_games, vote_tracker))

        # Add format voting if formats provided
        if available_formats:
            self.add_item(BracketFormatSelect(available_formats, vote_tracker))

        # Add control buttons
        self.add_item(JoinTournamentButton(vote_tracker))
        self.add_item(ConcludeVotingButton(vote_tracker, admin_id))
        self.add_item(StartTournamentButton(vote_tracker, admin_id))

        self.logger.info(
            f"TournamentVotingView initialized: {len(available_games)} games, "
            f"{len(available_formats) if available_formats else 0} formats, admin={admin_id}"
        )

    async def update_vote_display(self, interaction: Interaction) -> None:
        """Update the message to show current vote counts.

        Args:
        ----
            interaction: The interaction to update

        """
        self.logger.debug("Updating vote display")

        embed = self._create_vote_embed()

        try:
            await interaction.message.edit(embed=embed, view=self)
            self.logger.debug("Vote display updated successfully")
        except Exception as e:
            self.logger.exception(f"Failed to update vote display: {e}")

    def _create_vote_embed(self) -> discord.Embed:
        """Create an embed showing current voting status.

        Returns
        -------
            Discord embed with vote information

        """
        if self.vote_tracker.voting_concluded:
            color = discord.Color.green()
            title = "🏆 Tournament Voting - CONCLUDED"
            description = f"**Winner: {self.vote_tracker.winning_game}**\n\n"

            if self.vote_tracker.winning_format:
                description += f"**Format: {self.vote_tracker.winning_format}**\n\n"

            description += "Click 'Join Tournament' to participate!"
        else:
            color = discord.Color.blue()
            title = "🎮 Tournament Voting - IN PROGRESS"
            description = "Vote for the game you want to play!"

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
        )

        # Add vote counts
        if self.vote_tracker.vote_counts:
            vote_text = "\n".join(
                f"**{game}**: {count} vote{'s' if count != 1 else ''}"
                for game, count in sorted(
                    self.vote_tracker.vote_counts.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            )
            embed.add_field(name="📊 Current Votes", value=vote_text, inline=False)

        # Add format counts if applicable
        if self.vote_tracker.format_counts:
            format_text = "\n".join(
                f"**{fmt}**: {count} vote{'s' if count != 1 else ''}"
                for fmt, count in sorted(
                    self.vote_tracker.format_counts.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            )
            embed.add_field(name="🎯 Format Votes", value=format_text, inline=False)

        # Add participant count
        if self.vote_tracker.participants:
            embed.add_field(
                name="👥 Participants",
                value=f"{len(self.vote_tracker.participants)} player{'s' if len(self.vote_tracker.participants) != 1 else ''}",
                inline=True,
            )

        # Add status
        if self.vote_tracker.tournament_started:
            embed.set_footer(text="🚀 Tournament in progress!")
        elif self.vote_tracker.voting_concluded:
            embed.set_footer(text="✋ Voting concluded - Join now!")
        else:
            embed.set_footer(text="🗳️ Voting open - Cast your vote!")

        return embed
