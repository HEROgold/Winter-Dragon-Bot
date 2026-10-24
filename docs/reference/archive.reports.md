<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `archive.reports` (archive)
Reports on the archive's raw events: run with ``python -m archive.reports``.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `archive.reports.changing_fields` — `src/archive/reports/changing_fields.py`
Which fields of which objects change most often, from the raw events.

- `type Payload = Mapping[str, Any]`
- `type Copy = tuple[str, str, Payload]`
- `count_changes(events: Iterable[tuple[str, Payload]]) -> FieldChanges` — Count the field changes across ``events``, given in the order they were received as (name, payload).
- `copies_in(name: str, data: Payload) -> Iterator[Copy]` — Yield every object copy event ``name`` carries.
- `render(result: FieldChanges, *, limit: int) -> str` — Return the ``limit`` most changed fields as a text table.

### `@dataclass class FieldChanges`
Counts of field changes per kind of object.

- fields: changes: Counter[tuple[str, str]], copies: Counter[str]
- `add(kind: str, key: str, payload: Payload) -> None` — Compare one copy of an object with its previous one, and keep it as the latest.

## `archive.reports.unmodelled` — `src/archive/reports/unmodelled.py`
What wd-discord doesn't model yet, from the raw events: events without a model, and fields models don't know.

- `find_unmodelled(events: Iterable[tuple[str, Mapping[str, Any]]]) -> Unmodelled` — Sort ``events``, as (name, payload), into what wd-discord doesn't model.
- `unknown_fields(model: DiscordModel) -> Iterator[tuple[str, str]]` — Yield (model, field) for every field ``model`` and the models inside it keep as extra.
- `render(result: Unmodelled) -> str` — Return the report as text.

### `@dataclass class Unmodelled`
What the raw events carried that wd-discord doesn't model.

- fields: events: Counter[str], fields: Counter[tuple[str, str]], unparsable: Counter[str]
