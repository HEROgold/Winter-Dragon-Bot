<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `winter_dragon.cogs` (winter-dragon)
Cogs for the winter_dragon example bot (see run_test_bot.py).

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `winter_dragon.cogs` — `src/winter_dragon/cogs/__init__.py`

- `import_cogs() -> None` — Import every module the bot loads as an extension, so each feature and table the cogs define is known.

## `winter_dragon.cogs.auto_reassign` — `src/winter_dragon/cogs/auto_reassign.py`
The /autoreassign command group: a member who leaves and rejoins a guild gets their roles back.

- module names: REASSIGN_REASON, AUTO_REASSIGN_TABLES
- `is_enabled(session: Session, guild_id: Snowflake) -> bool` — Whether the guild ``guild_id`` gives rejoining members their roles back.
- `guild_setting(session: Session, guild_id: Snowflake) -> AutoReassignGuild | None` — Return the alive row turning giving roles back on in the guild ``guild_id``, if any.
- `remembered_roles(session: Session, guild_id: Snowflake, user_id: Snowflake | None=None) -> Generator[RememberedRole]` — Yield the roles remembered in the guild ``guild_id``: of the member ``user_id``, or of everyone without one.
- `forget(session: Session, guild_id: Snowflake, user_id: Snowflake | None=None) -> list[RememberedRole]` — Soft-delete the roles :func:`remembered_roles` yields, and return them; the caller commits.
- `giveable(bot: PermissionSolver, role_ids: Iterable[Snowflake]) -> Generator[Snowflake]` — Yield the roles of ``role_ids`` the bot may give: still in the guild, not managed, and below its highest role.

### `class AutoReassignGuild(DiscordKeyedModel, table=True)`
A guild that gives rejoining members their roles back; ``id`` is the guild's.

- fields: ownership: ClassVar[Ownership]

### `class RememberedRole(LifecycleModel, table=True)`
A role a member had when they left a guild that gives roles back.

- fields: ownership: ClassVar[Ownership], natural_key: ClassVar[tuple[str, ...]], guild_id: int, user_id: int, role_id:
  int

### `class AutoReassign(GroupCog, name='autoreassign', description='Give members who leave and rejoin the roles they had', default_member_permissions=Permissions.MANAGE_ROLES, contexts=[InteractionContextType.GUILD])`
Remembers a leaving member's roles, and gives them back when they rejoin.

- `async load() -> None` — Create the auto-reassign tables if missing.
- `@Cog.listener async on_member_remove(event: MemberRemove) -> None` — Remember the roles of a member leaving a guild that gives roles back, replacing what was remembered.
- `@Cog.listener async on_member_add(member: Member) -> None` — Give a rejoining member the roles remembered from when they left, then forget them.
- `@Cog.command async enable(interaction: GuildCommandInteraction) -> None` — Start remembering leaving members' roles in this guild; needs MANAGE_ROLES.
- `@Cog.command async disable(interaction: GuildCommandInteraction) -> None` — Stop remembering roles in this guild, and forget those remembered; needs MANAGE_ROLES.

## `winter_dragon.cogs.autochannel` — `src/winter_dragon/cogs/autochannel.py`
The /autochannel command group: joining a guild's hub voice channel gives a member a voice channel of their own.

- module names: OWNER_PERMISSIONS, CREATE_REASON, AUTOCHANNEL_TABLES
- `owner_overwrite(user_id: Snowflake) -> OverwriteParams` — Return the overwrite letting the member ``user_id`` run their own channel.
- `default_name(display_name: str) -> str` — Return the name of a member's channel when they didn't choose one.
- `channel_params(member: Member, parent_id: Snowflake | None, settings: AutoChannelSettings, remembered: Iterable[OverwriteParams]=()) -> GuildChannelParams` — Return ``member``'s new channel: under ``parent_id``, named and limited as their ``settings`` say.
- `hub_of(session: Session, guild_id: Snowflake) -> AutoChannelHub | None` — Return the guild ``guild_id``'s hub, if it has one.
- `owned_channel(session: Session, guild_id: Snowflake, owner_id: Snowflake) -> AutoChannel | None` — Return the automatic channel the member ``owner_id`` has in the guild ``guild_id``, if any.
- `remembered_overwrites(session: Session, guild_id: Snowflake, owner_id: Snowflake) -> list[AutoChannelOverwrite]` — Return the overwrites the member ``owner_id`` set on their channel in the guild ``guild_id``.
- `remember_overwrites(session: Session, record: AutoChannel, overwrites: Iterable[PermissionOverwrite]) -> None` — Make the overwrites remembered for ``record``'s owner exactly ``overwrites``, minus the owner's own; caller commits.
- `usable_overwrites(rows: Iterable[AutoChannelOverwrite], role_ids: Container[Snowflake] | None) -> list[OverwriteParams]` — Return ``rows`` as overwrites to set, without those for roles not in ``role_ids`` (``None`` if unknown: all stay).
- `settings_of(session: Session, user_id: Snowflake) -> AutoChannelSettings` — Return the member ``user_id``'s channel settings; new defaults, not in ``session``, when they have none.

### `class AutoChannelHub(DiscordKeyedModel, table=True)`
A guild's hub: the voice channel that gives whoever joins it a channel of their own; ``id`` is the guild's.

- fields: ownership: ClassVar[Ownership], channel_id: int, max_channels: int

### `class AutoChannel(DiscordKeyedModel, table=True)`
A member's automatic channel; ``id`` is the channel's.

- fields: ownership: ClassVar[Ownership], guild_id: int, owner_id: int

### `class AutoChannelSettings(DiscordKeyedModel, table=True)`
How a member wants their automatic channels: its name and user limit, in every guild; ``id`` is the member's.

- fields: ownership: ClassVar[Ownership], name: str | None, user_limit: int

### `class AutoChannelOverwrite(LifecycleModel, table=True)`
A permission overwrite a member set on their automatic channel in a guild, for their next channel there.

- fields: ownership: ClassVar[Ownership], natural_key: ClassVar[tuple[str, ...]], guild_id: int, owner_id: int,
  target_id: int, target_type: int, allow: int, deny: int

### `class AutoChannels(GroupCog, name='autochannel', description='Voice channels of your own, made by joining the hub channel', contexts=[InteractionContextType.GUILD])`
Gives a member who joins the hub their own voice channel, and deletes it once it's empty.

- `@property channels -> EmptiedChannels[AutoChannel]` — The automatic channels, deleted once empty.
- `async load() -> None` — Create the autochannel tables if missing.
- `@Cog.listener async on_guild_create(guild: GatewayGuild) -> None` — Learn who is in which voice channel, then delete the automatic channels that emptied while offline.
- `@Cog.listener async on_voice_state_update(state: VoiceState) -> None` — Give a member joining the hub their own channel, and delete an automatic channel the member left empty.
- `@Cog.listener async on_channel_update(channel: Channel) -> None` — Remember the name, user limit and permission overwrites an owner gave their automatic channel, for the next.
- `async give_channel(member: Member | PartialMember, hub: AutoChannelHub) -> None` — Move ``member`` into their automatic channel, creating it next to ``hub`` when they have none.
- `async create_channel(member: Member | PartialMember, hub: AutoChannelHub, settings: AutoChannelSettings, remembered: Iterable[AutoChannelOverwrite]=()) -> NetworkError | None` — Create ``member``'s channel in the hub's category, remember it and move them into it.
- `async delete_channel(channel: AutoChannel) -> None` — Delete the automatic ``channel`` and forget it once it's gone; one that's left is tried again later.
- `@Cog.command async setup(interaction: GuildCommandInteraction, category_name: str, hub_name: str) -> None` — Create the category ``category_name`` holding the hub voice channel ``hub_name``.
- `@Cog.command async mark(interaction: GuildCommandInteraction, channel: Channel) -> None` — Make ``channel`` the guild's hub, replacing the one it had.
- `@Cog.command async guild_limit(interaction: GuildCommandInteraction, limit: int) -> None` — Allow at most ``limit`` automatic channels at once, 0 for no limit.
- `@Cog.command async set_limit(interaction: GuildCommandInteraction, limit: int) -> None` — Remember ``limit`` as the invoker's user limit, and apply it to their channel here if they have one.
- `@Cog.command async set_name(interaction: GuildCommandInteraction, name: str) -> None` — Remember ``name`` as the invoker's channel name, and rename their channel here if they have one.

## `winter_dragon.cogs.bot_commands` — `src/winter_dragon/cogs/bot_commands.py`
Admin command group for inspecting and forcing the application-command sync state.

- `describe_sync_status(registry: CommandRegistry) -> Generator[str]` — Yield one "name (scope): synced|pending" line per registered command, scope by scope.

### `class BotCommands(GroupCog, name='bot-commands', description="Inspect and manage the bot's application commands", default_member_permissions=Permissions.MANAGE_GUILD, contexts=[InteractionContextType.GUILD])`
Admin ``/bot-commands`` group for inspecting/managing application-command sync.

- `@Cog.command async list_commands(interaction: CommandInteraction) -> None` — Show every registered command's synced/pending state.
- `@Cog.command async resync(interaction: CommandInteraction) -> None` — Acknowledge within Discord's 3s window, then re-read every scope from Discord and sync it; owners only.

## `winter_dragon.cogs.bot_stats` — `src/winter_dragon/cogs/bot_stats.py`
The /botstats command: what the bot serves right now, for its owners; and the snapshot the dashboard reads.

- module names: MAX_SHARD_LINES
- `shard_line(shard: ShardStats) -> str` — Return one shard as ``#0 up, 42 ms``.
- `shards_value(stats: BotStats) -> str` — Return the embed's shard field: each shard, or only the dead ones when there are too many to list.
- `stats_embed(stats: BotStats) -> Embed` — Return ``stats`` as the /botstats reply.

### `class BotStatsSettings`
Settings for the bot stats, in their ``cogs.ini`` section.

- attributes: snapshot_interval

### `class BotStatsCommand(Cog)`
Shows the bot's owners what it serves: guilds, channels, members, shards and uptime.

- `async load() -> None` — Create the snapshot table if missing.
- `@Cog.periodic async store() -> None` — Store a snapshot for the dashboard.
- `@Cog.command async botstats(interaction: CommandInteraction) -> None` — Reply, privately, with a :class:`BotStats` snapshot; only the bot's owners may.

## `winter_dragon.cogs.channel_utils` — `src/winter_dragon/cogs/channel_utils.py`
The /channel-utils command group: delete a whole category, and lock or unlock a channel for a role or member.

- module names: UNLOCKABLE, DELETE_PERMISSIONS
- `locked_permissions(existing: Iterable[PermissionOverwrite], target: User | Role, *, lock: bool) -> tuple[Permissions, Permissions]` — Return what ``target``'s overwrite among ``existing`` allows and denies, with SEND_MESSAGES denied or not.

