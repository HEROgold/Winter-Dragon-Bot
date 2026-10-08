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
