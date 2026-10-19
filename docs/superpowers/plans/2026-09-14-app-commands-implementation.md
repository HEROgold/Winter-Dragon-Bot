# Discord Application-Command Support — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add global Discord application-command (slash command) support to the wd-* stack — registration, diff-based sync, and `INTERACTION_CREATE` dispatch — then ship two commands built on it: `winter_dragon/cogs/percentage.py` (compatibility-percentage command) and an admin `/bot-commands` management command.

**Architecture:** `wd_discord` gains the data model (`Interaction`, `Embed`, a fixed `CommandOption` + a new `RegisteredCommand`) and REST methods (interaction responses, global command CRUD). `wd_bot` gains a `Command` class (built by a new `Cog.command()` decorator) that encapsulates a command's definition and dispatch, a `_commands` registry on `Bot` wired to a new `INTERACTION_CREATE` listener, and a diff-based sync engine (`CommandRecord` + `GlobalSyncedCommand` + `GuildSyncedCommand` tables) that only touches Discord's API for commands whose signature actually changed. This is Phase 2 of the work tracked in `.claude/tracking/PHASE1_PLAN.md`/`PHASE1_PROGRESS.md`, which explicitly deferred all of this.

**Tech Stack:** Python 3.15, pydantic v2 (`DiscordModel`), SQLModel/SQLAlchemy (`wd_db`), pytest.

**Spec:** `docs/superpowers/specs/2026-09-14-app-commands-design.md`

## Global Constraints

