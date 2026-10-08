<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_cogs.utility` (wd-cogs)
Package for utility cogs.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_cogs.utility` — `wd-cogs/src/wd_cogs/utility/__init__.py`

- exports: Invite, Team, Uptime

## `wd_cogs.utility.invite` — `wd-cogs/src/wd_cogs/utility/invite.py`
Module containing the invite cog for the bot.

### `class Invite(GroupCog, auto_load=True)`
Cog for inviting the bot to a guild or getting support.

- `@app_commands.command async slash_invite(interaction: discord.Interaction) -> None` — Send a message with the bot's invite link.
- `@app_commands.command async slash_support(interaction: discord.Interaction) -> None` — Send a message with the bot's support guild invite link.

## `wd_cogs.utility.team` — `wd-cogs/src/wd_cogs/utility/team.py`
Module for managing teams and respective voice channels.

### `class TeamDict(TypedDict)`
Dictionary representing a team.

- fields: id: int, members: list[Member]

### `@app_commands.guild_only class Team(GroupCog, auto_load=True)`
A cog for managing teams and respective voice channels.

- attributes: team_cleanup_interval
- `@loop async delete_empty_team_channels() -> None` — Delete any empty team channel.
- `@delete_empty_team_channels.before_loop async before_update() -> None` — Wait until the bot is ready. before cleaning up empty channels.
- `async cog_load() -> None` — Start the cog.
- `split_teams(team_count: int, members: list[Member]) -> list[TeamDict]` — Split a team evenly around :param:`team_count`.
- `async move_team(team: TeamDict, channel: VoiceChannel) -> None` — Move a whole team to its channel.
- `async create_team_channels(teams: list[TeamDict], category: CategoryChannel) -> tuple[list[Channels], list[VoiceChannel]]` — Create team channels based on a list of teams, adds those channels to database.
- `get_team_channels(guild: Guild) -> Sequence[Channels]` — Get all team channels from database.
- `get_teams_category(guild: Guild) -> CategoryChannel | None` — Find a category channel.
- `async create_teams_category(guild: Guild) -> CategoryChannel` — Create a category channel, and a lobby voice channel.
- `async fetch_teams_category(guild: Guild) -> CategoryChannel` — Find a category channel, if it doesn't find any, create it.
- `get_teams_lobby(guild: Guild) -> VoiceChannel | None` — Find a lobby channel.
- `async create_teams_lobby(category: CategoryChannel) -> VoiceChannel` — Create a lobby channel.
- `async fetch_teams_lobby(category: CategoryChannel) -> VoiceChannel` — Find a lobby channel, if not found create it.
- `async move_from_category(teams: list[TeamDict], channel: VoiceChannel) -> None` — Handle moving members, if member not in teams lobby, they won't get moved.
- `@app_commands.checks.has_permissions @app_commands.command async slash_team_lobby(interaction: discord.Interaction) -> None` — Find the lobby channel, or creates one for teams.
- `async send_lobby_info(interaction: Interaction) -> None` — Send lobby info to user.
- `async fetch_and_send_lobby_info(interaction: Interaction) -> None` — Fetch the lobby and then send it to the user.
- `@app_commands.command async slash_team_voice(interaction: discord.Interaction, team_count: int=2) -> None` — Create teams based on players in the user's voice channel, and move them to their respective channels.
- `@app_commands.command async slash_team_text(interaction: discord.Interaction, team_count: int=2) -> None` — Create teams based players in the user's voice channel, and send them in a message showing the teams.

## `wd_cogs.utility.uptime` — `wd-cogs/src/wd_cogs/utility/uptime.py`
Module containing a cog for showing bot uptime.

### `class Uptime(GroupCog, auto_load=True)`
Cog for showing the bot's uptime.

- `@app_commands.command async slash_uptime_bot(interaction: discord.Interaction) -> None` — Send a message with the bot's current uptime.
