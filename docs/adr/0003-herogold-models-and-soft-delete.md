# Bot tables are herogold models: soft delete by default, history only where it is read

Every table of the bot subclasses a `herogold.orm` model instead of plain `SQLModel`. By default that is `BaseModel`: one row per record with `created_at`, `updated_at` and `deleted_at`, where deleting only stamps `deleted_at` and the default `.query` and `count()` hide the row, so a deleted record is simply not present. A table whose change history is itself something people read (infractions, guild-setting changes shown in the server log) uses `DataModel` instead, which appends a row per create, update and delete.

Where a row is one per Discord object, its `id` is that object's Discord ID rather than an auto-increment number. A table whose natural key spans several IDs (a remembered role is guild, member and role) keeps the auto-increment `id` and puts a unique constraint on the natural key.

## Considered Options

- **Plain `SQLModel` tables, as the first ported cogs have.** Rejected: no timestamps, and deleting is final, so a guild that removes the bot by accident loses its setup at once.
- **`DataModel` everywhere.** Rejected: its key is `(id, timestamp)` and a delete is just another row, so "deleted means not present" needs a latest-row query on every read, and erasing a user means deleting every history row. History is kept only where someone reads it.
- **Soft delete only for tables tied to a guild or user.** Rejected: every new cog would have to decide which kind its table is; one rule for all tables is simpler.

## Consequences

- Creating a record whose key exists soft-deleted restores it: `deleted_at` is cleared and its fields are overwritten. Turning a feature off and on again, and re-adding the bot to a departed guild, both go through this.
- herogold has no purge, so the bot purges permanently itself: a member's data 30 days after they request deletion, and a departed guild's data 30 days after it removed the bot. Until then the rows are soft-deleted and hidden.
- Existing cog tables migrate to these bases; tables keyed by a Discord ID keep it as `id`.
