"""The messages a tournament shows: its sign-up card, bracket, match cards and votes, with their buttons."""

lazy from dataclasses import dataclass
lazy from enum import StrEnum
lazy from itertools import batched
lazy from typing import TYPE_CHECKING

lazy from wd_discord.components import (
    ActionRow,
    Button,
    ButtonStyle,
    MediaGallery,
    MediaGalleryItem,
    Section,
    Separator,
    SeparatorSpacing,
    UnfurledMediaItem,
)
lazy from wd_discord.embed import Embed
lazy from wd_discord.files import File
lazy from wd_discord.limits import MAX_ACTION_ROW_BUTTONS, MAX_BUTTON_LABEL_LENGTH, MAX_MEDIA_DESCRIPTION_LENGTH, truncate

lazy from winter_dragon.ui import Mark, Tone, block, card, steps

lazy from .bracket import BracketSlot, round_name, tally
lazy from .bracket_image import bracket_png
lazy from .models import DraftKind, MatchPhase, TeamMode, TournamentStatus
lazy from .service import following_phase


if TYPE_CHECKING:
    lazy from collections.abc import Iterable, Mapping, Sequence

    lazy from wd_bot.components import ComponentHandler
    lazy from wd_discord.components import Container, TextDisplay
    lazy from wd_discord.snowflake import Snowflake

    lazy from .models import DraftChoice, MatchVote, Tournament, TournamentMatch


PHASE_LABELS = {
    MatchPhase.WAITING: "Waiting for teams",
    MatchPhase.READY: "Ready",
    MatchPhase.BAN: "Bans",
    MatchPhase.PICK: "Picks",
    MatchPhase.LIVE: "Live",
    MatchPhase.FINISHED: "Finished",
    MatchPhase.FORFEIT: "Forfeit",
}

CARD_LIST_CHARACTERS = 3000
"""How much of a card's 4000 characters of text its list of players or teams may take; the rest is for the card itself."""


class MatchAction(StrEnum):
    """What one of the organiser's buttons under a match card does; it's part of the button's custom ID."""

    NEXT = "next"
    """Move the match on to its next phase."""
    WIN = "win"
    """Report the button's team as the winner."""
    FORFEIT = "forfeit"
    """Record the button's team forfeiting."""


@dataclass(frozen=True)
class SignupControls:
    """The handlers behind a sign-up card's buttons; each button carries the tournament's ID."""

    join: ComponentHandler
    leave: ComponentHandler
    participants: ComponentHandler
    enter: ComponentHandler
    add_player: ComponentHandler


def _fit(items: Sequence[str], separator: str) -> tuple[str, int]:
    """Join as many of ``items`` as fit in :data:`CARD_LIST_CHARACTERS`; return the text and how many were left out."""
    shown: list[str] = []
    length = 0
    for item in items:
        length += len(item) + len(separator)
        if length > CARD_LIST_CHARACTERS:
            break
        shown.append(item)
    return separator.join(shown), len(items) - len(shown)


def plural(count: int, noun: str) -> str:
    """Return ``count`` with ``noun``, adding an ``s`` unless there's exactly one."""
    return f"{count} {noun}{'' if count == 1 else 's'}"


def solo_progress(players: int, team_size: int) -> str:
    """Return how far solo sign-up is: the teams it makes so far, and how many more players make the next one."""
    if team_size == 1:
        return f"**{plural(players, 'player')}** signed up."
    teams = players // team_size
    missing = team_size - players % team_size
    more = "1 more player makes" if missing == 1 else f"{missing} more players make"
    return f"**{plural(players, 'player')}**, enough for {plural(teams, 'team')}. {more} team {teams + 1}."


def _team_line(name: str, players: Sequence[Snowflake], team_size: int) -> str:
    full = f" {Mark.WINNER}" if len(players) >= team_size else ""
    who = " ".join(f"<@{user_id}>" for user_id in players) or "No players yet."
    return f"**{name}** {len(players)} of {team_size}{full}\n{who}"


def _button(handler: ComponentHandler, tournament_id: int, label: str, style: ButtonStyle) -> Button:
    return Button(style=style, label=label, custom_id=handler.custom_id(tournament_id))


