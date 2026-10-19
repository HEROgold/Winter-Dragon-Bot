# Rewrite wd-bot's Bot/Cog onto wd-* only (Phase 1 of 2)

## Context

[wd-bot/src/wd_bot/bot.py](wd-bot/src/wd_bot/bot.py) is half-migrated: it mixes a correct
`wd_discord.Client`-based `start()` with dead discord.py-era code (`command_prefix`/`help_command`/`tree_cls`
constructor args that get passed into a `super().__init__()` on a class with no such base, `discord.utils.oauth_url`,
undefined `Context`/`CommandError` names, and reads from a name-mangled `discord.py`-only attribute
`self._BotBase__extensions`). The goal is a forever-running `Bot` that connects to Discord's gateway, loads
extensions ("cogs"), and reacts to gateway events — built entirely on `wd-*` packages.

Investigating what `bot.py` depends on turned up that the "new" side isn't actually finished either:
- `wd_discord.Client` **cannot be constructed today** — a dead `BotUser` class in
  [client.py](wd-discord/src/wd_discord/client.py) decorates methods with `@loop()` from `wd_bot.tasks`, which
  subclasses real `discord.ext.tasks.Loop` — discord.py isn't an installed dependency anywhere in this workspace, so
  merely using `Client` raises `ModuleNotFoundError`. `BotUser` has no other callers.
- `Client.get_shard_manager()` does `async with ShardManager(...) as manager: return manager` — this runs
  `__aexit__` (which closes every shard) *before* returning, so the manager handed back is already dead. This is the
  actual root cause of "the bot connects then exits immediately" that `bot.py`'s own TODO comment complains about.
- `wd_core.constants.BOT_PERMISSIONS = Permissions.all()` references `Permissions`, which is never imported in that
  file, and `Permissions.all()` doesn't exist (`Permissions` is a plain `IntFlag`). Importing `wd_core.constants` —
  which `bot.py`'s `BotConfig` does at class-definition time — currently raises `NameError`.
- [wd_bot/cogs.py](wd-bot/src/wd_bot/cogs.py)'s `Cog` also still subclasses `commands.Cog` (undefined import) and
  uses several other undefined discord.py names (`discord`, `app_commands`, `_cog_special_method`), plus
  `wd_bot.tasks.loop` (same discord.py dependency problem as `BotUser`). Every real extension in `wd-cogs` subclasses
  this `Cog`, so extension loading can't work until it's fixed.
- `wd_discord`'s gateway layer has **no event-dispatch loop at all**: `Gateway.connect()` stops reading the socket
  the moment it sees `READY`; every other dispatch frame after that is silently dropped, and only the heartbeat task
  keeps running. There's no listener/callback registration anywhere.

None of this is optional cleanup — each item blocks `Bot` from importing, connecting, staying connected, or loading
extensions at all. This plan (Phase 1) fixes all of it and produces a genuinely forever-running, event-reacting bot.
**Explicitly out of scope for Phase 1** (agreed with the user, deferred to a separate Phase 2): `wd_core.CommandTree`
stays an empty stub; `wd_discord.interactions` (application/slash command definitions, currently dataclass-based and
unimportable on Python 3.15 due to an unrelated `herogold` bug) is untouched; no `Interaction` event model, no
interaction-response REST, no slash-command registration/dispatch; no SIGTERM/graceful-shutdown handling (no
production entrypoint exists yet to hang it off); the real `wd_cogs` catalog (Welcome, Uptime, etc.) is **not**
required to import cleanly — those modules have their own unrelated broken imports (`app_commands`, `Menu`, `Modal`)
that are separate cleanup work.

## Changes, in dependency order

**1. [wd-discord/src/wd_discord/client.py](wd-discord/src/wd_discord/client.py)**
- Delete the `BotUser` class entirely (lines 258-304) and the now-unused `from wd_bot.tasks import loop` import —
  it's dead code with no callers, and pulls in a real discord.py dependency that doesn't exist in this workspace.
  Check whether `Snowflake`/`ApiResponseError`/`BaseError` imports become unused after the deletion and drop them if so.