- Python 3.15, ruff `select = ["ALL"]` (only `D105`/`TD005` ignored), pyright strict, `ty` — every new function needs a docstring, modern typing (`X | None`, PEP 695 generics), and passes `uv run ruff check .` / `uv run ruff format --check .` / `uv run pyright`.
- Module-level imports go through `lazy import`/`lazy from` (CLAUDE.md) except where pydantic needs a real class at class-definition time (see the existing eager-import notes in `wd_discord/gateway/events.py` and `connection.py`).
- Every module: one-line docstring, `from __future__ import annotations`, two blank lines after the import block.
- `Client` REST methods never raise on API/network failure — they return `ApiResponseError | RequestError` as a value (`returns_known_exception` / the existing `NetworkError` type alias).
- Collection-returning helpers/properties `yield` (`Generator[T]`), never build and return a `list`.
- V1 ships **global commands only**. `GuildSyncedCommand` and its diff logic are still built and unit-tested (per the design doc's Q8 answer), but nothing wires a real command to guild scope yet — do not add a `guild_ids` parameter to `Cog.command()`.
- Dependencies are added via `uv add <package>` (per the `dependencies` skill), never by hand-editing `pyproject.toml`/`uv.lock`.
- After adding a model to `EventName` (Task 4), regenerate `wd-discord/src/wd_discord/gateway/dispatch.pyi` via `uv run wd-discord/scripts/generate_dispatch_overloads.py` — a pre-push hook checks this file isn't stale.

---

### Task 1: `ApplicationCommandOptionType` + fix `CommandOption`'s type field

**Files:**
- Modify: `wd-discord/src/wd_discord/interactions.py`
- Modify: `wd-discord/tests/test_interactions.py`

**Interfaces:**
- Produces: `ApplicationCommandOptionType(IntEnum)` with members `SUB_COMMAND=1`, `SUB_COMMAND_GROUP=2`, `STRING=3`, `INTEGER=4`, `BOOLEAN=5`, `USER=6`, `CHANNEL=7`, `ROLE=8`, `MENTIONABLE=9`, `NUMBER=10`, `ATTACHMENT=11`.

- [ ] **Step 1: Write the failing test**

Add to `wd-discord/tests/test_interactions.py` (inside the existing `try` block's import list, add `ApplicationCommandOptionType`):

```python
def test_application_command_option_type_values() -> None:
    assert ApplicationCommandOptionType.STRING == 3
    assert ApplicationCommandOptionType.USER == 6
    assert ApplicationCommandOptionType.SUB_COMMAND == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest wd-discord/tests/test_interactions.py::test_application_command_option_type_values -v`
Expected: FAIL (`ImportError: cannot import name 'ApplicationCommandOptionType'`) — the whole module skips via the existing `try/except (ImportError, TypeError)` guard rather than showing a hard failure; confirm by temporarily running with `-p no:cacheprovider --no-header` and checking the skip reason mentions `ApplicationCommandOptionType`, or just add the import at the top of your local shell (`python -c "from wd_discord.interactions import ApplicationCommandOptionType"`) to see the raw `ImportError` directly.

- [ ] **Step 3: Implement**

In `wd-discord/src/wd_discord/interactions.py`, add near `ApplicationCommandType`:

```python
class ApplicationCommandOptionType(IntEnum):
    """Represents the type of an application command option (distinct from the command's own type)."""

    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8
    MENTIONABLE = 9
    NUMBER = 10
    ATTACHMENT = 11
```

Change `CommandOption.field_type: ApplicationCommandType | None` to `field_type: ApplicationCommandOptionType | None` (it was wrongly typed against the *command* type enum).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest wd-discord/tests/test_interactions.py -v`
Expected: PASS (module no longer skips for this symbol; may still skip overall if the pre-existing herogold py3.15 import bug is present in this environment — see `herogold-py315-break` note. If it skips, verify the fix by running `uv run python -c "from wd_discord.interactions import ApplicationCommandOptionType; print(ApplicationCommandOptionType.USER)"` directly instead.)

- [ ] **Step 5: Commit**

```bash
git add wd-discord/src/wd_discord/interactions.py wd-discord/tests/test_interactions.py
git commit -m "wd-discord: add ApplicationCommandOptionType, fix CommandOption's mistyped field_type"
```

---

### Task 2: Pydantic `CommandOption` + new `RegisteredCommand` model

**Files:**
- Modify: `wd-discord/src/wd_discord/interactions.py`
- Modify: `wd-discord/tests/test_interactions.py`

**Interfaces:**
- Consumes: `ApplicationCommandOptionType` (Task 1), `wd_discord.models.DiscordModel`, `wd_discord.snowflake.Snowflake`, `wd_discord.permissions.PermissionsField`.
- Produces: `CommandOption(DiscordModel)` — fields `type: ApplicationCommandOptionType`, `name: str`, `description: str`, `required: bool = False`, `choices: list[Mapping[str, object]] | None = None`, `options: list[CommandOption] | None = None`. `RegisteredCommand(DiscordModel)` — fields `id: Snowflake`, `application_id: Snowflake`, `guild_id: Snowflake | None = None`, `version: Snowflake`, `name: str`, `description: str`, `options: list[CommandOption] = []`, `default_member_permissions: PermissionsField | None = None`, `dm_permission: bool = True`, `nsfw: bool = False`. Both consumed by `Client` (Task 6) and `Command` (Task 9).

This replaces the existing hand-rolled `@validate @dataclass CommandOption` with a real pydantic model (per the design doc — this is the already-flagged-as-TODO "pydantic port"). `ApplicationCommand`/`UserApplicationCommand`/`MessageApplicationCommand`/`PrimaryEntryPointApplicationCommand`/`validate`/`required_if`/`absent_if` are **left untouched** — they have no other callers in the codebase (confirmed by grep), so this task doesn't need to migrate or delete them; `RegisteredCommand` is a fresh, narrower model for what this design actually needs (parsing what Discord's command-list endpoint returns), not a replacement for those dataclasses.

- [ ] **Step 1: Write the failing test**

Replace the interactions import block in `wd-discord/tests/test_interactions.py` to add `CommandOption`, `RegisteredCommand`, and change the `LimitedString`/`TooLongError` import source (they're general string utilities, not interaction-specific — import them from their real home instead of via the re-export):

```python
from wd_discord.utils.strings import LimitedString, TooLongError

try:
    from wd_discord.interactions import (
        ApplicationCommandOptionType,
        ApplicationCommandType,
        CommandHandlerType,
        CommandOption,
        IntegrationType,
        InteractionContextType,
        Locales,
        RegisteredCommand,
    )
except (ImportError, TypeError) as exc:  # pragma: no cover - environment-dependent
    pytest.skip(f"wd_discord.interactions is unimportable: {exc}", allow_module_level=True)
```

Remove `test_required_if_validator` and `test_absent_if_validator` (they tested dataclass-only machinery on the old `CommandOption`, which no longer applies — `required_if`/`absent_if` themselves are untouched and still used by the untouched `ApplicationCommand` dataclass, just no longer exercised by `CommandOption`'s own tests). Add:

```python
def test_command_option_validates_from_dict() -> None:
    option = CommandOption.model_validate(
        {"type": 6, "name": "user", "description": "The user to check", "required": True},
    )
    assert option.type is ApplicationCommandOptionType.USER
    assert option.required is True


def test_registered_command_validates_discord_payload() -> None:
    payload = {
        "id": "111",
        "application_id": "222",
        "version": "333",
        "name": "percentage",
        "description": "Calculate a random compatibility percentage with another user",
        "options": [{"type": 6, "name": "user", "description": "The user to check", "required": True}],
    }
    command = RegisteredCommand.model_validate(payload)
    assert command.name == "percentage"
    assert command.options[0].name == "user"
    assert command.guild_id is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest wd-discord/tests/test_interactions.py::test_command_option_validates_from_dict wd-discord/tests/test_interactions.py::test_registered_command_validates_discord_payload -v`
Expected: FAIL (`ImportError: cannot import name 'CommandOption'` — the pydantic version doesn't exist yet).

- [ ] **Step 3: Implement**

In `wd-discord/src/wd_discord/interactions.py`, remove the old `@validate @dataclass class CommandOption: ...` block (including its docstring table) and replace with:

```python
class CommandOption(DiscordModel):
    """An option for an application command (https://docs.discord.com/developers/interactions/application-commands#application-command-object-application-command-option-structure)."""

    type: ApplicationCommandOptionType
    name: str
    description: str
    required: bool = False
    choices: list[Mapping[str, object]] | None = None
    options: list[CommandOption] | None = None


class RegisteredCommand(DiscordModel):
    """A chat-input application command as Discord's REST API returns it (list/create/edit response)."""

    id: Snowflake
    application_id: Snowflake
    guild_id: Snowflake | None = None
    version: Snowflake
    name: str
    description: str
    options: list[CommandOption] = Field(default_factory=list)
    default_member_permissions: PermissionsField | None = None
    dm_permission: bool = True
    nsfw: bool = False
```

Add the needed imports at the top of the file (eager, since `DiscordModel` subclasses need real classes at class-definition time, matching the existing convention in `gateway/events.py`):

```python
from collections.abc import Mapping
from wd_discord.models import DiscordModel
from wd_discord.permissions import PermissionsField
from wd_discord.snowflake import Snowflake
```

and keep `from dataclasses import dataclass, field` (still used by the untouched `ApplicationCommand` family) plus add `from pydantic import Field` if not already imported.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest wd-discord/tests/test_interactions.py -v`
Expected: PASS on all non-skipped tests.

- [ ] **Step 5: Commit**

```bash
git add wd-discord/src/wd_discord/interactions.py wd-discord/tests/test_interactions.py
git commit -m "wd-discord: port CommandOption to pydantic, add RegisteredCommand"
```

---

### Task 3: Minimal `Embed` model

**Files:**
- Create: `wd-discord/src/wd_discord/embed.py`
- Create: `wd-discord/tests/test_embed.py`
- Modify: `wd-discord/src/wd_discord/__init__.py` (export `Embed`, `EmbedField`)

**Interfaces:**
- Consumes: `wd_discord.models.DiscordModel`.
- Produces: `EmbedField(DiscordModel)` — `name: str`, `value: str`, `inline: bool = False`. `Embed(DiscordModel)` — `title: str | None = None`, `description: str | None = None`, `color: int | None = None`, `fields: list[EmbedField] | None = None`. Consumed by `Client.create_interaction_response` (Task 6) and `winter_dragon/cogs/percentage.py` (Task 12).

- [ ] **Step 1: Write the failing test**

```python
# wd-discord/tests/test_embed.py
"""Unit tests: the minimal Embed model."""
from __future__ import annotations

from wd_discord.embed import Embed, EmbedField


def test_embed_serializes_only_set_fields() -> None:
    embed = Embed(title="Percentage", description="You and @x are 73% compatible!", color=0xFF69B4)
    dumped = embed.model_dump(mode="json", exclude_none=True)
    assert dumped == {"title": "Percentage", "description": "You and @x are 73% compatible!", "color": 0xFF69B4}


def test_embed_with_fields() -> None:
    embed = Embed(title="Love Meter", fields=[EmbedField(name="target", value="73%", inline=True)])
    dumped = embed.model_dump(mode="json", exclude_none=True)
    assert dumped["fields"] == [{"name": "target", "value": "73%", "inline": True}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest wd-discord/tests/test_embed.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'wd_discord.embed'`).

- [ ] **Step 3: Implement**

```python
# wd-discord/src/wd_discord/embed.py
"""A minimal Discord embed model.

Only the fields needed to replicate ``wd_cogs/games/love_meter.py``'s presentation
(https://docs.discord.com/developers/resources/message#embed-object) are modeled. Every embed
field is optional per Discord's docs; the ones not modeled yet are: ``type``, ``url``,
``timestamp``, ``footer``, ``image``, ``thumbnail``, ``video``, ``provider``, ``author``,
``flags`` — add them here (and to :class:`EmbedField` for ``fields``' nested shape, already
covered) as a future command actually needs them.
"""
from __future__ import annotations

from wd_discord.models import DiscordModel


class EmbedField(DiscordModel):
    """One entry in an embed's ``fields`` array."""

    name: str
    value: str
    inline: bool = False


class Embed(DiscordModel):
    """A Discord message embed (minimal subset - see module docstring for what's missing)."""

    title: str | None = None
    description: str | None = None
    color: int | None = None
    fields: list[EmbedField] | None = None
```

Add `from wd_discord.embed import Embed, EmbedField` to `wd_discord/__init__.py`'s import block and `__all__` list, matching how other resources are exported there.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest wd-discord/tests/test_embed.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add wd-discord/src/wd_discord/embed.py wd-discord/tests/test_embed.py wd-discord/src/wd_discord/__init__.py
git commit -m "wd-discord: add minimal Embed/EmbedField model"
```

---

### Task 4: `Interaction` model + wire `EventName.INTERACTION_CREATE`

**Files:**
- Modify: `wd-discord/src/wd_discord/gateway/events.py`
- Modify: `wd-discord/tests/test_gateway_payload.py` (or create `wd-discord/tests/test_interaction_event.py` — create it; keep `test_gateway_payload.py` focused on presence/READY as it is today)
- Regenerate: `wd-discord/src/wd_discord/gateway/dispatch.pyi` (generated file, not hand-edited)

**Interfaces:**
- Consumes: `CommandOption` (Task 2, for typing `InteractionDataOption`'s shape — actually not needed directly; see below), `wd_discord.resources.user.User`, `wd_discord.snowflake.Snowflake`.
- Produces: `InteractionType(IntEnum)` (`PING=1`, `APPLICATION_COMMAND=2`, `MESSAGE_COMPONENT=3`, `APPLICATION_COMMAND_AUTOCOMPLETE=4`, `MODAL_SUBMIT=5`). `ResolvedData(DiscordModel)` — `users: dict[str, User] | None = None`. `InteractionDataOption(DiscordModel)` — `name: str`, `type: int`, `value: str | int | bool | None = None`. `InteractionData(DiscordModel)` — `id: Snowflake`, `name: str`, `type: int`, `options: list[InteractionDataOption] = []`, `resolved: ResolvedData | None = None`. `Interaction(DiscordModel)` — `id: Snowflake`, `application_id: Snowflake`, `type: InteractionType`, `data: InteractionData | None = None`, `guild_id: Snowflake | None = None`, `channel_id: Snowflake | None = None`, `member: Mapping[str, object] | None = None`, `user: User | None = None`, `token: str`, `version: int`, plus a computed property `invoking_user: User | None`. `EventName.INTERACTION_CREATE` gains `Interaction` as its `.model`. Consumed by `wd_bot.bot.Bot` (Task 11) and `wd_bot.commands.Command` (Task 9).

- [ ] **Step 1: Write the failing test**

```python
# wd-discord/tests/test_interaction_event.py
"""Unit tests: the Interaction dispatch-event model."""
from __future__ import annotations

from wd_discord.gateway import EventName
from wd_discord.gateway.dispatch import parse_dispatch
from wd_discord.gateway.events import Interaction, InteractionType


def test_interaction_create_has_a_model() -> None:
    assert EventName.INTERACTION_CREATE.model is Interaction


def test_parse_dispatch_parses_application_command_interaction() -> None:
    payload = {
        "id": "1",
        "application_id": "2",
        "type": 2,
        "token": "tok",
        "version": 1,
        "user": {"id": "3", "username": "asker", "discriminator": "0"},
        "data": {
            "id": "10",
            "name": "percentage",
            "type": 1,
            "options": [{"name": "user", "type": 6, "value": "4"}],
            "resolved": {"users": {"4": {"id": "4", "username": "target", "discriminator": "0"}}},
        },
    }
    interaction = parse_dispatch("INTERACTION_CREATE", payload)
    assert isinstance(interaction, Interaction)
    assert interaction.type is InteractionType.APPLICATION_COMMAND
    assert interaction.data is not None
    assert interaction.data.name == "percentage"
    assert interaction.data.resolved is not None
    assert interaction.data.resolved.users is not None
    assert interaction.data.resolved.users["4"].username == "target"
    assert interaction.invoking_user is not None
    assert interaction.invoking_user.username == "asker"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest wd-discord/tests/test_interaction_event.py -v`
Expected: FAIL (`ImportError: cannot import name 'Interaction'`).

- [ ] **Step 3: Implement**

In `wd-discord/src/wd_discord/gateway/events.py`, add (near the other dispatch models, after `GuildCreate`):

```python
class InteractionType(IntEnum):
    """The kind of interaction an INTERACTION_CREATE dispatch carries."""

    PING = 1
    APPLICATION_COMMAND = 2
    MESSAGE_COMPONENT = 3
    APPLICATION_COMMAND_AUTOCOMPLETE = 4
    MODAL_SUBMIT = 5


class ResolvedData(DiscordModel):
    """The ``resolved`` block of interaction command data - full objects for referenced IDs."""

    users: dict[str, User] | None = None


class InteractionDataOption(DiscordModel):
    """One option value as submitted in an interaction (not the command's *definition* - see CommandOption for that)."""

    name: str
    type: int
    value: str | int | bool | None = None


class InteractionData(DiscordModel):
    """The ``data`` block of an application-command INTERACTION_CREATE."""

    id: Snowflake
    name: str
    type: int
    options: list[InteractionDataOption] = Field(default_factory=list)
    resolved: ResolvedData | None = None


class Interaction(DiscordModel):
    """INTERACTION_CREATE (https://docs.discord.com/developers/interactions/receiving-and-responding#interaction-object)."""

    id: Snowflake
    application_id: Snowflake
    type: InteractionType
    data: InteractionData | None = None
    guild_id: Snowflake | None = None
    channel_id: Snowflake | None = None
    member: Mapping[str, object] | None = None
    user: User | None = None
    token: str
    version: int

    @property
    def invoking_user(self) -> User | None:
        """The user who triggered this interaction, whether invoked in a guild (``member``) or a DM (``user``)."""
        if self.user is not None:
            return self.user
        if self.member is not None and "user" in self.member:
            return User.model_validate(self.member["user"])
        return None
```

`IntEnum` needs importing (`from enum import IntEnum, StrEnum`, already imports `StrEnum` — add `IntEnum` to that line). Add the new member to `EventName`, right after `GUILD_CREATE`:

```python
    MESSAGE_CREATE = ("MESSAGE_CREATE", Message)
    GUILD_CREATE = ("GUILD_CREATE", GuildCreate)
    INTERACTION_CREATE = ("INTERACTION_CREATE", Interaction)
```

Remove the old bare `INTERACTION_CREATE = "INTERACTION_CREATE"` line further down in the enum body (it's currently listed among the unmodeled events - delete that line, don't leave a duplicate member).

- [ ] **Step 4: Regenerate the dispatch overloads**

Run: `uv run wd-discord/scripts/generate_dispatch_overloads.py`
This updates `wd-discord/src/wd_discord/gateway/dispatch.pyi` to add an `@overload` for `Literal["INTERACTION_CREATE"]`. Verify with `uv run wd-discord/scripts/generate_dispatch_overloads.py --check` (exits 0).

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest wd-discord/tests/test_interaction_event.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add wd-discord/src/wd_discord/gateway/events.py wd-discord/src/wd_discord/gateway/dispatch.pyi wd-discord/tests/test_interaction_event.py
git commit -m "wd-discord: add Interaction model, wire EventName.INTERACTION_CREATE"
```

---

### Task 5: `Client` application-ID caching

**Files:**
- Modify: `wd-discord/src/wd_discord/client.py`
- Create: `wd-discord/tests/test_client_application_id.py`

**Interfaces:**
- Consumes: `Client.get_current_application()` (existing), `wd_config.bot.Settings.application_id` (existing `Config[int | None]`).
- Produces: `Client._get_application_id(self) -> str | NetworkError` (private — internal helper for Task 6's command-CRUD methods; returns Discord's decimal-string application ID, fetching-and-caching via `get_current_application()` on first use, and writing the result back into `Settings.application_id` if it was unset).

- [ ] **Step 1: Write the failing test**

```python
# wd-discord/tests/test_client_application_id.py
"""Unit tests: Client._get_application_id's fetch-and-cache behavior."""
from __future__ import annotations

import pytest
from wd_config.bot import Settings
from wd_discord import Client
from wd_discord.resources.application import Application


@pytest.fixture(autouse=True)
def _reset_application_id() -> None:
    original = Settings.application_id
    yield
    Settings.application_id = original


async def test_fetches_and_caches_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    Settings.application_id = None
    client = Client("token")
    calls = 0

    async def fake_get_current_application() -> Application:
        nonlocal calls
        calls += 1
        return Application.model_validate({"id": "999", "name": "test", "icon": None, "description": ""})

    monkeypatch.setattr(client, "get_current_application", fake_get_current_application)

    first = await client._get_application_id()  # noqa: SLF001 - testing the private cache path directly
    second = await client._get_application_id()  # noqa: SLF001

    assert first == "999"
    assert second == "999"
    assert calls == 1  # cached after the first call
    assert Settings.application_id == 999  # written back


async def test_uses_configured_value_without_fetching(monkeypatch: pytest.MonkeyPatch) -> None:
    Settings.application_id = 555
    client = Client("token")

    async def fail_if_called() -> Application:
        pytest.fail("should not fetch when Settings.application_id is already set")

    monkeypatch.setattr(client, "get_current_application", fail_if_called)

    assert await client._get_application_id() == "555"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest wd-discord/tests/test_client_application_id.py -v`
Expected: FAIL (`AttributeError: 'Client' object has no attribute '_get_application_id'`).

- [ ] **Step 3: Implement**

In `wd-discord/src/wd_discord/client.py`, add `self._application_id: str | None = None` to `Client.__init__`, and add `lazy from wd_config.bot import Settings` to the imports. Then add the method (near the other resource helpers):

```python
    async def _get_application_id(self) -> str | NetworkError:
        """Return this client's application ID, fetching-and-caching it via the API if unset.

        Prefers an already-configured ``Settings.application_id``; otherwise fetches it once via
        :meth:`get_current_application` and writes it back into ``Settings`` so future ``Client``
        instances don't need to fetch it again.
        """
        if self._application_id is not None:
            return self._application_id
        if Settings.application_id:
            self._application_id = str(Settings.application_id)
            return self._application_id
        app = await self.get_current_application()
        if isinstance(app, (ApiResponseError, RequestError)):
            return app
        application_id = app.model_dump(mode="json")["id"]
        self._application_id = application_id
        Settings.application_id = int(application_id)
        return application_id
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest wd-discord/tests/test_client_application_id.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add wd-discord/src/wd_discord/client.py wd-discord/tests/test_client_application_id.py
git commit -m "wd-discord: cache Client's application ID, fetching it lazily when unconfigured"
```

---

### Task 6: `Client` interaction-response + global-command REST methods

**Files:**
- Modify: `wd-discord/src/wd_discord/client.py`
- Create: `wd-discord/tests/test_client_commands.py`

**Interfaces:**
- Consumes: `Embed` (Task 3), `CommandOption`/`RegisteredCommand` (Task 2), `Interaction` (Task 4), `Client._get_application_id` (Task 5).
- Produces: `_build_command_payload(name: str, description: str, options: Sequence[CommandOption]) -> dict[str, Any]` (module-level pure function). `Client.create_interaction_response(interaction: Interaction, *, content: str | None = None, embeds: list[Embed] | None = None) -> RequestResult`. `Client.create_global_command(name: str, description: str, options: list[CommandOption] | None = None) -> RegisteredCommand | NetworkError`. `Client.edit_global_command(command_id: str, name: str, description: str, options: list[CommandOption] | None = None) -> RegisteredCommand | NetworkError`. `Client.delete_global_command(command_id: str) -> NetworkError | None`. `Client.get_global_commands() -> Generator[RegisteredCommand] | NetworkError`. Consumed by `wd_bot.auto_sync` (Task 8) and `wd_bot.commands.Command` (Task 9, for sending responses).

- [ ] **Step 1: Write the failing test**

```python
# wd-discord/tests/test_client_commands.py
"""Unit tests: command-payload building and response parsing (no network)."""
from __future__ import annotations

from wd_discord.client import _build_command_payload
from wd_discord.interactions import ApplicationCommandOptionType, CommandOption, RegisteredCommand


def test_build_command_payload_includes_options() -> None:
    option = CommandOption(type=ApplicationCommandOptionType.USER, name="user", description="Target user", required=True)
    payload = _build_command_payload("percentage", "Calculate a percentage", [option])
    assert payload == {
        "name": "percentage",
        "description": "Calculate a percentage",
        "type": 1,
        "options": [{"type": 6, "name": "user", "description": "Target user", "required": True}],
    }


def test_build_command_payload_no_options() -> None:
    payload = _build_command_payload("ping", "Ping", [])
    assert payload["options"] == []


def test_registered_command_round_trips_from_create_response() -> None:
    response_json = {
        "id": "1",
        "application_id": "2",
        "version": "3",
        "name": "percentage",
        "description": "Calculate a percentage",
        "options": [],
    }
    command = RegisteredCommand.model_validate(response_json)
    assert command.name == "percentage"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest wd-discord/tests/test_client_commands.py -v`
Expected: FAIL (`ImportError: cannot import name '_build_command_payload'`).

- [ ] **Step 3: Implement**

In `wd-discord/src/wd_discord/client.py`, add near the top-level helpers (after `_parse_error`):

```python
def _build_command_payload(name: str, description: str, options: Sequence[CommandOption]) -> dict[str, Any]:
    """Build the JSON body for creating/editing a chat-input application command."""
    return {
        "name": name,
        "description": description,
        "type": 1,
        "options": [option.model_dump(mode="json", exclude_none=True) for option in options],
    }
```

Add imports: `from collections.abc import Sequence` (TYPE_CHECKING block) and eager `from wd_discord.embed import Embed`, `from wd_discord.interactions import CommandOption, RegisteredCommand` (eager - pydantic needs these resolved for the method signatures' runtime annotations to work with `from __future__ import annotations` this is actually fine as strings, so these three can stay `lazy from` instead; use `lazy from` for consistency with the rest of the file). Also `lazy from wd_discord.gateway.events import Interaction` for `create_interaction_response`'s parameter type.

Add the REST methods (after `modify_current_user`):

```python
    async def create_interaction_response(
        self,
        interaction: Interaction,
        *,
        content: str | None = None,
        embeds: list[Embed] | None = None,
    ) -> RequestResult:
        """POST /interactions/{id}/{token}/callback - respond to an interaction (type 4: message with source)."""
        data: dict[str, Any] = {}
        if content is not None:
            data["content"] = content
        if embeds is not None:
            data["embeds"] = [embed.model_dump(mode="json", exclude_none=True) for embed in embeds]
        payload = {"type": 4, "data": data}
        return await self.post(f"/interactions/{interaction.id}/{interaction.token}/callback", json=payload)

    async def create_global_command(
        self,
        name: str,
        description: str,
        options: list[CommandOption] | None = None,
    ) -> RegisteredCommand | NetworkError:
        """POST /applications/{application_id}/commands - register a new global chat-input command."""
        application_id = await self._get_application_id()
        if isinstance(application_id, (ApiResponseError, RequestError)):
            return application_id
        result = await self.post(
            f"/applications/{application_id}/commands",
            json=_build_command_payload(name, description, options or []),
        )
        if isinstance(result, (ApiResponseError, RequestError)):
            return result
        return RegisteredCommand.model_validate(result.json())

    async def edit_global_command(
        self,
        command_id: str,
        name: str,
        description: str,
        options: list[CommandOption] | None = None,
    ) -> RegisteredCommand | NetworkError:
        """PATCH /applications/{application_id}/commands/{command_id} - update an existing global command."""
        application_id = await self._get_application_id()
        if isinstance(application_id, (ApiResponseError, RequestError)):
            return application_id
        result = await self.patch(
            f"/applications/{application_id}/commands/{command_id}",
            json=_build_command_payload(name, description, options or []),
        )
        if isinstance(result, (ApiResponseError, RequestError)):
            return result
        return RegisteredCommand.model_validate(result.json())

    async def delete_global_command(self, command_id: str) -> NetworkError | None:
        """DELETE /applications/{application_id}/commands/{command_id} - remove a global command."""
        application_id = await self._get_application_id()
        if isinstance(application_id, (ApiResponseError, RequestError)):
            return application_id
        result = await self.delete(f"/applications/{application_id}/commands/{command_id}", json={})
        if isinstance(result, (ApiResponseError, RequestError)):
            return result
        return None

    async def get_global_commands(self) -> Generator[RegisteredCommand] | NetworkError:
        """GET /applications/{application_id}/commands - every currently-registered global command."""
        application_id = await self._get_application_id()
        if isinstance(application_id, (ApiResponseError, RequestError)):
            return application_id
        result = await self.get(f"/applications/{application_id}/commands")
        if isinstance(result, (ApiResponseError, RequestError)):
            return result
        return (RegisteredCommand.model_validate(item) for item in result.json())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest wd-discord/tests/test_client_commands.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add wd-discord/src/wd_discord/client.py wd-discord/tests/test_client_commands.py
git commit -m "wd-discord: add interaction-response and global-command REST methods"
```

---

### Task 7: `wd_bot.signature.command_signature`

**Files:**
- Create: `wd-bot/src/wd_bot/signature.py`
- Create: `wd-bot/tests/test_signature.py`
- Modify: `wd-bot/src/wd_bot/auto_sync.py` (remove `AutoSync.get_signature`, now dead — see Task 8, which replaces the rest of this file; this task only removes the one method so nothing calls the old one during Task 8's rewrite)

**Interfaces:**
- Produces: `command_signature(func: Callable[..., object]) -> str`. Consumed by `wd_bot.commands.Command.signature()` (Task 9).

- [ ] **Step 1: Write the failing test**

```python
# wd-bot/tests/test_signature.py
"""Unit tests: command_signature's stable string form of a callable's signature."""
from __future__ import annotations

from wd_bot.signature import command_signature


def sample(a: int, b: str = "x") -> None:
    pass


def test_signature_is_stable_string() -> None:
    assert command_signature(sample) == "(a: int, b: str = 'x') -> None"


def test_signature_changes_when_params_change() -> None:
    def other(a: int, b: str, c: bool) -> None:
        pass

    assert command_signature(sample) != command_signature(other)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest wd-bot/tests/test_signature.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'wd_bot.signature'`).

- [ ] **Step 3: Implement**

```python
# wd-bot/src/wd_bot/signature.py
"""Derive a stable signature string for a command's callable, used to detect definition drift.

TODO: generic enough to belong in ``herogold`` rather than here - tracked upstream at
https://github.com/HEROgold/HeroPy/issues/33. Drop this module in favor of herogold's version
once that lands.
"""
from __future__ import annotations

lazy from inspect import signature
lazy from typing import TYPE_CHECKING


if TYPE_CHECKING:
    lazy from collections.abc import Callable


def command_signature(func: Callable[..., object]) -> str:
    """Return a stable string form of ``func``'s signature, used to detect when it has changed."""
    return str(signature(func))
```

In `wd-bot/src/wd_bot/auto_sync.py`, delete the `get_signature` static method from `AutoSync` (it's superseded by this module; `AutoSync`/`SyncedCommand` themselves are fully replaced in Task 8, so this removal is safe even before that task runs).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest wd-bot/tests/test_signature.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add wd-bot/src/wd_bot/signature.py wd-bot/tests/test_signature.py wd-bot/src/wd_bot/auto_sync.py
git commit -m "wd-bot: add command_signature, drop the now-superseded AutoSync.get_signature"
```

---

### Task 8: Sync schema + diff engine

**Files:**
- Modify: `wd-bot/src/wd_bot/auto_sync.py` (full rewrite of its table/class contents)
- Create: `wd-bot/tests/test_auto_sync.py`

**Interfaces:**
- Consumes: `command_signature` (Task 7), `wd_bot.commands.Command` (Task 9 — for the diff function's input type; see note below on task ordering).
- Produces: `CommandRecord(SQLModel, table=True)` — `id: int | None` (PK), `name: str` (unique). `GlobalSyncedCommand(SQLModel, table=True)` — `id`, `command_id: int` (FK → `commandrecord.id`, unique), `signature: str`, `discord_command_id: str`. `GuildSyncedCommand(SQLModel, table=True)` — same plus `guild_id: int`, unique on `(command_id, guild_id)`. `SyncPlan` (dataclass) — `to_create: list[CommandLike]`, `to_edit: list[tuple[CommandLike, str]]`, `to_delete: list[str]`. `diff_global_commands(session: Session, commands: Sequence[CommandLike]) -> SyncPlan`. `diff_guild_commands(session: Session, guild_id: int, commands: Sequence[CommandLike]) -> SyncPlan` (built as specified, unreachable from any real cog in v1). Both diff functions depend only on a `CommandLike` `Protocol` (`name: str`, `def signature(self) -> str`) rather than importing `wd_bot.commands.Command` directly, avoiding a circular import between `auto_sync.py` and `commands.py` (Task 9's `Command` also needs `command_signature`, not `auto_sync`).

**Note on task ordering:** this task defines `CommandLike` itself (doesn't wait on Task 9) — `Command` (Task 9) satisfies the protocol structurally, no import needed either direction.

- [ ] **Step 1: Write the failing test**

```python
# wd-bot/tests/test_auto_sync.py
"""Unit tests: the diff-based command sync engine (no network, no real Discord calls)."""
from __future__ import annotations

lazy from dataclasses import dataclass

lazy import pytest
lazy from sqlmodel import Session, SQLModel, create_engine

lazy from wd_bot.auto_sync import CommandRecord, GlobalSyncedCommand, diff_global_commands


@dataclass
class FakeCommand:
    name: str
    _signature: str

    def signature(self) -> str:
        return self._signature


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_new_command_is_created(session: Session) -> None:
    plan = diff_global_commands(session, [FakeCommand("percentage", "(user: User) -> None")])
    assert [c.name for c in plan.to_create] == ["percentage"]
    assert plan.to_edit == []
    assert plan.to_delete == []


def test_unchanged_signature_does_nothing(session: Session) -> None:
    record = CommandRecord(name="percentage")
    session.add(record)
    session.commit()
    session.refresh(record)
    session.add(GlobalSyncedCommand(command_id=record.id, signature="(user: User) -> None", discord_command_id="10"))
    session.commit()

    plan = diff_global_commands(session, [FakeCommand("percentage", "(user: User) -> None")])
    assert plan.to_create == []
    assert plan.to_edit == []
    assert plan.to_delete == []


def test_changed_signature_is_edited(session: Session) -> None:
    record = CommandRecord(name="percentage")
    session.add(record)
    session.commit()
    session.refresh(record)
    session.add(GlobalSyncedCommand(command_id=record.id, signature="(user: User) -> None", discord_command_id="10"))
    session.commit()

    plan = diff_global_commands(session, [FakeCommand("percentage", "(user: User, extra: int) -> None")])
    assert plan.to_create == []
    assert [(c.name, discord_id) for c, discord_id in plan.to_edit] == [("percentage", "10")]
    assert plan.to_delete == []


def test_removed_command_is_deleted(session: Session) -> None:
    record = CommandRecord(name="old")
    session.add(record)
    session.commit()
    session.refresh(record)
    session.add(GlobalSyncedCommand(command_id=record.id, signature="() -> None", discord_command_id="20"))
    session.commit()

    plan = diff_global_commands(session, [])
    assert plan.to_create == []
    assert plan.to_edit == []
    assert plan.to_delete == ["20"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest wd-bot/tests/test_auto_sync.py -v`
Expected: FAIL (`ImportError: cannot import name 'diff_global_commands'`).

- [ ] **Step 3: Implement**

Replace the entire contents of `wd-bot/src/wd_bot/auto_sync.py` with:

```python
"""Diff-based sync tracking for Discord application commands.

Tracks which commands are currently registered with Discord (globally, and - built but unused in
v1, see the design doc's "Deferred: guild scoping" - per guild) so the bot only issues create/edit/
delete REST calls for commands whose definition actually changed, never a full re-push.
"""
from __future__ import annotations

lazy from dataclasses import dataclass, field
lazy from typing import TYPE_CHECKING, Protocol

lazy from sqlmodel import Field, Session, UniqueConstraint, select
lazy from wd_db.extension.model import SQLModel


if TYPE_CHECKING:
    lazy from collections.abc import Sequence


class CommandLike(Protocol):
    """Anything with a stable name and a signature - satisfied structurally by wd_bot.commands.Command."""

    name: str

    def signature(self) -> str: ...


class CommandRecord(SQLModel, table=True):
    """The identity of a known command, independent of which scope(s) it's synced to."""

    name: str = Field(unique=True)


class GlobalSyncedCommand(SQLModel, table=True):
    """Tracks one command's global sync state: its last-synced signature and Discord's assigned ID.

    ``discord_command_id`` is ``str``, not ``Snowflake`` - no SQLModel table in this codebase
    stores a ``Snowflake`` column today (it has a pydantic core schema but no SQLAlchemy type
    adapter). TODO: switch to a real ``Snowflake`` column once one exists.
    """

    command_id: int = Field(foreign_key="commandrecord.id", unique=True)
    signature: str
    discord_command_id: str


class GuildSyncedCommand(SQLModel, table=True):
    """Per-guild counterpart to :class:`GlobalSyncedCommand`.

    Built now per the design doc (cheap and symmetrical to write alongside the global table), but
    unreachable in v1 - ``Cog.command()`` has no ``guild_ids`` parameter yet.
    """

    command_id: int = Field(foreign_key="commandrecord.id")
    guild_id: int
    signature: str
    discord_command_id: str

    __table_args__ = (UniqueConstraint("command_id", "guild_id"),)


@dataclass
class SyncPlan:
    """The set of REST calls needed to reconcile registered commands with Discord's actual state."""

    to_create: list[CommandLike] = field(default_factory=list)
    to_edit: list[tuple[CommandLike, str]] = field(default_factory=list)
    to_delete: list[str] = field(default_factory=list)


def _get_or_create_record(session: Session, name: str) -> CommandRecord:
    record = session.exec(select(CommandRecord).where(CommandRecord.name == name)).first()
    if record is None:
        record = CommandRecord(name=name)
        session.add(record)
        session.commit()
        session.refresh(record)
    return record


def diff_global_commands(session: Session, commands: Sequence[CommandLike]) -> SyncPlan:
    """Compare ``commands`` against :class:`GlobalSyncedCommand` rows and plan the minimal sync."""
    plan = SyncPlan()
    records_by_name = {record.name: record for record in session.exec(select(CommandRecord)).all()}
    synced_by_command_id = {row.command_id: row for row in session.exec(select(GlobalSyncedCommand)).all()}

    live_names = set()
    for command in commands:
        live_names.add(command.name)
        record = records_by_name.get(command.name)
        row = synced_by_command_id.get(record.id) if record else None
        if row is None:
            plan.to_create.append(command)
        elif row.signature != command.signature():
            plan.to_edit.append((command, row.discord_command_id))

    for record in records_by_name.values():
        if record.name in live_names:
            continue
        row = synced_by_command_id.get(record.id)
        if row is not None:
            plan.to_delete.append(row.discord_command_id)

    return plan


def diff_guild_commands(session: Session, guild_id: int, commands: Sequence[CommandLike]) -> SyncPlan:
    """Guild-scoped counterpart to :func:`diff_global_commands` (see class docstrings - unused in v1)."""
    plan = SyncPlan()
    records_by_name = {record.name: record for record in session.exec(select(CommandRecord)).all()}
    rows = session.exec(select(GuildSyncedCommand).where(GuildSyncedCommand.guild_id == guild_id)).all()
    synced_by_command_id = {row.command_id: row for row in rows}

    live_names = set()
    for command in commands:
        live_names.add(command.name)
        record = records_by_name.get(command.name)
        row = synced_by_command_id.get(record.id) if record else None
        if row is None:
            plan.to_create.append(command)
        elif row.signature != command.signature():
            plan.to_edit.append((command, row.discord_command_id))

    for record in records_by_name.values():
        if record.name in live_names:
            continue
        row = synced_by_command_id.get(record.id)
        if row is not None:
            plan.to_delete.append(row.discord_command_id)

    return plan
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest wd-bot/tests/test_auto_sync.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add wd-bot/src/wd_bot/auto_sync.py wd-bot/tests/test_auto_sync.py
git commit -m "wd-bot: replace SyncedCommand with CommandRecord + global/guild sync diff engine"
```

---

### Task 9: `wd_bot.commands.Command`

**Files:**
- Create: `wd-bot/src/wd_bot/commands.py`
- Create: `wd-bot/tests/test_commands.py`

**Interfaces:**
- Consumes: `command_signature` (Task 7), `ApplicationCommandOptionType`/`CommandOption` (Task 2), `Interaction`/`InteractionDataOption` (Task 4), `wd_discord.resources.user.User`.
- Produces: `Command` class — `__init__(self, func, *, name: str, description: str)`; attributes `name: str`, `description: str`, `func: Callable`; methods `options(self) -> list[CommandOption]`, `signature(self) -> str`, `async invoke(self, cog: Cog, interaction: Interaction) -> None`; `__get__` descriptor. Consumed by `Cog.command()` (Task 10) and `Bot` (Task 11).

- [ ] **Step 1: Write the failing test**

```python
# wd-bot/tests/test_commands.py
"""Unit tests: Command's option derivation and interaction-option resolution (no network)."""
from __future__ import annotations

lazy from unittest.mock import AsyncMock

lazy import pytest
lazy from wd_discord.gateway.events import Interaction, InteractionData, InteractionDataOption, InteractionType, ResolvedData
lazy from wd_discord.interactions import ApplicationCommandOptionType
lazy from wd_discord.resources.user import User

lazy from wd_bot.commands import Command


def make_user(user_id: str, username: str) -> User:
    return User.model_validate({"id": user_id, "username": username, "discriminator": "0"})


async def percentage(self: object, interaction: Interaction, user: User) -> None:
    pass


def test_options_derived_from_annotations() -> None:
    command = Command(percentage, name="percentage", description="Calculate a percentage")
    options = command.options()
    assert len(options) == 1
    assert options[0].name == "user"
    assert options[0].type is ApplicationCommandOptionType.USER
    assert options[0].required is True


def test_signature_reflects_the_wrapped_function() -> None:
    command = Command(percentage, name="percentage", description="d")
    assert "user" in command.signature()


async def test_invoke_resolves_user_option_from_resolved_data() -> None:
    handler = AsyncMock()
    command = Command(handler, name="percentage", description="d")
    command_impl_options = {"user": User}  # see Step 3 - Command stores this internally; asserted via behavior below

    target = make_user("4", "target")
    interaction = Interaction(
        id="1",
        application_id="2",
        type=InteractionType.APPLICATION_COMMAND,
        token="tok",
        version=1,
        user=make_user("3", "asker"),
        data=InteractionData(
            id="10",
            name="percentage",
            type=1,
            options=[InteractionDataOption(name="user", type=6, value="4")],
            resolved=ResolvedData(users={"4": target}),
        ),
    )

    cog = object()
    await command.invoke(cog, interaction)

    handler.assert_awaited_once_with(cog, interaction, user=target)
```

(Drop the unused `command_impl_options` line above once you see it's not needed - it's a leftover placeholder from drafting; the test asserts behavior through `handler.assert_awaited_once_with`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest wd-bot/tests/test_commands.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'wd_bot.commands'`).

- [ ] **Step 3: Implement**

```python
# wd-bot/src/wd_bot/commands.py
"""wd_bot.commands.Command: encapsulates one application command's definition and dispatch."""
from __future__ import annotations

lazy from inspect import Parameter, signature as inspect_signature
lazy from typing import TYPE_CHECKING, Self

lazy from herogold.log import LoggerMixin
lazy from wd_discord.interactions import ApplicationCommandOptionType, CommandOption
lazy from wd_discord.resources.user import User

lazy from wd_bot.signature import command_signature


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable

    lazy from wd_discord.gateway.events import Interaction

    lazy from wd_bot.cogs import Cog


_OPTION_TYPE_MAP: dict[type, ApplicationCommandOptionType] = {
    str: ApplicationCommandOptionType.STRING,
    int: ApplicationCommandOptionType.INTEGER,
    bool: ApplicationCommandOptionType.BOOLEAN,
    User: ApplicationCommandOptionType.USER,
}


class Command(LoggerMixin):
    """Encapsulates one chat-input application command: its Discord definition and its handler.

    Built by :meth:`wd_bot.cogs.Cog.command`. ``func``'s parameters (after ``self``/``interaction``)
    define the command's options via their type annotations.
    """

    def __init__(self, func: Callable[..., Awaitable[None]], *, name: str, description: str) -> None:
        """Wrap ``func`` as a command named ``name`` with the given ``description``."""
        self.func = func
        self.name = name
        self.description = description
        self._param_types: dict[str, type] = {}
        for param_name, param in inspect_signature(func).parameters.items():
            if param_name in ("self", "interaction"):
                continue
            if param.annotation not in _OPTION_TYPE_MAP:
                msg = f"Command {name!r}: unsupported option type {param.annotation!r} for parameter {param_name!r}"
                raise TypeError(msg)
            self._param_types[param_name] = param.annotation

    def options(self) -> list[CommandOption]:
        """Derive this command's Discord option definitions from its handler's parameters."""
        options: list[CommandOption] = []
        for param_name, param in inspect_signature(self.func).parameters.items():
            if param_name not in self._param_types:
                continue
            required = self._param_types_default_required(param_name)
            options.append(
                CommandOption(
                    type=_OPTION_TYPE_MAP[self._param_types[param_name]],
                    name=param_name,
                    description=param_name,
                    required=required,
                ),
            )
        return options

    def _param_types_default_required(self, param_name: str) -> bool:
        param = inspect_signature(self.func).parameters[param_name]
        return param.default is Parameter.empty

    def signature(self) -> str:
        """This command's current signature, used to detect definition drift for sync."""
        return command_signature(self.func)

    async def invoke(self, cog: Cog, interaction: Interaction) -> None:
        """Resolve ``interaction``'s option values into kwargs and call the wrapped handler."""
        kwargs: dict[str, object] = {}
        data = interaction.data
        options = data.options if data else []
        resolved = data.resolved if data else None
        for option in options:
            param_type = self._param_types.get(option.name)
            if param_type is User:
                user_id = str(option.value)
                kwargs[option.name] = resolved.users.get(user_id) if resolved and resolved.users else None
            else:
                kwargs[option.name] = option.value
        try:
            await self.func(cog, interaction, **kwargs)
        except Exception:
            self.logger.exception(t"Unhandled exception in command {self.name!r}")

    def __get__(self, instance: object, owner: type) -> Self:
        """Allow a Command to be accessed as a plain attribute on a Cog instance without binding it like a method."""
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest wd-bot/tests/test_commands.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add wd-bot/src/wd_bot/commands.py wd-bot/tests/test_commands.py
git commit -m "wd-bot: add Command, encapsulating one application command's definition and dispatch"
```

---

### Task 10: `Cog.command()` decorator

**Files:**
- Modify: `wd-bot/src/wd_bot/cogs.py`
- Modify: `wd-bot/tests/fixtures/example_cog.py` (add one `@Cog.command()`-tagged method, for Task 11's dispatch test to exercise)

**Interfaces:**
- Consumes: `Command` (Task 9).
- Produces: `Cog.command(name: str, description: str) -> Callable[[Callable], Command]` (bare class attribute, not `staticmethod` — matches `Cog.listener`'s existing workaround for the `ty` `@overload`-resolution bug, even though `command()` has no overloads today, for consistency).

- [ ] **Step 1: Write the failing test**

```python
# add to wd-bot/tests/fixtures/example_cog.py
lazy from wd_discord.resources.user import User


class ExampleCog(Cog):
    ...  # keep existing listener methods

    @Cog.command(name="ping-user", description="Ping a user (test fixture)")
    async def ping_user(self, interaction: Interaction, user: User) -> None:
        pass
```

(Adjust to the fixture's actual existing structure - add the import and method without removing anything already there.)

```python
# wd-bot/tests/test_cog_command.py
"""Unit tests: Cog.command() decorator builds a Command."""
from __future__ import annotations

from wd_bot.commands import Command
from wd_bot.tests.fixtures.example_cog import ExampleCog


def test_command_decorator_produces_a_command() -> None:
    assert isinstance(ExampleCog.__dict__["ping_user"], Command)
    assert ExampleCog.__dict__["ping_user"].name == "ping-user"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest wd-bot/tests/test_cog_command.py -v`
Expected: FAIL (`AttributeError: type object 'Cog' has no attribute 'command'`).

- [ ] **Step 3: Implement**

In `wd-bot/src/wd_bot/cogs.py`, add:

```python
lazy from wd_bot.commands import Command


def command(name: str, description: str) -> Callable[[Callable[..., Awaitable[None]]], Command]:
    """Tag a Cog method as a chat-input application command, building a :class:`Command` for it."""

    def decorator(func: Callable[..., Awaitable[None]]) -> Command:
        return Command(func, name=name, description=description)

    return decorator
```

and on `Cog`, alongside `listener = listener`:

```python
    command = command
```

(Bare attribute, not `staticmethod` - see the existing comment above `listener = listener` for why: `ty` loses `@overload` resolution through `staticmethod`, and `Cog.command(...)` is always accessed via the class, never an instance, so the wrapper buys nothing.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest wd-bot/tests/test_cog_command.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add wd-bot/src/wd_bot/cogs.py wd-bot/tests/fixtures/example_cog.py wd-bot/tests/test_cog_command.py
git commit -m "wd-bot: add Cog.command() decorator"
```

---

### Task 11: `Bot` command registry + `INTERACTION_CREATE` dispatch + startup sync

**Files:**
- Modify: `wd-bot/src/wd_bot/bot.py`
- Create: `wd-bot/tests/test_bot_commands.py`

**Interfaces:**
- Consumes: `Command` (Task 9), `diff_global_commands`/`CommandRecord`/`GlobalSyncedCommand` (Task 8), `Client.create_global_command`/`edit_global_command`/`delete_global_command` (Task 6), `EventName.INTERACTION_CREATE` (Task 4).
- Produces: `Bot._commands: dict[str, tuple[Cog, Command]]`. `Bot.add_cog` extended to also register `Command`-typed class attributes. `Bot._dispatch_interaction(self, interaction: Interaction) -> None` — looked up via the `_listeners` mechanism like any other event, registered once in `Bot.__init__`. `Bot.sync_commands(self, client: Client) -> None` — runs the diff-and-push at startup.

- [ ] **Step 1: Write the failing test**

```python
# wd-bot/tests/test_bot_commands.py
"""Unit tests: Bot's command registry and INTERACTION_CREATE dispatch (no real Discord calls)."""
from __future__ import annotations

lazy from unittest.mock import AsyncMock

lazy import pytest
lazy from wd_discord.gateway.events import Interaction, InteractionData, InteractionType
lazy from wd_discord.resources.user import User

lazy from wd_bot.bot import Bot
lazy from wd_bot.commands import Command


class _FakeCog:
    __cog_name__ = "FakeCog"

    def __init__(self) -> None:
        self.bot = None

    async def handle(self, interaction: Interaction) -> None:
        pass


async def test_add_cog_registers_commands() -> None:
    bot = Bot()
    bot.loop = __import__("asyncio").get_event_loop()
    cog = _FakeCog()
    cog.bot = bot
    command = Command(_FakeCog.handle, name="ping", description="d")
    type(cog).ping = command  # simulate a @Cog.command()-decorated method
    await bot.add_cog(cog)  # type: ignore[arg-type] - _FakeCog duck-types Cog for this test
    assert "ping" in bot._commands  # noqa: SLF001 - testing internal registry directly


async def test_dispatch_interaction_invokes_matching_command(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = Bot()
    bot.loop = __import__("asyncio").get_event_loop()
    cog = _FakeCog()
    cog.bot = bot
    handler = AsyncMock()

    async def fake_handle(self: object, interaction: Interaction) -> None:
        await handler(interaction)

    command = Command(fake_handle, name="ping", description="d")
    type(cog).ping = command
    await bot.add_cog(cog)  # type: ignore[arg-type]

    interaction = Interaction(
        id="1", application_id="2", type=InteractionType.APPLICATION_COMMAND, token="tok", version=1,
        user=User.model_validate({"id": "3", "username": "asker", "discriminator": "0"}),
        data=InteractionData(id="10", name="ping", type=1),
    )
    await bot._dispatch_interaction(interaction)  # noqa: SLF001

    handler.assert_awaited_once_with(interaction)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest wd-bot/tests/test_bot_commands.py -v`
Expected: FAIL (`AttributeError: 'Bot' object has no attribute '_commands'`).

- [ ] **Step 3: Implement**

In `wd-bot/src/wd_bot/bot.py`:

Add to imports: `lazy from wd_bot.auto_sync import diff_global_commands, CommandRecord, GlobalSyncedCommand` (module-level, non-`TYPE_CHECKING` since used at runtime in `sync_commands`), `lazy from wd_bot.commands import Command`, `lazy from wd_discord.gateway import EventName` (for registering the interaction listener), and under `TYPE_CHECKING`: `lazy from wd_discord.gateway.events import Interaction`.

In `Bot.__init__`, add `self._commands: dict[str, tuple[Cog, Command]] = {}` and register the built-in interaction listener:

```python
        self._listeners.setdefault(EventName.INTERACTION_CREATE.value, []).append(self._dispatch_interaction)
```

Extend `add_cog` (after the existing listener-registration loop, before `await cog.load()`):

```python
        for attr_name in dir(type(cog)):
            attr = type(cog).__dict__.get(attr_name)
            if isinstance(attr, Command):
                self._commands[attr.name] = (cog, attr)
```

Add the dispatch method:

```python
    async def _dispatch_interaction(self, interaction: Interaction) -> None:
        """Route an APPLICATION_COMMAND interaction to its registered Command, if any."""
        if interaction.type is not InteractionType.APPLICATION_COMMAND or interaction.data is None:
            return
        entry = self._commands.get(interaction.data.name)
        if entry is None:
            self.logger.warning(t"No registered command for interaction {interaction.data.name!r}")
            return
        cog, command = entry
        await command.invoke(cog, interaction)
```

(Add `lazy from wd_discord.gateway.events import InteractionType` alongside the `Interaction` import - both are used only under `TYPE_CHECKING` except `InteractionType`, which is compared at runtime, so import it eagerly outside `TYPE_CHECKING`.)

Add the sync method (called from `start()`, right after `load_extensions()`):

```python
    async def sync_commands(self, client: Client) -> None:
        """Diff registered commands against Discord's actual global commands and reconcile."""
        lazy from sqlmodel import Session
        lazy from wd_db.constants import engine

        commands = [command for _, command in self._commands.values()]
        with Session(engine) as session:
            plan = diff_global_commands(session, commands)
            for command in plan.to_create:
                result = await client.create_global_command(command.name, command.description, command.options())
                if isinstance(result, (ApiResponseError, RequestError)):
                    self.logger.warning(t"Failed to create command {command.name!r}: {result}")
                    continue
                record = session.exec(select(CommandRecord).where(CommandRecord.name == command.name)).first()
                if record is None:
                    record = CommandRecord(name=command.name)
                    session.add(record)
                    session.commit()
                    session.refresh(record)
                session.add(
                    GlobalSyncedCommand(
                        command_id=record.id,
                        signature=command.signature(),
                        discord_command_id=str(result.id),
                    ),
                )
                session.commit()
            for command, discord_command_id in plan.to_edit:
                result = await client.edit_global_command(
                    discord_command_id, command.name, command.description, command.options(),
                )
                if isinstance(result, (ApiResponseError, RequestError)):
                    self.logger.warning(t"Failed to edit command {command.name!r}: {result}")
                    continue
                record = session.exec(select(CommandRecord).where(CommandRecord.name == command.name)).first()
                row = session.exec(
                    select(GlobalSyncedCommand).where(GlobalSyncedCommand.command_id == record.id),
                ).first()
                row.signature = command.signature()
                session.add(row)
                session.commit()
            for discord_command_id in plan.to_delete:
                result = await client.delete_global_command(discord_command_id)
                if isinstance(result, (ApiResponseError, RequestError)):
                    self.logger.warning(t"Failed to delete command {discord_command_id!r}: {result}")
                    continue
                row = session.exec(
                    select(GlobalSyncedCommand).where(GlobalSyncedCommand.discord_command_id == discord_command_id),
                ).first()
                if row is not None:
                    session.delete(row)
                    session.commit()
```

Add `lazy from sqlmodel import select`, `lazy from wd_discord.errors.api import ApiResponseError`, `lazy from httpxyz import RequestError` to the module's top-level imports (needed outside the method body too, for the `isinstance` checks - move those two up from the inline `lazy` position, keep only `Session`/`engine` inline since they're only used in this one method and importing `wd_db.constants.engine` eagerly at module load forces a real DB connection per the existing `Cog.__init__` precedent).

Call `sync_commands` from `start()`, right after `await self.load_extensions()`:

```python
            await self.load_extensions()
            await self.sync_commands(client)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest wd-bot/tests/test_bot_commands.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add wd-bot/src/wd_bot/bot.py wd-bot/tests/test_bot_commands.py
git commit -m "wd-bot: wire Bot's command registry, INTERACTION_CREATE dispatch, and startup sync"
```

---

### Task 12: `winter_dragon/cogs/percentage.py`

**Files:**
- Create: `src/winter_dragon/cogs/percentage.py`
- Create: `wd-bot/tests/test_percentage_cog.py` (or `winter_dragon`'s own test location if one exists - check `src/winter_dragon/` for a `tests/` sibling first; if none exists yet, create `tests/winter_dragon/test_percentage_cog.py` at the repo root, matching wherever `run_test_bot.py`'s own tests (if any) live - if genuinely nothing precedents this, put it at `wd-bot/tests/test_percentage_cog.py` since the cog only depends on wd-bot/wd-discord types, not on anything winter_dragon-specific)

**Interfaces:**
- Consumes: `Cog`/`Cog.command` (Task 10), `Interaction` (Task 4), `Embed` (Task 3), `User`.

- [ ] **Step 1: Write the failing test**

```python
# wd-bot/tests/test_percentage_cog.py
"""Unit tests: the percentage command's compatibility calculation is deterministic per user pair."""
from __future__ import annotations

lazy import random

lazy from winter_dragon.cogs.percentage import calculate_percentage


def test_percentage_is_deterministic_for_the_same_pair() -> None:
    assert calculate_percentage(1, 2) == calculate_percentage(1, 2)


def test_percentage_is_order_independent() -> None:
    assert calculate_percentage(1, 2) == calculate_percentage(2, 1)


def test_percentage_is_within_bounds() -> None:
    value = calculate_percentage(123, 456)
    assert 0 <= value <= 100


def test_percentage_matches_manual_seed() -> None:
    expected = random.Random(1 + 2).randint(0, 100)
    assert calculate_percentage(1, 2) == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest wd-bot/tests/test_percentage_cog.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'winter_dragon.cogs.percentage'`).

- [ ] **Step 3: Implement**

```python
# src/winter_dragon/cogs/percentage.py
"""A cog with a single command: a random compatibility percentage between two users."""
from __future__ import annotations

lazy import random
lazy from typing import TYPE_CHECKING

lazy from wd_bot.cogs import Cog
lazy from wd_discord.embed import Embed


if TYPE_CHECKING:
    lazy from wd_discord.gateway.events import Interaction
    lazy from wd_discord.resources.user import User


def calculate_percentage(user_id_a: int, user_id_b: int) -> int:
    """Compute a random 0-100 percentage, seeded by both user IDs (order-independent)."""
    rng = random.Random(user_id_a + user_id_b)
    return rng.randint(0, 100)


class Percentage(Cog):
    """Cog for the /percentage command."""

    @Cog.command(name="percentage", description="Calculate a random compatibility percentage with another user")
    async def percentage(self, interaction: Interaction, user: User) -> None:
        """Reply with a random compatibility percentage between the invoking user and ``user``."""
        asker = interaction.invoking_user
        percent = calculate_percentage(int(asker.id._snowflake), int(user.id._snowflake)) if asker else 0
        embed = Embed(
            title="Compatibility",
            description=f"You and {user.username} are {percent}% compatible!",
            color=0xFF69B4,
        )
        await self.bot.client.create_interaction_response(interaction, embeds=[embed])
```

Note on `user.id._snowflake`: `Snowflake` has no public `int()`/`__int__` conversion today (confirmed while researching the design - only a pydantic JSON serializer to decimal string). Accessing the private `_snowflake` attribute from outside `Snowflake` violates its own encapsulation; prefer `int(str(user.id.model_dump(mode="json")))` - but `Snowflake` itself isn't a pydantic model, so it has no `.model_dump()`. The clean fix is a public `Snowflake.__int__` method - add it as part of this task since it's a one-line, clearly-justified addition (not scope creep: this exact conversion need is what surfaced the gap):

```python
# wd-discord/src/wd_discord/snowflake.py - add to the Snowflake dataclass
    def __int__(self) -> int:
        """Return the raw snowflake integer."""
        return self._snowflake
```

Then use `int(asker.id)` / `int(user.id)` in `percentage.py` instead of reaching into `_snowflake` directly. Add a test to `wd-discord/tests/test_snowflake.py` if that file exists (check first: `Glob wd-discord/tests/test_snowflake*.py`) — if it doesn't, add one:

```python
def test_snowflake_converts_to_int() -> None:
    assert int(Snowflake(123)) == 123
```

Update `percentage.py`'s command body to:

```python
        asker = interaction.invoking_user
        percent = calculate_percentage(int(asker.id), int(user.id)) if asker else 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest wd-bot/tests/test_percentage_cog.py wd-discord/tests/test_snowflake.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/winter_dragon/cogs/percentage.py wd-bot/tests/test_percentage_cog.py wd-discord/src/wd_discord/snowflake.py wd-discord/tests/test_snowflake.py
git commit -m "winter_dragon: add /percentage command; add Snowflake.__int__"
```

---

### Task 13: Admin `/bot-commands` management command

**Files:**
- Create: `src/winter_dragon/cogs/bot_commands.py`
- Create: `wd-bot/tests/test_bot_commands_admin_cog.py`

**Interfaces:**
- Consumes: `GroupCog`, `Cog.command` (Task 10), `CommandRecord`/`GlobalSyncedCommand` (Task 8), `Permissions` (for `default_member_permissions` - note: Discord's `default_member_permissions` is set on the *registered command*, not enforced client-side; see implementation note below).

- [ ] **Step 1: Write the failing test**

```python
# wd-bot/tests/test_bot_commands_admin_cog.py
"""Unit tests: the admin bot-commands cog's pure status-formatting logic (no network)."""
from __future__ import annotations

lazy from sqlmodel import Session, SQLModel, create_engine

lazy from wd_bot.auto_sync import CommandRecord, GlobalSyncedCommand
lazy from winter_dragon.cogs.bot_commands import describe_sync_status


def test_describe_sync_status_reports_synced_and_pending() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        record = CommandRecord(name="percentage")
        session.add(record)
        session.commit()
        session.refresh(record)
        session.add(GlobalSyncedCommand(command_id=record.id, signature="sig", discord_command_id="1"))
        session.commit()

        lines = describe_sync_status(session, [("percentage", "sig"), ("other", "sig2")])

    assert "percentage: synced" in lines
    assert "other: pending" in lines
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest wd-bot/tests/test_bot_commands_admin_cog.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'winter_dragon.cogs.bot_commands'`).

- [ ] **Step 3: Implement**

```python
# src/winter_dragon/cogs/bot_commands.py
"""Admin command group for inspecting and forcing the application-command sync state."""
from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from sqlmodel import select
lazy from wd_bot.auto_sync import CommandRecord, GlobalSyncedCommand, diff_global_commands
lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_discord.embed import Embed
lazy from wd_discord.permissions import Permissions


if TYPE_CHECKING:
    lazy from collections.abc import Sequence

    lazy from sqlmodel import Session
    lazy from wd_discord.gateway.events import Interaction


def describe_sync_status(session: Session, commands: Sequence[tuple[str, str]]) -> list[str]:
    """Return one "name: synced|pending" line per (name, signature) pair in ``commands``."""
    records_by_name = {record.name: record for record in session.exec(select(CommandRecord)).all()}
    synced_by_command_id = {row.command_id: row for row in session.exec(select(GlobalSyncedCommand)).all()}

    lines = []
    for name, current_signature in commands:
        record = records_by_name.get(name)
        row = synced_by_command_id.get(record.id) if record else None
        state = "synced" if row is not None and row.signature == current_signature else "pending"
        lines.append(f"{name}: {state}")
    return lines


class BotCommands(GroupCog):
    """Admin commands for inspecting/forcing application-command sync."""

    @Cog.command(name="bot-commands-list", description="List registered commands and their sync status")
    async def list_commands(self, interaction: Interaction) -> None:
        """Show every registered command's synced/pending state."""
        with self.session as session:
            commands = [(command.name, command.signature()) for _, command in self.bot._commands.values()]
            lines = describe_sync_status(session, commands)
        embed = Embed(title="Registered commands", description="\n".join(lines) or "No commands registered.")
        await self.bot.client.create_interaction_response(interaction, embeds=[embed])

    @Cog.command(name="bot-commands-resync", description="Force an immediate command sync with Discord")
    async def resync(self, interaction: Interaction) -> None:
        """Force the diff-and-push sync immediately."""
        await self.bot.sync_commands(self.bot.client)
        await self.bot.client.create_interaction_response(interaction, content="Resync complete.")
```

Implementation note on `default_member_permissions`: Discord's API accepts this on command *creation*, not as a client-side gate - it's a bitfield the sync engine would need to pass through `create_global_command`/`edit_global_command`. Extend `Command` (Task 9) to accept an optional `default_member_permissions: Permissions | None = None` constructor kwarg, thread it through `_build_command_payload`/`create_global_command`/`edit_global_command` (Task 6) as an additional `default_member_permissions: Permissions | None = None` parameter, and set it on this cog's two commands: `@Cog.command(..., default_member_permissions=Permissions.MANAGE_GUILD)`. Given this touches Tasks 6 and 9's signatures, apply this as a small amendment to those tasks' code when you reach this task (add the parameter with a `None` default so Tasks 6/9's original tests still pass unmodified), rather than re-deriving the whole method bodies here.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest wd-bot/tests/test_bot_commands_admin_cog.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/winter_dragon/cogs/bot_commands.py wd-bot/tests/test_bot_commands_admin_cog.py wd-bot/src/wd_bot/commands.py wd-discord/src/wd_discord/client.py
git commit -m "winter_dragon: add admin /bot-commands list+resync; thread default_member_permissions through Command/Client"
```

---

### Task 14: Full-suite verification + manual smoke test

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `uv run pytest wd-discord/tests wd-bot/tests -v`
Expected: all new tests pass; the 5 pre-existing/unrelated failures noted in `.claude/tracking/PHASE1_PROGRESS.md` (`test_shard_for_guild_routes_after_start` + 4 `test_utils.py` XOR/descriptor tests) may still appear - confirm no *new* failures beyond that known baseline.

- [ ] **Step 2: Lint and type-check**

Run: `uv run ruff check .` and `uv run ruff format --check .` and `uv run pyright`
Expected: clean on every file touched by this plan.

- [ ] **Step 3: Manual smoke test (needs a real bot token in config.ini)**

Use the `run-wd-discord` skill to start the bot against a real test guild, confirm in Discord that `/percentage` and `/bot-commands-list`/`/bot-commands-resync` appear (global commands can take up to ~1 hour to propagate on first registration - if they don't show up immediately, that's expected, not a bug), invoke `/percentage @someone`, and confirm a response with a 0-100% embed appears. Re-run the bot a second time and confirm the logs show **no** create/edit calls for those commands the second time (only the diff engine's "no changes" path) - this is the actual proof that unnecessary-work avoidance works.

- [ ] **Step 4: Update tracking**

Create `.claude/tracking/PHASE2_PLAN.md` (a short pointer file, mirroring `PHASE1_PLAN.md`'s convention) with a one-paragraph summary and a link to `docs/superpowers/specs/2026-09-14-app-commands-design.md` and this plan file, and `.claude/tracking/PHASE2_PROGRESS.md` with a checklist mirroring Tasks 1-13 above (mark each `[x]` as it's completed during execution, per `PHASE1_PROGRESS.md`'s "update right before each commit" convention). Note in `PHASE2_PROGRESS.md`'s final section that guild-scoped commands remain deferred (link to the `app-commands-guild-scoping-todo` memory).

---

## Self-Review Notes

- **Spec coverage**: every architecture section in the design doc maps to a task (data model → 1-4, REST → 5-6, signature extraction → 7, sync schema → 8, `Command` → 9, `Cog.command()` → 10, `Bot` wiring → 11, concrete command → 12, admin command → 13, verification → 14). The one deliberate simplification from the spec's wording: `Command.to_application_command()` (spec) became `Command.options()` + `Client._build_command_payload()` (plan) — the spec's `ApplicationCommand` dataclass family has required server-assigned fields (`id`/`application_id`/`version`) that don't exist before registration, so a *request* payload needed a different shape than the *response* model (`RegisteredCommand`) anyway; this is documented inline in Task 2.
- **Type consistency checked**: `Command.invoke(cog, interaction)` (Task 9) matches `command.invoke(cog, interaction)`'s call site in `Bot._dispatch_interaction` (Task 11). `Command.options()` (Task 9, method) matches its call sites in `Bot.sync_commands` (Task 11) and `BotCommands` (Task 13). `CommandLike` (Task 8) matches `Command`'s actual `name`/`signature()` shape (Task 9) structurally. `GlobalSyncedCommand.discord_command_id: str` (Task 8) matches `RegisteredCommand.id` being converted via `str(result.id)` at the one call site that stores it (Task 11).
- **Known deferred item carried through**: guild scoping is explicitly out of scope in Tasks 8/10/11 (built-but-unreachable `GuildSyncedCommand`/`diff_guild_commands`, no `guild_ids` param) — matches the design doc and the `app-commands-guild-scoping-todo` memory.
