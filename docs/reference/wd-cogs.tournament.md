<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_cogs.tournament` (wd-cogs)
Tournament extension package.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_cogs.tournament.controller` — `wd-cogs/src/wd_cogs/tournament/controller.py`
Tournament Cog for announcements and match status management.

- module names: STATUS_SEQUENCE: tuple[MatchStatus, ...]

### `class TournamentStatusView(discord.ui.View)`
Interactive controls for a tournament status card.

- `@discord.ui.button async advance_phase(interaction: discord.Interaction, _: discord.ui.Button[TournamentStatusView]) -> None`
- `@discord.ui.button async announce_status(interaction: discord.Interaction, _: discord.ui.Button[TournamentStatusView]) -> None`
- `@discord.ui.button async reset_status(interaction: discord.Interaction, _: discord.ui.Button[TournamentStatusView]) -> None`

### `class Tournament(GroupCog, auto_load=True)`
Manage tournament announcements and match state transitions.

- `get_match(guild_id: int) -> MatchInformation` — Return the tracked match for a guild, creating a default record when needed.
- `build_status_embed(match: MatchInformation, guild: discord.Guild | None=None) -> discord.Embed` — Build a visually clear status card for a tournament match.
- `async advance_match(match: MatchInformation) -> None` — Advance a match to the next phase, preferring the configured state machine when available.
- `async set_match_status(match: MatchInformation, status: MatchStatus) -> None` — Set a match to a specific status.
- `@app_commands.command @app_commands.guild_only async tournament_status(interaction: discord.Interaction) -> None` — Show the current tournament status in an ephemeral message with controls for advancing and announcing.
- `@app_commands.command @app_commands.guild_only async tournament_announce(interaction: discord.Interaction) -> None` — Announce the current tournament status in the channel, without controls.

## `wd_cogs.tournament.match_information` — `wd-cogs/src/wd_cogs/tournament/match_information.py`

### `@dataclass class Player`

- fields: name: str, intended_pick: str

### `@dataclass class Teams`

- fields: players: list[Player]

### `@dataclass class MatchInformation`

- fields: teams: list[Teams], status: MatchStatus, controller: object

## `wd_cogs.tournament.status` — `wd-cogs/src/wd_cogs/tournament/status.py`
Module for managing the status of a tournament match using a state machine.

- module names: match_controller

### `class MatchStatus(Enum)`
Enum representing the different statuses a match can be in.

- attributes: PRE, FORMING_TEAMS, BAN_PHASE, SELECT_PHASE, IN_PROGRESS, POST, FORFEIT

### `class Events(Enum)`
Events that can occur during a match, used for state transitions in the state machine.

- attributes: FORM_TEAMS, BAN, SELECT, START, GAME_ENDED, FORFEIT

### `@dataclass class Context`
Context for a match, can hold any relevant information about the match.

## `wd_cogs.tournament.store` — `wd-cogs/src/wd_cogs/tournament/store.py`
Shared tournament registry for Discord and API surfaces.

- module names: registry

### `@dataclass class TournamentSnapshot`
Serializable tournament view for the API layer.

- fields: guild_id: int, status: MatchStatus, teams: list[Teams]

### `class TournamentRegistry`
In-memory registry for tournament match state.

- `get_match(guild_id: int) -> MatchInformation`
- `snapshot(guild_id: int) -> TournamentSnapshot`
