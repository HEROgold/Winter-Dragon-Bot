<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_types` (wd-types)

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_types.clock` — `wd-types/src/wd_types/clock.py`
The one clock: every "now" in the workspace comes from :func:`utc_now`.

- `utc_now() -> datetime` — Return the current time as an aware UTC datetime.

## `wd_types.protocol` — `wd-types/src/wd_types/protocol.py`
Contains protocols for WinterDragon.

### `@runtime_checkable class Mentionable(Protocol)`
A protocol for objects that can be mentioned in Discord.

- `@property mention -> str` — Return the string that can be used to mention this object.
