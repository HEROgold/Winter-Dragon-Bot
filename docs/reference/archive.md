<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `archive` (archive)
The archive: a read-only bot that records every gateway event into the database (docs/spec/archive.md).

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `archive.cleanup` — `src/archive/cleanup.py`
The archive's daily task: purge raw events older than the retention period.

- module names: DAY

### `@dataclass class RawEventPurge(LoggerMixin)`
Deletes raw events older than :attr:`retention_days`, once a day.

- fields: engine: Engine, retention_days: int
- `async run() -> None` — Purge now, then once a day, until cancelled.
- `purge() -> int` — Delete the raw events older than :attr:`retention_days`; return how many.

## `archive.handlers` — `src/archive/handlers.py`
What the archive writes for each gateway event.

- module names: GUILD_LISTS, HANDLERS: dict[str, Handler]
- `type Payload = dict[str, Any]`
- `type Handler = Callable[[Session, Payload], None]`
- `payload_of(event: DiscordModel) -> Payload` — Return ``event`` as the JSON Discord sent: only the fields it carried, under Discord's names.
- `store_raw(session: Session, name: str, sequence: int | None, data: Mapping[str, Any]) -> None` — Append one dispatch, exactly as received, to the raw events.
- `handle(session: Session, name: str, data: Payload) -> None` — Write ``data`` to the typed tables, when event ``name`` has a handler.
- `save_user(session: Session, user: Payload) -> None` — Upsert a user from any payload that carries one; only its ID means there is nothing to write.
- `save_member(session: Session, guild_id: object, member: Payload, user_id: object=None) -> None` — Upsert a member, and its user when the payload carries it.
- `save_presence(session: Session, presence: Payload, source: str, guild_id: object=None) -> None` — Append a presence, and upsert whatever of its user it carries.
- `save_voice_state(session: Session, state: Payload, source: str, guild_id: object=None) -> None` — Append a voice state, and upsert the member it carries.
- `save_message(session: Session, message: Payload) -> None` — Upsert a message, with its author and the author's membership.
- `replace_guild_set(session: Session, table: type[db.Emoji | db.Sticker], guild_id: object, items: list[Payload]) -> None` — Upsert a guild's full emoji or sticker list, and delete the ones no longer in it.
- `on_ready(session: Session, data: Payload) -> None` — READY: the archive's own user.
- `on_guild_create(session: Session, data: Payload) -> None` — GUILD_CREATE / GUILD_UPDATE: the guild, and everything it lists, with presences and voice as a snapshot.
- `on_guild_delete(session: Session, data: Payload) -> None` — GUILD_DELETE: the archive left the guild; an outage (``unavailable``) is not a removal.
- `on_channel(session: Session, data: Payload) -> None` — CHANNEL_CREATE / _UPDATE, THREAD_CREATE / _UPDATE and the voice channel status and start time updates.
- `on_channel_delete(session: Session, data: Payload) -> None` — CHANNEL_DELETE / THREAD_DELETE.
- `on_channel_pins_update(session: Session, data: Payload) -> None` — CHANNEL_PINS_UPDATE.
- `on_thread_list_sync(session: Session, data: Payload) -> None` — THREAD_LIST_SYNC: the threads of some channels, and the archive's own membership of them.
- `on_thread_member_update(session: Session, data: Payload) -> None` — THREAD_MEMBER_UPDATE.
- `on_thread_members_update(session: Session, data: Payload) -> None` — THREAD_MEMBERS_UPDATE: who joined and left a thread.
- `on_member(session: Session, data: Payload) -> None` — GUILD_MEMBER_ADD / GUILD_MEMBER_UPDATE.
- `on_member_remove(session: Session, data: Payload) -> None` — GUILD_MEMBER_REMOVE.
- `on_members_chunk(session: Session, data: Payload) -> None` — GUILD_MEMBERS_CHUNK: members, and their presences as a snapshot.
- `on_role(session: Session, data: Payload) -> None` — GUILD_ROLE_CREATE / GUILD_ROLE_UPDATE.
- `on_role_delete(session: Session, data: Payload) -> None` — GUILD_ROLE_DELETE.
- `on_emojis_update(session: Session, data: Payload) -> None` — GUILD_EMOJIS_UPDATE.
- `on_stickers_update(session: Session, data: Payload) -> None` — GUILD_STICKERS_UPDATE.
- `on_user_update(session: Session, data: Payload) -> None` — USER_UPDATE.
- `on_presence_update(session: Session, data: Payload) -> None` — PRESENCE_UPDATE.
- `on_voice_state_update(session: Session, data: Payload) -> None` — VOICE_STATE_UPDATE.
- `on_message_create(session: Session, data: Payload) -> None` — MESSAGE_CREATE.
- `on_message_update(session: Session, data: Payload) -> None` — MESSAGE_UPDATE: the message, and its new content as a revision.
- `on_message_delete(session: Session, data: Payload) -> None` — MESSAGE_DELETE.
- `on_message_delete_bulk(session: Session, data: Payload) -> None` — MESSAGE_DELETE_BULK.
- `reaction(action: str) -> Handler` — Return the handler that appends a reaction event of ``action``.
- `on_typing_start(session: Session, data: Payload) -> None` — TYPING_START.
- `on_interaction(session: Session, data: Payload) -> None` — INTERACTION_CREATE.
- `without(payload: Mapping[str, Any], *keys: str) -> Payload` — Return ``payload`` without ``keys``.