### `class ChannelUtils(GroupCog, name='channel-utils', description='Manage channels', default_member_permissions=Permissions.MANAGE_CHANNELS, contexts=[InteractionContextType.GUILD])`
Moderation helpers for channels: removing a category with its channels, and locking channels.

- `@Cog.command async delete_category(interaction: GuildCommandInteraction, category: Channel) -> None` — Delete every channel in ``category``, then the category itself.
- `@Cog.command async lock(interaction: GuildCommandInteraction, target: User | Role) -> None` — Deny ``target`` SEND_MESSAGES in the channel the command was used in.
- `@Cog.command async unlock(interaction: GuildCommandInteraction, target: User | Role) -> None` — Stop denying ``target`` SEND_MESSAGES in the channel the command was used in.

## `winter_dragon.cogs.fuel` — `src/winter_dragon/cogs/fuel.py`
The /fuel command group: log refuels, and graph fuel efficiency over time.

- `member_units(session: Session, user_id: Snowflake) -> FuelUnits` — Return the units ``user_id`` picked, or km/L when they never did.
- `parse_refuel_date(value: str) -> datetime | None` — Return midnight UTC of the ``YYYY-MM-DD`` day in ``value``, or ``None`` when it isn't one.
- `graphable(refuels: Sequence[CarFuels], units: FuelUnits=FuelUnits.KM_PER_L) -> list[tuple[datetime, float]]` — Return the ``(date, efficiency in units)`` of each of ``refuels`` that added fuel, oldest first.
- `render_efficiency_graph(refuels: Sequence[CarFuels], units: FuelUnits=FuelUnits.KM_PER_L) -> bytes` — Return a PNG line graph of the efficiency of ``refuels`` over time, oldest first; refuels without fuel are left out.

### `class FuelSettings`
Settings for /fuel, in its ``cogs.ini`` section.

- attributes: graph_width_inches, graph_height_inches, graph_filename

### `class FuelUnits(StrEnum)`
How a member wants fuel efficiency shown; refuels are stored as distance and amount either way.

- attributes: KM_PER_L, L_PER_100_KM
- `convert(km_per_l: float) -> float` — Return ``km_per_l`` in these units; a value of 0 or less has no L/100km, so it gives 0.

### `class FuelPreferences(DiscordKeyedModel, table=True)`
A member's fuel settings; ``id`` is their Discord user ID, and they own it.

- fields: ownership: ClassVar[Ownership], units: FuelUnits

### `class CarFuels(LifecycleModel, table=True)`
One refuel a user logged; ``user_id`` is their Discord user ID, and they own it.

- fields: ownership: ClassVar[Ownership], user_id: int, amount: float, distance: float, price: float, timestamp:
  datetime, refueled_at: datetime | None
- `@property refuel_date -> datetime` — When the refuel happened: ``refueled_at``, or the entry time when that is empty.
- `@property efficiency -> float` — Distance driven per unit of fuel (km/L).
- `efficiency_in(units: FuelUnits) -> float` — Return the efficiency of this refuel in ``units``.

### `class Fuel(GroupCog, name='fuel', description="Track your car's refuels and fuel efficiency")`
Logs a user's refuels and graphs their fuel efficiency.

- `async load() -> None` — Create the refuel table if missing.
- `@Cog.command async add(interaction: CommandInteraction, price: float, distance: float, amount: float, date: str | None=None) -> None` — Store a refuel for the invoking user, dated ``date`` (``YYYY-MM-DD``, UTC) or now.
- `@Cog.command async efficiency(interaction: CommandInteraction) -> None` — Reply with a graph of the invoking user's fuel efficiency.
- `async units_choices(interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]` — Suggest the units that contain what was typed.
- `@Cog.command async units(interaction: CommandInteraction, units: str) -> None` — Store the invoking user's fuel efficiency units.

## `winter_dragon.cogs.hangman.cards` — `src/winter_dragon/cogs/hangman/cards.py`
The message a hangman game shows, and its Guess button.

- module names: GALLOWS
- `drawing(wrong: int) -> str` — Return the gallows after ``wrong`` wrong guesses.
- `game_message(game: HangmanGame, participants: Sequence[int]=()) -> str` — Return the text of the game's message: the drawing, the word so far, the wrong guesses and, once over, the result.
- `guess_buttons(guess_button: ComponentHandler, game: HangmanGame) -> list[ActionRow]` — Return the row holding the Guess button of ``game``; none once the game is over.

## `winter_dragon.cogs.hangman.cog` — `src/winter_dragon/cogs/hangman/cog.py`
The /hangman command: start a game, and guess at it with a button and a modal.

- module names: MODAL_INPUT

### `class Hangman(Cog)`
Plays hangman in a channel: each game is one message, anyone may guess, and a channel can hold several.

- attributes: rng
- `async load() -> None` — Create the hangman tables if missing.
- `@Cog.command async hangman(interaction: GuildCommandInteraction) -> None` — Start a game: a message with a Guess button that anyone in the channel may use.
- `@Cog.component async guess_button(interaction: ComponentInteraction, game_id: str) -> None` — Open the modal for guessing a letter or the whole word.
- `@Cog.modal async guess_modal(interaction: ModalSubmitInteraction, game_id: str) -> None` — Apply the submitted guess to the game and update its message.

## `winter_dragon.cogs.hangman.models` — `src/winter_dragon/cogs/hangman/models.py`
The hangman tables: a game, and the members who took part in it.

- module names: MAX_WRONG_GUESSES, HANGMAN_TABLES

### `class HangmanStatus(StrEnum)`
Where a hangman game is: still being guessed, or over with a result.

- attributes: ACTIVE, WON, LOST

### `class HangmanGame(LifecycleModel, table=True)`
One hangman game in a channel, owned by its guild; it keeps its state while active and its result once over.

- fields: ownership: ClassVar[Ownership], guild_id: int, channel_id: int, word: str, letters: str, wrong_words: str,
  status: HangmanStatus, finished_at: datetime | None
- `@property wrong_letters -> str` — The guessed letters that are not in the word.
- `@property wrong_word_list -> list[str]` — The wrong whole-word guesses.
- `@property wrong_count -> int` — How many lives the game has cost: wrong letters plus wrong words.
- `@property masked -> str` — The word with the letters not guessed yet hidden as ``_``.
- `@property solved -> bool` — Whether every letter of the word was guessed.

### `class HangmanParticipant(LifecycleModel, table=True)`
A member who guessed a correct letter in a game; every Participant of a won game is credited.

- fields: ownership: ClassVar[Ownership], natural_key: ClassVar[tuple[str, ...]], game_id: int, user_id: int

## `winter_dragon.cogs.hangman.service` — `src/winter_dragon/cogs/hangman/service.py`
The rules of hangman: starting a game, and what a guess does to it.

- module names: WORDS_FILE
- `load_words() -> list[str]` — Return the words of the bundled list.
- `start_game(session: Session, *, guild_id: Snowflake, channel_id: Snowflake, rng: Random, words: list[str] | None=None) -> HangmanGame` — Store a new game in the channel with a word drawn from ``words`` (default: the bundled list).
- `parse_guess(text: str) -> str` — Return ``text`` as a guess: a single letter or a whole word, lowercase; refuse anything else.
- `guess(session: Session, game: HangmanGame, user_id: Snowflake, text: str) -> Guess` — Apply ``text`` (one letter or the whole word) from ``user_id`` to ``game``; the caller commits.
- `participants_of(session: Session, game: HangmanGame) -> list[int]` — Return the IDs of the members who took part in ``game``, in the order they joined.

### `class Guess(StrEnum)`
What a guess did to a game.

- attributes: CORRECT_LETTER, WRONG_LETTER, CORRECT_WORD, WRONG_WORD

## `winter_dragon.cogs.health` — `src/winter_dragon/cogs/health.py`
Tells the container's healthcheck that the bot is connected to Discord; see :mod:`winter_dragon.health`.

- module names: TOUCH_INTERVAL

### `class Health(Cog)`
Touches :data:`~winter_dragon.health.ALIVE_FILE` every :data:`TOUCH_INTERVAL` while every shard is alive.

- `@Cog.periodic async touch_alive_file() -> None` — Touch the alive file, but only while :attr:`~wd_discord.gateway.sharding.ShardManager.alive`.

## `winter_dragon.cogs.heartbeat` — `src/winter_dragon/cogs/heartbeat.py`
A cog demonstrating independent background work, not just reacting to dispatch events.

### `class HeartbeatSettings`
Settings for the heartbeat, in its ``cogs.ini`` section.

- attributes: interval

### `class Heartbeat(Cog)`
Logs "still alive" every :attr:`HeartbeatSettings.interval` seconds for as long as the cog is loaded.

- `@Cog.periodic async beat() -> None` — Log a heartbeat; the bot repeats it at the configured interval and stops when the cog unloads.

## `winter_dragon.cogs.invite` — `src/winter_dragon/cogs/invite.py`
The /invite command group: invite the bot to a guild, or join the support guild.

- module names: NO_SUPPORT_INVITE
- `async invite_channel(client: Client, guild_id: Snowflake) -> BaseChannel | NetworkError | None` — Return the channel to invite people to in the guild ``guild_id``: its system channel, else its first text channel.

### `class InviteSettings`
Settings for /invite, in its ``cogs.ini`` section.

- attributes: support_invite_max_age

### `class Invite(GroupCog, name='invite', description='Invite the bot to your guild, or join its support guild')`
Cog for inviting the bot to a guild or getting support.

- `@Cog.command async bot_invite(interaction: CommandInteraction) -> None` — Reply with the link that adds the bot to a guild.
- `@Cog.command async support_invite(interaction: CommandInteraction) -> None` — Reply with a single-use, short-lived invite to the support guild.

## `winter_dragon.cogs.message_logger` — `src/winter_dragon/cogs/message_logger.py`
A cog that logs real gateway dispatch events at DEBUG level.

### `class MessageLogger(Cog)`
Logs every READY/MESSAGE_CREATE/GUILD_CREATE it's dispatched, at DEBUG level.

- `@Cog.listener async on_ready(ready: Ready) -> None` — Log a shard's READY.
- `@Cog.listener async on_message_create(message: Message) -> None` — Log a dispatched MESSAGE_CREATE event.
- `@Cog.listener async on_guild_create(guild: Guild) -> None` — Log a dispatched GUILD_CREATE event.

## `winter_dragon.cogs.metrics` — `src/winter_dragon/cogs/metrics.py`
Serves the bot's Prometheus metrics on ``/metrics``; see :mod:`winter_dragon.metrics`.

### `class Metrics(Cog)`
Starts the ``/metrics`` endpoint with the bot's stats, timings and gateway event counts.

- `async load() -> None` — Serve the bot's metrics, read from this cog's bot at each scrape.

## `winter_dragon.cogs.percentage` — `src/winter_dragon/cogs/percentage.py`
A cog with a single command: a random compatibility percentage between two users.

