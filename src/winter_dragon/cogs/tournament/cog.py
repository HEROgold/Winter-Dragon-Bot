"""The /tournament command group: sign-up, teams, a single-elimination bracket, match cards, drafts and votes."""

from typing import Annotated
lazy from random import Random
lazy from typing import TYPE_CHECKING, override

from sqlmodel import Session
from wd_bot.commands import Describe, Length, Lookup, Range
lazy from wd_bot.checks import member_has
lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_db.extension.lifecycle import DELETED_MEMBER, alive_by_id

# Command resolves option annotations from module globals at runtime, so User must be available here.
lazy from wd_discord import (
    GuildCommandInteraction,
    GuildComponentInteraction,
    User,
    is_network_error,
)
lazy from wd_discord.components import ActionRow, SelectOption, StringSelect, UserSelect
lazy from wd_discord.embed import Embed
lazy from wd_discord.interactions import ApplicationCommandOptionChoice, InteractionContextType
lazy from wd_discord.limits import MAX_EMBED_DESCRIPTION_LENGTH, MAX_SELECT_OPTIONS, truncate
lazy from wd_discord.permissions import Permissions
lazy from wd_discord.snowflake import Snowflake
lazy from wd_errors import Refused, unwrap

lazy from winter_dragon.cogs.team.cog import Teams
lazy from winter_dragon.cogs.team.models import Team, TeamKind
lazy from winter_dragon.cogs.team.service import members_of, teams_of
lazy from winter_dragon.config import CogConfig
lazy from winter_dragon.stored import stored
lazy from winter_dragon.ui import ChangedEmbed, CreatedEmbed, DeletedEmbed, Tone, block, card

lazy from .bracket import MAX_QUESTION_LENGTH, parse_options, round_count
lazy from .cards import (
    MatchAction,
    MatchControls,
    MatchView,
    SignupControls,
    bracket_card,
    bracket_file,
    card_of_match,
    manage_panel,
    match_line,
    participants_card,
    plural,
    signup_card,
    vote_card,
    vote_options,
)
lazy from .models import (
    ACTIVE,
    TOURNAMENT_TABLES,
    DraftKind,
    LineupChange,
    MatchEvent,
    MatchPhase,
    MatchVote,
    TeamMode,
    Tournament,
    TournamentEntry,
    TournamentMatch,
    TournamentStatus,
)
lazy from .service import (
    LineupRequest,
    add_player,
    add_post,
    advance,
    cancel,
    cast,
    change_lineup,
    choices_of,
    clashes,
    close_vote,
    draft,
    drafts_of,
    drop_clash,
    entries_of,
    entry_in_match,
    entry_of_captain,
    lineup,
    match_log,
    matches_of,
    open_vote,
    posts_of,
    remove_player,
    report,
    roster,
    sign_up,
    signups_of,
    start,
    visible_tournaments,
    withdraw,
)
lazy from .service import (
    enter as enter_team,
)


if TYPE_CHECKING:
    lazy from wd_discord import AnyGuildInteraction, AutocompleteInteraction
    lazy from wd_discord.components import Container
    lazy from wd_discord.files import File


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


async def require_server_member(interaction: AnyGuildInteraction, player_id: Snowflake) -> None:
    """Refuse unless ``player_id`` is a member of the invoker's server, the only members who can play in its tournaments."""
    member = await interaction.guild.member(player_id).fetch()
    if is_network_error(member):
        msg = "They aren't in this server, so they can't play in its tournament."
        raise Refused(msg)


def entry_names(session: Session, tournament: Tournament) -> dict[int, str]:
    """Return each team's name by its ID."""
    return {team.id: team.name for team in entries_of(session, tournament) if team.id is not None}


def captained_entry(session: Session, tournament: Tournament, captain_id: Snowflake) -> TournamentEntry:
    """Return the entry whose team ``captain_id`` captains in ``tournament``; refuse when there's none."""
    entry = entry_of_captain(session, tournament, captain_id)
    if entry is None:
        msg = "You don't captain an entry in this tournament."
        raise Refused(msg)
    return entry


