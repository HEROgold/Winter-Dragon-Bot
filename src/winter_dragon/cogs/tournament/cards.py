"""The messages a tournament shows: its sign-up card, bracket, match cards and votes, with their buttons."""

lazy from dataclasses import dataclass
lazy from enum import StrEnum
lazy from itertools import batched
lazy from typing import TYPE_CHECKING

lazy from wd_discord.components import ActionRow, Button, ButtonStyle, Section, Separator
lazy from wd_discord.embed import Embed, EmbedField
lazy from wd_discord.limits import (
    MAX_ACTION_ROW_BUTTONS,
    MAX_BUTTON_LABEL_LENGTH,
    MAX_EMBED_FIELD_VALUE_LENGTH,
    truncate,
)

lazy from winter_dragon.ui import Mark, Tone, block, card, mentions

lazy from .bracket import BracketSlot, round_name, tally
lazy from .models import DraftKind, MatchPhase, TeamMode, TournamentStatus
lazy from .service import following_phase


if TYPE_CHECKING:
    lazy from collections.abc import Iterable, Mapping, Sequence

    lazy from wd_bot.components import ComponentHandler
    lazy from wd_discord.components import Container
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


def bracket_card(tournament: Tournament, matches: Sequence[TournamentMatch], names: Mapping[int, str]) -> Container:
    """Return the bracket: what's being played now or who won, then every round's matches."""
    rounds = max((match.round for match in matches), default=0) + 1
    champion = tournament.winner_entry_id
    if tournament.status is TournamentStatus.CANCELLED:
        tone, state = Tone.STOP, "This tournament was called off."
    elif champion is not None:
        tone, state = Tone.WAIT, f"{Mark.WINNER} **{names.get(champion, '?')}** won."
    else:
        tone, state = Tone.ACT, _now(matches)
    ids = match_ids(matches)
    round_texts = [
        block(
            f"**{round_name(round_, rounds)}**",
            *(match_line(match, names, ids) for match in matches if match.round == round_),
        )
        for round_ in range(rounds)
    ]
    return card(tone, block(f"## {tournament.name} bracket", state), Separator(), *round_texts)


def match_embed(
    match: TournamentMatch,
    rounds: int,
    names: Mapping[int, str],
    rosters: Mapping[int, Sequence[Snowflake]],
    drafts: Sequence[DraftChoice],
) -> Embed:
    """Return a match card: its round, phase, the teams' lineups, what each team banned and picked, and any clash."""
    fields: list[EmbedField] = []
    for entry_id in (match.entry_a_id, match.entry_b_id):
        if entry_id is None:
            continue
        own = [draft for draft in drafts if draft.entry_id == entry_id]
        bans = ", ".join(draft.value for draft in own if draft.kind is DraftKind.BAN) or "—"
        picks = ", ".join(draft.value for draft in own if draft.kind is DraftKind.PICK) or "—"
        value = f"{mentions(rosters.get(entry_id, []))}\nBans: {bans}\nPicks: {picks}"
        fields.append(
            EmbedField(name=names.get(entry_id, "?"), value=truncate(value, MAX_EMBED_FIELD_VALUE_LENGTH), inline=True),
        )
    title = f"Match #{match.id} — {round_name(match.round, rounds)}"
    description = PHASE_LABELS[match.phase]
    if match.phase.decided and match.winner_id is not None:
        description += f": **{names.get(match.winner_id, '?')}** wins"
    if match.phase is MatchPhase.READY and match.entry_a_id is not None and match.entry_b_id is not None:
        other_side = set(rosters.get(match.entry_b_id, []))
        clash = [user_id for user_id in rosters.get(match.entry_a_id, []) if user_id in other_side]
        if clash:
            mentioned = ", ".join(f"<@{user_id}>" for user_id in clash)
            description += f"\nClash: {mentioned} play for both sides."
    return Embed(title=title, description=description, fields=fields)


def match_buttons(
    handler: ComponentHandler,
    match: TournamentMatch,
    names: Mapping[int, str],
    clash_handler: ComponentHandler,
    clash: Sequence[Snowflake] = (),
) -> list[ActionRow]:
    """Return the controls under a match card: a clash's drop buttons, then the organiser's next phase, winner or forfeit."""
    if match.phase.decided or match.entry_a_id is None or match.entry_b_id is None or match.id is None:
        return []
    teams = (match.entry_a_id, match.entry_b_id)
    rows: list[ActionRow] = []
    if match.phase is MatchPhase.READY and clash:
        rows.append(
            ActionRow(
                components=[
                    Button(
                        style=ButtonStyle.DANGER,
                        label=f"Drop clash from {names.get(team, '?')}"[:MAX_BUTTON_LABEL_LENGTH],
                        custom_id=clash_handler.custom_id(match.id, team),
                    )
                    for team in teams
                ],
            ),
        )
    following = following_phase(match.phase)
    if following is not None:
        label = f"Next: {PHASE_LABELS[following]}"
        custom_id = handler.custom_id(match.id, MatchAction.NEXT)
        rows.append(ActionRow(components=[Button(style=ButtonStyle.PRIMARY, label=label, custom_id=custom_id)]))
    if match.phase is MatchPhase.LIVE:
        rows.append(_team_buttons(handler, match.id, teams, names, MatchAction.WIN))
    rows.append(_team_buttons(handler, match.id, teams, names, MatchAction.FORFEIT))
    return rows


TEAM_BUTTONS = {MatchAction.WIN: (ButtonStyle.SUCCESS, "won"), MatchAction.FORFEIT: (ButtonStyle.DANGER, "forfeits")}
"""The style and label ending of the per-team buttons under a match card."""


def _team_buttons(
    handler: ComponentHandler,
    match_id: int,
    teams: Sequence[int],
    names: Mapping[int, str],
    action: MatchAction,
) -> ActionRow:
    """Return a row with a button per team of the match doing ``action`` for that team."""
    style, verb = TEAM_BUTTONS[action]
    return ActionRow(
        components=[
            Button(
                style=style,
                label=f"{names.get(team, '?')} {verb}"[:MAX_BUTTON_LABEL_LENGTH],
                custom_id=handler.custom_id(match_id, action, team),
            )
            for team in teams
        ],
    )


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