- `record_check(session: Session, user_id: Snowflake, target_id: Snowflake, target_name: str) -> CompatibilityCheck` — Store that ``user_id`` checked ``target_id``, or refresh the earlier check of the same pair; the caller commits.
- `calculate_percentage(user_id_a: Snowflake, user_id_b: Snowflake) -> int` — Compute a random 0-100 percentage, seeded by both user IDs (order-independent).
- `build_love_embed(target: User, percent: int) -> Embed` — Build the "Love Meter" embed for ``target`` with the given compatibility ``percent``.

### `class PercentageSettings`
Settings for /love, in its ``cogs.ini`` section.

- attributes: love_color

### `class CompatibilityCheck(LifecycleModel, table=True)`
A member's check of their compatibility with another user; ``user_id`` is the member who asked, and they own it.

- fields: ownership: ClassVar[Ownership], natural_key: ClassVar[tuple[str, ...]], user_id: int, target_id: int,
  target_name: str, checked_at: datetime

### `class Love(Cog)`
Cog for the /love command.

- `async load() -> None` — Create the compatibility check table if missing.
- `@Cog.command async love(interaction: CommandInteraction, user: User) -> None` — Reply with a random compatibility love between the invoking user and ``user``.

## `winter_dragon.cogs.privacy.cog` — `src/winter_dragon/cogs/privacy/cog.py`
Privacy: soft-deleted records are purged for good once they've been deleted for :data:`RETENTION`.

- `command_path(interaction: CommandInteraction) -> str` — Return the full name of the command ``interaction`` ran, with its group and subcommand: ``reminder add``.

### `class Privacy(Cog)`
Purges soft-deleted records daily, and hides the data of departed guilds and of members who asked.

- `async load() -> None` — Create the privacy tables; the bot then starts :meth:`purge_daily`.
- `@Cog.periodic async purge_daily() -> None` — Purge what's due now; the bot repeats it every :data:`PURGE_INTERVAL` while the cog is loaded.
- `@Cog.listener async on_guild_delete(event: GuildDelete) -> None` — Hide the data of a guild that removed the bot; a guild that only went offline keeps it.
- `@Cog.listener async on_guild_create(guild: GatewayGuild) -> None` — Bring back the data a guild had when it removed the bot, if it's back within :data:`RETENTION`.
- `async request_deletion(member_id: Snowflake, now: datetime) -> None` — Hide all of the member ``member_id``'s data at ``now`` (:func:`hide_member_data`); :meth:`purge` deletes it later.
- `deletion_steps(member_id: Snowflake) -> Generator[tuple[DeletionStep, datetime]]` — Yield the steps the member ``member_id``'s deletion request got through, with when, in order.
- `@Cog.listener async on_interaction(interaction: AnyInteraction) -> None` — Count a run of an application command; autocomplete and component interactions don't count.
- `usage(member_id: Snowflake) -> Generator[UsageCount]` — Yield the member ``member_id``'s command usage counts, day by day.
- `async purge(now: datetime) -> None` — Hard-delete every lifecycle row soft-deleted more than :data:`RETENTION` before ``now``, children first.

## `winter_dragon.cogs.privacy.domain` — `src/winter_dragon/cogs/privacy/domain.py`
The privacy tables, and the rules for hiding a member's or a guild's data, for the privacy cog and the dashboard.

- module names: RETENTION, PURGE_INTERVAL, USAGE_RETENTION, PRIVACY_TABLES
- `purge_order(models: Iterable[type[LifecycleModel]]) -> list[type[LifecycleModel]]` — Return ``models`` children first: a table that points at another (by foreign key) comes before it.
- `stored_models(bind: Engine | Connection) -> list[type[LifecycleModel]]` — Return every lifecycle model whose table exists in ``bind``, children first.
- `hide_owned(session: Session, models: Iterable[type[LifecycleModel]], now: datetime, *, member: Snowflake | None=None, guild: Snowflake | None=None) -> None` — Soft-delete at ``now`` every alive row of ``models`` owned by ``member`` and/or ``guild``.
- `anonymise_member(session: Session, models: Iterable[type[LifecycleModel]], member_id: Snowflake) -> None` — Replace ``member_id`` with :data:`~wd_db.extension.lifecycle.DELETED_MEMBER` in every alive row's anonymised columns.
- `hide_member_data(bind: Engine | Connection, member_id: Snowflake, now: datetime) -> bool` — Hide all of the member ``member_id``'s data at ``now``, for their deletion request; ``False`` if it was already.
- `deletion_steps(bind: Engine | Connection, member_id: Snowflake) -> Generator[tuple[DeletionStep, datetime]]` — Yield the steps the member ``member_id``'s deletion request got through, with when, in order.

### `class DepartedGuild(DiscordKeyedModel, table=True)`
A guild that removed the bot, whose data is hidden until it's back or purged; ``id`` is the guild's.

- fields: departed_at: datetime

### `class DeletionStep(StrEnum)`
How far a member's deletion request got, in order.

- attributes: REQUESTED, HIDDEN, PURGED

### `class DeletionRequest(DiscordKeyedModel, table=True)`
A member's request to delete all their data, and when each :class:`DeletionStep` was done; ``id`` is the member's.

- fields: requested_at: datetime, hidden_at: datetime | None, purged_at: datetime | None
- `@property steps -> Generator[tuple[DeletionStep, datetime]]` — Yield each step done so far with when it was done, in order.

### `class CommandUsage(LifecycleModel, table=True)`
How often a member ran a command in a guild on one UTC day; the member owns it, so a departing guild leaves it.

- fields: ownership: ClassVar[Ownership], natural_key: ClassVar[tuple[str, ...]], user_id: int, command: str, guild_id:
  int | None, day: date, uses: int

### `@dataclass class UsageCount`
How often a member ran ``command`` in the guild ``guild_id`` (``None`` for a DM) on ``day``.

- fields: command: str, guild_id: Snowflake | None, day: date, count: int

## `winter_dragon.cogs.reminder.cog` — `src/winter_dragon/cogs/reminder/cog.py`
The /reminder command group: one-off and repeating reminders, sent as DMs by a background task.

- `reminder_choices(reminders: Generator[AnyReminder], current: str) -> Generator[ApplicationCommandOptionChoice]` — Yield a choice for each of ``reminders`` whose content contains ``current``, ignoring case.
- `async send_reminder(client: Client, reminder: AnyReminder) -> bool` — DM ``reminder`` to its user; ``False`` when Discord refused it (e.g. their DMs are closed).

### `class Reminders(GroupCog, name='reminder', description='Set reminders for yourself')`
Stores reminders and DMs them to their users when due, from a background task.

- `async load() -> None` — Create the reminder tables if missing; the bot then starts :meth:`deliver_due`.
- `@Cog.periodic async deliver_due() -> None` — Send the reminders due now; the bot repeats it every :attr:`ReminderSettings.check_interval` seconds.
- `async send_due(now: datetime) -> int` — DM every reminder due at ``now``; soft-delete one-off ones and move repeating ones on. Return how many were due.
- `@Cog.command async add(interaction: CommandInteraction, reminder: str, minutes: int=0, hours: int=0, days: int=0) -> None` — Remind the invoking user of ``reminder`` once, after the given time.
- `@Cog.command async repeat(interaction: CommandInteraction, reminder: str, minutes: int=0, hours: int=0, days: int=0, weeks: int=0) -> None` — Remind the invoking user of ``reminder`` every given time, starting one interval from now.
- `async remove_choices(interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]` — Suggest the invoking user's reminders whose content contains what they typed.
- `@Cog.command async remove(interaction: CommandInteraction, reminder: Reminder | TimedReminder) -> None` — Remove the invoking user's ``reminder``; refuse another member's.

## `winter_dragon.cogs.reminder.domain` — `src/winter_dragon/cogs/reminder/domain.py`
The reminder tables, their queries, and the rules a new reminder must meet, for ``/reminder`` and the dashboard alike.

- module names: SECONDS_PER_UNIT, REMINDER_TABLES
- `type AnyReminder = Reminder | TimedReminder`
- `delay_from(**amounts: int) -> timedelta` — Return the delay made of ``amounts`` per unit (``minutes=5, hours=1``), for :func:`new_reminder` to check.
- `new_reminder(content: str, user_id: Snowflake, due: datetime, now: datetime, repeat_every: timedelta | None=None) -> AnyReminder | Refused` — Return the reminder of ``content`` for ``user_id``, due at ``due``, or why it can't be set at ``now``.
- `next_occurrence(due: datetime, repeat_every: timedelta, now: datetime) -> datetime` — Return the first time after ``now`` that a reminder due at ``due`` and repeating every ``repeat_every`` is due.
- `reminder_message(content: str) -> str` — Return the DM reminding someone of ``content``.
- `owned_reminders(session: Session, user_id: Snowflake) -> Generator[AnyReminder]` — Yield every reminder of the user ``user_id``: repeating ones first, then one-off ones by when they're due.

### `class ReminderSettings`
Settings for reminders, in their ``cogs.ini`` section.

- attributes: check_interval, max_delay_days, max_content_length

### `class ReminderBase(LifecycleModel)`
What one-off and repeating reminders share; ``user_id`` is the Discord user to remind, who owns it.

- fields: ownership: ClassVar[Ownership], content: str, user_id: int, timestamp: datetime

### `class Reminder(ReminderBase, table=True)`
A reminder sent once, then soft-deleted.

### `class TimedReminder(ReminderBase, table=True)`
A reminder sent again every :attr:`repeat_every`, until removed.

- fields: repeat_every: timedelta

## `winter_dragon.cogs.stats` — `src/winter_dragon/cogs/stats.py`
The /stats command group: a guild's member counts, shown on demand and as the names of locked voice channels.

- module names: SHOWN, STATS_TABLES
- `async count_bots(guild: BaseGuild) -> int | NetworkError` — Count the bots among ``guild``'s members.
- `async guild_counts(guild: BaseGuild) -> GuildCounts | NetworkError` — Read ``guild``'s member, bot and online counts.
- `channel_name(kind: StatKind, counts: GuildCounts, peak: int) -> str` — Return the name of the stats channel showing ``kind``.
- `plan_renames(stats: Iterable[StatChannel], names: Mapping[int, str | None], counts: GuildCounts, peak: int) -> RenamePlan` — Plan updating ``stats`` to ``counts`` and ``peak``, given each existing channel's name by ID.
- `category_params(guild_id: Snowflake) -> GuildChannelParams` — Return the stats category: listed first, visible to everyone, and joined by nobody.
- `stats_embed(name: str, counts: GuildCounts, afk_channel: BaseChannel | None) -> Embed` — Return the embed /stats show answers with.
- `guild_stat_channels(session: Session, guild_id: Snowflake) -> list[StatChannel]` — Return the stats channels recorded for the guild ``guild_id``, category included.
- `stats_guild_ids(session: Session) -> Generator[Snowflake]` — Yield every guild with stats channels.