def play(
    session: Session,
    match: TournamentMatch,
    action: MatchAction,
    entry_id: str,
    actor_id: Snowflake,
) -> None:
    """Do what the organiser's button ``action`` under the match card says, for the team ``entry_id`` if it names one."""
    if action is MatchAction.NEXT:
        advance(session, match, actor_id)
        return
    team = int(entry_id)
    other = match.entry_b_id if team == match.entry_a_id else match.entry_a_id
    winner = team if action is MatchAction.WIN else other
    if winner is None:
        msg = "That team doesn't play this match."
        raise Refused(msg)
    report(session, match, winner, actor_id, forfeit=action is MatchAction.FORFEIT)


def _person(user_id: int) -> str:
    """Return a mention of ``user_id``, or ``deleted player`` once their data is deleted."""
    return "deleted player" if user_id == DELETED_MEMBER else f"<@{user_id}>"


def _logged_line(row: MatchEvent | LineupChange) -> str:
    """Return one line of a match's log: when it happened, who did it, and what."""
    if isinstance(row, MatchEvent):
        when = f"<t:{int(row.at.timestamp())}:t>"
        detail = f": {row.detail}" if row.detail else ""
        return f"{when} {_person(row.actor_id)} {row.kind}{detail}"
    when = f"<t:{int(row.changed_at.timestamp())}:t>"
    verb = "put {player} in" if row.playing else "took {player} out"
    reason = f" ({row.reason})" if row.reason else ""
    return f"{when} {_person(row.changed_by)} {verb.format(player=_person(row.user_id))}{reason}"


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
        """Suggest the tournaments the invoker can see that aren't over, whose name contains what was typed."""
        return self._tournament_options(interaction, current, include_over=False)

    async def log_tournament_choices(
        self,
        interaction: AutocompleteInteraction,
        current: str,
    ) -> list[ApplicationCommandOptionChoice]:
        """Suggest every tournament the invoker can see, finished ones too, whose name contains what was typed."""
        return self._tournament_options(interaction, current, include_over=True)

    def _tournament_options(
        self,
        interaction: AutocompleteInteraction,
        current: str,
        *,
        include_over: bool,
    ) -> list[ApplicationCommandOptionChoice]:
        """Return the tournaments the invoker can see whose name contains ``current``, as choices."""
        guild = interaction.guild
        user = interaction.user
        if guild is None or user is None:
            return []
        channel = interaction.channel
        with Session(self.bind) as session:
            tournaments = list(
                visible_tournaments(
                    session,
                    guild.id,
                    user.id,
                    None if channel is None else channel.id,
                    include_over=include_over,
                ),
            )
        return [
            Lookup.choice(tournament, tournament.name)
            for tournament in tournaments
            if current.casefold() in tournament.name.casefold()
        ]

    # --- Sign-up ---------------------------------------------------------------------------------------------------

    @staticmethod
    def _participants(session: Session, tournament: Tournament) -> tuple[dict[str, list[Snowflake]], list[Snowflake]]:
        """Return each team's players by team name, and the players signed up alone."""
        rosters = {entry.name: roster(session, entry) for entry in entries_of(session, tournament) if entry.id is not None}
        solo = [Snowflake(signup.user_id) for signup in signups_of(session, tournament)]
        return rosters, solo

    def _card(self, session: Session, tournament: Tournament) -> tuple[Container, list[File]]:
        """Return what a post shows, with the files to send along: the sign-up card, else the bracket and its image."""
        if tournament.status is TournamentStatus.SIGNUP:
            rosters, solo = self._participants(session, tournament)
            controls = SignupControls(
                join=self.join_button,
                leave=self.leave_button,
                participants=self.participants_button,
                enter=self.enter_button,
                add_player=self.add_player_button,
            )
            return signup_card(tournament, rosters, solo, controls), []
        matches, names = list(matches_of(session, tournament)), entry_names(session, tournament)
        return bracket_card(tournament, matches, names, self.show_match_button), [bracket_file(tournament, matches, names)]

    async def _refresh_posts(self, tournament_id: int, *, skip_message_id: int | None = None) -> None:
        """Edit every post of the tournament to show it as it is now, except ``skip_message_id``, which the caller updated."""
        with Session(self.bind) as session:
            tournament = stored(session, Tournament, tournament_id, "This tournament is gone.")
            shown, files = self._card(session, tournament)
            posts = [(post.channel_id, post.message_id) for post in posts_of(session, tournament)]
        await self._edit_posts(posts, shown, files, skip_message_id=skip_message_id)

    async def _edit_posts(
        self,
        posts: list[tuple[int, int]],
        shown: Container,
        files: list[File],
        *,
        skip_message_id: int | None = None,
    ) -> None:
        """Edit each ``(channel_id, message_id)`` post to show ``shown`` and ``files``, skipping ``skip_message_id``."""
        for channel_id, message_id in posts:
            if message_id == skip_message_id:
                continue
            message = self.bot.client.channels.partial(channel_id).message(message_id)
            edited = await message.edit(components=[shown], files=files)
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
        await interaction.defer(ephemeral=True)
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
            shown, files = self._card(session, tournament)
            sent = unwrap(
                await self.bot.client.channels.partial(interaction.channel.id).send(components=[shown], files=files),
                "I couldn't post the tournament here.",
            )
            add_post(session, tournament, interaction.channel.id, sent.id)
            session.commit()
            tournament_name = tournament.name
        await interaction.followup(
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
        await interaction.defer(ephemeral=True)
        with Session(self.bind) as session:
            found = self._tournament(interaction, session, tournament)
            shown, files = self._card(session, found)
            sent = unwrap(
                await self.bot.client.channels.partial(interaction.channel.id).send(components=[shown], files=files),
                "I couldn't post the tournament here.",
            )
            add_post(session, found, interaction.channel.id, sent.id)
            session.commit()
            tournament_name = found.name
        await interaction.followup(embeds=[CreatedEmbed(description=f"Posted **{tournament_name}** here.")], ephemeral=True)

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
        await interaction.respond(embeds=[CreatedEmbed(description="You're signed up!")], ephemeral=True)
        await self._refresh_posts(tournament_id)

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
        await interaction.respond(embeds=[DeletedEmbed(description="You've left the tournament.")], ephemeral=True)
        await self._refresh_posts(tournament_id)

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
            shown = participants_card(tournament, rosters, solo)
        await interaction.respond(components=[shown], ephemeral=True)

    async def _signup_click(self, interaction: GuildComponentInteraction, tournament_id: str, *, join: bool) -> None:
        with Session(self.bind) as session:
            tournament = stored(session, Tournament, int(tournament_id), "This tournament is gone.")
            user_id = interaction.user.id
            if join:
                sign_up(session, tournament, user_id)
            else:
                withdraw(session, tournament, user_id)
            session.commit()
            shown, files = self._card(session, tournament)
        await interaction.update(components=[shown], files=files)
        await self._refresh_posts(int(tournament_id), skip_message_id=int(interaction.message.id))

    def _open_signup(self, session: Session, interaction: AnyGuildInteraction, tournament_id: str) -> Tournament:
        """Return the tournament ``tournament_id`` from a sign-up card's button; refuse unless captains can still sign up."""
        tournament = self._tournament(
            interaction,
            session,
            stored(session, Tournament, int(tournament_id), "This tournament is gone."),
        )
        if tournament.status is not TournamentStatus.SIGNUP:
            msg = "Sign-up for this tournament has closed."
            raise Refused(msg)
        return tournament

    @Cog.component("tourney-enter")
    async def enter_button(self, interaction: GuildComponentInteraction, tournament_id: str) -> None:
        """Enter the clicker's team; with more than one team they could enter, ask which first."""
        user_id = interaction.user.id
        with Session(self.bind) as session:
            tournament = self._open_signup(session, interaction, tournament_id)
            entered = {entry.team_id for entry in entries_of(session, tournament)}
            teams = [
                team
                for team in teams_of(session, user_id)
                if team.kind is TeamKind.LASTING and team.captain_id == int(user_id) and team.id not in entered
            ]
            if not teams:
                msg = f"You don't captain a team that isn't entered yet; make one with {self.mention(Teams.create)}."
                raise Refused(msg)
            if len(teams) == 1:
                team = teams[0]
                enter_team(session, tournament, team, user_id)
                session.commit()
                name = team.name
            else:
                options = [
                    SelectOption(
                        label=team.name,
                        value=str(team.id),
                        description=plural(len(list(members_of(session, team))), "member"),
                    )
                    for team in teams[:MAX_SELECT_OPTIONS]
                ]
                select = StringSelect(
                    custom_id=self.enter_pick.custom_id(tournament_id),
                    options=options,
                    placeholder="Choose a team",
                )
                prompt = block(f"Pick the team to enter into **{tournament.name}**. You'll be its first player.")
                await interaction.respond(components=[card(Tone.ACT, prompt, ActionRow(components=[select]))], ephemeral=True)
                return
        await interaction.respond(embeds=[CreatedEmbed(description=f"**{name}** is entered.")], ephemeral=True)
        await self._refresh_posts(int(tournament_id))

    @Cog.component("tourney-enter-pick")
    async def enter_pick(self, interaction: GuildComponentInteraction, tournament_id: str) -> None:
        """Enter the team the clicker chose from the select of their teams."""
        with Session(self.bind) as session:
            tournament = self._open_signup(session, interaction, tournament_id)
            team = stored(session, Team, int(interaction.values[0]), "That team is gone.")
            enter_team(session, tournament, team, interaction.user.id)
            session.commit()
            name = team.name
        await interaction.update(components=[card(Tone.WAIT, block(f"**{name}** is entered."))])
        await self._refresh_posts(int(tournament_id))

    @Cog.component("tourney-add")
    async def add_player_button(self, interaction: GuildComponentInteraction, tournament_id: str) -> None:
        """Ask the clicker which members to add to the entry they captain, up to the places it has left."""
        with Session(self.bind) as session:
            tournament = self._open_signup(session, interaction, tournament_id)
            entry = captained_entry(session, tournament, interaction.user.id)
            free = tournament.team_size - len(roster(session, entry))
            name = entry.name
        if free < 1:
            msg = f"**{name}** is full."
            raise Refused(msg)
        select = UserSelect(
            custom_id=self.add_player_pick.custom_id(tournament_id),
            placeholder="Choose players",
            max_values=min(free, MAX_SELECT_OPTIONS),
        )
        prompt = block(f"Pick up to {plural(free, 'player')} to add to **{name}**. They must be in your team.")
        await interaction.respond(components=[card(Tone.ACT, prompt, ActionRow(components=[select]))], ephemeral=True)

    @Cog.component("tourney-add-pick")
    async def add_player_pick(self, interaction: GuildComponentInteraction, tournament_id: str) -> None:
        """Add the members the clicker chose to the entry they captain."""
        players = [Snowflake(int(user_id)) for user_id in interaction.values]
        for player in players:
            await require_server_member(interaction, player)
        with Session(self.bind) as session:
            tournament = self._open_signup(session, interaction, tournament_id)
            entry = captained_entry(session, tournament, interaction.user.id)
            for player in players:
                add_player(session, tournament, entry, interaction.user.id, player)
            session.commit()
            name = entry.name
        added = " ".join(f"<@{player}>" for player in players)
        await interaction.update(components=[card(Tone.WAIT, block(f"Added {added} to **{name}**."))])
        await self._refresh_posts(int(tournament_id))

    async def team_choices(self, interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]:
        """Suggest the lasting teams the invoker captains whose name contains what was typed."""
        user = interaction.user
        if user is None:
            return []
        with Session(self.bind) as session:
            teams = [team for team in teams_of(session, user.id) if team.kind is TeamKind.LASTING]
        return [
            Lookup.choice(team, team.name)
            for team in teams
            if team.captain_id == int(user.id) and current.casefold() in team.name.casefold()
        ]

    @Cog.command(name="enter", description="Enter one of your teams into a tournament, as its captain")
    async def enter(
        self,
        interaction: GuildCommandInteraction,
        tournament: Annotated[Tournament, Lookup(tournament_choices), Describe("The tournament")],
        team: Annotated[Team, Lookup(team_choices), Describe("Your team to enter")],
    ) -> None:
        """Enter the invoker's team into the tournament, with the invoker as its first player."""
        with Session(self.bind) as session:
            found = self._tournament(interaction, session, tournament)
            enter_team(session, found, stored(session, Team, team.id or 0, "That team is gone."), interaction.user.id)
            session.commit()
            tournament_id = found.id or 0
        message = f"Your team **{team.name}** is entered; add players with {self.mention(self.entry_add)}."
        await interaction.respond(embeds=[CreatedEmbed(description=message)], ephemeral=True)
        await self._refresh_posts(tournament_id)

    @Cog.command(name="entry-add", description="Add a server member to the entry you captain")
    async def entry_add(
        self,
        interaction: GuildCommandInteraction,
        tournament: Annotated[Tournament, Lookup(tournament_choices), Describe("The tournament")],
        player: Annotated[User, Describe("The player to add to your entry")],
    ) -> None:
        """Add ``player``, a member of this server and of your team, to the entry you captain."""
        await require_server_member(interaction, player.id)
        with Session(self.bind) as session:
            found = self._tournament(interaction, session, tournament)
            add_player(session, found, captained_entry(session, found, interaction.user.id), interaction.user.id, player.id)
            session.commit()
            tournament_id = found.id or 0
        await interaction.respond(embeds=[ChangedEmbed(description=f"Added {player.mention} to your entry.")], ephemeral=True)
        await self._refresh_posts(tournament_id)

    @Cog.command(name="entry-remove", description="Remove a player from the entry you captain")
    async def entry_remove(
        self,
        interaction: GuildCommandInteraction,
        tournament: Annotated[Tournament, Lookup(tournament_choices), Describe("The tournament")],
        player: Annotated[User, Describe("The player to remove from your entry")],
    ) -> None:
        """Remove ``player`` from the entry you captain."""
        with Session(self.bind) as session:
            found = self._tournament(interaction, session, tournament)
            remove_player(session, found, captained_entry(session, found, interaction.user.id), interaction.user.id, player.id)
            session.commit()
            tournament_id = found.id or 0
        message = f"Removed {player.mention} from your entry."
        await interaction.respond(embeds=[ChangedEmbed(description=message)], ephemeral=True)
        await self._refresh_posts(tournament_id)

    @Cog.command(name="lineup-in", description="Put a server member in your entry's lineup, from its next match not yet live")
    async def lineup_in(
        self,
        interaction: GuildCommandInteraction,
        tournament: Annotated[Tournament, Lookup(tournament_choices), Describe("The tournament")],
        player: Annotated[User, Describe("The member to put in your lineup")],
        reason: Annotated[
            str | None,
            Describe("Why, e.g. stand-in or illness"),
            Length(min_length=1, max_length=100),
        ] = None,
    ) -> None:
        """Put ``player``, a server member, in the lineup of the entry you captain; a stand-in needn't be in your team."""
        await require_server_member(interaction, player.id)
        with Session(self.bind) as session:
            found = self._tournament(interaction, session, tournament)
            change_lineup(
                session,
                found,
                captained_entry(session, found, interaction.user.id),
                LineupRequest(
                    captain_id=interaction.user.id,
                    user_id=player.id,
                    playing=True,
                    reason=reason,
                ),
            )
            session.commit()
            tournament_id = found.id or 0
        await interaction.respond(embeds=[ChangedEmbed(description=f"Put {player.mention} in your lineup.")], ephemeral=True)
        await self._refresh_posts(tournament_id)

    @Cog.command(name="lineup-out", description="Take a player out of your entry's lineup, from its next match not yet live")
    async def lineup_out(
        self,
        interaction: GuildCommandInteraction,
        tournament: Annotated[Tournament, Lookup(tournament_choices), Describe("The tournament")],
        player: Annotated[User, Describe("The player to take out of your lineup")],
        reason: Annotated[
            str | None,
            Describe("Why, e.g. stand-in or illness"),
            Length(min_length=1, max_length=100),
        ] = None,
    ) -> None:
        """Take ``player`` out of the lineup of the entry you captain, for its next match not yet live."""
        with Session(self.bind) as session:
            found = self._tournament(interaction, session, tournament)
            change_lineup(
                session,
                found,
                captained_entry(session, found, interaction.user.id),
                LineupRequest(
                    captain_id=interaction.user.id,
                    user_id=player.id,
                    playing=False,
                    reason=reason,
                ),
            )
            session.commit()
            tournament_id = found.id or 0
        await interaction.respond(
            embeds=[ChangedEmbed(description=f"Took {player.mention} out of your lineup.")],
            ephemeral=True,
        )
        await self._refresh_posts(tournament_id)

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
            shown, files = self._card(session, found)
            tournament_name = found.name
        started = block(f"**{tournament_name}** has started. {self.mention(self.match_card)} shows a match.")
        await interaction.respond(components=[started, shown], files=files)
        await self._refresh_posts(tournament_id)

    @Cog.command(name="bracket", description="Show a tournament's bracket")
    async def bracket(
        self,
        interaction: GuildCommandInteraction,
        tournament: Annotated[Tournament, Lookup(tournament_choices), Describe("The tournament")],
    ) -> None:
        """Show the bracket, or the sign-up card before the tournament starts."""
        with Session(self.bind) as session:
            found = self._tournament(interaction, session, tournament, over_ok=True)
            files: list[File] = []
            if found.status is TournamentStatus.SIGNUP:
                shown = participants_card(found, *self._participants(session, found))
            else:
                shown, files = self._card(session, found)
        await interaction.respond(components=[shown], files=files)

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
            posts = [(post.channel_id, post.message_id) for post in posts_of(session, found)]
            found.status = TournamentStatus.CANCELLED
            shown, files = self._card(session, found)
            cancel(session, found)
            session.commit()
            name = found.name
        await interaction.respond(embeds=[DeletedEmbed(description=f"**{name}** is called off.")])
        await self._edit_posts(posts, shown, files)

    # --- Matches ---------------------------------------------------------------------------------------------------

    def _match(
        self,
        interaction: AnyGuildInteraction,
        session: Session,
        match_id: int,
        *,
        over_ok: bool = False,
    ) -> tuple[Tournament, TournamentMatch]:
        """Return the match ``match_id`` and its tournament; refuse when there's no such match or the tournament is unusable.

        A tournament that is over is refused too, unless ``over_ok``.
        """
        match = alive_by_id(session, TournamentMatch, match_id)
        if match is None:
            msg = f"There's no match #{match_id}; {self.mention(self.bracket)} lists them."
            raise Refused(msg)
        tournament = self._tournament(
            interaction,
            session,
            stored(session, Tournament, match.tournament_id, "This match's tournament is gone."),
            over_ok=over_ok,
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

    @staticmethod
    def _match_view(session: Session, tournament: Tournament, match: TournamentMatch) -> MatchView:
        """Return what the match's card shows, as it is now."""
        names = entry_names(session, tournament)
        entries = {entry.id: entry for entry in entries_of(session, tournament) if entry.id is not None}
        # A match has no lineups until it's ready; until then its entries' current players stand in.
        rosters = {
            team: roster(session, entries[team]) if match.phase is MatchPhase.WAITING else lineup(session, match, entries[team])
            for team in (match.entry_a_id, match.entry_b_id)
            if team is not None and team in entries
        }
        return MatchView(
            match=match,
            tournament_name=tournament.name,
            rounds=round_count(len(names)),
            names=names,
            rosters=rosters,
            drafts=list(drafts_of(session, match)),
            clash=clashes(session, match) if match.phase is MatchPhase.READY else [],
        )

    @property
    def _match_controls(self) -> MatchControls:
        return MatchControls(manage=self.manage_button, act=self.match_control, clash=self.clash_button)

    def _match_card(self, session: Session, tournament: Tournament, match: TournamentMatch) -> Container:
        """Return the match's card, as it is now."""
        return card_of_match(self._match_view(session, tournament, match), self._match_controls)

    async def match_choices(self, interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]:
        """Suggest the undecided matches of the tournaments the invoker can see, whose label contains what was typed."""
        return self._match_options(interaction, current, include_over=False, include_decided=False)

    async def log_match_choices(
        self,
        interaction: AutocompleteInteraction,
        current: str,
    ) -> list[ApplicationCommandOptionChoice]:
        """Suggest every match, decided or not, of the tournaments the invoker can see, finished ones too."""
        return self._match_options(interaction, current, include_over=True, include_decided=True)

    def _match_options(
        self,
        interaction: AutocompleteInteraction,
        current: str,
        *,
        include_over: bool,
        include_decided: bool,
    ) -> list[ApplicationCommandOptionChoice]:
        """Return the matches of the visible tournaments whose label contains ``current``, as choices."""
        guild = interaction.guild
        user = interaction.user
        choices: list[ApplicationCommandOptionChoice] = []
        if guild is None or user is None:
            return choices
        channel = interaction.channel
        with Session(self.bind) as session:
            visible = visible_tournaments(
                session,
                guild.id,
                user.id,
                None if channel is None else channel.id,
                include_over=include_over,
            )
            for tournament in visible:
                names = entry_names(session, tournament)
                for match in matches_of(session, tournament):
                    if (match.phase.decided and not include_decided) or match.id is None:
                        continue
                    label = f"{tournament.name}: {match_line(match, names).replace('`', '')}"
                    if current.casefold() in label.casefold():
                        choices.append(Lookup.choice(match, label))
        return choices

    @Cog.command(name="match", description="Show a match's card; its organiser manages the match from it")
    async def match_card(
        self,
        interaction: GuildCommandInteraction,
        match: Annotated[TournamentMatch, Lookup(match_choices), Describe("The match to show")],
    ) -> None:
        """Post the card of match ``match``."""
        with Session(self.bind) as session:
            shown = self._match_card(session, *self._match(interaction, session, match.id or 0))
        await interaction.respond(components=[shown])

    @Cog.command(name="log", description="Show what happened in a match: its phases, drafts, votes, lineups and result")
    async def log(
        self,
        interaction: GuildCommandInteraction,
        tournament: Annotated[Tournament, Lookup(log_tournament_choices), Describe("The tournament")],
        match: Annotated[TournamentMatch, Lookup(log_match_choices), Describe("The match to show the log of")],
    ) -> None:
        """Post the log of ``match`` to the invoker only; its organiser and the captains of its two entries can see it."""
        with Session(self.bind) as session:
            found = self._tournament(interaction, session, tournament, over_ok=True)
            _, found_match = self._match(interaction, session, match.id or 0, over_ok=True)
            if found_match.tournament_id != found.id:
                msg = "That match isn't in this tournament."
                raise Refused(msg)
            if not is_organiser(interaction, found) and entry_in_match(session, found_match, interaction.user.id) is None:
                msg = "Only the organiser or a captain of this match can see its log."
                raise Refused(msg)
            title = f"Log: {match_line(found_match, entry_names(session, found)).replace('`', '')}"
            lines = [_logged_line(row) for row in match_log(session, found_match)]
        description = truncate("\n".join(lines) or "Nothing has been logged yet.", MAX_EMBED_DESCRIPTION_LENGTH)
        await interaction.respond(embeds=[Embed(title=title, description=description)], ephemeral=True)

    @Cog.component("tourney-manage")
    async def manage_button(self, interaction: GuildComponentInteraction, match_id: str) -> None:
        """Show the organiser, and only them, the panel to move the match on, report its winner or record a forfeit."""
        with Session(self.bind) as session:
            tournament, match = self._running_match(session, int(match_id))
            require_organiser(interaction, tournament)
            panel = manage_panel(
                self._match_view(session, tournament, match),
                self.match_control,
                (interaction.channel.id, interaction.message.id),
            )
        await interaction.respond(components=[panel], ephemeral=True)

    @Cog.component("tourney-show-match")
    async def show_match_button(self, interaction: GuildComponentInteraction, match_id: str) -> None:
        """Show the clicker, and only them, the card of a match from the bracket."""
        with Session(self.bind) as session:
            tournament, match = self._match(interaction, session, int(match_id), over_ok=True)
            shown = card_of_match(self._match_view(session, tournament, match), None)
        await interaction.respond(components=[shown], ephemeral=True)

    @Cog.component("tourney-match")
    async def match_control(  # noqa: PLR0913 - a panel button carries the match, the action, its team and the card it edits
        self,
        interaction: GuildComponentInteraction,
        match_id: str,
        action: str,
        entry_id: str = "",
        card_channel_id: str = "",
        card_message_id: str = "",
    ) -> None:
        """Move a match to its next phase, report its winner, or record a forfeit; organisers only.

        A button on the organiser's panel names the match card it was opened from, and edits that card along with the
        panel. A button without one sits on an older match card, and edits that card.
        """
        with Session(self.bind) as session:
            tournament, match = self._running_match(session, int(match_id))
            require_organiser(interaction, tournament)
            play(session, match, MatchAction(action), entry_id, interaction.user.id)
            session.commit()
            tournament_id = tournament.id or 0
            view = self._match_view(session, tournament, match)
            shown = card_of_match(view, self._match_controls)
            finished = tournament.status is TournamentStatus.FINISHED
            final, final_files = self._card(session, tournament)
        if card_message_id:
            card_at = (Snowflake(int(card_channel_id)), Snowflake(int(card_message_id)))
            await interaction.update(components=[manage_panel(view, self.match_control, card_at)])
            edited = await self.bot.client.channels.partial(card_at[0]).message(card_at[1]).edit(components=[shown])
            if is_network_error(edited):
                self.logger.debug(t"Could not edit match card {card_message_id} in channel {card_channel_id}: {edited}")
        else:
            await interaction.update(components=[shown])
        await self._refresh_posts(tournament_id, skip_message_id=int(interaction.message.id))
        if finished:
            await interaction.followup(components=[block(f"**{tournament.name}** is over."), final], files=final_files)

    @Cog.component("tourney-clash")
    async def clash_button(self, interaction: GuildComponentInteraction, match_id: str, entry_id: str) -> None:
        """Drop the clashing members from one side of a ready match; its organiser or a captain of either side only."""
        with Session(self.bind) as session:
            tournament, match = self._running_match(session, int(match_id))
            entry = stored(session, TournamentEntry, int(entry_id), "That entry is gone.")
            if not is_organiser(interaction, tournament):
                own = entry_in_match(session, match, interaction.user.id)
                if own is None:
                    msg = "Only the organiser or a captain of this match can resolve a clash."
                    raise Refused(msg)
                if own.id != entry.id:
                    msg = "You can only drop players from your own entry."
                    raise Refused(msg)
            drop_clash(session, match, entry, interaction.user.id)
            session.commit()
            shown = self._match_card(session, tournament, match)
        await interaction.update(components=[shown])

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
            opened = open_vote(session, found, question, parse_options(answers), interaction.user.id)
            session.commit()
            session.refresh(opened)
            shown = vote_card(opened, [], self.vote_button, self.close_vote_button)
        await interaction.respond(components=[shown])

    @Cog.component("tourney-vote")
    async def vote_button(self, interaction: GuildComponentInteraction, vote_id: str, choice: str) -> None:
        """Record the clicker's answer, refresh the tally, and tell the clicker, and only them, what they voted."""
        with Session(self.bind) as session:
            vote = stored(session, MatchVote, int(vote_id), "This vote is gone.")
            cast(session, vote, interaction.user.id, int(choice))
            session.commit()
            shown = vote_card(vote, choices_of(session, vote), self.vote_button, self.close_vote_button)
            answer = vote_options(vote)[int(choice)]
        await interaction.update(components=[shown])
        voted = block(f"You voted **{answer}**. Vote for another answer to change it.")
        await interaction.followup(components=[card(Tone.WAIT, voted)], ephemeral=True)

    @Cog.component("tourney-close")
    async def close_vote_button(self, interaction: GuildComponentInteraction, vote_id: str) -> None:
        """Close the vote and show the final tally; organisers only."""
        with Session(self.bind) as session:
            vote = stored(session, MatchVote, int(vote_id), "This vote is gone.")
            match = stored(session, TournamentMatch, vote.match_id, "This vote is gone.")
            require_organiser(interaction, stored(session, Tournament, match.tournament_id, "This vote is gone."))
            close_vote(session, vote, interaction.user.id)
            session.commit()
            shown = vote_card(vote, choices_of(session, vote), self.vote_button, self.close_vote_button)
        await interaction.update(components=[shown])
