"""The /tournament command group: sign-up, teams, a single-elimination bracket, match cards, drafts and votes."""

from typing import Annotated
lazy from random import Random
lazy from typing import TYPE_CHECKING, override

from sqlmodel import Session
from wd_bot.commands import Describe, Length, Lookup, Range
lazy from wd_bot.checks import member_has
lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_db.extension.lifecycle import alive_by_id

# Command resolves option annotations from module globals at runtime, so User must be available here.
lazy from wd_discord import (
    GuildCommandInteraction,
    GuildComponentInteraction,
    User,
    is_network_error,
)
lazy from wd_discord.interactions import ApplicationCommandOptionChoice, InteractionContextType
lazy from wd_discord.permissions import Permissions
lazy from wd_errors import Refused, unwrap

lazy from winter_dragon.config import CogConfig
lazy from winter_dragon.stored import stored
lazy from winter_dragon.ui import ChangedEmbed, CreatedEmbed, DeletedEmbed

lazy from .bracket import MAX_QUESTION_LENGTH, parse_options, round_count
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
lazy from .models import (
    ACTIVE,
    TOURNAMENT_TABLES,
    DraftKind,
    MatchVote,
    TeamMode,
    Tournament,
    TournamentMatch,
    TournamentStatus,
)
lazy from .service import (
    add_post,
    add_to_team,
    advance,
    cancel,
    cast,
    choices_of,
    create_team,
    draft,
    drafts_of,
    entries_of,
    matches_of,
    open_vote,
    players_of,
    posts_of,
    remove_from_team,
    report,
    roster,
    sign_up,
    start,
    visible_tournaments,
    withdraw,
)


if TYPE_CHECKING:
    lazy from wd_discord import AnyGuildInteraction, AutocompleteInteraction
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


def entry_names(session: Session, tournament_id: int) -> dict[int, str]:
    """Return each team's name by its ID."""
    return {team.id: team.name for team in entries_of(session, tournament_id) if team.id is not None}