### `class StatsSettings`
Settings for the stats channels, in their ``cogs.ini`` section.

- attributes: update_interval, category_name

### `class StatKind(StrEnum)`
What a stats channel shows; the category holding them is one too.

- attributes: CATEGORY, USERS, ONLINE, BOTS, CREATED, PEAK

### `class StatChannel(DiscordKeyedModel, table=True)`
One of a guild's stats channels, or the category holding them; ``id`` is the channel's.

- fields: ownership: ClassVar[Ownership], alive_unique: ClassVar[tuple[str, ...]], guild_id: int, kind: StatKind

### `class PeakOnline(DiscordKeyedModel, table=True)`
The most users a guild has seen online at once, since its stats channels were added; ``id`` is the guild's.

- fields: ownership: ClassVar[Ownership], peak: int

### `@dataclass class GuildCounts`
How many members a guild has, how many are bots and how many are online; Discord's counts are approximate.

- fields: members: int, bots: int, online: int, created: datetime
- `@property users -> int` — Members that aren't bots.
- `@property online_users -> int` — Members online that aren't bots, taking every bot to be online.

### `@dataclass class RenamePlan`
What an update does to a guild's stats channels: rename those showing stale counts, forget deleted ones.

- fields: renames: dict[int, str], gone: list[StatChannel]

### `class Stats(GroupCog, name='stats', description="Show this server's member counts", contexts=[InteractionContextType.GUILD])`
Shows a guild's member counts, and keeps a locked category of voice channels named after them up to date.

- `async load() -> None` — Create the stats tables if missing; the bot then starts :meth:`rename_channels`.
- `@Cog.periodic async rename_channels() -> None` — Update every guild's stats channels; the bot repeats it every :attr:`StatsSettings.update_interval` seconds.
- `async update_all() -> None` — Update the stats channels of every guild that has them.
- `async update_guild(guild_id: Snowflake) -> None` — Rename ``guild_id``'s stats channels to the current counts, record a new peak, and forget deleted ones.
- `async create_channels(client: Client, guild_id: Snowflake, *, reason: str) -> NetworkError | None` — Create ``guild_id``'s locked stats category and its channels, named after the current counts.
- `async remove_channels(client: Client, stats: Iterable[StatChannel], *, reason: str) -> bool` — Delete the channels of ``stats``, category last, soft-deleting each one that's gone; whether all of them are.
- `@Cog.command async show(interaction: GuildCommandInteraction) -> None` — Answer with an embed of the guild's member counts.
- `@Cog.command async add(interaction: GuildCommandInteraction) -> None` — Create the stats channels, unless the guild has them already.
- `@Cog.command async remove(interaction: GuildCommandInteraction) -> None` — Delete the guild's stats channels.
- `@Cog.command async reset(interaction: GuildCommandInteraction) -> None` — Delete and recreate every guild's stats channels; only the bot's owners may.

## `winter_dragon.cogs.steam.cog` — `src/winter_dragon/cogs/steam/cog.py`
The /steam command group, its page buttons, and the background scrape of Steam's specials.

- `next_scrape_time(now: datetime, interval: timedelta) -> datetime` — Return when to scrape next: after ``interval``, or just after Steam's daily rollover if that comes first.
- `sale_queries(percent: int, complete_percent: int, top_sellers: int) -> Generator[tuple[int, int | None]]` — Yield the ``(percent, limit)`` of each query a scrape makes.

### `class SteamSales(GroupCog, name='steam', description='Get notified about free and discounted Steam games')`
Lists Steam sales on request and DMs subscribers new ones, re-checking sales right after they end.

- `@property throttle -> RequestThrottle` — The request throttle every scraper of this cog shares, so spacing and rate-limit pauses span them all.
- `async load() -> None` — Create the Steam tables if missing; the bot then starts :meth:`scrape_and_recheck`.
- `@Cog.periodic async scrape_and_recheck() -> float` — Scrape when due, re-check sales that just ended, and return the seconds until either is due next.
- `async scrape(now: datetime) -> None` — Ask Steam for its sales, store them, and DM subscribers new ones.
- `async recheck_due(now: datetime) -> None` — Check the sales whose announced end has passed: update those still running, remove those that ended.
- `@Cog.command async add(interaction: CommandInteraction) -> None` — Subscribe the invoking user to Steam sale DMs.
- `@Cog.command async percentage(interaction: CommandInteraction, percent: int) -> None` — Set the minimum discount the invoking user is notified about, subscribing them when they aren't.
- `@Cog.command async remove(interaction: CommandInteraction) -> None` — Unsubscribe the invoking user from Steam sale DMs.
- `@Cog.command async show(interaction: CommandInteraction, percent: int | None=None) -> None` — Show the first page of current sales of at least ``percent``, with buttons to page through them.
- `@Cog.component async show_page(interaction: ComponentInteraction, owner_id: str, percent: str, page: str) -> None` — Turn a /steam show listing to ``page``; only the user who ran the command may.

## `winter_dragon.cogs.steam.models` — `src/winter_dragon/cogs/steam/models.py`
Database tables for Steam sales and the users subscribed to them.

- module names: STEAM_TABLES

### `class SaleTypes(StrEnum)`
What kind of store item a sale is for, beyond a plain game.

- attributes: DLC, BUNDLE

### `class SteamSale(LifecycleModel, table=True)`
A Steam store item on sale; ``id`` is its Steam app (or bundle/sub) ID. Shared data, owned by no one.

- fields: title: str, url: str, sale_percent: int, final_price: float, update_datetime: datetime, discovered_at:
  datetime, sale_end: datetime | None
- `@property steam_url -> SteamURL` — The sale's store page.
- `is_outdated(after: timedelta, now: datetime) -> bool` — Whether the sale hasn't been seen on Steam for at least ``after``.

### `class SteamSaleProperties(LifecycleModel, table=True)`
One :class:`SaleTypes` a sale has.

- fields: ownership: ClassVar[Ownership], natural_key: ClassVar[tuple[str, ...]], steam_sale_id: int, property:
  SaleTypes

### `class SteamUsers(DiscordKeyedModel, table=True)`
A Discord user subscribed to Steam sale DMs; ``id`` is their Discord user ID, and they own it.

- fields: ownership: ClassVar[Ownership], sale_threshold: int, last_notification: datetime

### `class SaleNotification(LifecycleModel, table=True)`
One sale a DM told a member about; ``user_id`` is their Discord user ID, and they own it.

- fields: ownership: ClassVar[Ownership], user_id: int, sale_id: int, title: str, sale_percent: int, sale_threshold:
  int, sent_at: datetime

## `winter_dragon.cogs.steam.notifier` — `src/winter_dragon/cogs/steam/notifier.py`
DM subscribers the Steam sales they haven't been told about yet.

### `@dataclass class SteamSaleNotifier(LoggerMixin)`
Sends each subscriber one DM with the sales above their threshold discovered since their last notification.

- fields: client: Client, store: SteamSaleStore, color: int
- `async notify(*, now: datetime, content: str) -> int` — DM every subscriber with new sales, with ``content`` above the embed; return how many were notified.

## `winter_dragon.cogs.steam.pages` — `src/winter_dragon/cogs/steam/pages.py`
Embeds and buttons that show Steam sales: the pages of /steam show and the sale DMs.

- module names: HTTP_SCHEMES
- `format_sale(sale: SteamSale, properties: set[SaleTypes], *, open_in_steam: bool=False) -> str` — Describe one sale: link, discount, price, kind, when it was last seen, and an install link for apps.
- `page_count(total: int) -> int` — Return how many /steam show pages ``total`` sales take; at least one.
- `build_page(sales: Sequence[SteamSale], properties: Mapping[int, set[SaleTypes]], *, page: int, color: int) -> Embed` — Build page ``page`` (0-based, clamped to the valid range) of the /steam show listing of ``sales``.
- `page_buttons(handler: ComponentHandler, *, owner_id: Snowflake, percent: int, page: int, pages: int) -> list[ActionRow]` — Build the previous / page counter / next buttons under page ``page`` of ``pages``.
- `build_notification(sales: Sequence[SteamSale], properties: Mapping[int, set[SaleTypes]], *, color: int) -> Embed` — Build the DM embed announcing ``sales``, dropping trailing sales that don't fit Discord's embed limits.

## `winter_dragon.cogs.steam.scrapers` — `src/winter_dragon/cogs/steam/scrapers.py`
Find Steam sales through Steam's store web APIs.

- module names: STORE_API_URL, QUERY_URL, GET_ITEMS_URL, TOP_SELLERS_SORT, MIN_DISCOUNT_FILTER, RATE_LIMITED

### `class ScrapeFailure(Enum)`
Why Steam gave no answer, as opposed to answering "not on sale".

- attributes: UNAVAILABLE

### `@dataclass class ScrapedSale`
One sale as found on Steam.

- fields: id: int, title: str, url: SteamURL, sale_percent: int, final_price: float, properties: frozenset[SaleTypes],
  sale_end: datetime | None
- `@classmethod from_store_item(item: StoreItem) -> Self | None` — Return the sale on ``item``, or ``None`` when it isn't discounted (or isn't a store item Steam knows).

### `class SteamScraper(LoggerMixin)`
Asks Steam's store APIs for sales; use as ``async with SteamScraper() as scraper``.

- `async query_sales(percent: int, limit: int | None=None) -> AsyncGenerator[ScrapedSale]` — Yield the sales of at least ``percent``, best-selling first: the first ``limit``, or every one without.
- `async get_sales(items: Iterable[StoreItemID]) -> AsyncGenerator[tuple[StoreItemID, ScrapedSale | ScrapeFailure | None]]` — Yield each item with its current sale, ``None`` when it isn't on sale, or why Steam gave no answer.

## `winter_dragon.cogs.steam.settings` — `src/winter_dragon/cogs/steam/settings.py`
Settings for the Steam sale finder, in its ``cogs.ini`` section.

### `class SteamSettings`
How often Steam is scraped, and how its sales are shown.

- attributes: country_code, stored_percent, complete_percent, top_sellers, request_interval, update_interval,
  outdated_after, recheck_delay, embed_color, steam_redirect, default_threshold, min_sleep, sale_end_hour,
  rollover_grace, query_page_size, get_items_batch_size, request_timeout, language, initial_backoff, max_backoff,
  items_per_page

## `winter_dragon.cogs.steam.store` — `src/winter_dragon/cogs/steam/store.py`
Storing and querying Steam sales and their subscribers.

### `@dataclass class SteamSaleStore`
Reads and writes Steam sales through one database session.