def signup_card(
    tournament: Tournament,
    rosters: Mapping[str, Sequence[Snowflake]],
    solo_players: Sequence[Snowflake],
    controls: SignupControls,
) -> Container:
    """Return the sign-up card: what the format is, who signed up, and the buttons to join, enter a team or leave.

    The list of players or teams is cut to fit the card; only then does it get a Participants button showing all of them.
    """
    tournament_id = tournament.id or 0
    leave = _button(controls.leave, tournament_id, "Leave", ButtonStyle.DANGER)
    if tournament.mode is TeamMode.SOLO:
        listed, hidden = _fit([f"<@{user_id}>" for user_id in solo_players], " ")
        join = _button(controls.join, tournament_id, "Join", ButtonStyle.SUCCESS)
        body = [
            block(f"## {tournament.name}", f"Sign-up is open. Teams of {tournament.team_size} are drawn when it starts."),
            Section(components=[block(solo_progress(len(solo_players), tournament.team_size))], accessory=join),
            Separator(),
        ]
        if listed:
            body.append(block(listed, f"-# +{plural(hidden, 'more player')}." if hidden else ""))
        buttons = [leave]
        counts = ""
    else:
        lines = [_team_line(name, players, tournament.team_size) for name, players in rosters.items()]
        listed, hidden = _fit(lines, "\n")
        body = [
            block(f"## {tournament.name}", f"Sign-up is open. Captains enter a team of up to {tournament.team_size} players."),
            Separator(),
        ]
        if listed:
            body += [block(listed, f"-# +{plural(hidden, 'more team')}." if hidden else ""), Separator()]
        buttons = [
            _button(controls.enter, tournament_id, "Enter my team", ButtonStyle.PRIMARY),
            _button(controls.add_player, tournament_id, "Add a player", ButtonStyle.SECONDARY),
            leave,
        ]
        players = sum(len(players) for players in rosters.values())
        counts = f"-# {plural(len(rosters), 'team')}, {plural(players, 'player')}."
    if hidden:
        buttons.append(_button(controls.participants, tournament_id, "Participants", ButtonStyle.SECONDARY))
    footer = block(counts, f"-# Organised by <@{tournament.organiser_id}>.")
    return card(Tone.ACT, *body, ActionRow(components=buttons), footer)


def participants_card(
    tournament: Tournament,
    rosters: Mapping[str, Sequence[Snowflake]],
    solo_players: Sequence[Snowflake],
) -> Container:
    """Return everyone signed up to ``tournament``: the players, or each team with its players."""
    if tournament.mode is TeamMode.SOLO:
        lines = [f"<@{user_id}>" for user_id in solo_players]
        count = plural(len(solo_players), "player")
    else:
        lines = [_team_line(name, players, tournament.team_size) for name, players in rosters.items()]
        count = plural(len(rosters), "team")
    listed = truncate("\n".join(lines) or "Nobody has signed up yet.", CARD_LIST_CHARACTERS)
    return card(Tone.WAIT, block(f"## {tournament.name}", f"{count} signed up."), Separator(), block(listed))


def match_ids(matches: Iterable[TournamentMatch]) -> dict[BracketSlot, int]:
    """Return each match's ID by where it sits in the bracket."""
    return {BracketSlot(match.round, match.slot): match.id for match in matches if match.id is not None}


def _side(match: TournamentMatch, names: Mapping[int, str], ids: Mapping[BracketSlot, int], *, side_b: bool) -> str:
    """Return who plays one side of ``match``: the team, a bye, or which earlier match decides it."""
    entry_id = match.entry_b_id if side_b else match.entry_a_id
    if entry_id is not None:
        return names.get(entry_id, f"Team {entry_id}")
    if match.round == 0:
        return "a bye"
    feeder = ids.get(BracketSlot(match.round - 1, 2 * match.slot + int(side_b)))
    return "to be decided" if feeder is None else f"winner of #{feeder}"


def match_line(match: TournamentMatch, names: Mapping[int, str], ids: Mapping[BracketSlot, int] | None = None) -> str:
    """Return one line of the bracket: the match's number, its teams, and its state or winner.

    ``ids`` (see :func:`match_ids`) names the matches whose winners fill a side that isn't known yet.
    """
    ids = ids or {}
    teams = f"{_side(match, names, ids, side_b=False)} vs {_side(match, names, ids, side_b=True)}"
    if match.phase.decided and match.winner_id is not None:
        return f"`#{match.id}` {teams}, {Mark.WINNER} {names.get(match.winner_id, '?')}"
    return f"`#{match.id}` {teams}, {PHASE_LABELS[match.phase].lower()}"


