"""The messages a tournament shows: its sign-up card, bracket, match cards and votes, with their buttons."""

lazy from enum import StrEnum
lazy from itertools import batched
lazy from typing import TYPE_CHECKING

lazy from wd_discord.components import ActionRow, Button, ButtonStyle
lazy from wd_discord.embed import Embed, EmbedField
lazy from wd_discord.limits import (
    MAX_ACTION_ROW_BUTTONS,
    MAX_BUTTON_LABEL_LENGTH,
    MAX_EMBED_DESCRIPTION_LENGTH,
    MAX_EMBED_FIELD_VALUE_LENGTH,
    MAX_EMBED_FIELDS,
    truncate,
)

lazy from winter_dragon.ui import mentions

lazy from .bracket import round_name, tally
lazy from .models import DraftKind, MatchPhase, TeamMode, TournamentStatus


if TYPE_CHECKING:
    lazy from collections.abc import Mapping, Sequence

    lazy from wd_bot.components import ComponentHandler
    lazy from wd_bot.registry import CommandMention
    lazy from wd_discord.snowflake import Snowflake

    lazy from .models import DraftChoice, MatchVote, Tournament, TournamentMatch


PHASE_LABELS = {
    MatchPhase.WAITING: "⏳ Waiting for teams",
    MatchPhase.READY: "🟦 Ready",
    MatchPhase.BAN: "🚫 Bans",
    MatchPhase.PICK: "✅ Picks",
    MatchPhase.LIVE: "🔴 Live",
    MatchPhase.FINISHED: "🏁 Finished",
    MatchPhase.FORFEIT: "🏳️ Forfeit",
}


class MatchAction(StrEnum):
    """What one of the organiser's buttons under a match card does; it's part of the button's custom ID."""

    NEXT = "next"
    """Move the match on to its next phase."""
    WIN = "win"
    """Report the button's team as the winner."""
    FORFEIT = "forfeit"
    """Record the button's team forfeiting."""


def signup_embed(
    tournament: Tournament,
    rosters: Mapping[str, Sequence[Snowflake]],
    solo_players: Sequence[Snowflake],
    *,
    enter: CommandMention,
    entry_add: CommandMention,
) -> Embed:
    """Return the sign-up card: the format, and who signed up, alone or per entry.

    ``enter`` and ``entry_add`` are mentions of the commands that enter a team into a captains' tournament and add its players.
    """
    if tournament.mode is TeamMode.SOLO:
        how = f"Sign up alone; teams of {tournament.team_size} are drawn when the tournament starts."
        fields = [EmbedField(name=f"Players ({len(solo_players)})", value=mentions(solo_players))]
    else:
        how = (
            f"Captains enter a team of up to {tournament.team_size} players with {enter}, "
            f"then add their players with {entry_add}."
        )
        fields = [EmbedField(name=name, value=mentions(players)) for name, players in rosters.items()][:MAX_EMBED_FIELDS]
    status = "open" if tournament.status is TournamentStatus.SIGNUP else tournament.status.value
    return Embed(title=f"🏆 {tournament.name}", description=f"{how}\nSign-up is {status}.", fields=fields)


def signup_buttons(
    join: ComponentHandler,
    leave: ComponentHandler,
    participants: ComponentHandler,
    tournament: Tournament,
) -> list[ActionRow]:
    """Return the Join, Leave and Participants buttons under a sign-up card.

    Captains' tournaments join by command, not button, so they have no Join button.
    """
    tournament_id = tournament.id or 0
    buttons = [
        Button(style=ButtonStyle.DANGER, label="Leave", custom_id=leave.custom_id(tournament_id)),
        Button(style=ButtonStyle.SECONDARY, label="Participants", custom_id=participants.custom_id(tournament_id)),
    ]
    if tournament.mode is TeamMode.SOLO:
        buttons.insert(0, Button(style=ButtonStyle.SUCCESS, label="Join", custom_id=join.custom_id(tournament_id)))
    return [ActionRow(components=buttons)]


def participants_embed(
    tournament: Tournament,
    rosters: Mapping[str, Sequence[Snowflake]],
    solo_players: Sequence[Snowflake],
) -> Embed:
    """Return everyone signed up to ``tournament``: one line per player, or one line per team with its players."""
    if tournament.mode is TeamMode.SOLO:
        count = len(solo_players)
        lines = [f"<@{user_id}>" for user_id in solo_players]
    else:
        count = sum(len(players) for players in rosters.values())
        lines = [
            f"**{name}** ({len(players)}/{tournament.team_size}): {', '.join(f'<@{user_id}>' for user_id in players) or '—'}"
            for name, players in rosters.items()
        ]
    text = truncate("\n".join(lines) or "Nobody has signed up yet.", MAX_EMBED_DESCRIPTION_LENGTH)
    return Embed(title=f"🏆 {tournament.name}: {count} participant{'' if count == 1 else 's'}", description=text)


def _team(names: Mapping[int, str], entry_id: int | None, *, bye: bool) -> str:
    if entry_id is None:
        return "bye" if bye else "TBD"
    return names.get(entry_id, f"Team {entry_id}")


def match_line(match: TournamentMatch, names: Mapping[int, str]) -> str:
    """Return one line of the bracket: the match's number, its teams, and its state or winner."""
    bye = match.round == 0
    teams = f"{_team(names, match.entry_a_id, bye=False)} vs {_team(names, match.entry_b_id, bye=bye)}"
    if match.phase.decided and match.winner_id is not None:
        return f"`#{match.id}` {teams} — 🏆 {names.get(match.winner_id, '?')}"
    return f"`#{match.id}` {teams} — {PHASE_LABELS[match.phase]}"


def bracket_embed(tournament: Tournament, matches: Sequence[TournamentMatch], names: Mapping[int, str]) -> Embed:
    """Return the bracket: every round's matches, and the champion once there is one."""
    rounds = max((match.round for match in matches), default=0) + 1
    fields = [
        EmbedField(
            name=round_name(round_, rounds),
            value=truncate(
                "\n".join(match_line(match, names) for match in matches if match.round == round_),
                MAX_EMBED_FIELD_VALUE_LENGTH,
            ),
        )
        for round_ in range(rounds)
    ]
    champion = tournament.winner_entry_id
    description = f"🏆 Champion: **{names.get(champion, '?')}**" if champion is not None else "Single elimination."
    return Embed(title=f"{tournament.name} — bracket", description=description, fields=fields)


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
    following = match.phase.next
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