- fields: session: Session
- `record(scraped: ScrapedSale, *, now: datetime, outdated_after: timedelta) -> tuple[SteamSale, bool]` — Store a scraped sale, returning the stored row and whether it counts as new.
- `refresh(sale: SteamSale, scraped: ScrapedSale, *, now: datetime) -> None` — Apply what Steam now says about ``sale``: its current discount, end and properties.
- `remove(sale: SteamSale) -> None` — Soft-delete ``sale`` and its properties.
- `properties(sales: Iterable[SteamSale]) -> dict[int, set[SaleTypes]]` — Return the properties of each of ``sales``, by sale ID.
- `current_sales(percent: int, *, now: datetime, outdated_after: timedelta) -> list[SteamSale]` — Return the sales of at least ``percent`` still running: biggest discount first, then cheapest.
- `unseen_without_end(moment: datetime, percent: int, *, outdated_after: timedelta) -> list[SteamSale]` — Return the shown sales of at least ``percent`` last seen before ``moment``, longest unseen first.
- `due_rechecks(*, now: datetime, delay: timedelta) -> Sequence[SteamSale]` — Return the sales whose announced end was at least ``delay`` ago.
- `next_recheck(*, delay: timedelta) -> datetime | None` — Return when the next sale is due for a re-check, if any sale has a known end.
- `new_since(moment: datetime, percent: int) -> list[SteamSale]` — Return the sales of at least ``percent`` discovered after ``moment``, newest first.
- `subscriber(user_id: Snowflake) -> SteamUsers | None` — Return the subscription of ``user_id``, if subscribed.
- `subscribers() -> Sequence[SteamUsers]` — Return every subscribed user.
- `lowest_threshold() -> int | None` — Return the lowest ``sale_threshold`` among subscribers, or ``None`` without subscribers.

## `winter_dragon.cogs.steam.store_api` — `src/winter_dragon/cogs/steam/store_api.py`
The parts of Steam's store web APIs the sale finder reads.

- module names: ITEM_KINDS, DLC_APP_TYPE, FOUND

### `class SteamModel(BaseModel)`
A part of a Steam store API answer.

- attributes: model_config

### `class ActiveDiscount(SteamModel)`
One discount applied to a purchase option.

- fields: discount_end_date: datetime | None

### `class PurchaseOption(SteamModel)`
The cheapest way to buy a store item, and the discount it gets.

- fields: final_price_in_cents: int, discount_pct: int, active_discounts: list[ActiveDiscount], is_free_to_keep: bool,
  free_to_keep_ends: datetime | None
- `@property discount_end -> datetime | None` — When the discount ends: its first discount to run out, or the end of a free giveaway.

### `class StoreItem(SteamModel)`
An app, package or bundle on the Steam store.

- fields: item_type: int, id: int, success: int, name: str, store_url_path: str, type: int, best_purchase_option:
  PurchaseOption | None
- `@property item_id -> StoreItemID | None` — The item's ID, or ``None`` for an ``item_type`` the sale finder doesn't know.
- `@property url -> SteamURL | None` — The item's store page.

### `class QueryMetadata(SteamModel)`
How many items a store query matches in total.

- fields: total_matching_records: int

### `class QueryResult(SteamModel)`
One page of ``IStoreQueryService/Query`` results.

- fields: metadata: QueryMetadata, store_items: list[StoreItem]

### `class QueryResponse(SteamModel)`
The answer of ``IStoreQueryService/Query``.

- fields: response: QueryResult

### `class ItemsResult(SteamModel)`
The items ``IStoreBrowseService/GetItems`` looked up.

- fields: store_items: list[StoreItem]

### `class ItemsResponse(SteamModel)`
The answer of ``IStoreBrowseService/GetItems``.

- fields: response: ItemsResult

## `winter_dragon.cogs.steam.throttle` — `src/winter_dragon/cogs/steam/throttle.py`
Space out requests to Steam, and stop sending them for a while once Steam rate-limits us.

### `@dataclass class RequestThrottle`
Lets requests through at least ``interval`` seconds apart, and none at all while paused by a rate limit.

- fields: interval: float, clock: Callable[[], float], sleep: Callable[[float], Awaitable[None]], sent: int
- `@property paused -> bool` — Whether requests are paused after a rate-limit answer.
- `async acquire() -> bool` — Wait for the next request slot and claim it; ``False`` (without waiting) while paused.
- `rate_limited(retry_after: float | None) -> float` — Pause requests for ``retry_after`` seconds, or the current backoff when Steam didn't say; return the pause.
- `succeeded() -> None` — Reset the backoff after a request Steam answered normally.

## `winter_dragon.cogs.steam.urls` — `src/winter_dragon/cogs/steam/urls.py`
Steam store URLs, and the IDs of the store items they point at.

- module names: STORE_URL, CLIENT_OPEN_URL, APP_URL_PATTERN, ITEM_URL_PATTERN, ITEM_PATHS

### `class StoreItemKind(StrEnum)`
What a Steam store ID numbers; the value is the key Steam's store APIs take such an ID under.

- attributes: APP, PACKAGE, BUNDLE
- `@property path -> str` — The store URL path segment of this kind's pages.

### `@dataclass class StoreItemID`
One store item: app, package and bundle IDs are separate number ranges, so the kind is part of the ID.

- fields: kind: StoreItemKind, id: int
- `as_request() -> dict[str, int]` — Return this ID the way Steam's store APIs take it, e.g. ``{"appid": 730}``.
- `@property url -> SteamURL` — The item's store page.

### `class SteamURL(str)`
A Steam store URL.

- `@property app_id -> int | None` — The app ID of an app page URL, or ``None`` for any other page (bundles, subs, search).
- `@property client_url -> str` — The ``steam://`` link opening this page in the Steam client.
- `@property is_app -> bool` — Whether this URL points at a single app's store page.
- `@property is_bundle -> bool` — Whether this URL points at a bundle (``/bundle/``) or a package (``/sub/``).
- `@property store_item -> StoreItemID | None` — The store item this URL's page is for, or ``None`` for a page that isn't one item's.

## `winter_dragon.cogs.team.cards` — `src/winter_dragon/cogs/team/cards.py`
The messages the team features post: the split teams, with the buttons under them.

- module names: BUTTONS_PER_ROW
- `split_post(teams: Sequence[tuple[Team, Sequence[Snowflake]]], keep: ComponentHandler, move: Callable[[Team], str] | None=None) -> tuple[Embed, list[ActionRow]]` — Return the post showing freshly split teams: a field per team, with Keep buttons under it.

## `winter_dragon.cogs.team.cog` — `src/winter_dragon/cogs/team/cog.py`
The /team command group: create a lasting team, split members into temporary ones, invite, manage and leave teams.

- module names: KEEP_NAME_INPUT

### `class TeamSettings`
Settings for /team, in its ``cogs.ini`` section.

- attributes: max_name_length, temporary_lifetime_hours

### `class Teams(GroupCog, name='team', description='Teams of members that outlast any one tournament', contexts=[InteractionContextType.GUILD])`
Lasting teams: create one, see who is in it, and leave it. Temporary teams come from a split and can be kept.

- attributes: rng
- `async load() -> None` — Create the team tables if missing.
- `async team_choices(interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]` — Suggest the invoker's teams whose name contains what was typed.
- `@Cog.command async create(interaction: GuildCommandInteraction, name: str) -> None` — Create the lasting team ``name`` with the invoker as its captain.
- `@Cog.command async split(interaction: GuildCommandInteraction, teams: int=2) -> None` — Ask for the members to split, with a user select menu taking at least ``teams`` and at most 25 of them.
- `@Cog.component async split_select(interaction: GuildComponentInteraction, teams: str) -> None` — Draw temporary teams from the picked members and post them publicly, each with a Keep button.
- `@Cog.component async keep_button(interaction: GuildComponentInteraction, team_id: str) -> None` — Open the modal asking for a name, when the presser may keep the temporary team.
- `@Cog.modal async keep_modal(interaction: ModalSubmitInteraction, team_id: str) -> None` — Make the temporary team lasting under the submitted name, with the presser as captain.
- `@Cog.periodic async end_expired_teams() -> None` — End the temporary teams nobody kept within ``temporary_lifetime_hours``.
- `@Cog.command async show(interaction: GuildCommandInteraction, team: Team) -> None` — Post the team's name, captain and members.
- `@Cog.command async leave_team(interaction: GuildCommandInteraction, team: Team) -> None` — Take the invoker out of the team.
- `@Cog.command async invite(interaction: GuildCommandInteraction, team: Team, member: User) -> None` — Post a public invite with a Join button that only ``member`` can press.
- `@Cog.component async accept_invite(interaction: GuildComponentInteraction, team_id: str, invitee_id: str) -> None` — Join the invitee to the team when the invitee presses Join.
- `@Cog.command async kick_member(interaction: GuildCommandInteraction, team: Team, member: User) -> None` — Take ``member`` out of the team, for its captain.
- `@Cog.command async make_captain(interaction: GuildCommandInteraction, team: Team, member: User) -> None` — Make ``member`` the captain of the team, for its captain.
- `@Cog.command async disband_team(interaction: GuildCommandInteraction, team: Team) -> None` — Soft-delete the team and every membership, for its captain.

## `winter_dragon.cogs.team.models` — `src/winter_dragon/cogs/team/models.py`
The team tables: a team and its members, lasting or temporary.

- module names: TEAM_TABLES

### `class TeamKind(StrEnum)`
Whether a team was drawn for one occasion or is kept.

- attributes: TEMPORARY, LASTING

### `class TeamOrigin(StrEnum)`
How a team came to be.

- attributes: CREATED, VOICE_SPLIT, TEXT_SPLIT, SOLO_TOURNAMENT

### `class Team(LifecycleModel, table=True)`
A group of members, from any guild, apart from any tournament; it belongs to no guild.

- fields: name: str, kind: TeamKind, origin: TeamOrigin, captain_id: int | None, ended_at: datetime | None

### `class TeamMember(LifecycleModel, table=True)`
A member of a team, since ``joined_at``; the longest-standing member takes over from a leaving captain.

- fields: ownership: ClassVar[Ownership], natural_key: ClassVar[tuple[str, ...]], team_id: int, user_id: int, joined_at:
  datetime

## `winter_dragon.cogs.team.service` — `src/winter_dragon/cogs/team/service.py`
What can happen to a team: creating it, keeping a temporary one, listing its members, and members leaving it.