- Fix `get_shard_manager`: stop entering/exiting the `ShardManager` context — just construct and return it unstarted,
  and thread `intents` through (currently hardcoded to `0`):
  ```python
  async def get_shard_manager(self, info: GatewayBotInfo, *, intents: Intents = 0) -> ShardManager:
      return ShardManager(self.token, info, intents=intents)
  ```

**2. [wd-discord/src/wd_discord/permissions.py](wd-discord/src/wd_discord/permissions.py)**
- Add an `all()`/`none()` pair to `Permissions`, matching the existing no-`self` convention already used by
  `Intents.all()`/`Intents.none()` in [wd-core/src/wd_core/intents.py:159-168](wd-core/src/wd_core/intents.py#L159-L168):
  ```python
  def none() -> Permissions:
      return Permissions(0)

  def all() -> Permissions:
      result = Permissions.none()
      for member in Permissions:
          result |= member
      return result
  ```

**3. [wd-core/src/wd_core/constants.py](wd-core/src/wd_core/constants.py)**
- Add `from wd_discord.permissions import Permissions` (wd-core already depends on wd-discord in
  [pyproject.toml](wd-core/pyproject.toml), no manifest change needed here). `BOT_PERMISSIONS = Permissions.all()`
  now resolves correctly.

**4. [wd-discord/src/wd_discord/gateway/connection.py](wd-discord/src/wd_discord/gateway/connection.py)**
- Fix the `Ready` model to use real fields instead of a raw `user: dict`:
  ```python
  class Ready(DiscordModel):
      v: int
      user: User
      guilds: list[dict[str, Any]] = Field(default_factory=list)  # TODO(Phase 2): type as PartialGuild
      session_id: str
      resume_gateway_url: str
      shard: tuple[int, int] | None = None
      application_id: str | None = None
  ```
  Update `parse_ready` accordingly (`user=User.model_validate(data["user"])`, plus `v`, `guilds`, `shard`).
- Add a continuous receive loop to `Gateway`, callable only after `connect()`/`READY`:
  ```python
  type DispatchCallback = Callable[[str, DiscordModel], Awaitable[None]]

  async def listen(self, dispatch: DispatchCallback) -> None:
      """Receive gateway frames forever, updating `_seq` and dispatching on DISPATCH.

      Runs until the connection closes, is cancelled, or Discord sends RECONNECT/INVALID_SESSION
      (TODO(Phase 2): implement RESUME using resume_gateway_url/session_id/_seq; for now this just
      logs and returns, dropping the shard).
      """
      if self._ws is None:
          msg = "Gateway is not connected."
          raise RuntimeError(msg)
      while True:
          message = json.loads(await self._ws.recv())
          if (seq := message.get("s")) is not None:
              self._seq = seq
          match message["op"]:
              case Opcode.DISPATCH:
                  name = message.get("t")
                  if name:
                      await dispatch(name, parse_dispatch(name, message.get("d", {})))
              case Opcode.HEARTBEAT:
                  await self._send(Opcode.HEARTBEAT, self._seq)
              case Opcode.RECONNECT | Opcode.INVALID_SESSION:
                  self.logger.warning(t"Gateway requested reconnect (op {message['op']}); closing shard.")
                  return
              case Opcode.HEARTBEAT_ACK:
                  pass
  ```
  Import `parse_dispatch` from the new `events.py` (item 5). To avoid an import cycle (`events.py` needs nothing
  from `connection.py` except reuse of `Ready`/`parse_ready`, which stay local to `connection.py` and are *not*
  routed through `parse_dispatch` — `Gateway.listen` never sees another `READY` after `connect()` returns, so
  `parse_dispatch` never needs to special-case it).

**5. New file: `wd-discord/src/wd_discord/gateway/events.py`**
- Owns event-name → model mapping, pure and unit-testable (mirrors the existing `parse_ready`/`parse_gateway_bot` style):
  ```python
  class RawEvent(DiscordModel):
      """Fallback for any dispatch event without a dedicated model."""
      name: str
      data: dict[str, Any]

  class GuildCreate(Guild):
      """GUILD_CREATE: Guild plus the gateway-only fields REST omits."""
      joined_at: str | None = None
      large: bool | None = None
      unavailable: bool | None = None
      member_count: int | None = None
      channels: list[Channel] = Field(default_factory=list)
      # TODO(Phase 2): members/voice_states/presences/threads/... need real models
      # (Member, VoiceState, ...); kept as raw dicts for now.
      members: list[dict[str, Any]] = Field(default_factory=list)
      voice_states: list[dict[str, Any]] = Field(default_factory=list)
      presences: list[dict[str, Any]] = Field(default_factory=list)

  class Message(DiscordModel):
      """MESSAGE_CREATE (subset)."""
      id: Snowflake
      channel_id: Snowflake
      guild_id: Snowflake | None = None
      author: User
      content: str
      timestamp: str
      edited_timestamp: str | None = None
      tts: bool
      mention_everyone: bool
      # TODO(Phase 2): mentions[]/attachments[]/embeds[]/reactions[] need their own models.

  _EVENT_MODELS: dict[str, type[DiscordModel]] = {
      "GUILD_CREATE": GuildCreate,
      "MESSAGE_CREATE": Message,
  }

  def parse_dispatch(name: str, data: dict[str, Any]) -> DiscordModel:
      model = _EVENT_MODELS.get(name)
      return model.model_validate(data) if model else RawEvent(name=name, data=data)
  ```
- Wire `RawEvent`, `GuildCreate`, `Message`, `parse_dispatch` into
  [gateway/\_\_init\_\_.py](wd-discord/src/wd_discord/gateway/__init__.py) and, for `RawEvent`/`Message`/`GuildCreate`
  if useful externally, into [wd_discord/\_\_init\_\_.py](wd-discord/src/wd_discord/__init__.py)'s `__all__`.

**6. [wd-discord/src/wd_discord/gateway/sharding.py](wd-discord/src/wd_discord/gateway/sharding.py)**
- Add to `ShardManager`:
  ```python
  async def serve_forever(self, dispatch: DispatchCallback) -> None:
      """Run every shard's receive loop until cancelled. Call while started (inside `async with manager:`)."""
      if not self.shards:
          msg = "ShardManager is not started."
          raise RuntimeError(msg)
      await asyncio.gather(*(shard.listen(dispatch) for shard in self.shards))
  ```

**7. [wd-bot/src/wd_bot/cogs.py](wd-bot/src/wd_bot/cogs.py) — rewrite**
- Drop `commands.Cog` base, `AppCommandCache`/`cache`/`get_app_command`/`get_command_mention`, `@loop()`-based
  `add_mentions`, `has_error_handler`/`has_app_command_error_handler` checks, `cog_command_error`/
  `cog_app_command_error` (all discord.py- or CommandTree-shaped — CommandTree is a stub, so there's nothing to
  route errors from yet; this is intentional Phase 2 debt, not an oversight).
- Keep: `BotArgs` (retype `bot: Required[Bot]`, importing the new `Bot` from `wd_bot.bot`), `CogFlags` (drop
  `_HasAppCommandMentions`), `default_flags`, `__init_subclass__`'s flag logic, `AutoReloadWatcher` wiring,
  `auto_load`.
- Add a minimal listener tag, per the user's explicit instruction to keep it simple now and formalize later:
  ```python
  def listener(name: str | None = None) -> Callable[[F], F]:
      """Tag a Cog method as a gateway dispatch-event listener.

      TODO: replace with a strictly-typed listener registry (handler signature checked against
      the event's payload type) once more dispatch events are modeled — this is intentionally a
      bare attribute tag for now, not a maintainable long-term design.
      """
      def decorator(func: F) -> F:
          func.__listener_event__ = name or func.__name__.removeprefix("on_").upper()
          return func
      return decorator
  ```
- Resulting shape:
  ```python
  class Cog(LoggerMixin):
      bot: Bot
      flags: CogFlags = default_flags
      __cog_name__: ClassVar[str]
      listener = staticmethod(listener)

      def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
          self.bot = kwargs["bot"]
          self.session = kwargs.get("db_session", Session(engine))
          self._auto_reloader = AutoReloadWatcher(bot=self.bot, cog_cls=type(self))
          if self.__class__ not in (Cog, GroupCog):
              self.bot.loop.create_task(self.auto_load())
              self._auto_reloader.register()

      def __init_subclass__(cls, *, auto_load: bool = True, flags: CogFlags | None = None) -> None:
          super().__init_subclass__()
          cls.__cog_name__ = cls.__name__
          if flags:
              cls.flags = flags
          if auto_load:
              cls.flags |= CogFlags.AutoLoad
          else:
              cls.flags &= ~CogFlags.AutoLoad

      async def auto_load(self) -> None:
          if self.__cog_name__ in self.bot.cogs:
              return
          if self.flags & CogFlags.AutoLoad:
              self.logger.debug(t"Auto loaded Cog {type(self).__name__}")
              await self.bot.add_cog(self)

      async def cog_load(self) -> None:
          """Hook for subclasses; no-op by default (no CommandTree to sync yet)."""

      async def cog_unload(self) -> None:
          self._auto_reloader.deregister()

  class GroupCog(Cog):
      """Marker subclass for future app-command-group cogs (Phase 2)."""
  ```

**8. [wd-bot/src/wd_bot/bot.py](wd-bot/src/wd_bot/bot.py) — rewrite**
- Drop `command_prefix`, `help_command`, `tree_cls`, `PrefixType` entirely — no prefix-based command system exists
  in the new architecture, and `CommandTree` is a stub. Don't import `wd_bot.help` at all (it's also broken —
  `wd_core.ui` doesn't exist — importing it would blow up at class-definition time).
- Add a cog registry and a minimal dispatcher:
  ```python
  class Bot(LoggerMixin):
      launch_time: datetime.datetime
      loop: asyncio.AbstractEventLoop
      cogs: dict[str, Cog]
      _extensions: dict[str, ModuleType]
      _listeners: dict[str, list[Callable[[DiscordModel], Awaitable[None]]]]

      def __init__(self, *, intents: Intents = BotConfig.Intents, description: str | None = None) -> None:
          self.launch_time = datetime.datetime.now(datetime.UTC)
          self.intents = intents
          self.description = description
          self.cogs = {}
          self._extensions = {}
          self._listeners = {}

      def get_bot_invite(self) -> str:
          if not Settings.application_id:
              msg = "application_id is not configured."
              raise ValueError(msg)
          scope = "%20".join(Settings.BOT_SCOPE)
          return (
              "https://discord.com/api/oauth2/authorize"
              f"?client_id={Settings.application_id}&permissions={int(BotConfig.Permissions)}&scope={scope}"
          )

      async def add_cog(self, cog: Cog) -> None:
          self.cogs[cog.__cog_name__] = cog
          for _, member in inspect.getmembers(cog, predicate=inspect.iscoroutinefunction):
              event = getattr(member, "__listener_event__", None)
              if event:
                  self._listeners.setdefault(event, []).append(member)
          await cog.cog_load()

      async def _dispatch(self, event_name: str, payload: DiscordModel) -> None:
          for handler in self._listeners.get(event_name, []):
              self.loop.create_task(self._invoke_listener(handler, payload))

      async def _invoke_listener(self, handler, payload: DiscordModel) -> None:
          try:
              await handler(payload)
          except Exception:
              self.logger.exception(t"Unhandled exception in listener {handler!r} for {payload!r}")
  ```
- Keep `_discover_wd_cogs_modules`/`get_extensions`/`load_extension`/`load_extensions` as-is in structure, but fix
  `_load_from_module_spec` to use a plain `self._extensions` dict instead of the nonexistent
  `self._BotBase__extensions`:
  ```python
  async def _load_from_module_spec(self, spec: ModuleSpec, key: str) -> None:
      if spec.loader is None:
          raise ExtensionError(key, RuntimeError("Module spec has no loader"))
      module = module_from_spec(spec)
      try:
          spec.loader.exec_module(module)
          await self._init_cogs(module)
      except Exception as e:
          raise ExtensionError(key, e) from e
      self._extensions[key] = module
  ```
  `_init_cogs` stays the same shape (instantiate every `Cog` subclass found in the module — instantiation itself
  triggers `auto_load()` via `Cog.__init__`), just excluding `Cog`/`GroupCog` themselves from the check.
- Rewrite `start()` to actually stay connected:
  ```python
  @with_known_exception(StartupError)
  @Config.with_kwarg("Tokens", "discord_token")
  async def start(self, token: str) -> None:
      self.loop = asyncio.get_running_loop()
      async with Client(token) as client:
          me = await client.get_current_user()
          if not isinstance(me, User):
              raise StartupError("Failed to get current user from Discord API")
          gw_info = await client.get_gateway_bot()
          if not isinstance(gw_info, GatewayBotInfo):
              raise StartupError("Failed to get gateway bot info from Discord API")
          manager = await client.get_shard_manager(gw_info, intents=self.intents)
          await self.load_extensions()
          async with manager:
              self.logger.info(t"Bot is running with {len(manager.shards)} shards")
              await manager.serve_forever(self._dispatch)
  ```
- Drop `on_error`/`on_command_error` (both `Context`/`CommandError`-shaped — no command framework exists yet).
- **Open call, decided**: keep `description` in `__init__` even though nothing consumes it yet — cheap to keep,
  avoids re-adding the param when Phase 2 lands. No signal/SIGTERM handling added — there's no real entrypoint
  script yet to hang it off (only test/verify drivers exist); whoever writes the eventual entrypoint wraps
  `asyncio.run(bot.start())`, and Ctrl+C/`CancelledError` propagates through `asyncio.gather` in `serve_forever` and
  unwinds the `async with` blocks cleanly already.

**9. [wd-bot/pyproject.toml](wd-bot/pyproject.toml)**
- Currently only declares `wd-config` as a workspace dependency, but `bot.py`/`cogs.py` now import `wd_discord`,
  `wd_core`, `wd_errors`, `wd_types` directly. Add them via `uv add wd-discord wd-core wd-errors wd-types` (per the
  `dependencies` skill — never hand-edit `pyproject.toml`/`uv.lock`). `wd-db`/`wd-cogs` stay implicit/undeclared —
  out of scope, not touched by this change.

**10. Tests**
- New `wd-bot/tests/` directory (none exists today).
- `wd-bot/tests/fixtures/example_cog.py`: a minimal self-contained `Cog` subclass with one `@Cog.listener()`-tagged
  method — used to prove `load_extension`/`_init_cogs`/`add_cog`/dispatch wiring end-to-end without touching the
  real (partly-broken, out-of-scope) `wd_cogs` catalog.
- `wd-discord/tests/test_gateway_dispatch.py` (or extend `test_gateway_payload.py` if it already covers
  `parse_ready`-style pure parsing): unit-test `parse_dispatch`/`GuildCreate`/`Message`/fixed `Ready`+`parse_ready`
  purely on payload dicts, no socket. Also a fake-`ClientConnection`-based test (matching whatever fake-gateway
  pattern `wd-discord/tests/test_sharding.py` already uses) that feeds `Gateway.listen()` canned JSON frames and
  asserts `_seq` updates and the dispatch callback fires with the right parsed model.
- Extend `wd-discord/tests/test_permissions.py` with a `Permissions.all()` case (OR of every member).
- Optional live smoke test: a small script (following the existing `run-wd-discord` skill's token-loading
  convention) that calls `await asyncio.wait_for(bot.start(), timeout=N)` and expects `TimeoutError` — proving the
  bot stayed connected instead of exiting immediately.

## Verification

1. `uv sync` after the `pyproject.toml` change.
2. `uv run pytest wd-discord/tests wd-bot/tests` — new and existing tests green (use the `run-tests` skill for the
   known-broken subset to exclude, if any apply here).
3. `uv run ruff check` / whatever type checker this repo uses (`ty`/pyright per the `code-style` skill) on the
   touched files — confirm no undefined-name errors remain in `bot.py`/`cogs.py`/`client.py`.
4. Manually import-check the previously-broken chain: `python -c "from wd_bot.bot import Bot"` should succeed
   without `NameError`/`ModuleNotFoundError`.
5. Run the optional live smoke test (needs a real bot token in `config.ini`/`discord.ini` per existing convention)
   to confirm `Bot.start()` no longer exits immediately and dispatches at least a `READY`-driven connection log.