def play(session: Session, tournament: Tournament, match: TournamentMatch, action: MatchAction, entry_id: str) -> None:
    """Do what the organiser's button ``action`` under the match card says, for the team ``entry_id`` if it names one."""
    if action is MatchAction.NEXT:
        advance(session, match)
        return
    team = int(entry_id)
    other = match.entry_b_id if team == match.entry_a_id else match.entry_a_id
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
    """Runs tournaments per guild: players sign up, teams form, and a single-elimination bracket plays out.

    A guild can run several at once. Every action refuses with :class:`~wd_errors.Refused` from inside its session,
    which drops the session's changes.
    """

    rng = Random()  # noqa: S311 - drawing teams and seeds isn't cryptography
    """Draws the teams and seeds; tests replace it with a seeded one."""

    @override
    async def load(self) -> None:
        """Create the tournament tables if missing."""
        self.create_tables(*TOURNAMENT_TABLES)

    def _tournament(
        self,
        interaction: AnyGuildInteraction,
        session: Session,
        picked: Tournament,
        *,
        over_ok: bool = False,
    ) -> Tournament:
        """Reload the picked tournament in ``session``; refuse when it's gone, over, or belongs to another server."""
        tournament = stored(session, Tournament, picked.id or 0, "That tournament is gone.")
        if tournament.guild_id != int(interaction.guild_id):
            msg = "That tournament belongs to another server."
            raise Refused(msg)
        if not over_ok and tournament.status not in ACTIVE:
            msg = "That tournament is over."
            raise Refused(msg)
        return tournament

    async def tournament_choices(
        self,
        interaction: AutocompleteInteraction,
        current: str,
    ) -> list[ApplicationCommandOptionChoice]:
        """Suggest the tournaments the invoker can see whose name contains what was typed."""
        guild = interaction.guild
        user = interaction.user
        if guild is None or user is None:
            return []
        channel = interaction.channel
        with Session(self.bind) as session:
            tournaments = list(visible_tournaments(session, guild.id, user.id, None if channel is None else channel.id))
        return [
            Lookup.choice(tournament, tournament.name)
            for tournament in tournaments
            if current.casefold() in tournament.name.casefold()
        ]

    # --- Sign-up ---------------------------------------------------------------------------------------------------

    @staticmethod
    def _participants(session: Session, tournament: Tournament) -> tuple[dict[str, list[int]], list[int]]:
        """Return each team's players by team name, and the players signed up alone."""
        tournament_id = tournament.id or 0
        rosters = {team.name: roster(session, team.id) for team in entries_of(session, tournament_id) if team.id is not None}
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

    def _card(self, session: Session, tournament: Tournament) -> tuple[Embed, list[ActionRow]]:
        """Return what a post shows: the sign-up card while signing up, else the bracket."""
        if tournament.status is TournamentStatus.SIGNUP:
            return self._signup_card(session, tournament)
        embed = bracket_embed(tournament, matches_of(session, tournament.id or 0), entry_names(session, tournament.id or 0))
        return embed, []

    async def _refresh_posts(self, tournament_id: int) -> None:
        """Edit every post of the tournament to show it as it is now; a post that can't be edited is left as it is."""
        with Session(self.bind) as session:
            tournament = stored(session, Tournament, tournament_id, "This tournament is gone.")
            embed, rows = self._card(session, tournament)
            posts = [(post.channel_id, post.message_id) for post in posts_of(session, tournament_id)]
        for channel_id, message_id in posts:
            edited = (
                await self.bot.client.channels.partial(channel_id).message(message_id).edit(embeds=[embed], components=rows)
            )
            if is_network_error(edited):
                self.logger.debug(t"Could not edit tournament post {message_id} in channel {channel_id}: {edited}")

    @Cog.command(
        name="create",
        description="Open sign-up for a tournament, shown in this channel",
        requires=Permissions.MANAGE_GUILD,
    )
    async def create(
        self,
        interaction: GuildCommandInteraction,
        name: Annotated[
            str,
            Describe("The name of the tournament"),
            Length(min_length=1, max_length=TournamentSettings.max_name_length),
        ],
        team_size: Annotated[
            int,
            Describe("The size of each team"),
            Range(min_value=1, max_value=TournamentSettings.max_team_size),
        ] = 1,
        captains: Annotated[bool, Describe("Allow team captains to register entire teams")] = False,  # noqa: FBT002
    ) -> None:
        """Open a tournament: solo sign-up into drawn teams of ``team_size``, or teams registered by ``captains``.

        The creator organises it. The sign-up card is posted in this channel.
        """
        with Session(self.bind) as session:
            tournament = Tournament(
                guild_id=int(interaction.guild_id),
                organiser_id=int(interaction.user.id),
                name=name,
                mode=TeamMode.CAPTAINS if captains else TeamMode.SOLO,
                team_size=team_size,
            )
            session.add(tournament)
            session.flush()
            embed, buttons = self._card(session, tournament)
            sent = unwrap(
                await self.bot.client.channels.partial(interaction.channel.id).send(embeds=[embed], components=buttons),
                "I couldn't post the tournament here.",
            )
            add_post(session, tournament, interaction.channel.id, sent.id)
            session.commit()
            tournament_name = tournament.name
        await interaction.respond(
            embeds=[CreatedEmbed(description=f"**{tournament_name}** is open for sign-up.")],
            ephemeral=True,
        )

    @Cog.command(
        name="post",
        description="Show a tournament in this channel, and keep the post up to date",
        requires=Permissions.MANAGE_MESSAGES,
    )
    async def post_tournament(
        self,
        interaction: GuildCommandInteraction,
        tournament: Annotated[Tournament, Lookup(tournament_choices), Describe("The tournament to show here")],
    ) -> None:
        """Post ``tournament`` in this channel; every change to the tournament edits the post."""
        with Session(self.bind) as session:
            found = self._tournament(interaction, session, tournament)
            embed, buttons = self._card(session, found)
            sent = unwrap(
                await self.bot.client.channels.partial(interaction.channel.id).send(embeds=[embed], components=buttons),
                "I couldn't post the tournament here.",
            )
            add_post(session, found, interaction.channel.id, sent.id)
            session.commit()
            tournament_name = found.name
        await interaction.respond(embeds=[CreatedEmbed(description=f"Posted **{tournament_name}** here.")], ephemeral=True)

    @Cog.command(name="join", description="Sign up for a tournament")
    async def join(
        self,
        interaction: GuildCommandInteraction,
        tournament: Annotated[Tournament, Lookup(tournament_choices), Describe("The tournament")],
    ) -> None:
        """Sign the invoker up for the tournament."""
        with Session(self.bind) as session:
            found = self._tournament(interaction, session, tournament)
            sign_up(session, found, interaction.user.id)
            session.commit()
            tournament_id = found.id or 0
        await self._refresh_posts(tournament_id)
        await interaction.respond(embeds=[CreatedEmbed(description="You're signed up!")], ephemeral=True)

    @Cog.command(name="leave", description="Withdraw from a tournament before it starts")
    async def leave(
        self,
        interaction: GuildCommandInteraction,
        tournament: Annotated[Tournament, Lookup(tournament_choices), Describe("The tournament")],
    ) -> None:
        """Take the invoker out of the tournament; a captain leaving disbands their team."""
        with Session(self.bind) as session:
            found = self._tournament(interaction, session, tournament)
            withdraw(session, found, interaction.user.id)
            session.commit()
            tournament_id = found.id or 0
        await self._refresh_posts(tournament_id)
        await interaction.respond(embeds=[DeletedEmbed(description="You've left the tournament.")], ephemeral=True)

    @Cog.component("tourney-join")
    async def join_button(self, interaction: GuildComponentInteraction, tournament_id: str) -> None:
        """Sign the clicker up, then refresh the sign-up card."""
        await self._signup_click(interaction, tournament_id, join=True)

    @Cog.component("tourney-leave")
    async def leave_button(self, interaction: GuildComponentInteraction, tournament_id: str) -> None:
        """Take the clicker out, then refresh the sign-up card."""
        await self._signup_click(interaction, tournament_id, join=False)

    @Cog.component("tourney-participants")
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
            user_id = interaction.user.id
            if join:
                sign_up(session, tournament, user_id)
            else:
                withdraw(session, tournament, user_id)
            session.commit()
            embed, buttons = self._signup_card(session, tournament)
        await interaction.update(embeds=[embed], components=buttons)
        await self._refresh_posts(int(tournament_id))

    @Cog.command(name="team-create", description="Register a team for a tournament, as its captain")
    async def team_create(
        self,
        interaction: GuildCommandInteraction,
        tournament: Annotated[Tournament, Lookup(tournament_choices), Describe("The tournament")],
        name: Annotated[
            str,
            Describe("The name of the team"),
            Length(min_length=1, max_length=TournamentSettings.max_name_length),
        ],
    ) -> None:
        """Register the team ``name`` captained by the invoker."""
        with Session(self.bind) as session:
            found = self._tournament(interaction, session, tournament)
            create_team(session, found, interaction.user.id, name)
            session.commit()
            tournament_id = found.id or 0
        await self._refresh_posts(tournament_id)
        message = f"Team **{name}** is registered; add players with {self.mention(self.team_add)}."
        await interaction.respond(embeds=[CreatedEmbed(description=message)], ephemeral=True)

    @Cog.command(name="team-add", description="Add a player to the team you captain")
    async def team_add(
        self,
        interaction: GuildCommandInteraction,
        tournament: Annotated[Tournament, Lookup(tournament_choices), Describe("The tournament")],
        player: Annotated[User, Describe("The player to add to the team")],
    ) -> None:
        """Add ``player`` to the invoker's team."""
        with Session(self.bind) as session:
            found = self._tournament(interaction, session, tournament)
            add_to_team(session, found, interaction.user.id, player.id)
            session.commit()
            tournament_id = found.id or 0
        await self._refresh_posts(tournament_id)
        await interaction.respond(embeds=[ChangedEmbed(description=f"Added {player.mention} to your team.")], ephemeral=True)

    @Cog.command(name="team-remove", description="Remove a player from the team you captain")
    async def team_remove(
        self,
        interaction: GuildCommandInteraction,
        tournament: Annotated[Tournament, Lookup(tournament_choices), Describe("The tournament")],
        player: Annotated[User, Describe("The player to remove from the team")],
    ) -> None:
        """Remove ``player`` from the invoker's team."""
        with Session(self.bind) as session:
            found = self._tournament(interaction, session, tournament)
            remove_from_team(session, found, interaction.user.id, player.id)
            session.commit()
            tournament_id = found.id or 0
        await self._refresh_posts(tournament_id)
        message = f"Removed {player.mention} from your team."
        await interaction.respond(embeds=[ChangedEmbed(description=message)], ephemeral=True)

    # --- Running it ------------------------------------------------------------------------------------------------

    @Cog.command(name="start", description="Close sign-up, form the teams and draw the bracket")
    async def start_tournament(
        self,
        interaction: GuildCommandInteraction,
        tournament: Annotated[Tournament, Lookup(tournament_choices), Describe("The tournament")],
    ) -> None:
        """Start the tournament and show its bracket; organisers only."""
        with Session(self.bind) as session:
            found = self._tournament(interaction, session, tournament)
            require_organiser(interaction, found)
            start(session, found, self.rng)
            session.commit()
            tournament_id = found.id or 0
            embed = bracket_embed(found, matches_of(session, tournament_id), entry_names(session, tournament_id))
            tournament_name = found.name
        await self._refresh_posts(tournament_id)
        await interaction.respond(
            f"**{tournament_name}** has started! {self.mention(self.match_card)} shows a match.",
            embeds=[embed],
        )

    @Cog.command(name="bracket", description="Show a tournament's bracket")
    async def bracket(
        self,
        interaction: GuildCommandInteraction,
        tournament: Annotated[Tournament, Lookup(tournament_choices), Describe("The tournament")],
    ) -> None:
        """Show the bracket, or the sign-up card before the tournament starts."""
        with Session(self.bind) as session:
            found = self._tournament(interaction, session, tournament, over_ok=True)
            if found.status is TournamentStatus.SIGNUP:
                embed, _ = self._signup_card(session, found)
            else:
                embed = bracket_embed(
                    found,
                    matches_of(session, found.id or 0),
                    entry_names(session, found.id or 0),
                )
        await interaction.respond(embeds=[embed])

    @Cog.command(name="cancel", description="Call off a tournament")
    async def cancel_tournament(
        self,
        interaction: GuildCommandInteraction,
        tournament: Annotated[Tournament, Lookup(tournament_choices), Describe("The tournament")],
    ) -> None:
        """Cancel the tournament; organisers only."""
        with Session(self.bind) as session:
            found = self._tournament(interaction, session, tournament)
            require_organiser(interaction, found)
            cancel(session, found)
            session.commit()
            tournament_id = found.id or 0
            name = found.name
        await self._refresh_posts(tournament_id)
        await interaction.respond(embeds=[DeletedEmbed(description=f"**{name}** is called off.")])

    # --- Matches ---------------------------------------------------------------------------------------------------

    def _match(self, interaction: AnyGuildInteraction, session: Session, match_id: int) -> tuple[Tournament, TournamentMatch]:
        """Return the match ``match_id`` and its tournament; refuse when there's no such match or the tournament is unusable."""
        match = alive_by_id(session, TournamentMatch, match_id)
        if match is None:
            msg = f"There's no match #{match_id}; {self.mention(self.bracket)} lists them."
            raise Refused(msg)
        tournament = self._tournament(
            interaction,
            session,
            stored(session, Tournament, match.tournament_id, "This match's tournament is gone."),
        )
        return tournament, match

    @staticmethod
    def _running_match(session: Session, match_id: int) -> tuple[Tournament, TournamentMatch]:
        """Return the match ``match_id`` and its tournament; refuse unless that tournament is running."""
        match = alive_by_id(session, TournamentMatch, match_id)
        tournament = None if match is None else alive_by_id(session, Tournament, match.tournament_id)
        if match is None or tournament is None or tournament.status is not TournamentStatus.RUNNING:
            msg = "This match's tournament isn't running any more."
            raise Refused(msg)
        return tournament, match

    def _match_card(self, session: Session, tournament: Tournament, match: TournamentMatch) -> tuple[Embed, list[ActionRow]]:
        """Return the match's card and its controls, as they are now."""
        tournament_id = tournament.id or 0
        names = entry_names(session, tournament_id)
        rosters = {team: roster(session, team) for team in (match.entry_a_id, match.entry_b_id) if team is not None}
        embed = match_embed(match, round_count(len(names)), names, rosters, drafts_of(session, match.id or 0))
        return embed, match_buttons(self.match_control, match, names)

    async def match_choices(self, interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]:
        """Suggest the undecided matches of the tournaments the invoker can see, whose label contains what was typed."""
        guild = interaction.guild
        user = interaction.user
        choices: list[ApplicationCommandOptionChoice] = []
        if guild is None or user is None:
            return choices
        channel = interaction.channel
        with Session(self.bind) as session:
            for tournament in visible_tournaments(session, guild.id, user.id, None if channel is None else channel.id):
                names = entry_names(session, tournament.id or 0)
                for match in matches_of(session, tournament.id or 0):
                    if match.phase.decided or match.id is None:
                        continue
                    label = f"{tournament.name}: {match_line(match, names).replace('`', '')}"
                    if current.casefold() in label.casefold():
                        choices.append(Lookup.choice(match, label))
        return choices

    @Cog.command(name="match", description="Show a match's card, with the organiser's controls")
    async def match_card(
        self,
        interaction: GuildCommandInteraction,
        match: Annotated[TournamentMatch, Lookup(match_choices), Describe("The match to show")],
    ) -> None:
        """Post the card of match ``match``."""
        with Session(self.bind) as session:
            embed, buttons = self._match_card(session, *self._match(interaction, session, match.id or 0))
        await interaction.respond(embeds=[embed], components=buttons)

    @Cog.component("tourney-match")
    async def match_control(
        self,
        interaction: GuildComponentInteraction,
        match_id: str,
        action: str,
        entry_id: str = "",
    ) -> None:
        """Move a match to its next phase, report its winner, or record a forfeit; organisers only."""
        with Session(self.bind) as session:
            tournament, match = self._running_match(session, int(match_id))
            require_organiser(interaction, tournament)
            play(session, tournament, match, MatchAction(action), entry_id)
            session.commit()
            tournament_id = tournament.id or 0
            embed, buttons = self._match_card(session, tournament, match)
            finished = tournament.status is TournamentStatus.FINISHED
            final = bracket_embed(tournament, matches_of(session, tournament_id), entry_names(session, tournament_id))
        await self._refresh_posts(tournament_id)
        await interaction.update(embeds=[embed], components=buttons)
        if finished:
            await interaction.followup(f"🏆 **{tournament.name}** is over!", embeds=[final])

    async def _draft(self, interaction: GuildCommandInteraction, match: int, choice: str, kind: DraftKind) -> None:
        with Session(self.bind) as session:
            _, found = self._match(interaction, session, match)
            draft(session, found, interaction.user.id, kind, choice)
            session.commit()
        verb = "banned" if kind is DraftKind.BAN else "picked"
        drafted = CreatedEmbed(description=f"Your team {verb} **{choice}** in match #{match}.")
        await interaction.respond(embeds=[drafted], ephemeral=True)

    @Cog.command(name="ban", description="Ban something from your match, as your team's captain")
    async def ban(
        self,
        interaction: GuildCommandInteraction,
        match: Annotated[TournamentMatch, Lookup(match_choices), Describe("The match to ban in")],
        choice: Annotated[str, Describe("The item to ban")],
    ) -> None:
        """Record the invoker's team banning ``choice`` in ``match``."""
        await self._draft(interaction, match.id or 0, choice, DraftKind.BAN)

    @Cog.command(name="pick", description="Pick something for your match, as your team's captain")
    async def pick(
        self,
        interaction: GuildCommandInteraction,
        match: Annotated[TournamentMatch, Lookup(match_choices), Describe("The match to pick in")],
        choice: Annotated[str, Describe("The item to pick")],
    ) -> None:
        """Record the invoker's team picking ``choice`` in ``match``."""
        await self._draft(interaction, match.id or 0, choice, DraftKind.PICK)

    # --- Votes -----------------------------------------------------------------------------------------------------

    @Cog.command(name="vote", description="Let a match's players vote, e.g. on a map; answers separated by commas")
    async def vote(
        self,
        interaction: GuildCommandInteraction,
        match: Annotated[TournamentMatch, Lookup(match_choices), Describe("The match to vote in")],
        question: Annotated[str, Describe("The question to vote on"), Length(max_length=MAX_QUESTION_LENGTH)],
        answers: Annotated[str, Describe("The answers to the question, separated by commas")],
    ) -> None:
        """Post a vote on ``question`` for the players of ``match``; organisers only."""
        with Session(self.bind) as session:
            tournament, found = self._match(interaction, session, match.id or 0)
            require_organiser(interaction, tournament)
            opened = open_vote(session, found, question, parse_options(answers))
            session.commit()
            session.refresh(opened)
            embed, buttons = vote_embed(opened, []), vote_buttons(self.vote_button, self.close_vote_button, opened)
        await interaction.respond(embeds=[embed], components=buttons)

    @Cog.component("tourney-vote")
    async def vote_button(self, interaction: GuildComponentInteraction, vote_id: str, choice: str) -> None:
        """Record the clicker's answer, then refresh the tally."""
        with Session(self.bind) as session:
            vote = stored(session, MatchVote, int(vote_id), "This vote is gone.")
            cast(session, vote, interaction.user.id, int(choice))
            session.commit()
            embed = vote_embed(vote, choices_of(session, int(vote_id)))
            buttons = vote_buttons(self.vote_button, self.close_vote_button, vote)
        await interaction.update(embeds=[embed], components=buttons)

    @Cog.component("tourney-close")
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
