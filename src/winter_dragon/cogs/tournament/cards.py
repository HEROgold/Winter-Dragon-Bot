"""The messages a tournament shows: its sign-up card, bracket, match cards and votes, with their buttons."""

from __future__ import annotations

lazy from itertools import batched
lazy from typing import TYPE_CHECKING

lazy from wd_discord.components import MAX_ACTION_ROW_BUTTONS, ActionRow, Button, ButtonStyle
lazy from wd_discord.embed import Embed, EmbedField

lazy from .bracket import round_name, tally
lazy from .models import DraftKind, MatchPhase, TeamMode, TournamentStatus


if TYPE_CHECKING:
    lazy from collections.abc import Mapping, Sequence

    lazy from wd_bot.components import ComponentHandler

    lazy from .models import DraftChoice, MatchVote, Tournament, TournamentMatch


MAX_FIELD_LENGTH = 1024
"""Discord's limit on an embed field's value."""
PHASE_LABELS = {
    MatchPhase.WAITING: "⏳ Waiting for teams",
    MatchPhase.READY: "🟦 Ready",
    MatchPhase.BAN: "🚫 Bans",
    MatchPhase.PICK: "✅ Picks",
    MatchPhase.LIVE: "🔴 Live",
    MatchPhase.FINISHED: "🏁 Finished",
    MatchPhase.FORFEIT: "🏳️ Forfeit",
}


def mentions(user_ids: Sequence[int]) -> str:
    """Return the users as mentions, or a dash for nobody; cut to fit an embed field."""
    text = ", ".join(f"<@{user_id}>" for user_id in user_ids) or "—"
    return text if len(text) <= MAX_FIELD_LENGTH else text[: MAX_FIELD_LENGTH - 1] + "…"


def signup_embed(tournament: Tournament, rosters: Mapping[str, Sequence[int]], solo_players: Sequence[int]) -> Embed:
    """Return the sign-up card: the format, and who signed up, alone or per team."""
    if tournament.mode is TeamMode.SOLO:
        how = f"Sign up alone; teams of {tournament.team_size} are drawn when the tournament starts."
        fields = [EmbedField(name=f"Players ({len(solo_players)})", value=mentions(solo_players))]
    else:
        how = f"Captains register a team of up to {tournament.team_size} players and add their teammates."
        fields = [EmbedField(name=name, value=mentions(players)) for name, players in rosters.items()][:25]
    status = "open" if tournament.status is TournamentStatus.SIGNUP else tournament.status.value
    return Embed(title=f"🏆 {tournament.name}", description=f"{how}\nSign-up is {status}.", fields=fields)


def signup_buttons(join: ComponentHandler, leave: ComponentHandler, tournament: Tournament) -> list[ActionRow]:
    """Return the Join and Leave buttons under a sign-up card; captains' tournaments join by command, not button."""
    buttons = [Button(style=ButtonStyle.DANGER, label="Leave", custom_id=leave.custom_id(tournament.id or 0))]
    if tournament.mode is TeamMode.SOLO:
        buttons.insert(0, Button(style=ButtonStyle.SUCCESS, label="Join", custom_id=join.custom_id(tournament.id or 0)))
    return [ActionRow(components=buttons)]


def _team(names: Mapping[int, str], team_id: int | None, *, bye: bool) -> str:
    if team_id is None:
        return "bye" if bye else "TBD"
    return names.get(team_id, f"Team {team_id}")


def match_line(match: TournamentMatch, names: Mapping[int, str]) -> str:
    """Return one line of the bracket: the match's number, its teams, and its state or winner."""
    bye = match.round == 0
    teams = f"{_team(names, match.team_a_id, bye=False)} vs {_team(names, match.team_b_id, bye=bye)}"
    if match.phase.decided and match.winner_id is not None:
        return f"`#{match.id}` {teams} — 🏆 {names.get(match.winner_id, '?')}"
    return f"`#{match.id}` {teams} — {PHASE_LABELS[match.phase]}"


def bracket_embed(tournament: Tournament, matches: Sequence[TournamentMatch], names: Mapping[int, str]) -> Embed:
    """Return the bracket: every round's matches, and the champion once there is one."""
    rounds = max((match.round for match in matches), default=0) + 1
    fields = [
        EmbedField(
            name=round_name(round_, rounds),
            value="\n".join(match_line(match, names) for match in matches if match.round == round_)[:MAX_FIELD_LENGTH],
        )
        for round_ in range(rounds)
    ]
    champion = tournament.winner_team_id
    description = f"🏆 Champion: **{names.get(champion, '?')}**" if champion is not None else "Single elimination."
    return Embed(title=f"{tournament.name} — bracket", description=description, fields=fields)


def match_embed(
    match: TournamentMatch,
    rounds: int,
    names: Mapping[int, str],
    rosters: Mapping[int, Sequence[int]],
    drafts: Sequence[DraftChoice],
) -> Embed:
    """Return a match card: its round, phase, the teams' players, and what each team banned and picked."""
    fields: list[EmbedField] = []
    for team_id in (match.team_a_id, match.team_b_id):
        if team_id is None:
            continue
        own = [draft for draft in drafts if draft.team_id == team_id]
        bans = ", ".join(draft.value for draft in own if draft.kind is DraftKind.BAN) or "—"
        picks = ", ".join(draft.value for draft in own if draft.kind is DraftKind.PICK) or "—"
        value = f"{mentions(rosters.get(team_id, []))}\nBans: {bans}\nPicks: {picks}"
        fields.append(EmbedField(name=names.get(team_id, "?"), value=value[:MAX_FIELD_LENGTH], inline=True))
    title = f"Match #{match.id} — {round_name(match.round, rounds)}"
    description = PHASE_LABELS[match.phase]
    if match.phase.decided and match.winner_id is not None:
        description += f": **{names.get(match.winner_id, '?')}** wins"
    return Embed(title=title, description=description, fields=fields)


def match_buttons(handler: ComponentHandler, match: TournamentMatch, names: Mapping[int, str]) -> list[ActionRow]:
    """Return the organiser's controls under a match card: next phase, report a winner, or a forfeit."""
    if match.phase.decided or match.team_a_id is None or match.team_b_id is None or match.id is None:
        return []
    teams = (match.team_a_id, match.team_b_id)
    rows: list[ActionRow] = []
    following = match.phase.next
    if following is not None:
        label = f"Next: {PHASE_LABELS[following]}"
        rows.append(
            ActionRow(
                components=[Button(style=ButtonStyle.PRIMARY, label=label, custom_id=handler.custom_id(match.id, "next"))],
            ),
        )
    if match.phase is MatchPhase.LIVE:
        wins = [
            Button(
                style=ButtonStyle.SUCCESS,
                label=f"{names.get(team, '?')} won"[:80],
                custom_id=handler.custom_id(match.id, "win", team),
            )
            for team in teams
        ]
        rows.append(ActionRow(components=wins))
    forfeits = [
        Button(
            style=ButtonStyle.DANGER,
            label=f"{names.get(team, '?')} forfeits"[:80],
            custom_id=handler.custom_id(match.id, "forfeit", team),
        )
        for team in teams
    ]
    rows.append(ActionRow(components=forfeits))
    return rows


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
