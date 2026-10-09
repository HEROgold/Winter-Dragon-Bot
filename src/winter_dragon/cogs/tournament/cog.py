"""The /tournament command group: sign-up, teams, a single-elimination bracket, match cards, drafts and votes."""

from __future__ import annotations

lazy from random import Random
lazy from typing import TYPE_CHECKING, override

from sqlmodel import Session
lazy from wd_bot.checks import member_has
lazy from wd_bot.cogs import Cog, GroupCog

# Command resolves option annotations from module globals at runtime, so User must be available here.
lazy from wd_discord import User  # noqa: TC002
lazy from wd_discord.interactions import ApplicationCommandOptionChoice, InteractionContextType
lazy from wd_discord.permissions import Permissions

lazy from .bracket import parse_options, round_count
lazy from .cards import (
    bracket_embed,
    match_buttons,
    match_embed,
    match_line,
    signup_buttons,
    signup_embed,
    vote_buttons,
    vote_embed,
)
lazy from .models import TOURNAMENT_TABLES, DraftKind, MatchVote, TeamMode, Tournament, TournamentMatch, TournamentStatus
lazy from .service import (
    Refusal,
    active_tournament,
    add_to_team,
    advance,
    cancel,
    cast,
    choices_of,
    create_team,
    draft,
    drafts_of,
    matches_of,
    open_vote,
    players_of,
    remove_from_team,
    report,
    roster,
    sign_up,
    start,
    teams_of,
    withdraw,
)


if TYPE_CHECKING:
    lazy from wd_discord import AnyInteraction, AutocompleteInteraction, CommandInteraction, ComponentInteraction
    lazy from wd_discord.components import ActionRow
    lazy from wd_discord.embed import Embed


MAX_NAME_LENGTH = 100
MAX_TEAM_SIZE = 25


def is_organiser(interaction: AnyInteraction, tournament: Tournament) -> bool:
    """Whether the invoker runs ``tournament``: they created it, or they may manage the server."""
    user = interaction.user
    return (user is not None and int(user.id) == tournament.organiser_id) or member_has(interaction, Permissions.MANAGE_GUILD)


def team_names(session: Session, tournament_id: int) -> dict[int, str]:
    """Return each team's name by its ID."""
    return {team.id: team.name for team in teams_of(session, tournament_id) if team.id is not None}


