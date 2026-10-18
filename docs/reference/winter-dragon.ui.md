<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `winter_dragon.ui` (winter-dragon)
Reusable pieces of the app's Discord replies.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `winter_dragon.ui` — `src/winter_dragon/ui/__init__.py`

- exports: ChangedEmbed, CreatedEmbed, DeletedEmbed

## `winter_dragon.ui.embeds` — `src/winter_dragon/ui/embeds.py`
Confirmation embeds for something created, changed or deleted, in the colors set in ``config.ini``.

### `class CreatedEmbed(Embed)`
Confirms that something was created, in ``Settings.created_color``.

- fields: color: int | None

### `class ChangedEmbed(Embed)`
Confirms that something was changed, in ``Settings.changed_color``.

- fields: color: int | None

### `class DeletedEmbed(Embed)`
Confirms that something was deleted, in ``Settings.deleted_color``.

- fields: color: int | None