def _now(matches: Sequence[TournamentMatch]) -> str:
    """Return the matches being drafted or played right now, as one line."""
    playing = [match for match in matches if match.phase in {MatchPhase.BAN, MatchPhase.PICK, MatchPhase.LIVE}]
    if not playing:
        return "No match is being played right now."
    parts = [f"match {match.id} is in {PHASE_LABELS[match.phase].lower()}" for match in playing]
    return f"{Mark.HERE} Now: {', '.join(parts)}."


BRACKET_IMAGE = "bracket.png"
"""The filename the bracket image is sent under, and the card shows through ``attachment://``."""


def bracket_file(tournament: Tournament, matches: Sequence[TournamentMatch], names: Mapping[int, str]) -> File:
    """Return the bracket drawn as an image, to send with :func:`bracket_card`."""
    image = bracket_png(matches, names, tournament.winner_entry_id)
    return File(BRACKET_IMAGE, image, content_type="image/png")


def _alt_text(matches: Sequence[TournamentMatch], names: Mapping[int, str]) -> str:
    """Return the bracket as text, round by round, for whoever can't see the image."""
    rounds = max((match.round for match in matches), default=0) + 1
    ids = match_ids(matches)
    lines = [
        f"{round_name(match.round, rounds)}: {match_line(match, names, ids).replace('`', '')}."
        for match in sorted(matches, key=lambda match: (match.round, match.slot))
    ]
    return truncate(" ".join(lines), MAX_MEDIA_DESCRIPTION_LENGTH)


def bracket_card(
    tournament: Tournament,
    matches: Sequence[TournamentMatch],
    names: Mapping[int, str],
    show_match: ComponentHandler,
) -> Container:
    """Return the bracket: what's being played now or who won, the bracket image, and a button per match being played.

    Send it with :func:`bracket_file`. Each button shows its match's card to whoever clicks it.
    """
    champion = tournament.winner_entry_id
    if tournament.status is TournamentStatus.CANCELLED:
        tone, state = Tone.STOP, "This tournament was called off."
    elif champion is not None:
        tone, state = Tone.WAIT, f"{Mark.WINNER} **{names.get(champion, '?')}** won."
    else:
        tone, state = Tone.ACT, _now(matches)
    image = MediaGalleryItem(
        media=UnfurledMediaItem(url=f"attachment://{BRACKET_IMAGE}"),
        description=_alt_text(matches, names),
    )
    body: list[TextDisplay | MediaGallery | ActionRow] = [
        block(f"## {tournament.name} bracket", state),
        MediaGallery(items=[image]),
    ]
    playing = [
        Button(
            style=ButtonStyle.SECONDARY,
            label=f"Match {match.id}, {PHASE_LABELS[match.phase].lower()}",
            custom_id=show_match.custom_id(match.id),
        )
        for match in matches
        if match.phase in {MatchPhase.BAN, MatchPhase.PICK, MatchPhase.LIVE} and match.id is not None
    ]
    if tournament.status is TournamentStatus.RUNNING:
        body += [ActionRow(components=list(row)) for row in batched(playing, MAX_ACTION_ROW_BUTTONS, strict=False)]
    return card(tone, *body)


ROUTE = (MatchPhase.READY, MatchPhase.BAN, MatchPhase.PICK, MatchPhase.LIVE)
"""The phases a match goes through before its result, in order."""
ROUTE_NAMES = ["Ready", "Bans", "Picks", "Live", "Result"]
"""The steps of a match card's route line: its :data:`ROUTE`, then the result."""

NEXT_STEPS = {
    MatchPhase.BAN: ("Both teams are ready? Open the bans.", "Start bans"),
    MatchPhase.PICK: ("Both teams have banned? Open the picks.", "Start picks"),
    MatchPhase.LIVE: ("Both teams have picked? Start the match.", "Start the match"),
}
"""For each phase the organiser can move a match on to: when to do it, and the button that does it."""


