# wd-discord TODO

Features `wd-discord` still needs before dependent packages (starting with `wd-errors`)
can fully migrate off `discord.py`. Today wd-discord is a low-level REST/gateway API
client (response models + WebSocket gateway); it lacks the application-framework layer
that command/error handling relies on.

Ordering matters: item 0 unblocks everything else, then the model/runtime types, then
the command-framework surface.

---

## 0. Break the wd-discord ↔ wd-errors dependency cycle

wd-discord already imports wd-errors (`src/wd_discord/errors/api.py` → `from wd_errors import ErrorNode`),
so wd-errors cannot import wd-discord at runtime without creating a cycle.

- [ ] Decide the dependency direction. wd-discord is lower-level, so it should **not**
      depend on wd-errors. Move `ErrorNode` (or the small piece wd-discord needs) into
      wd-discord or a shared lower package, or invert so wd-errors depends on wd-discord.
- [ ] Once resolved, declare the dependency explicitly in `pyproject.toml` (currently
      wd-discord imports wd_errors without declaring it).

## 1. `Embed` model

Blocks: `wd-errors/error.py`, `wd-errors/handlers/base.py`.

- [ ] Add an `Embed` model (pydantic `DiscordModel`, consistent with existing models).
- [ ] Constructor accepting `title`, `description`, `color`.
- [ ] `set_footer(text=..., icon_url=...)` (returns self, matching discord.py ergonomics).
- [ ] Serialize to the Discord embed JSON shape for REST/gateway send.
- [ ] Export from `wd_discord/__init__.py`.

## 2. Runtime `Interaction` type

Blocks: `wd-errors/error.py` (`.response.is_done()`, `.response.send_message(...)`, `.followup.send(...)`).

Note: current `interactions.py` only models command *definitions* (`ApplicationCommand`,
`CommandOption`), not a runtime interaction/response object.

- [ ] Add a runtime `Interaction` type.
- [ ] `.response` with `is_done()` and `send_message(embed=..., ephemeral=...)`.
- [ ] `.followup.send(...)`.
- [ ] Wire to the REST client for the actual interaction-response calls.
- [ ] Export from `wd_discord/__init__.py`.

## 3. Command-error exception hierarchy

Blocks: `wd-errors/error.py`, `wd-errors/factory.py`, `wd-errors/handlers/*` (these use the
exception classes as registration keys).

- [ ] Base `DiscordException`.
- [ ] `AppCommandError`, `CommandError`.
- [ ] `CommandNotFound` (used by `handlers/not_found.py`).
- [ ] `CommandInvokeError` (used by `handlers/command_invoke_error.py`).
- [ ] Keep hierarchy shape so `issubclass`/registration-by-type in the error factory works.

## 4. `Context` equivalent (prefix commands)

Blocks: `wd-errors/error.py` (`isinstance(..., Context)`, `.send(...)`).

- [ ] Add a `Context` type with `.send(...)`, **or** decide to drop prefix-command support
      and remove that branch in wd-errors.

## 5. `Bot` / `BotBase` equivalent

Blocks: `wd-errors/error.py`, `wd-errors/factory.py` (TYPE_CHECKING), and the `wd_types.alias` `Bot` alias.

- [ ] Provide a command-dispatching Bot type (or clarify that the existing `Client` plus a
      thin dispatcher covers it) so `wd_types.alias.Bot` can stop pointing at discord.py.

## 6. Detangle `wd_types.alias`

`wd-types/src/wd_types/alias.py` imports discord.py directly (`Embed`, `Member`, `Message`,
`BotBase`, ...) and defines `ResponseTypes = Embed | str` and `Bot`. wd-errors depends on
these aliases transitively.

- [ ] Repoint `ResponseTypes` and `Bot` at the new wd-discord types once items 1 and 5 land.
- [ ] Remove discord.py imports from `wd_types.alias`.

---

## Migration readiness (wd-errors)

- Ready today (no discord.py): `handlers/base.py` logic sans Embed, `size.py`, `base.py`.
- Blocked until the above land: `error.py`, `factory.py`, `handlers/not_found.py`,
  `handlers/command_invoke_error.py`, and the currently commented-out
  `from .handlers import *` in `wd-errors/src/wd_errors/__init__.py`.
