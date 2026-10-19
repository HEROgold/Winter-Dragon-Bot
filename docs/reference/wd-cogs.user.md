<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_cogs.user` (wd-cogs)
Package for user cogs.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_cogs.user` — `wd-cogs/src/wd_cogs/user/__init__.py`

- exports: Fuel, Reminder

## `wd_cogs.user.car_fuel` — `wd-cogs/src/wd_cogs/user/car_fuel.py`
Module for storing and managing fuel data.

### `class Fuel(GroupCog, auto_load=True)`
Cog for managing fuel data.

- attributes: graph
- `@app_commands.command @app_commands.describe async slash_add(interaction: discord.Interaction, price: float, distance: float, amount: float) -> None` — Store some data about tanking fuel.
- `@graph.command async slash_efficiency(interaction: discord.Interaction) -> None` — Show a graph showing distance traveled per fuel.

## `wd_cogs.user.guild_creator` — `wd-cogs/src/wd_cogs/user/guild_creator.py`
Module to help users create a new guild.

### `class GuildCreator(GroupCog, auto_load=False)`
Cog for creating a new guild.

- attributes: INIT_NAME, WEEK, guild_check_interval
- `@Cog.listener async on_member_join(member: discord.Member) -> None` — Listen for when a member joins the guild.
- `async cog_load() -> None` — Load the cog.
- `@app_commands.checks.cooldown @app_commands.command async slash_generate(interaction: discord.Interaction, name: str, invite_code: str | None=None, *, discoverable: bool=True, disable_invites: bool=True, disable_widget: bool=True) -> None` — Update the current guild for the user, then invite the user.

## `wd_cogs.user.reminder` — `wd-cogs/src/wd_cogs/user/reminder.py`
Module for reminding users of things.

- module names: WEEKS_IN_MONTH

### `class Reminder(Cog, auto_load=True)`
Cog for setting reminders.

- attributes: check_interval
- `async cog_load() -> None` — Load the cog.
- `@loop async send_reminder() -> None` — Task to send reminders to users.
- `@send_reminder.before_loop async before_send_reminder() -> None` — Wait until the bot is ready before starting the loop.
- `@app_commands.command async slash_reminder(interaction: discord.Interaction, reminder: str, minutes: int=0, hours: int=0, days: int=0) -> None` — Set a reminder for the user.
- `@app_commands.command async slash_repeat_reminder(interaction: discord.Interaction, reminder: str, minutes: int=0, hours: int=0, days: int=0, weeks: int=0, years: int=0) -> None` — Set a repeating reminder for the user.
- `@app_commands.command async slash_remove_reminder(interaction: discord.Interaction, reminder: str) -> None` — Let a user remove any of their reminders.
- `@slash_remove_reminder.autocomplete async autocomplete_active_reminders(interaction: discord.Interaction, current: str) -> list[Choice]` — Autocomplete active reminders for the user.

## `wd_cogs.user.urban` — `wd-cogs/src/wd_cogs/user/urban.py`
Urban Dictionary cog for Discord bot.

- module names: UD_DEFINE_URL, UD_RANDOM_URL

### `class Urban(GroupCog, auto_load=True)`
Urban Dictionary cog for Discord bot.

- attributes: allow_random, max_size
- `@app_commands.command async slash_urban_random(interaction: discord.Interaction) -> None` — Get a random definition from the Urban Dictionary.
- `@app_commands.command async slash_urban(interaction: discord.Interaction, query: str) -> None` — Search for a word in the Urban Dictionary.