- `create_team(session: Session, name: str, captain_id: Snowflake) -> Team` — Create the lasting team ``name`` with ``captain_id`` as its captain and first member.
- `create_temporary_teams(session: Session, groups: Sequence[Sequence[Snowflake]], origin: TeamOrigin) -> list[Team]` — Store one temporary team per group, named Team 1, Team 2, ..., with no captain; return them in order.
- `require_keepable(session: Session, team: Team, user_id: Snowflake) -> None` — Refuse unless ``user_id`` is a member of ``team``, which must be temporary and unended, so they may keep it.
- `keep(session: Session, team: Team, user_id: Snowflake, name: str) -> None` — Make the temporary ``team`` lasting under ``name``, with ``user_id`` as its captain; only its members may.
- `end_expired(session: Session, now: datetime, lifetime: timedelta) -> int` — End every alive temporary team, except a solo tournament's, made at or before ``now - lifetime``; return how many.
- `end_team(session: Session, team: Team, now: datetime) -> None` — End the temporary ``team`` at ``now``; a lasting or already ended team stays as it is.
- `members_of(session: Session, team: Team) -> Generator[TeamMember]` — Yield the team's members, longest-standing first.
- `teams_of(session: Session, user_id: Snowflake) -> Generator[Team]` — Yield the alive, unended teams ``user_id`` is a member of, by name.
- `membership(session: Session, team: Team, user_id: Snowflake) -> TeamMember | None` — Return ``user_id``'s alive membership of ``team``, if they're in it.
- `leave(session: Session, team: Team, user_id: Snowflake) -> None` — Take ``user_id`` out of ``team``.
- `require_captain(team: Team, user_id: Snowflake) -> None` — Refuse unless ``user_id`` captains ``team``.
- `join(session: Session, team: Team, user_id: Snowflake) -> None` — Add ``user_id`` to ``team``, joining now; refuse when they're in it already.
- `kick(session: Session, team: Team, captain_id: Snowflake, user_id: Snowflake) -> None` — Take ``user_id`` out of ``team`` for its captain; the captain can't kick themselves.
- `hand_over(session: Session, team: Team, captain_id: Snowflake, user_id: Snowflake) -> None` — Make the member ``user_id`` captain of ``team``, for its captain.
- `disband(session: Session, team: Team, captain_id: Snowflake) -> None` — Disband ``team`` for its captain: soft-delete it and every membership.

### `class LeaveHiddenMember(MemberHiddenHook)`
A member whose data is hidden leaves each of their teams, by the rule ``/team leave`` follows.

- attributes: tables
- `@classmethod on_member_hidden(session: Session, member_id: Snowflake) -> None` — Take the member ``member_id`` out of every team they're in, handing over captaincies.

## `winter_dragon.cogs.team.split` — `src/winter_dragon/cogs/team/split.py`
Splitting members into teams: pure arithmetic, no database, no Discord.

- module names: MIN_TEAMS
- `split_into_teams[T](user_ids: Sequence[T], team_size: int, rng: Random) -> list[list[T]]` — Shuffle ``user_ids`` into teams of ``team_size``; players left over join the first teams, one each.
- `split_into[T](user_ids: Sequence[T], count: int, rng: Random) -> list[list[T]]` — Shuffle ``user_ids`` into ``count`` teams whose sizes differ by at most one; none if there are too few players.

## `winter_dragon.cogs.tournament.bracket` — `src/winter_dragon/cogs/tournament/bracket.py`
The arithmetic of a single-elimination bracket, and of splitting players into teams; no database, no Discord.

- module names: MAX_VOTE_OPTIONS, MAX_QUESTION_LENGTH
- `round_count(teams: int) -> int` — Return how many rounds a bracket of ``teams`` teams takes.
- `first_round[T](seeds: Sequence[T]) -> list[Pairing[T]]` — Pair ``seeds`` for the first round, in seed order; a ``None`` second seed is a bye.
- `next_match(at: BracketSlot) -> NextMatch` — Return where the winner of the match at ``at`` plays next: its round, its slot, and whether as entry A.
- `round_name(round_: int, rounds: int) -> str` — Return how players call round ``round_`` of a bracket of ``rounds`` rounds.
- `parse_options(text: str) -> list[str]` — Split comma-separated answers, dropping blanks and repeats; check the vote's limits with :func:`valid_options`.
- `valid_options(options: Sequence[str]) -> bool` — Whether ``options`` can be voted on: 2 to :data:`MAX_VOTE_OPTIONS` answers that fit on a button.
- `tally(option_count: int, choices: Iterable[int]) -> list[int]` — Count the votes for each of ``option_count`` answers; out-of-range choices are ignored.

### `@dataclass class Pairing[T]`
Two seeds meeting in a first-round match; ``second`` is ``None`` for a bye.

- fields: first: T, second: T | None
- `@property bye -> bool` — Whether ``first`` goes through without playing.

### `@dataclass class BracketSlot`
Where in the bracket a match sits: its round (0 first) and its place in that round, top to bottom.

- fields: round: int, slot: int

### `@dataclass class NextMatch`
Where a match's winner plays next, and on which side.

- fields: at: BracketSlot, as_entry_a: bool

## `winter_dragon.cogs.tournament.bracket_image` — `src/winter_dragon/cogs/tournament/bracket_image.py`
Draw a tournament's bracket as a PNG: each round a column of match boxes, joined to the next, climbing to the champion.

- module names: FONT, SCALE, SNOW, WHITE, ICE, SLATE, GRANITE, BOX_WIDTH, BOX_HEIGHT, ROW_GAP, LINK, MARGIN, HEADER,
  SUMMIT_WIDTH, PLAYING
- `bracket_png(matches: Sequence[TournamentMatch], names: Mapping[int, str], champion: int | None) -> bytes` — Return the bracket of ``matches`` as a PNG, with the champion's name at its summit once there is one.

## `winter_dragon.cogs.tournament.cards` — `src/winter_dragon/cogs/tournament/cards.py`
The messages a tournament shows: its sign-up card, bracket, match cards and votes, with their buttons.

- module names: PHASE_LABELS, CARD_LIST_CHARACTERS, BRACKET_IMAGE, ROUTE, ROUTE_NAMES, NEXT_STEPS, VOTE_BAR_LENGTH
- `plural(count: int, noun: str) -> str` — Return ``count`` with ``noun``, adding an ``s`` unless there's exactly one.
- `solo_progress(players: int, team_size: int) -> str` — Return how far solo sign-up is: the teams it makes so far, and how many more players make the next one.
- `signup_card(tournament: Tournament, rosters: Mapping[str, Sequence[Snowflake]], solo_players: Sequence[Snowflake], controls: SignupControls) -> Container` — Return the sign-up card: what the format is, who signed up, and the buttons to join, enter a team or leave.
- `participants_card(tournament: Tournament, rosters: Mapping[str, Sequence[Snowflake]], solo_players: Sequence[Snowflake]) -> Container` — Return everyone signed up to ``tournament``: the players, or each team with its players.
- `match_ids(matches: Iterable[TournamentMatch]) -> dict[BracketSlot, int]` — Return each match's ID by where it sits in the bracket.
- `match_line(match: TournamentMatch, names: Mapping[int, str], ids: Mapping[BracketSlot, int] | None=None) -> str` — Return one line of the bracket: the match's number, its teams, and its state or winner.
- `bracket_file(tournament: Tournament, matches: Sequence[TournamentMatch], names: Mapping[int, str]) -> File` — Return the bracket drawn as an image, to send with :func:`bracket_card`.
- `bracket_card(tournament: Tournament, matches: Sequence[TournamentMatch], names: Mapping[int, str], show_match: ComponentHandler) -> Container` — Return the bracket: what's being played now or who won, the bracket image, and a button per match being played.
- `card_of_match(view: MatchView, controls: MatchControls | None) -> Container` — Return a match card: its teams, a route line through its phases, where it stands, and each team's players and drafts.
- `manage_panel(view: MatchView, act: ComponentHandler, card_at: tuple[Snowflake, Snowflake]) -> Container` — Return the organiser's panel for a match: each action beside a line saying when to use it.
- `vote_options(vote: MatchVote) -> list[str]` — Return the vote's answers.
- `vote_card(vote: MatchVote, choices: Sequence[int], choose: ComponentHandler, close: ComponentHandler) -> Container` — Return a vote: its question, how many voted, and each answer with its share of the votes and a Vote button.

### `class MatchAction(StrEnum)`
What one of the organiser's buttons under a match card does; it's part of the button's custom ID.

- attributes: NEXT, WIN, FORFEIT

### `@dataclass class SignupControls`
The handlers behind a sign-up card's buttons; each button carries the tournament's ID.

- fields: join: ComponentHandler, leave: ComponentHandler, participants: ComponentHandler, enter: ComponentHandler,
  add_player: ComponentHandler

### `@dataclass class MatchControls`
The handlers behind a match card's buttons and its organiser's panel; each button carries the match's ID.

- fields: manage: ComponentHandler, act: ComponentHandler, clash: ComponentHandler

### `@dataclass class MatchView`
What a match card shows: the match, its tournament and round, the teams, their players and drafts.

- fields: match: TournamentMatch, tournament_name: str, rounds: int, names: Mapping[int, str], rosters: Mapping[int,
  Sequence[Snowflake]], drafts: Sequence[DraftChoice], clash: Sequence[Snowflake]
- `@property teams -> list[int]` — The IDs of the match's teams known so far.
- `name(team: int | None) -> str` — Return the team's name.
- `@property playable -> bool` — Whether the organiser can still act on the match: both teams known, and no winner yet.

## `winter_dragon.cogs.tournament.cog` — `src/winter_dragon/cogs/tournament/cog.py`
The /tournament command group: sign-up, teams, a single-elimination bracket, match cards, drafts and votes.

- `is_organiser(interaction: AnyGuildInteraction, tournament: Tournament) -> bool` — Whether the invoker runs ``tournament``: they created it, or they may manage the server.
- `require_organiser(interaction: AnyGuildInteraction, tournament: Tournament) -> None` — Refuse unless the invoker runs ``tournament``.
- `async require_server_member(interaction: AnyGuildInteraction, player_id: Snowflake) -> None` — Refuse unless ``player_id`` is a member of the invoker's server, the only members who can play in its tournaments.
- `entry_names(session: Session, tournament: Tournament) -> dict[int, str]` — Return each team's name by its ID.
- `captained_entry(session: Session, tournament: Tournament, captain_id: Snowflake) -> TournamentEntry` — Return the entry whose team ``captain_id`` captains in ``tournament``; refuse when there's none.
- `play(session: Session, match: TournamentMatch, action: MatchAction, entry_id: str, actor_id: Snowflake) -> None` — Do what the organiser's button ``action`` under the match card says, for the team ``entry_id`` if it names one.

### `class TournamentSettings`
Settings for /tournament, in its ``cogs.ini`` section.

- attributes: max_name_length, max_team_size

### `class Tournaments(GroupCog, name='tournament', description='Run a team tournament: sign-up, a bracket, drafts and votes', contexts=[InteractionContextType.GUILD])`
Runs tournaments per guild: players sign up, teams form, and a single-elimination bracket plays out.

