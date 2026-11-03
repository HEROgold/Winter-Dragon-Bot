<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `winter_dragon.ui` (winter-dragon)
Reusable pieces of the app's Discord replies.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `winter_dragon.ui` — `src/winter_dragon/ui/__init__.py`

- exports: ChangedEmbed, CreatedEmbed, DeletedEmbed, Mark, Tone, block, card, mentions, steps

## `winter_dragon.ui.cards` — `src/winter_dragon/ui/cards.py`
Components v2 cards: one colored container per message, and the marks that steps and winners share.

- `steps(names: list[str], current: int) -> str` — Return ``names`` as one line of steps, marking those before ``current`` done and ``current`` itself in bold.
- `card(tone: Tone, *components: ActionRow | TextDisplay | Section | MediaGallery | Separator | FileDisplay) -> Container` — Return ``components`` in one container, its bar colored for ``tone``.
- `block(*lines: str) -> TextDisplay` — Return ``lines`` as one text display, one per line; empty lines are left out.

### `class Tone(Enum)`
What a card asks of whoever reads it, shown as the color of its bar.

- attributes: ACT, WAIT, STOP
- `@property color -> Color` — The bar color set for this tone in ``config.ini``.

### `class Mark(Enum)`
A mark put before text: where a sequence of steps stands, or who won.

- attributes: DONE, HERE, NEXT, WINNER

## `winter_dragon.ui.embeds` — `src/winter_dragon/ui/embeds.py`
Confirmation embeds for something created, changed or deleted, in the colors set in ``config.ini``.

### `class CreatedEmbed(Embed)`
Confirms that something was created, in ``Settings.created_color``.

- fields: color: Color | None

### `class ChangedEmbed(Embed)`
Confirms that something was changed, in ``Settings.changed_color``.

- fields: color: Color | None

### `class DeletedEmbed(Embed)`
Confirms that something was deleted, in ``Settings.deleted_color``.

- fields: color: Color | None

## `winter_dragon.ui.text` — `src/winter_dragon/ui/text.py`
Text the bot's messages share.

- `mentions(user_ids: Iterable[Snowflake]) -> str` — Return the users as mentions, or a dash for nobody; cut to fit an embed field.