@dataclass(frozen=True)
class MatchControls:
    """The handlers behind a match card's buttons and its organiser's panel; each button carries the match's ID."""

    manage: ComponentHandler
    """Opens the organiser's panel."""
    act: ComponentHandler
    """Moves the match on, reports its winner or records a forfeit."""
    clash: ComponentHandler
    """Drops the players who play for both sides from one of them."""


@dataclass(frozen=True)
class MatchView:
    """What a match card shows: the match, its tournament and round, the teams, their players and drafts."""

    match: TournamentMatch
    tournament_name: str
    rounds: int
    names: Mapping[int, str]
    rosters: Mapping[int, Sequence[Snowflake]]
    drafts: Sequence[DraftChoice]
    clash: Sequence[Snowflake] = ()

    @property
    def teams(self) -> list[int]:
        """The IDs of the match's teams known so far."""
        return [team for team in (self.match.entry_a_id, self.match.entry_b_id) if team is not None]

    def name(self, team: int | None) -> str:
        """Return the team's name."""
        return "?" if team is None else self.names.get(team, f"Team {team}")

    @property
    def playable(self) -> bool:
        """Whether the organiser can still act on the match: both teams known, and no winner yet."""
        return len(self.teams) == 2 and not self.match.phase.decided and self.match.id is not None  # noqa: PLR2004 - a match has two sides


def _route(phase: MatchPhase) -> str:
    """Return the match's route line, marking where ``phase`` is."""
    if phase is MatchPhase.WAITING:
        return steps(ROUTE_NAMES, -1)
    if phase.decided:
        return steps(ROUTE_NAMES, len(ROUTE_NAMES) - 1)
    return steps(ROUTE_NAMES, ROUTE.index(phase))


def _state(view: MatchView) -> str:
    """Return one line saying where the match stands and who it waits for."""
    match = view.match
    winner = view.name(match.winner_id)
    match match.phase:
        case MatchPhase.WAITING:
            return "Waiting for an earlier match to decide who plays."
        case MatchPhase.READY:
            return "Both teams are ready. The organiser opens the bans."
        case MatchPhase.BAN | MatchPhase.PICK:
            return f"{PHASE_LABELS[match.phase]} are open for both captains."
        case MatchPhase.LIVE:
            return "Being played now."
        case MatchPhase.FINISHED:
            return f"{Mark.WINNER} **{winner}** won."
        case MatchPhase.FORFEIT:
            loser = next((team for team in view.teams if team != match.winner_id), None)
            return f"**{view.name(loser)}** forfeited, so **{winner}** goes through."


def _team_block(view: MatchView, team: int) -> TextDisplay:
    """Return one team's part of the card: its name, its players, and what it banned and picked."""
    who = " ".join(f"<@{user_id}>" for user_id in view.rosters.get(team, [])) or "No players yet."
    own = [draft for draft in view.drafts if draft.entry_id == team]
    bans = ", ".join(draft.value for draft in own if draft.kind is DraftKind.BAN)
    picks = ", ".join(draft.value for draft in own if draft.kind is DraftKind.PICK)
    drafted = " ".join(part for part in (f"Banned {bans}." if bans else "", f"Picked {picks}." if picks else "") if part)
    return block(f"**{view.name(team)}**", who, drafted)


def _tone(phase: MatchPhase) -> Tone:
    if phase is MatchPhase.FORFEIT:
        return Tone.STOP
    if phase in {MatchPhase.WAITING, MatchPhase.FINISHED}:
        return Tone.WAIT
    return Tone.ACT