- attributes: rng
- `async load() -> None` — Create the tournament tables if missing.
- `async tournament_choices(interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]` — Suggest the tournaments the invoker can see that aren't over, whose name contains what was typed.
- `async log_tournament_choices(interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]` — Suggest every tournament the invoker can see, finished ones too, whose name contains what was typed.
- `@Cog.command async create(interaction: GuildCommandInteraction, name: str, team_size: int=1, captains: bool=False) -> None` — Open a tournament: solo sign-up into drawn teams of ``team_size``, or teams registered by ``captains``.
- `@Cog.command async post_tournament(interaction: GuildCommandInteraction, tournament: Tournament) -> None` — Post ``tournament`` in this channel; every change to the tournament edits the post.
- `@Cog.command async join(interaction: GuildCommandInteraction, tournament: Tournament) -> None` — Sign the invoker up for the tournament.
- `@Cog.command async leave(interaction: GuildCommandInteraction, tournament: Tournament) -> None` — Take the invoker out of the tournament; a captain leaving disbands their team.
- `@Cog.component async join_button(interaction: GuildComponentInteraction, tournament_id: str) -> None` — Sign the clicker up, then refresh the sign-up card.
- `@Cog.component async leave_button(interaction: GuildComponentInteraction, tournament_id: str) -> None` — Take the clicker out, then refresh the sign-up card.
- `@Cog.component async participants_button(interaction: GuildComponentInteraction, tournament_id: str) -> None` — Show the clicker, and only them, everyone signed up so far.
- `@Cog.component async enter_button(interaction: GuildComponentInteraction, tournament_id: str) -> None` — Enter the clicker's team; with more than one team they could enter, ask which first.
- `@Cog.component async enter_pick(interaction: GuildComponentInteraction, tournament_id: str) -> None` — Enter the team the clicker chose from the select of their teams.
- `@Cog.component async add_player_button(interaction: GuildComponentInteraction, tournament_id: str) -> None` — Ask the clicker which members to add to the entry they captain, up to the places it has left.
- `@Cog.component async add_player_pick(interaction: GuildComponentInteraction, tournament_id: str) -> None` — Add the members the clicker chose to the entry they captain.
- `async team_choices(interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]` — Suggest the lasting teams the invoker captains whose name contains what was typed.
- `@Cog.command async enter(interaction: GuildCommandInteraction, tournament: Tournament, team: Team) -> None` — Enter the invoker's team into the tournament, with the invoker as its first player.
- `@Cog.command async entry_add(interaction: GuildCommandInteraction, tournament: Tournament, player: User) -> None` — Add ``player``, a member of this server and of your team, to the entry you captain.
- `@Cog.command async entry_remove(interaction: GuildCommandInteraction, tournament: Tournament, player: User) -> None` — Remove ``player`` from the entry you captain.
- `@Cog.command async lineup_in(interaction: GuildCommandInteraction, tournament: Tournament, player: User, reason: str | None=None) -> None` — Put ``player``, a server member, in the lineup of the entry you captain; a stand-in needn't be in your team.
- `@Cog.command async lineup_out(interaction: GuildCommandInteraction, tournament: Tournament, player: User, reason: str | None=None) -> None` — Take ``player`` out of the lineup of the entry you captain, for its next match not yet live.
- `@Cog.command async start_tournament(interaction: GuildCommandInteraction, tournament: Tournament) -> None` — Start the tournament and show its bracket; organisers only.
- `@Cog.command async bracket(interaction: GuildCommandInteraction, tournament: Tournament) -> None` — Show the bracket, or the sign-up card before the tournament starts.
- `@Cog.command async cancel_tournament(interaction: GuildCommandInteraction, tournament: Tournament) -> None` — Cancel the tournament; organisers only.
- `async match_choices(interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]` — Suggest the undecided matches of the tournaments the invoker can see, whose label contains what was typed.
- `async log_match_choices(interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]` — Suggest every match, decided or not, of the tournaments the invoker can see, finished ones too.
- `@Cog.command async match_card(interaction: GuildCommandInteraction, match: TournamentMatch) -> None` — Post the card of match ``match``.
- `@Cog.command async log(interaction: GuildCommandInteraction, tournament: Tournament, match: TournamentMatch) -> None` — Post the log of ``match`` to the invoker only; its organiser and the captains of its two entries can see it.
- `@Cog.component async manage_button(interaction: GuildComponentInteraction, match_id: str) -> None` — Show the organiser, and only them, the panel to move the match on, report its winner or record a forfeit.
- `@Cog.component async show_match_button(interaction: GuildComponentInteraction, match_id: str) -> None` — Show the clicker, and only them, the card of a match from the bracket.
- `@Cog.component async match_control(interaction: GuildComponentInteraction, match_id: str, action: str, entry_id: str='', card_channel_id: str='', card_message_id: str='') -> None` — Move a match to its next phase, report its winner, or record a forfeit; organisers only.
- `@Cog.component async clash_button(interaction: GuildComponentInteraction, match_id: str, entry_id: str) -> None` — Drop the clashing members from one side of a ready match; its organiser or a captain of either side only.
- `@Cog.command async ban(interaction: GuildCommandInteraction, match: TournamentMatch, choice: str) -> None` — Record the invoker's team banning ``choice`` in ``match``.
- `@Cog.command async pick(interaction: GuildCommandInteraction, match: TournamentMatch, choice: str) -> None` — Record the invoker's team picking ``choice`` in ``match``.
- `@Cog.command async vote(interaction: GuildCommandInteraction, match: TournamentMatch, question: str, answers: str) -> None` — Post a vote on ``question`` for the players of ``match``; organisers only.
- `@Cog.component async vote_button(interaction: GuildComponentInteraction, vote_id: str, choice: str) -> None` — Record the clicker's answer, refresh the tally, and tell the clicker, and only them, what they voted.
- `@Cog.component async close_vote_button(interaction: GuildComponentInteraction, vote_id: str) -> None` — Close the vote and show the final tally; organisers only.

## `winter_dragon.cogs.tournament.models` — `src/winter_dragon/cogs/tournament/models.py`
The tournament tables: a tournament, its teams and players, its bracket's matches, their drafts and votes.

- module names: ACTIVE, TOURNAMENT_TABLES

### `class TeamMode(StrEnum)`
How a tournament's teams are formed.

- attributes: SOLO, CAPTAINS

### `class TournamentStatus(StrEnum)`
Where a tournament is in its life.

- attributes: SIGNUP, RUNNING, FINISHED, CANCELLED

### `class MatchPhase(StrEnum)`
Where a match is: waiting for its teams, through the draft, live, and decided.

- attributes: WAITING, READY, BAN, PICK, LIVE, FINISHED, FORFEIT
- `@property decided -> bool` — Whether the match has a winner.

### `class MatchStep(StrEnum)`
What happens to a match: its teams become known, it advances, it is reported or forfeited, or a bye decides it.

- attributes: TEAMS_KNOWN, ADVANCE, REPORT, FORFEIT, BYE

### `class DraftKind(StrEnum)`
Whether a team bans something from the match, or picks it.

- attributes: BAN, PICK

### `class MatchEventKind(StrEnum)`
What happened in a match.

- attributes: PHASE, DRAFT, VOTE_OPENED, VOTE_CLOSED, WINNER, FORFEIT, CLASH_DROPPED

### `class Tournament(LifecycleModel, table=True)`
A guild's tournament, shown in any channels it is posted to; the guild owns it and everything in it.

- fields: ownership: ClassVar[Ownership], guild_id: int, organiser_id: int, name: str, mode: TeamMode, team_size: int,
  status: TournamentStatus, winner_entry_id: int | None

### `class TournamentPost(LifecycleModel, table=True)`
A message showing a tournament in one channel of its guild; the bot edits it whenever the tournament changes.

- fields: ownership: ClassVar[Ownership], tournament_id: int, channel_id: int, message_id: int

### `class TournamentEntry(LifecycleModel, table=True)`
A team's place in one tournament; its team's captain bans and picks for it.

- fields: ownership: ClassVar[Ownership], tournament_id: int, team_id: int, name: str

### `class TournamentSignup(LifecycleModel, table=True)`
A member signed up alone for a solo tournament, before its teams are drawn.

- fields: ownership: ClassVar[Ownership], natural_key: ClassVar[tuple[str, ...]], tournament_id: int, user_id: int

### `class EntryPlayer(LifecycleModel, table=True)`
A member playing for a tournament entry; a member may play for several entries of one tournament.

- fields: ownership: ClassVar[Ownership], natural_key: ClassVar[tuple[str, ...]], entry_id: int, user_id: int

### `class TournamentMatch(LifecycleModel, table=True)`
One match of a tournament's single-elimination bracket; round 0 is the first.

- fields: ownership: ClassVar[Ownership], tournament_id: int, round: int, slot: int, entry_a_id: int | None, entry_b_id:
  int | None, phase: MatchPhase, winner_id: int | None, started_at: datetime | None, decided_at: datetime | None,
  decided_by: int | None, anonymised: ClassVar[tuple[str, ...]]

### `class MatchLineup(LifecycleModel, table=True)`
A member playing for an entry in one match; a decided match's lineup is what was played.

- fields: ownership: ClassVar[Ownership], anonymised: ClassVar[tuple[str, ...]], match_id: int, entry_id: int, user_id:
  int

### `class MatchEvent(LifecycleModel, table=True)`
Something someone did in a match, and when.

- fields: ownership: ClassVar[Ownership], anonymised: ClassVar[tuple[str, ...]], match_id: int, kind: MatchEventKind,
  actor_id: int, at: datetime, detail: str

### `class LineupChange(LifecycleModel, table=True)`
A member put in or taken out of an entry's lineup, by whom, when, and why.

- fields: ownership: ClassVar[Ownership], anonymised: ClassVar[tuple[str, ...]], entry_id: int, match_id: int | None,
  user_id: int, playing: bool, changed_by: int, changed_at: datetime, reason: str | None

### `class DraftChoice(LifecycleModel, table=True)`
Something a team banned from, or picked for, a match.

- fields: ownership: ClassVar[Ownership], match_id: int, entry_id: int, kind: DraftKind, value: str

### `class MatchVote(LifecycleModel, table=True)`
A question the players of a match vote on, like which map to play.

- fields: ownership: ClassVar[Ownership], match_id: int, question: str, options: str, open: bool

### `class MatchBallot(LifecycleModel, table=True)`
One player's answer to a vote; voting again changes it.

- fields: ownership: ClassVar[Ownership], natural_key: ClassVar[tuple[str, ...]], vote_id: int, user_id: int, choice:
  int

## `winter_dragon.cogs.tournament.service` — `src/winter_dragon/cogs/tournament/service.py`
What can happen to a tournament: signing up, forming teams, running the bracket, drafting and voting.