## `archive.mapping` — `src/archive/mapping.py`
Sort a Discord payload into a table's columns, its child lists and the rest (kept as custom data).

- module names: TIMESTAMPS, CHILD_BOOKKEEPING
- `split(table: type[ArchiveTable], payload: Mapping[str, Any]) -> Split` — Sort ``payload`` into ``table``'s columns, child lists and custom data.
- `column_for(table: type[ArchiveTable], key: str) -> str | None` — Return the column ``table`` stores payload ``key`` in, or ``None`` when it has none.
- `convert(column: Column[Any], value: object) -> Any` — Convert a JSON ``value`` to what ``column`` stores.

### `@dataclass class Split`
A payload sorted for one table.

- fields: values: dict[str, Any], children: dict[str, list[Any]], extra: dict[str, Any]

## `archive.store` — `src/archive/store.py`
Write sorted payloads to the archive tables: upsert an entity, append an event, soft-delete, replace child lists.

- `type Entity = ArchiveEntity | ArchiveCompositeEntity`
- `upsert[E: Entity](session: Session, table: type[E], payload: Mapping[str, Any], **known: object) -> E` — Write ``payload`` onto ``table``'s stored row, creating it, or restoring it when deleted; return the row.
- `append[V: ArchiveEvent](session: Session, table: type[V], payload: Mapping[str, Any], **known: object) -> V` — Append ``payload`` to ``table`` as a new row, with ``known`` columns set; return the row.
- `soft_delete(session: Session, table: type[Entity], **key: object) -> None` — Mark the stored row with ``key`` (its ``id``, or its natural key) deleted; nothing happens when there is none.

## `archive.writer` — `src/archive/writer.py`
The archive's single database writer: a bounded queue of jobs, written in batches by one task.

- `type Job = Callable[[Session], None]`

### `@dataclass class Writer(LoggerMixin)`
Queues jobs and writes them to ``engine`` in batches.

- fields: engine: Engine, queue_limit: int, batch_size: int, batch_interval: float, max_backoff: float, queue:
  asyncio.Queue[Job], dropped: int
- `put(job: Job) -> None` — Queue ``job``; when the queue is full, drop it and count it.
- `async run() -> None` — Write batches until cancelled; on cancel, write what is still queued first.
- `write(session: Session, batch: list[Job]) -> None` — Run ``batch`` in ``session`` and commit; a job that fails is logged and skipped.