def card_of_match(view: MatchView, controls: MatchControls | None) -> Container:
    """Return a match card: its teams, a route line through its phases, where it stands, and each team's players and drafts.

    Its only buttons are Manage match, which opens the organiser's panel, and a clash's drop buttons; ``controls`` of
    ``None`` leaves them out, for a copy shown to one person.
    """
    match = view.match
    sides = (match.entry_a_id, match.entry_b_id)
    title = " vs ".join(view.name(team) if team is not None else "to be decided" for team in sides)
    heading = block(
        f"## {title}",
        f"-# {view.tournament_name}, {round_name(match.round, view.rounds).lower()}, match {match.id}",
    )
    if view.playable and controls is not None:
        manage = Button(style=ButtonStyle.SECONDARY, label="Manage match", custom_id=controls.manage.custom_id(match.id or 0))
        heading = Section(components=[heading], accessory=manage)
    clash = ""
    if view.clash:
        clash = f"Clash: {' '.join(f'<@{user_id}>' for user_id in view.clash)} play for both sides."
    body: list[ActionRow | TextDisplay | Section | Separator] = [heading, block(_route(match.phase), _state(view), clash)]
    if view.clash and view.playable and controls is not None and match.id is not None:
        body.append(
            ActionRow(
                components=[
                    Button(
                        style=ButtonStyle.DANGER,
                        label=f"Drop clash from {view.name(team)}"[:MAX_BUTTON_LABEL_LENGTH],
                        custom_id=controls.clash.custom_id(match.id, team),
                    )
                    for team in view.teams
                ],
            ),
        )
    for index, team in enumerate(view.teams):
        body += [Separator(divider=index == 0), _team_block(view, team)]
    return card(_tone(match.phase), *body)


def manage_panel(view: MatchView, act: ComponentHandler, card_at: tuple[Snowflake, Snowflake]) -> Container:
    """Return the organiser's panel for a match: each action beside a line saying when to use it.

    ``card_at`` is the channel and message of the match card the panel was opened from; its buttons carry it, so the
    card is edited along with the panel.
    """
    match = view.match
    if not view.playable or match.id is None:
        return card(Tone.WAIT, block(f"**Match {match.id}** has nothing left to do."))
    match_id = match.id

    def button(style: ButtonStyle, label: str, action: MatchAction, team: int | str = "") -> Button:
        custom_id = act.custom_id(match_id, action, team, *card_at)
        return Button(style=style, label=label[:MAX_BUTTON_LABEL_LENGTH], custom_id=custom_id)

    body: list[TextDisplay | Section | Separator] = [block(f"**Match {match_id}**: {_state(view)}"), Separator()]
    following = following_phase(match.phase)
    if following is not None:
        when, label = NEXT_STEPS[following]
        body.append(Section(components=[block(when)], accessory=button(ButtonStyle.PRIMARY, label, MatchAction.NEXT)))
    if match.phase is MatchPhase.LIVE:
        body += [
            Section(
                components=[block(f"**{view.name(team)}** won the match?")],
                accessory=button(ButtonStyle.SUCCESS, f"{view.name(team)} won", MatchAction.WIN, team),
            )
            for team in view.teams
        ]
    body.append(Separator(spacing=SeparatorSpacing.LARGE))
    body += [
        Section(
            components=[block(f"**{view.name(team)}** can't play.")],
            accessory=button(ButtonStyle.DANGER, f"{view.name(team)} forfeits", MatchAction.FORFEIT, team),
        )
        for team in view.teams
    ]
    return card(Tone.WAIT, *body)


# Maybe namespace vote_ into a vote class?
def vote_options(vote: MatchVote) -> list[str]:
    """Return the vote's answers."""
    return vote.options.split("\n")


def vote_embed(vote: MatchVote, choices: Sequence[int]) -> Embed:
    """Return a vote: its question, and each answer's votes so far."""
    options = vote_options(vote)
    counts = tally(len(options), choices)
    lines = [f"**{option}** — {count} vote{'s' if count != 1 else ''}" for option, count in zip(options, counts, strict=True)]
    state = "Players of the match: pick an answer below." if vote.open else "This vote is closed."
    return Embed(title=f"🗳️ {vote.question}", description="\n".join([*lines, "", state]))


def vote_buttons(choose: ComponentHandler, close: ComponentHandler, vote: MatchVote) -> list[ActionRow]:
    """Return one button per answer, then the organiser's Close button; none once the vote is closed."""
    if not vote.open or vote.id is None:
        return []
    vote_id = vote.id
    answers = [
        Button(style=ButtonStyle.SECONDARY, label=option, custom_id=choose.custom_id(vote_id, index))
        for index, option in enumerate(vote_options(vote))
    ]
    rows = [ActionRow(components=list(row)) for row in batched(answers, MAX_ACTION_ROW_BUTTONS, strict=False)]
    rows.append(
        ActionRow(components=[Button(style=ButtonStyle.DANGER, label="Close vote", custom_id=close.custom_id(vote_id))]),
    )
    return rows