class Tournaments(
    GroupCog,
    name="tournament",
    description="Run a team tournament: sign-up, a bracket, drafts and votes",
    contexts=[InteractionContextType.GUILD],
):
    """Runs one tournament per guild: players sign up, teams form, and a single-elimination bracket plays out."""

    rng = Random()  # noqa: S311 - drawing teams and seeds isn't cryptography
    """Draws the teams and seeds; tests replace it with a seeded one."""

    @override
    async def load(self) -> None:
        """Create the tournament tables if missing."""
        self.create_tables(*TOURNAMENT_TABLES)

    async def _active(self, interaction: AnyInteraction, session: Session) -> Tournament | None:
        """Return the guild's running or signing-up tournament; tell the invoker when there's none."""
        guild = interaction.guild
        tournament = None if guild is None else active_tournament(session, int(guild.id))
        if tournament is None:
            await interaction.respond(f"There's no tournament here; {self.mention(self.create)} starts one.", ephemeral=True)
        return tournament

    async def _organiser(self, interaction: AnyInteraction, tournament: Tournament) -> bool:
        """Whether the invoker runs ``tournament``; tells them otherwise."""
        if is_organiser(interaction, tournament):
            return True
        await interaction.respond(
            "Only the tournament's organiser, or someone who can manage the server, can do that.",
            ephemeral=True,
        )
        return False

    async def _done(self, interaction: AnyInteraction, session: Session, refusal: Refusal, success: str) -> bool:
        """Commit and answer ``success``, or answer ``refusal`` and drop the changes; return whether it was done."""
        if refusal is not None:
            session.rollback()
            await interaction.respond(refusal, ephemeral=True)
            return False
        session.commit()
        await interaction.respond(success, ephemeral=True)
        return True

    @staticmethod
    def _user_id(interaction: AnyInteraction) -> int:
        user = interaction.user
        if user is None:
            msg = "Guild interactions always have a user"
            raise ValueError(msg)
        return int(user.id)

    # --- Sign-up ---------------------------------------------------------------------------------------------------

    def _signup_card(self, session: Session, tournament: Tournament) -> tuple[Embed, list[ActionRow]]:
        """Return the tournament's sign-up card and its buttons, as they are now."""
        tournament_id = tournament.id or 0
        rosters = {team.name: roster(session, team.id) for team in teams_of(session, tournament_id) if team.id is not None}
        solo = [player.user_id for player in players_of(session, tournament_id)]
        buttons = (
            signup_buttons(self.join_button, self.leave_button, tournament)
            if tournament.status is TournamentStatus.SIGNUP
            else []
        )
        return signup_embed(tournament, rosters, solo), buttons

    @Cog.command(name="create", description="Open sign-up for a tournament in this channel")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def create(self, interaction: CommandInteraction, name: str, team_size: int, captains: bool = False) -> None:  # noqa: FBT001, FBT002 - a command option
        """Open a tournament: solo sign-up into drawn teams of ``team_size``, or teams registered by ``captains``.

        Needs MANAGE_GUILD; the creator organises it.
        """
        guild, channel = interaction.guild, interaction.channel
        if guild is None or channel is None or not member_has(interaction, Permissions.MANAGE_GUILD):
            await interaction.respond("You need the Manage Server permission to open a tournament.", ephemeral=True)
            return
        if not (0 < len(name) <= MAX_NAME_LENGTH and 0 < team_size <= MAX_TEAM_SIZE):
            await interaction.respond(
                f"Give a name under {MAX_NAME_LENGTH} characters and a team size from 1 to {MAX_TEAM_SIZE}.",
                ephemeral=True,
            )
            return
        with Session(self.bind) as session:
            if active_tournament(session, int(guild.id)) is not None:
                await interaction.respond(
                    f"This server has a tournament going; {self.mention(self.cancel_tournament)} ends it.",
                    ephemeral=True,
                )
                return
            tournament = Tournament(
                guild_id=int(guild.id),
                channel_id=int(channel.id),
                organiser_id=self._user_id(interaction),
                name=name,
                mode=TeamMode.CAPTAINS if captains else TeamMode.SOLO,
                team_size=team_size,
            )
            session.add(tournament)
            session.commit()
            session.refresh(tournament)
            embed, buttons = self._signup_card(session, tournament)
        await interaction.respond(embeds=[embed], components=buttons)

    @Cog.command(name="join", description="Sign up for this server's tournament")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def join(self, interaction: CommandInteraction) -> None:
        """Sign the invoker up for the guild's solo tournament."""
        with Session(self.bind) as session:
            if (tournament := await self._active(interaction, session)) is None:
                return
            await self._done(
                interaction,
                session,
                sign_up(session, tournament, self._user_id(interaction)),
                "You're signed up!",
            )

    @Cog.command(name="leave", description="Withdraw from this server's tournament before it starts")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def leave(self, interaction: CommandInteraction) -> None:
        """Take the invoker out of the tournament; a captain leaving disbands their team."""
        with Session(self.bind) as session:
            if (tournament := await self._active(interaction, session)) is None:
                return
            await self._done(
                interaction,
                session,
                withdraw(session, tournament, self._user_id(interaction)),
                "You've left the tournament.",
            )

    @Cog.component("tourney-join")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def join_button(self, interaction: ComponentInteraction, tournament_id: str) -> None:
        """Sign the clicker up, then refresh the sign-up card."""
        await self._signup_click(interaction, tournament_id, join=True)

    @Cog.component("tourney-leave")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def leave_button(self, interaction: ComponentInteraction, tournament_id: str) -> None:
        """Take the clicker out, then refresh the sign-up card."""
        await self._signup_click(interaction, tournament_id, join=False)

    async def _signup_click(self, interaction: ComponentInteraction, tournament_id: str, *, join: bool) -> None:
        with Session(self.bind) as session:
            tournament = session.get(Tournament, int(tournament_id))
            if tournament is None:
                await interaction.respond("This tournament is gone.", ephemeral=True)
                return
            user_id = self._user_id(interaction)
            refusal = sign_up(session, tournament, user_id) if join else withdraw(session, tournament, user_id)
            if refusal is not None:
                await interaction.respond(refusal, ephemeral=True)
                return
            session.commit()
            embed, buttons = self._signup_card(session, tournament)
        await interaction.update(embeds=[embed], components=buttons)

    @Cog.command(name="team-create", description="Register a team for this server's tournament, as its captain")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def team_create(self, interaction: CommandInteraction, name: str) -> None:
        """Register the team ``name`` captained by the invoker."""
        if not 0 < len(name) <= MAX_NAME_LENGTH:
            await interaction.respond(f"Keep the team name under {MAX_NAME_LENGTH} characters.", ephemeral=True)
            return
        with Session(self.bind) as session:
            if (tournament := await self._active(interaction, session)) is None:
                return
            refusal = create_team(session, tournament, self._user_id(interaction), name)
            success = f"Team **{name}** is registered; add players with {self.mention(self.team_add)}."
            await self._done(interaction, session, refusal, success)

    @Cog.command(name="team-add", description="Add a player to the team you captain")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def team_add(self, interaction: CommandInteraction, player: User) -> None:
        """Add ``player`` to the invoker's team."""
        with Session(self.bind) as session:
            if (tournament := await self._active(interaction, session)) is None:
                return
            refusal = add_to_team(session, tournament, self._user_id(interaction), int(player.id))
            await self._done(interaction, session, refusal, f"Added {player.mention} to your team.")

    @Cog.command(name="team-remove", description="Remove a player from the team you captain")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def team_remove(self, interaction: CommandInteraction, player: User) -> None:
        """Remove ``player`` from the invoker's team."""
        with Session(self.bind) as session:
            if (tournament := await self._active(interaction, session)) is None:
                return
            refusal = remove_from_team(session, tournament, self._user_id(interaction), int(player.id))
            await self._done(interaction, session, refusal, f"Removed {player.mention} from your team.")

    # --- Running it ------------------------------------------------------------------------------------------------

    @Cog.command(name="start", description="Close sign-up, form the teams and draw the bracket")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def start_tournament(self, interaction: CommandInteraction) -> None:
        """Start the tournament and show its bracket; organisers only."""
        with Session(self.bind) as session:
            if (tournament := await self._active(interaction, session)) is None or not await self._organiser(
                interaction,
                tournament,
            ):
                return
            refusal = start(session, tournament, self.rng)
            if refusal is not None:
                session.rollback()
                await interaction.respond(refusal, ephemeral=True)
                return
            session.commit()
            embed = bracket_embed(tournament, matches_of(session, tournament.id or 0), team_names(session, tournament.id or 0))
        await interaction.respond(
            f"**{tournament.name}** has started! {self.mention(self.match_card)} shows a match.",
            embeds=[embed],
        )

    @Cog.command(name="bracket", description="Show the tournament's bracket")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def bracket(self, interaction: CommandInteraction) -> None:
        """Show the bracket, or the sign-up card before the tournament starts."""
        with Session(self.bind) as session:
            if (tournament := await self._active(interaction, session)) is None:
                return
            if tournament.status is TournamentStatus.SIGNUP:
                embed, _ = self._signup_card(session, tournament)
            else:
                embed = bracket_embed(
                    tournament,
                    matches_of(session, tournament.id or 0),
                    team_names(session, tournament.id or 0),
                )
        await interaction.respond(embeds=[embed])

    @Cog.command(name="cancel", description="Call off this server's tournament")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def cancel_tournament(self, interaction: CommandInteraction) -> None:
        """Cancel the tournament; organisers only."""
        with Session(self.bind) as session:
            if (tournament := await self._active(interaction, session)) is None or not await self._organiser(
                interaction,
                tournament,
            ):
                return
            cancel(session, tournament)
            session.commit()
            name = tournament.name
        await interaction.respond(f"**{name}** is called off.")

    # --- Matches ---------------------------------------------------------------------------------------------------

    async def _match(
        self,
        interaction: AnyInteraction,
        session: Session,
        match_id: int,
    ) -> tuple[Tournament, TournamentMatch] | None:
        """Return the guild's running tournament and its match ``match_id``; tell the invoker when there's no such match."""
        tournament = await self._active(interaction, session)
        if tournament is None:
            return None
        match = session.get(TournamentMatch, match_id)
        if match is None or match.tournament_id != tournament.id:
            await interaction.respond(
                f"This tournament has no match #{match_id}; {self.mention(self.bracket)} lists them.",
                ephemeral=True,
            )
            return None
        return tournament, match

    def _match_card(self, session: Session, tournament: Tournament, match: TournamentMatch) -> tuple[Embed, list[ActionRow]]:
        """Return the match's card and its controls, as they are now."""
        tournament_id = tournament.id or 0
        names = team_names(session, tournament_id)
        rosters = {team: roster(session, team) for team in (match.team_a_id, match.team_b_id) if team is not None}
        embed = match_embed(match, round_count(len(names)), names, rosters, drafts_of(session, match.id or 0))
        return embed, match_buttons(self.match_control, match, names)

    @Cog.command(name="match", description="Show a match's card, with the organiser's controls")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def match_card(self, interaction: CommandInteraction, match: int) -> None:
        """Post the card of match ``match``."""
        with Session(self.bind) as session:
            if (found := await self._match(interaction, session, match)) is None:
                return
            embed, buttons = self._match_card(session, *found)
        await interaction.respond(embeds=[embed], components=buttons)

    @Cog.component("tourney-match")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def match_control(self, interaction: ComponentInteraction, match_id: str, action: str, team_id: str = "") -> None:
        """Move a match to its next phase, report its winner, or record a forfeit; organisers only."""
        with Session(self.bind) as session:
            match = session.get(TournamentMatch, int(match_id))
            tournament = None if match is None else session.get(Tournament, match.tournament_id)
            if match is None or tournament is None or tournament.status is not TournamentStatus.RUNNING:
                await interaction.respond("This match's tournament isn't running any more.", ephemeral=True)
                return
            if not await self._organiser(interaction, tournament):
                return
            if action == "next":
                refusal = advance(session, match)
            else:
                team = int(team_id)
                other = match.team_b_id if team == match.team_a_id else match.team_a_id
                winner = team if action == "win" else other
                refusal = (
                    "That team doesn't play this match."
                    if winner is None
                    else report(session, tournament, match, winner, forfeit=action == "forfeit")
                )
            if refusal is not None:
                session.rollback()
                await interaction.respond(refusal, ephemeral=True)
                return
            session.commit()
            embed, buttons = self._match_card(session, tournament, match)
            finished = tournament.status is TournamentStatus.FINISHED
            final = bracket_embed(tournament, matches_of(session, tournament.id or 0), team_names(session, tournament.id or 0))
        await interaction.update(embeds=[embed], components=buttons)
        if finished:
            await interaction.followup(f"🏆 **{tournament.name}** is over!", embeds=[final])

    async def _draft(self, interaction: CommandInteraction, match: int, choice: str, kind: DraftKind) -> None:
        with Session(self.bind) as session:
            if (found := await self._match(interaction, session, match)) is None:
                return
            refusal = draft(session, found[1], self._user_id(interaction), kind, choice)
            verb = "banned" if kind is DraftKind.BAN else "picked"
            await self._done(interaction, session, refusal, f"Your team {verb} **{choice}** in match #{match}.")

    @Cog.command(name="ban", description="Ban something from your match, as your team's captain")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def ban(self, interaction: CommandInteraction, match: int, choice: str) -> None:
        """Record the invoker's team banning ``choice`` in ``match``."""
        await self._draft(interaction, match, choice, DraftKind.BAN)

    @Cog.command(name="pick", description="Pick something for your match, as your team's captain")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def pick(self, interaction: CommandInteraction, match: int, choice: str) -> None:
        """Record the invoker's team picking ``choice`` in ``match``."""
        await self._draft(interaction, match, choice, DraftKind.PICK)

    # --- Votes -----------------------------------------------------------------------------------------------------

    @Cog.command(name="vote", description="Let a match's players vote, e.g. on a map; answers separated by commas")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def vote(self, interaction: CommandInteraction, match: int, question: str, answers: str) -> None:
        """Post a vote on ``question`` for the players of ``match``; organisers only."""
        with Session(self.bind) as session:
            if (found := await self._match(interaction, session, match)) is None or not await self._organiser(
                interaction,
                found[0],
            ):
                return
            opened = open_vote(session, found[1], question[:200], parse_options(answers))
            if isinstance(opened, str):
                session.rollback()
                await interaction.respond(opened, ephemeral=True)
                return
            session.commit()
            session.refresh(opened)
            embed, buttons = vote_embed(opened, []), vote_buttons(self.vote_button, self.close_vote_button, opened)
        await interaction.respond(embeds=[embed], components=buttons)

    @vote.autocomplete("match")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    @pick.autocomplete("match")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    @ban.autocomplete("match")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    @match_card.autocomplete("match")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def match_choices(self, interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]:
        """Suggest the tournament's undecided matches whose line contains what was typed."""
        guild = interaction.guild
        with Session(self.bind) as session:
            tournament = None if guild is None else active_tournament(session, int(guild.id))
            if tournament is None:
                return []
            names = team_names(session, tournament.id or 0)
            matches = [
                match for match in matches_of(session, tournament.id or 0) if not match.phase.decided and match.id is not None
            ]
        lines = ((match, match_line(match, names).replace("`", "")) for match in matches)
        return [
            ApplicationCommandOptionChoice(name=line[:100], value=match.id or 0)
            for match, line in lines
            if current.casefold() in line.casefold()
        ]

    @Cog.component("tourney-vote")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def vote_button(self, interaction: ComponentInteraction, vote_id: str, choice: str) -> None:
        """Record the clicker's answer, then refresh the tally."""
        with Session(self.bind) as session:
            vote = session.get(MatchVote, int(vote_id))
            if vote is None:
                await interaction.respond("This vote is gone.", ephemeral=True)
                return
            refusal = cast(session, vote, self._user_id(interaction), int(choice))
            if refusal is not None:
                await interaction.respond(refusal, ephemeral=True)
                return
            session.commit()
            embed = vote_embed(vote, choices_of(session, int(vote_id)))
            buttons = vote_buttons(self.vote_button, self.close_vote_button, vote)
        await interaction.update(embeds=[embed], components=buttons)

    @Cog.component("tourney-close")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def close_vote_button(self, interaction: ComponentInteraction, vote_id: str) -> None:
        """Close the vote and show the final tally; organisers only."""
        with Session(self.bind) as session:
            vote = session.get(MatchVote, int(vote_id))
            match = None if vote is None else session.get(TournamentMatch, vote.match_id)
            tournament = None if match is None else session.get(Tournament, match.tournament_id)
            if vote is None or tournament is None:
                await interaction.respond("This vote is gone.", ephemeral=True)
                return
            if not await self._organiser(interaction, tournament):
                return
            vote.open = False
            session.add(vote)
            session.commit()
            embed = vote_embed(vote, choices_of(session, int(vote_id)))
        await interaction.update(embeds=[embed], components=[])