- module names: PHASES: StateMachine[MatchPhase, MatchStep, PhaseContext]
- `visible_tournaments(session: Session, guild_id: Snowflake, user_id: Snowflake, channel_id: Snowflake | None, *, include_over: bool=False) -> Generator[Tournament]` — Yield the guild's tournaments that ``user_id`` organises, signed up for, or that are posted in ``channel_id``, by name.
- `posts_of(session: Session, tournament: Tournament) -> Generator[TournamentPost]` — Yield the tournament's posts.
- `add_post(session: Session, tournament: Tournament, channel_id: Snowflake, message_id: Snowflake) -> None` — Record that the tournament is shown by ``message_id`` in ``channel_id``.
- `signups_of(session: Session, tournament: Tournament) -> list[TournamentSignup]` — Return everyone signed up alone for the tournament, in sign-up order.
- `signup_of(session: Session, tournament: Tournament, user_id: Snowflake) -> TournamentSignup | None` — Return the user's solo sign-up for the tournament, if any.
- `entries_of(session: Session, tournament: Tournament) -> list[TournamentEntry]` — Return the tournament's teams, in the order they were formed.
- `roster(session: Session, entry: TournamentEntry) -> list[Snowflake]` — Return the user IDs of the entry's players.
- `matches_of(session: Session, tournament: Tournament) -> list[TournamentMatch]` — Return the tournament's matches, round by round, top to bottom.
- `record_event(session: Session, match: TournamentMatch, kind: MatchEventKind, actor_id: Snowflake, detail: str='') -> None` — Record that ``actor_id`` did ``kind`` in ``match`` now, with a short ``detail``.
- `match_log(session: Session, match: TournamentMatch) -> list[MatchEvent | LineupChange]` — Return what happened in ``match``: its events, and the lineup changes made for it, oldest first.
- `sign_up(session: Session, tournament: Tournament, user_id: Snowflake) -> None` — Sign ``user_id`` up for a solo tournament.
- `open_signups_of(session: Session, user_id: Snowflake) -> Generator[Tournament]` — Yield the tournaments ``user_id`` signed up for, alone or in an entry, that haven't started.
- `withdraw(session: Session, tournament: Tournament, user_id: Snowflake) -> None` — Take ``user_id`` out of the tournament before it starts; a captain leaving withdraws their entry.
- `enter(session: Session, tournament: Tournament, team: Team, captain_id: Snowflake) -> TournamentEntry` — Enter the lasting ``team`` into ``tournament`` for its captain, with the captain as its first player.
- `add_player(session: Session, tournament: Tournament, entry: TournamentEntry, captain_id: Snowflake, user_id: Snowflake) -> None` — Add the team member ``user_id`` to ``entry``'s players, for its captain.
- `remove_player(session: Session, tournament: Tournament, entry: TournamentEntry, captain_id: Snowflake, user_id: Snowflake) -> None` — Take ``user_id`` off ``entry``'s players, for its captain; the captain stays.
- `entry_of_captain(session: Session, tournament: Tournament, captain_id: Snowflake) -> TournamentEntry | None` — Return the entry whose team ``captain_id`` captains in ``tournament``, if any.
- `start(session: Session, tournament: Tournament, rng: Random) -> None` — Form the teams of a solo tournament, then lay out the bracket and give the byes their wins.
- `following_phase(phase: MatchPhase) -> MatchPhase | None` — Return the phase the next button moves a match in ``phase`` to; ``None`` when that step is reporting a winner.
- `advance(session: Session, match: TournamentMatch, actor_id: Snowflake) -> None` — Move ``match`` on to its next phase: from ready to the bans, the picks, and live.
- `report(session: Session, match: TournamentMatch, winner_id: int, actor_id: Snowflake, *, forfeit: bool=False) -> None` — Record ``winner_id`` as the winner of ``match``: by playing it live, or because the other team forfeited.
- `cancel(session: Session, tournament: Tournament) -> None` — Call the tournament off: soft-delete it and everything in it, so none of it is seen again.
- `lineup(session: Session, match: TournamentMatch, entry: TournamentEntry) -> list[Snowflake]` — Return the user IDs playing for ``entry`` in ``match``.
- `clashes(session: Session, match: TournamentMatch) -> list[Snowflake]` — Return the members in both lineups of ``match``, ignoring anonymised ones: their deleted IDs don't match.
- `change_lineup(session: Session, tournament: Tournament, entry: TournamentEntry, change: LineupRequest) -> None` — Put ``change.user_id`` in (or take them out of) ``entry``'s lineup for its captain, from its next match not yet live.
- `drop_clash(session: Session, match: TournamentMatch, entry: TournamentEntry, actor_id: Snowflake) -> None` — Drop the clashing members from ``entry``'s side of ``match``, recording who did it.
- `entry_in_match(session: Session, match: TournamentMatch, user_id: Snowflake) -> TournamentEntry | None` — Return the entry in ``match`` whose team ``user_id`` captains, if they captain one of the two.
- `draft(session: Session, match: TournamentMatch, captain_id: Snowflake, kind: DraftKind, value: str) -> None` — Record ``captain_id``'s team banning or picking ``value`` in ``match``, during that phase.
- `drafts_of(session: Session, match: TournamentMatch) -> list[DraftChoice]` — Return the bans and picks made in the match, in the order they were made.
- `open_vote(session: Session, match: TournamentMatch, question: str, options: Sequence[str], actor_id: Snowflake) -> MatchVote` — Open a vote on ``question`` among ``options`` for the players of ``match``, recording who opened it.
- `close_vote(session: Session, vote: MatchVote, actor_id: Snowflake) -> None` — Close ``vote`` so it takes no more answers, recording who closed it.
- `cast(session: Session, vote: MatchVote, user_id: Snowflake, choice: int) -> None` — Record ``user_id``'s answer ``choice`` to ``vote``, replacing their earlier one.
- `choices_of(session: Session, vote: MatchVote) -> list[int]` — Return every answer given to the vote.

### `class WithdrawHiddenMember(MemberHiddenHook)`
A member whose data is hidden leaves each tournament that hasn't started.

- attributes: tables
- `@classmethod on_member_hidden(session: Session, member_id: Snowflake) -> None` — Take the member ``member_id`` out of every tournament they're in that hasn't started.
- `@classmethod removes(member_id: Snowflake) -> Generator[RemovedRows]` — Yield the entries the member ``member_id`` is the only player of, in tournaments that haven't started.

### `@dataclass class PhaseContext`
What a match step acts on: the session, the match, who took the step, and the winner it names.

- fields: session: Session, match: TournamentMatch, actor_id: Snowflake | None, winner_id: int | None

### `@dataclass class LineupRequest`
A captain's request to put a member in or take them out of their entry's lineup.

- fields: captain_id: Snowflake, user_id: Snowflake, playing: bool, reason: str | None

## `winter_dragon.cogs.uptime` — `src/winter_dragon/cogs/uptime.py`
The /uptime command group: how long the bot has been running.

- `uptime_message(launch_time: datetime) -> str` — Return the reply to /uptime bot: when the bot started, as an absolute and a relative Discord timestamp.

### `class Uptime(GroupCog, name='uptime', description='Show how long the bot has been running')`
Cog for showing the bot's uptime.

- `@Cog.command async bot_uptime(interaction: CommandInteraction) -> None` — Reply with when the bot started.

## `winter_dragon.cogs.urban` — `src/winter_dragon/cogs/urban.py`
The /urban command group: look up a term, or random terms, on Urban Dictionary.

- module names: DEFINE_URL, RANDOM_URL
- `definition_field(index: int, definition: Definition) -> EmbedField` — Return the embed field showing ``definition``, numbered ``index``, with its votes and link.
- `definition_fields(definitions: Sequence[Definition], limit: int, budget: int) -> Generator[EmbedField]` — Yield a field for each of the first ``limit`` definitions, stopping before their text exceeds ``budget``.
- `build_embed(title: str, definitions: Sequence[Definition], limit: int) -> Embed` — Return an embed titled ``title`` showing up to ``limit`` of ``definitions``, within Discord's embed limits.

### `class Lookup(LifecycleModel, table=True)`
One /urban search that returned a definition; ``user_id`` is the Discord user ID of who searched, and they own it.

- fields: ownership: ClassVar[Ownership], user_id: int, term: str, looked_up_at: datetime

### `class UrbanSettings`
Settings for /urban, in its ``cogs.ini`` section.

- attributes: allow_random, max_definitions, request_timeout

### `class Definition(BaseModel)`
One definition of a term, as Urban Dictionary's API returns it.

- fields: word: str, definition: str, permalink: str, thumbs_up: int, thumbs_down: int

### `class DefinitionList(BaseModel)`
The body of an Urban Dictionary API response.

- fields: definitions: list[Definition]

### `class LookupFailed(BaseError)`
Urban Dictionary couldn't be asked, or answered something unexpected; the message says which, for the user.

### `class UrbanDictionary(LoggerMixin)`
Asks Urban Dictionary's API for definitions; use as ``async with UrbanDictionary() as urban``.

- `async define(term: str) -> list[Definition] | LookupFailed` — Return the definitions of ``term``, best first; empty when it has none.
- `async random() -> list[Definition] | LookupFailed` — Return a handful of definitions of random terms.

### `class Urban(GroupCog, name='urban', description='Look up words on Urban Dictionary')`
Looks up terms on Urban Dictionary.

- fields: http: AsyncClient | None
- `async load() -> None` — Create the lookup table if missing.
- `@Cog.command async search(interaction: CommandInteraction, query: str) -> None` — Reply with the definitions of ``query``.
- `@Cog.command async random(interaction: CommandInteraction) -> None` — Reply with definitions of random terms, unless that's turned off.

## `winter_dragon.cogs.voice` — `src/winter_dragon/cogs/voice.py`
The /voice command group: split a voice channel into teams that each get a voice channel of their own.

- module names: VOICE_TABLES, CHANNEL_REFUSAL

### `class TeamVoiceChannel(DiscordKeyedModel, table=True)`
A voice channel made for a team of a voice split; ``id`` is the channel's, deleted once empty.

- fields: ownership: ClassVar[Ownership], guild_id: int, team_id: int

### `class Voice(GroupCog, name='voice', description='Voice channel tools: split everyone in your channel into teams', contexts=[InteractionContextType.GUILD])`
Splits the members of a voice channel into random teams, and gives each team a voice channel to move to.

- attributes: rng
- `@property channels -> EmptiedChannels[TeamVoiceChannel]` — The team voice channels, deleted once empty.
- `async load() -> None` — Create the voice tables if missing.
- `@Cog.listener async on_guild_create(guild: GatewayGuild) -> None` — Learn who is in which voice channel, then delete the team channels that emptied while offline.
- `@Cog.listener async on_voice_state_update(state: VoiceState) -> None` — Track who joins and leaves voice, and delete a team channel the member left empty.
- `@Cog.command async split(interaction: GuildCommandInteraction, teams: int=2, move: bool=True) -> None` — Draw temporary teams from the members of the caller's voice channel and post them in its chat.
- `@Cog.component async move_button(interaction: GuildComponentInteraction, team_id: str, split_channel_id: str) -> None` — Move the presser to their team's voice channel, creating it on the team's first press.
