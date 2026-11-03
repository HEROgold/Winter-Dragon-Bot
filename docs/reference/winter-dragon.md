<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `winter_dragon` (winter-dragon)
Winter Dragon: the Discord bot and its web dashboard.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `winter_dragon.bot_stats` — `src/winter_dragon/bot_stats.py`
What the bot serves right now, read from its gateway cache: guilds, channels, members, shards and uptime.

- module names: SNAPSHOT_ID
- `member_count(state: GuildState) -> int` — Return how many members ``state``'s guild has: as GUILD_CREATE or a counted fetch said, else as cached.
- `store_snapshot(session: Session, stats: BotStats) -> None` — Make ``stats`` the latest snapshot. The caller commits.
- `latest_snapshot(bind: Engine) -> BotStats | None` — Return the latest snapshot the bot stored; ``None`` before its first.

### `class ShardStats(BaseModel, frozen=True)`
One gateway shard: whether Discord still acknowledges its heartbeats, and how fast.

- fields: id: int, alive: bool, latency: float | None
- `@classmethod of(gateway: Gateway, index: int) -> ShardStats` — Read ``gateway``, the ``index``-th shard; its ID is the one it identified with, else ``index``.

### `class BotStats(BaseModel, frozen=True)`
A snapshot of what the bot serves, built from the cache without a request to Discord.

- fields: taken_at: datetime, launch_time: datetime, version: str, guilds: int, unavailable_guilds: int, channels: int,
  threads: int, members: int, cached_users: int, shards: tuple[ShardStats, ...]
- `@property uptime -> timedelta` — How long the bot had been running when the snapshot was taken.
- `@property shards_alive -> int` — How many shards Discord still acknowledges.
- `@classmethod of(bot: Bot) -> BotStats` — Take a snapshot of ``bot``: its client's cache and its shards.
- `@classmethod from_cache(cache: StateCache, shards: ShardManager | None, *, launch_time: datetime) -> BotStats` — Take a snapshot of ``cache`` and ``shards`` (``None`` before the gateway connects).

### `class BotStatsSnapshot(LifecycleModel, table=True)`
The bot's latest :class:`BotStats`, for the dashboard; shared data, owned by no one.

- fields: stats: str

## `winter_dragon.config` — `src/winter_dragon/config.py`
The app's own config scopes: app-wide settings in ``config.ini``, cog settings in ``cogs.ini``.

### `class Config[T](BaseConfig[T])`
Config descriptor scoped to the app-wide settings file.

### `class CogConfig[T](BaseConfig[T])`
Config descriptor scoped to the cog settings file; every cog shares it, one section per settings class.

### `class Settings`
Application-wide settings.

- attributes: bot_name, support_guild_id, dashboard_url, log_level, created_color, changed_color, deleted_color,
  act_color, wait_color, stop_color, step_done_mark, step_here_mark, step_next_mark, winner_mark, bot_status_messages

## `winter_dragon.config_migration` — `src/winter_dragon/config_migration.py`
Where every section of the old single ``config.ini`` lives now, and the startup step that moves it there.

- module names: MOVES
- `migrate_legacy_config() -> MigrationReport | None` — Move the old single ``config.ini`` into the per-scope files, logging what moved and what was dropped.

## `winter_dragon.event_logger` — `src/winter_dragon/event_logger.py`
A bot that does nothing but log every frame the Discord gateway sends it.

- `async main() -> None` — Connect with every intent and log events until interrupted.

### `class EventLoggingGateway(Gateway)`
A gateway that logs every frame it receives as raw JSON before handling it.

- `async log_ready(name: str, event: DiscordModel) -> None` — Log READY, which :meth:`connect` consumes before :meth:`_handle` sees it; other events are logged raw.

## `winter_dragon.health` — `src/winter_dragon/health.py`
Container health checks, run by compose: ``python -m winter_dragon.health bot`` or ``... web``.

- module names: ALIVE_FILE, ALIVE_MAX_AGE, WEB_TIMEOUT, CHECKS
- `bot_healthy() -> bool` — Return whether :data:`ALIVE_FILE` was touched within :data:`ALIVE_MAX_AGE` seconds.
- `web_healthy() -> bool` — Return whether the dashboard's landing page answers 200 on this host.
- `main(argv: list[str]) -> int` — Run the check named by ``argv[0]`` and return the exit code.

## `winter_dragon.member_hidden` — `src/winter_dragon/member_hidden.py`
Hooks a feature registers to clean up after a member whose data is hidden, so privacy needn't know the feature.

### `@dataclass class RemovedRows`
Rows of ``model`` a hook removes that the member doesn't own; ``ids`` selects their ``id``.

- fields: model: type[LifecycleModel], ids: SelectOfScalar[int | None]

### `class MemberHiddenHook`
A feature's own cleanup when a member's data is hidden; defining a subclass registers it.

- fields: tables: ClassVar[tuple[type[LifecycleModel], ...]]
- `@classmethod on_member_hidden(session: Session, member_id: Snowflake) -> None` — Clean up the member ``member_id``'s data in ``session``, before their owned rows are hidden; don't commit.
- `@classmethod removes(member_id: Snowflake) -> Generator[RemovedRows]` — Yield the rows :meth:`on_member_hidden` removes that the member ``member_id`` doesn't own; none by default.
- `@staticmethod run_all(session: Session, member_id: Snowflake, stored: Collection[type[LifecycleModel]]) -> None` — Call every registered hook whose :attr:`tables` are all in ``stored``, for the member ``member_id``.
- `@staticmethod removed_by_all(member_id: Snowflake, stored: Collection[type[LifecycleModel]]) -> Generator[RemovedRows]` — Yield the rows the hooks :meth:`run_all` calls remove for the member ``member_id``, beyond what they own.

