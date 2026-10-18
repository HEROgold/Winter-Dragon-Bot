<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_db.extension` (wd-db)

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_db.extension.api_table` — `wd-db/src/wd_db/extension/api_table.py`
Extension for databases, integrating api's with the database layer.

### `class ApiArguments(TypedDict)`
Required arguments for API calls.

- fields: api_key: Required[str]

### `class ApiTable(SQLModel, table=True)`
Base class for API-related tables.

- fields: base_url: ClassVar[str], route: ClassVar[str], required_params: ClassVar[ApiArguments], fields:
  ClassVar[dict[str, Any]]
- `fetch(**kwargs: Unpack[ApiArguments]) -> Self` — Fetch data from the API and store it in the database.
- `@classmethod make_api_call(**params: Unpack[ApiArguments]) -> Self` — Make the actual API call.
- `@classmethod get_headers() -> dict[str, str]` — Get headers for the API request.
- `validate() -> None` — Validate that all required parameters are set.

### `class RiotClashV1(ApiTable)`
Table for storing Riot Clash API endpoints and parameters.

- attributes: base_url

### `class RiotTournaments(RiotClashV1, table=True)`
Table for storing Riot Tournaments API endpoints and parameters.

- fields: fields: ClassVar[dict[str, Any]]
- attributes: route

## `wd_db.extension.columns` — `wd-db/src/wd_db/extension/columns.py`
Column types shared by the models of several features.

- `as_utc(moment: datetime) -> datetime` — Return ``moment`` as an aware UTC datetime; naive values are taken as UTC.

### `class AwareDateTime(TypeDecorator[datetime])`
A timestamp column that always stores and reads back aware UTC datetimes, also on sqlite (which drops zones).

- attributes: impl, cache_ok
- `process_bind_param(value: datetime | None, dialect: Dialect) -> datetime | None` — Store ``value`` as UTC.
- `process_result_value(value: datetime | None, dialect: Dialect) -> datetime | None` — Read the stored value back as aware UTC.

## `wd_db.extension.lifecycle` — `wd-db/src/wd_db/extension/lifecycle.py`
The lifecycle every bot table follows: timestamps, soft delete, create-or-restore and a declared owner.

- module names: LIFECYCLE_COLUMNS
- `utc_now() -> datetime` — Return the current time in UTC.
- `alive[M: LifecycleModel](model: type[M]) -> SelectOfScalar[M]` — Return a select of ``model``'s rows that aren't soft-deleted; use it for every read.
- `soft_delete(session: Session, row: LifecycleModel) -> None` — Soft-delete ``row``: stamp its ``deleted_at``, hiding it from :func:`alive`. The caller commits.
- `create_or_restore[M: LifecycleModel](session: Session, row: M) -> M` — Insert ``row``, or restore the soft-deleted row with the same ``id`` or natural key; return the stored row.
- `owned_by[M: LifecycleModel](model: type[M], *, member: int | None=None, guild: int | None=None) -> SelectOfScalar[M]` — Return a select of ``model``'s alive rows owned by ``member`` and/or ``guild``, following its :class:`Through` chain.
- `lifecycle_models() -> Generator[type[LifecycleModel]]` — Yield every lifecycle model class that is a table.
- `ensure_lifecycle_columns(bind: Engine | Connection, *models: type[LifecycleModel]) -> None` — Add the lifecycle columns missing from ``models``' existing tables, as an older bot created them.

### `@dataclass class Through`
Ownership inherited from a parent table: ``column`` holds the ``id`` of a ``parent`` row.

- fields: column: str, parent: type[LifecycleModel]

### `@dataclass class Ownership`
Who a lifecycle table's rows belong to; member deletion and guild departure find rows only through this.

- fields: member: str | None, guild: str | None, through: Through | None

### `class LifecycleModel(BaseModel)`
The base of every bot table: ``created_at``, ``updated_at`` and ``deleted_at``, all aware UTC.

- fields: ownership: ClassVar[Ownership], natural_key: ClassVar[tuple[str, ...]], created_at: datetime, updated_at:
  datetime, deleted_at: datetime | None

### `class DiscordKeyedModel(LifecycleModel)`
A lifecycle model with one row per Discord object, whose ``id`` is that object's Discord ID.

- fields: id: int

## `wd_db.extension.model` — `wd-db/src/wd_db/extension/model.py`
Module for extending SQLModel with custom methods.

- module names: models: set[type[BaseModel]]

### `class ModelLogger(LoggerMixin)`
Polymorphic logger for model, on cls level methods.

### `class BaseModel(BaseSQLModel)`
Base model class with custom methods.

- fields: session: ClassVar[Session], logger: ClassVar[logging.Logger], http_client: ClassVar[Client]
- `add(session: Session | None=None) -> None` — Add a record to Database.
- `update(session: Session | None=None) -> None` — Create or update a record in Database.
- `@classmethod get(id_: int, session: Session | None=None, *, with_for_update: bool=False) -> Self` — Get a record from Database.
- `@classmethod get_all(session: Session | None=None) -> Sequence[Self]` — Get all records from Database.
- `delete(session: Session | None=None) -> None` — Delete a record from Database.
- `@classmethod from_[T](column: Mapped[T], value: T, session: Session | None=None) -> ScalarResult[Self]` — Get a record from Database by field and value.

### `class SQLModel(BaseModel)`
Base SQLModel class with custom methods.

- fields: id: int | None

### `class DiscordID(BaseModel)`
Model with a Discord ID as primary key.

- fields: id: int
- `@classmethod fetch(id_: int) -> Self` — Find existing or create new discord snowflake by id, and return it.
