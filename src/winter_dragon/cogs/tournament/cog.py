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
lazy from wd_errors import Refused

lazy from winter_dragon.config import CogConfig
lazy from winter_dragon.ui import ChangedEmbed, CreatedEmbed, DeletedEmbed

lazy from .bracket import parse_options, round_count
lazy from .cards import (
    MatchAction,
    bracket_embed,
    match_buttons,
    match_embed,
    match_line,
    participants_embed,
    signup_buttons,
    signup_embed,
    vote_buttons,
    vote_embed,
)
lazy from .models import TOURNAMENT_TABLES, DraftKind, MatchVote, TeamMode, Tournament, TournamentMatch, TournamentStatus
lazy from .service import (
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
    lazy from wd_discord import (
        AnyGuildInteraction,
        AutocompleteInteraction,
        GuildCommandInteraction,
        GuildComponentInteraction,
    )
    lazy from wd_discord.components import ActionRow
    lazy from wd_discord.embed import Embed


class TournamentSettings:
    """Settings for /tournament, in its ``cogs.ini`` section."""

    max_name_length = CogConfig(100)
    """The longest tournament or team name accepted."""
    max_team_size = CogConfig(25)
    """The most players one team may have."""


def is_organiser(interaction: AnyGuildInteraction, tournament: Tournament) -> bool:
    """Whether the invoker runs ``tournament``: they created it, or they may manage the server."""
    return int(interaction.user.id) == tournament.organiser_id or member_has(interaction, Permissions.MANAGE_GUILD)


def require_organiser(interaction: AnyGuildInteraction, tournament: Tournament) -> None:
    """Refuse unless the invoker runs ``tournament``."""
    if not is_organiser(interaction, tournament):
        msg = "Only the tournament's organiser, or someone who can manage the server, can do that."
        raise Refused(msg)


def stored[M](session: Session, model: type[M], record_id: int, gone: str) -> M:
    """Return the ``model`` stored as ``record_id``; refuse with ``gone`` when there's none."""
    record = session.get(model, record_id)
    if record is None:
        raise Refused(gone)
    return record


def team_names(session: Session, tournament_id: int) -> dict[int, str]:
    """Return each team's name by its ID."""
    return {team.id: team.name for team in teams_of(session, tournament_id) if team.id is not None}


def play(session: Session, tournament: Tournament, match: TournamentMatch, action: MatchAction, team_id: str) -> None:
    """Do what the organiser's button ``action`` under the match card says, for the team ``team_id`` if it names one."""
    if action is MatchAction.NEXT:
        advance(session, match)
        return
    team = int(team_id)
    other = match.team_b_id if team == match.team_a_id else match.team_a_id
    winner = team if action is MatchAction.WIN else other
    if winner is None:
        msg = "That team doesn't play this match."
        raise Refused(msg)
    report(session, tournament, match, winner, forfeit=action is MatchAction.FORFEIT)


class Tournaments(
    GroupCog,
    name="tournament",
    description="Run a team tournament: sign-up, a bracket, drafts and votes",
    contexts=[InteractionContextType.GUILD],
):
    """Runs one tournament per guild: players sign up, teams form, and a single-elimination bracket plays out.

    Every action refuses with :class:`~wd_errors.Refused` from inside its session, which drops the session's changes.
    """

    rng = Random()  # noqa: S311 - drawing teams and seeds isn't cryptography
    """Draws the teams and seeds; tests replace it with a seeded one."""

    @override
    async def load(self) -> None:
        """Create the tournament tables if missing."""
        self.create_tables(*TOURNAMENT_TABLES)

    def _active(self, interaction: AnyGuildInteraction, session: Session) -> Tournament:
        """Return the guild's running or signing-up tournament; refuse when there's none."""
        tournament = active_tournament(session, int(interaction.guild_id))
        if tournament is None:
            msg = f"There's no tournament here; {self.mention(self.create)} starts one."
            raise Refused(msg)
        return tournament

    # --- Sign-up ---------------------------------------------------------------------------------------------------

    @staticmethod
    def _participants(session: Session, tournament: Tournament) -> tuple[dict[str, list[int]], list[int]]:
        """Return each team's players by team name, and the players signed up alone."""
        tournament_id = tournament.id or 0
        rosters = {team.name: roster(session, team.id) for team in teams_of(session, tournament_id) if team.id is not None}
        solo = [player.user_id for player in players_of(session, tournament_id)]
        return rosters, solo

    def _signup_card(self, session: Session, tournament: Tournament) -> tuple[Embed, list[ActionRow]]:
        """Return the tournament's sign-up card and its buttons, as they are now."""
        rosters, solo = self._participants(session, tournament)
        buttons = (
            signup_buttons(self.join_button, self.leave_button, self.participants_button, tournament)
            if tournament.status is TournamentStatus.SIGNUP
            else []
        )
        embed = signup_embed(
            tournament,
            rosters,
            solo,
            team_create=self.mention(self.team_create),
            team_add=self.mention(self.team_add),
        )
        return embed, buttons

    @Cog.command(  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
        name="create",
        description="Open sign-up for a tournament in this channel",
        requires=Permissions.MANAGE_GUILD,
    )
    async def create(self, interaction: GuildCommandInteraction, name: str, team_size: int, captains: bool = False) -> None:  # noqa: FBT001, FBT002 - a command option
        """Open a tournament: solo sign-up into drawn teams of ``team_size``, or teams registered by ``captains``.

        The creator organises it.
        """
        max_name, max_size = TournamentSettings.max_name_length, TournamentSettings.max_team_size
        if not (0 < len(name) <= max_name and 0 < team_size <= max_size):
            msg = f"Give a name under {max_name} characters and a team size from 1 to {max_size}."
            raise Refused(msg)
        with Session(self.bind) as session:
            if active_tournament(session, int(interaction.guild_id)) is not None:
                msg = f"This server has a tournament going; {self.mention(self.cancel_tournament)} ends it."
                raise Refused(msg)
            tournament = Tournament(
                guild_id=int(interaction.guild_id),
                channel_id=int(interaction.channel.id),
                organiser_id=int(interaction.user.id),
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
    async def join(self, interaction: GuildCommandInteraction) -> None:
        """Sign the invoker up for the guild's solo tournament."""
        with Session(self.bind) as session:
            sign_up(session, self._active(interaction, session), int(interaction.user.id))
            session.commit()
        await interaction.respond("You're signed up!", ephemeral=True)

    @Cog.command(name="leave", description="Withdraw from this server's tournament before it starts")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def leave(self, interaction: GuildCommandInteraction) -> None:
        """Take the invoker out of the tournament; a captain leaving disbands their team."""
        with Session(self.bind) as session:
            withdraw(session, self._active(interaction, session), int(interaction.user.id))
            session.commit()
        await interaction.respond("You've left the tournament.", ephemeral=True)

    @Cog.component("tourney-join")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def join_button(self, interaction: GuildComponentInteraction, tournament_id: str) -> None:
        """Sign the clicker up, then refresh the sign-up card."""
        await self._signup_click(interaction, tournament_id, join=True)

    @Cog.component("tourney-leave")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def leave_button(self, interaction: GuildComponentInteraction, tournament_id: str) -> None:
        """Take the clicker out, then refresh the sign-up card."""
        await self._signup_click(interaction, tournament_id, join=False)

    @Cog.component("tourney-participants")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def participants_button(self, interaction: GuildComponentInteraction, tournament_id: str) -> None:
        """Show the clicker, and only them, everyone signed up so far."""
        with Session(self.bind) as session:
            tournament = stored(session, Tournament, int(tournament_id), "This tournament is gone.")
            rosters, solo = self._participants(session, tournament)
            embed = participants_embed(tournament, rosters, solo)
        await interaction.respond(embeds=[embed], ephemeral=True)

    async def _signup_click(self, interaction: GuildComponentInteraction, tournament_id: str, *, join: bool) -> None:
        with Session(self.bind) as session:
            tournament = stored(session, Tournament, int(tournament_id), "This tournament is gone.")
            user_id = int(interaction.user.id)
            if join:
                sign_up(session, tournament, user_id)
            else:
                withdraw(session, tournament, user_id)
            session.commit()
            embed, buttons = self._signup_card(session, tournament)
        await interaction.update(embeds=[embed], components=buttons)

    @Cog.command(name="team-create", description="Register a team for this server's tournament, as its captain")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def team_create(self, interaction: GuildCommandInteraction, name: str) -> None:
        """Register the team ``name`` captained by the invoker."""
        if not 0 < len(name) <= TournamentSettings.max_name_length:
            msg = f"Keep the team name under {TournamentSettings.max_name_length} characters."
            raise Refused(msg)
        with Session(self.bind) as session:
            create_team(session, self._active(interaction, session), int(interaction.user.id), name)
            session.commit()
        message = f"Team **{name}** is registered; add players with {self.mention(self.team_add)}."
        await interaction.respond(embeds=[CreatedEmbed(description=message)], ephemeral=True)

    @Cog.command(name="team-add", description="Add a player to the team you captain")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def team_add(self, interaction: GuildCommandInteraction, player: User) -> None:
        """Add ``player`` to the invoker's team."""
        with Session(self.bind) as session:
            add_to_team(session, self._active(interaction, session), int(interaction.user.id), int(player.id))
            session.commit()
        await interaction.respond(embeds=[ChangedEmbed(description=f"Added {player.mention} to your team.")], ephemeral=True)

    @Cog.command(name="team-remove", description="Remove a player from the team you captain")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def team_remove(self, interaction: GuildCommandInteraction, player: User) -> None:
        """Remove ``player`` from the invoker's team."""
        with Session(self.bind) as session:
            remove_from_team(session, self._active(interaction, session), int(interaction.user.id), int(player.id))
            session.commit()
        message = f"Removed {player.mention} from your team."
        await interaction.respond(embeds=[ChangedEmbed(description=message)], ephemeral=True)

    # --- Running it ------------------------------------------------------------------------------------------------

    @Cog.command(name="start", description="Close sign-up, form the teams and draw the bracket")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def start_tournament(self, interaction: GuildCommandInteraction) -> None:
        """Start the tournament and show its bracket; organisers only."""
        with Session(self.bind) as session:
            tournament = self._active(interaction, session)
            require_organiser(interaction, tournament)
            start(session, tournament, self.rng)
            session.commit()
            embed = bracket_embed(tournament, matches_of(session, tournament.id or 0), team_names(session, tournament.id or 0))
        await interaction.respond(
            f"**{tournament.name}** has started! {self.mention(self.match_card)} shows a match.",
            embeds=[embed],
        )

    @Cog.command(name="bracket", description="Show the tournament's bracket")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def bracket(self, interaction: GuildCommandInteraction) -> None:
        """Show the bracket, or the sign-up card before the tournament starts."""
        with Session(self.bind) as session:
            tournament = self._active(interaction, session)
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
    async def cancel_tournament(self, interaction: GuildCommandInteraction) -> None:
        """Cancel the tournament; organisers only."""
        with Session(self.bind) as session:
            tournament = self._active(interaction, session)
            require_organiser(interaction, tournament)
            cancel(session, tournament)
            session.commit()
            name = tournament.name
        await interaction.respond(embeds=[DeletedEmbed(description=f"**{name}** is called off.")])

    # --- Matches ---------------------------------------------------------------------------------------------------

    def _match(self, interaction: AnyGuildInteraction, session: Session, match_id: int) -> tuple[Tournament, TournamentMatch]:
        """Return the guild's running tournament and its match ``match_id``; refuse when there's no such match."""
        tournament = self._active(interaction, session)
        match = session.get(TournamentMatch, match_id)
        if match is None or match.tournament_id != tournament.id:
            msg = f"This tournament has no match #{match_id}; {self.mention(self.bracket)} lists them."
            raise Refused(msg)
        return tournament, match

    @staticmethod
    def _running_match(session: Session, match_id: int) -> tuple[Tournament, TournamentMatch]:
        """Return the match ``match_id`` and its tournament; refuse unless that tournament is running."""
        match = session.get(TournamentMatch, match_id)
        tournament = None if match is None else session.get(Tournament, match.tournament_id)
        if match is None or tournament is None or tournament.status is not TournamentStatus.RUNNING:
            msg = "This match's tournament isn't running any more."
            raise Refused(msg)
        return tournament, match

    def _match_card(self, session: Session, tournament: Tournament, match: TournamentMatch) -> tuple[Embed, list[ActionRow]]:
        """Return the match's card and its controls, as they are now."""
        tournament_id = tournament.id or 0
        names = team_names(session, tournament_id)
        rosters = {team: roster(session, team) for team in (match.team_a_id, match.team_b_id) if team is not None}
        embed = match_embed(match, round_count(len(names)), names, rosters, drafts_of(session, match.id or 0))
        return embed, match_buttons(self.match_control, match, names)

    @Cog.command(name="match", description="Show a match's card, with the organiser's controls")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def match_card(self, interaction: GuildCommandInteraction, match: int) -> None:
        """Post the card of match ``match``."""
        with Session(self.bind) as session:
            embed, buttons = self._match_card(session, *self._match(interaction, session, match))
        await interaction.respond(embeds=[embed], components=buttons)

    @Cog.component("tourney-match")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def match_control(
        self,
        interaction: GuildComponentInteraction,
        match_id: str,
        action: str,
        team_id: str = "",
    ) -> None:
        """Move a match to its next phase, report its winner, or record a forfeit; organisers only."""
        with Session(self.bind) as session:
            tournament, match = self._running_match(session, int(match_id))
            require_organiser(interaction, tournament)
            play(session, tournament, match, MatchAction(action), team_id)
            session.commit()
            embed, buttons = self._match_card(session, tournament, match)
            finished = tournament.status is TournamentStatus.FINISHED
            final = bracket_embed(tournament, matches_of(session, tournament.id or 0), team_names(session, tournament.id or 0))
        await interaction.update(embeds=[embed], components=buttons)
        if finished:
            await interaction.followup(f"🏆 **{tournament.name}** is over!", embeds=[final])

    async def _draft(self, interaction: GuildCommandInteraction, match: int, choice: str, kind: DraftKind) -> None:
        with Session(self.bind) as session:
            _, found = self._match(interaction, session, match)
            draft(session, found, int(interaction.user.id), kind, choice)
            session.commit()
        verb = "banned" if kind is DraftKind.BAN else "picked"
        await interaction.respond(f"Your team {verb} **{choice}** in match #{match}.", ephemeral=True)

    @Cog.command(name="ban", description="Ban something from your match, as your team's captain")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def ban(self, interaction: GuildCommandInteraction, match: int, choice: str) -> None:
        """Record the invoker's team banning ``choice`` in ``match``."""
        await self._draft(interaction, match, choice, DraftKind.BAN)

    @Cog.command(name="pick", description="Pick something for your match, as your team's captain")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def pick(self, interaction: GuildCommandInteraction, match: int, choice: str) -> None:
        """Record the invoker's team picking ``choice`` in ``match``."""
        await self._draft(interaction, match, choice, DraftKind.PICK)

    # --- Votes -----------------------------------------------------------------------------------------------------

    @Cog.command(name="vote", description="Let a match's players vote, e.g. on a map; answers separated by commas")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def vote(self, interaction: GuildCommandInteraction, match: int, question: str, answers: str) -> None:
        """Post a vote on ``question`` for the players of ``match``; organisers only."""
        with Session(self.bind) as session:
            tournament, found = self._match(interaction, session, match)
            require_organiser(interaction, tournament)
            opened = open_vote(session, found, question[:200], parse_options(answers))
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
    async def vote_button(self, interaction: GuildComponentInteraction, vote_id: str, choice: str) -> None:
        """Record the clicker's answer, then refresh the tally."""
        with Session(self.bind) as session:
            vote = stored(session, MatchVote, int(vote_id), "This vote is gone.")
            cast(session, vote, int(interaction.user.id), int(choice))
            session.commit()
            embed = vote_embed(vote, choices_of(session, int(vote_id)))
            buttons = vote_buttons(self.vote_button, self.close_vote_button, vote)
        await interaction.update(embeds=[embed], components=buttons)

    @Cog.component("tourney-close")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def close_vote_button(self, interaction: GuildComponentInteraction, vote_id: str) -> None:
        """Close the vote and show the final tally; organisers only."""
        with Session(self.bind) as session:
            vote = stored(session, MatchVote, int(vote_id), "This vote is gone.")
            match = stored(session, TournamentMatch, vote.match_id, "This vote is gone.")
            require_organiser(interaction, stored(session, Tournament, match.tournament_id, "This vote is gone."))
            vote.open = False
            session.add(vote)
            session.commit()
            embed = vote_embed(vote, choices_of(session, int(vote_id)))
        await interaction.update(embeds=[embed], components=[])