## `winter_dragon.metrics` — `src/winter_dragon/metrics.py`
The Prometheus metrics the bot and the dashboard serve on ``/metrics``, inside the compose network only.

- module names: BUCKETS, WORK_SECONDS, REST_SECONDS, GATEWAY_EVENTS, WEB_REQUEST_SECONDS
- `observe(timing: Timing) -> None` — Record ``timing`` in :data:`REST_SECONDS` or :data:`WORK_SECONDS`.
- `count_event(name: str) -> None` — Count the gateway event ``name`` in :data:`GATEWAY_EVENTS`.
- `observe_requests(app: FastAPI) -> None` — Time each request ``app`` answers in :data:`WEB_REQUEST_SECONDS`, labelled by its route's path template.

### `class MetricsSettings`
Where the ``/metrics`` endpoint listens, in ``config.ini``.

- attributes: port

### `class BotStatsCollector(Collector)`
Reads a fresh :class:`~winter_dragon.bot_stats.BotStats` at each scrape and serves it as gauges.

- `collect() -> Generator[Metric]` — Yield the snapshot's counts, and each shard's state and latency.

### `class Exporter`
The ``/metrics`` endpoint of this process: started once, whatever reloads the cogs do.

- fields: serving: ClassVar[bool], collector: ClassVar[BotStatsCollector | None]
- `@classmethod serve() -> None` — Serve ``/metrics`` on :attr:`MetricsSettings.port`, unless this process already does.
- `@classmethod serve_bot(take: Callable[[], BotStats]) -> None` — Serve the bot's metrics: what ``take`` returns at each scrape, and what :class:`Telemetry` reports.

## `winter_dragon.redirect_link` — `src/winter_dragon/redirect_link.py`
Links to the dashboard's ``/redirect`` page, which opens an app link (``steam://...``) Discord won't make clickable.

- module names: REDIRECT_PATH, BLOCKED_SCHEMES, FALLBACK_SCHEME

### `class UnsafeLinkError(ValueError)`
A link the redirect page won't open; the message says why, for the visitor who followed it.

### `@dataclass class RedirectLink`
Where the redirect page sends a visitor: ``uri``, ``mobile`` on a phone, and a ``fallback`` page without the app.

- fields: uri: str, mobile: str | None, fallback: str | None
- `target(*, phone: bool) -> str` — Return the link to open: :attr:`mobile` on a phone when there is one, else :attr:`uri`.
- `on(dashboard_url: str) -> str` — Return the URL of this link's redirect page on the dashboard served at ``dashboard_url``.

## `winter_dragon.run_test_bot` — `src/winter_dragon/run_test_bot.py`
Run a real wd_bot.Bot for up to 10 minutes against the live Discord API.

- module names: RUN_DURATION_SECONDS
- `async main() -> int` — Run the bot for up to RUN_DURATION_SECONDS, then report the outcome.

## `winter_dragon.stored` — `src/winter_dragon/stored.py`
Loading a stored row a command needs, refusing when it's gone.

- `stored[M: LifecycleModel](session: Session, model: type[M], record_id: int, gone: str) -> M` — Return the alive ``model`` stored as ``record_id``; refuse with ``gone`` when there's none.

## `winter_dragon.voice_channels` — `src/winter_dragon/voice_channels.py`
Voice channels a cog creates and records, deleted once everyone left.

### `@dataclass class VoiceOccupancy`
Who is in which voice channel, per guild, as far as the gateway told.

- `reset(guild_id: Snowflake, states: Iterable[VoiceState]) -> None` — Forget what was known about ``guild_id``, and learn ``states`` instead.
- `move(guild_id: Snowflake, user_id: Snowflake, channel_id: Snowflake | None) -> Snowflake | None` — Record that ``user_id`` is now in ``channel_id``, or left voice when ``None``; return where they were.
- `occupied(guild_id: Snowflake, channel_id: Snowflake) -> bool` — Whether anyone is in the voice channel ``channel_id``.
- `channel_of(guild_id: Snowflake, user_id: Snowflake) -> Snowflake | None` — Return the voice channel ``user_id`` is in, if the gateway told.
- `members_in(guild_id: Snowflake, channel_id: Snowflake) -> list[Snowflake]` — Return who is in the voice channel ``channel_id``.

### `@dataclass class EmptiedChannels[M: DiscordKeyedModel]`
Voice channels a cog created and records as ``model`` rows (``id`` is the channel's), deleted once empty.

- fields: model: type[M], bind: Engine | Connection, client: Client, logger: Logger, reason: str, on_forgotten:
  Callable[[Session, M], None] | None
- `record(session: Session, channel_id: Snowflake) -> M | None` — Return the live row recording the voice channel ``channel_id``, or ``None`` if it has none.
- `async delete(record: M) -> None` — Delete the voice channel of ``record`` and forget it once it's gone; one that's left is tried again later.
- `forget(record: M) -> None` — Forget the voice channel of ``record``, which is gone: soft-delete its row.
- `async sweep(voice: VoiceOccupancy, guild_id: Snowflake) -> None` — Delete the recorded voice channels of ``guild_id`` that nobody is in.
- `async left(voice: VoiceOccupancy, guild_id: Snowflake, before: Snowflake | None, after: Snowflake | None) -> None` — Delete the recorded voice channel ``before`` once the member who left it left it empty.
