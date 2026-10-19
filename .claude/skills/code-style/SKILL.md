---
name: code-style
description: WinterDragonV2 code style and typing rules. Use when writing, editing, refactoring, or reviewing any Python code in this repo — formatting, imports, docstrings, type annotations, fixing pyrefly/ty/ruff errors, or deciding how to handle Any/cast/noqa.
---

# Code style & typing

Python **3.15**, ruff `select = ["ALL"]` (ignores only `D105`, `TD005`, `CPY001`, `T20` — see [ruff.toml](../../../ruff.toml)), **pyrefly strict** with a baseline (pre-commit), and astral `ty` (pre-push). Write code that passes without suppressions; suppress only with a specific code.

## Module skeleton

```python
"""One-line module docstring."""
from __future__ import annotations

lazy import asyncio
lazy from typing import TYPE_CHECKING

lazy from wd_config import Config


if TYPE_CHECKING:
    lazy from collections.abc import Callable
```

- **PEP 810 `lazy` imports** at module level, as every module in the tree does. A plain (eager) import only where the tooling needs the name at class-definition time — e.g. pydantic/SQLModel field types (see the `runtime-evaluated-base-classes` note in ruff.toml).
- Line length **128**, 4-space indent, **double quotes**, magic trailing commas kept, **two blank lines after imports**.
- Annotation-only imports go under `if TYPE_CHECKING:`.
- Docstrings: PEP-257 imperative ("Send a GET request."), on every public class/function. Sphinx roles welcome. The first paragraph is what [docs/reference/](../../../docs/reference/index.md) shows, so make it say what the thing does.
- Logging: herogold loggers render **t-strings** — `self.logger.warning(t"Unresolved user '{name}'")`, not `%`-style.

## Typing rules

| Use | Never |
|---|---|
| `X \| None` | `Optional[X]`, `Union[X, Y]` |
| PEP 695 `type Alias = ...` | `Alias: TypeAlias = ...` |
| PEP 695 `class Store[T]:` / `def f[**P, T](...)` | module-level `TypeVar(...)` / `ParamSpec(...)` |
| `Self` for `__aenter__`, alt constructors | returning the class name |
| `@override` on every overriding method | silent overrides |
| `TypeIs[T]` for narrowing predicates (`is_network_error`) | `bool` returns the caller must `cast` after |

Examples: [wd_types/alias.py](../../../wd-types/src/wd_types/alias.py) (bounded generics, ParamSpec, defaulted type params); `returns_known_exception[**P, T, E: Exception]` in [wd_discord/client.py](../../../wd-discord/src/wd_discord/client.py).

Kwargs are a `TypedDict` + `Unpack`, not `**kwargs: Any` — `BotArgs` in [wd_bot/cogs.py](../../../wd-bot/src/wd_bot/cogs.py) (`Required`/`NotRequired` per key).

Plain-data classes whose `__init__` only copies parameters are `@dataclass`es (keyword-only after `_: KW_ONLY`) — e.g. `SteamSaleNotifier`, `ClientBound`.

### Prefer generators for collection-returning helpers

A helper/property deriving a sequence **yields** and is annotated `Generator[T]`; callers wrap with `list(...)` when they need one. Example: `Channel.applied_forum_tags` in [resources/channel/channel.py](../../../wd-discord/src/wd_discord/resources/channel/channel.py):

```python
@property
def applied_forum_tags(self) -> Generator[ForumTag]:
    if not self.applied_tags or not self.available_tags:
        return
    yield from (tag for tid in self.applied_tags for tag in self.available_tags if tag.id == tid)
```

(`Snowflake` is a non-frozen `@dataclass`, so unhashable — resolve id→object by `==` scan, not a `dict`/`set`.)

## Errors as values, not exceptions

Fallible functions return the error; the return type is a union the caller narrows:

```python
type NetworkError = ApiResponseError | RequestError

me = await client.users.me()          # User | NetworkError
if is_network_error(me):
    ...handle...
```

`returns_known_exception` (async, [client.py](../../../wd-discord/src/wd_discord/client.py)) and herogold's `with_known_exception` (sync) turn a known exception into a return value. No bare `raise` paths for expected failures in wd-discord/wd-errors/wd-bot.

## Escape hatches — the discipline

- **No blanket suppressions** (pygrep hook). Coded forms only: `# noqa: ANN401`, `# pyrefly: ignore[not-async]`, `# ty: ignore[missing-argument]`.
- `Any` only where unavoidable, with `# noqa: ANN401` at that site.
- `cast("Guild", channel)` (string-literal target), only for third-party/dynamic objects. Prefer a `Protocol` (advanced-patterns).
- Suppressing a behavior rule needs a reason on the same line — `# noqa: BLE001 - non-JSON or unexpected shape` in `Client.request`.

## Naming

- `snake_case` modules/functions, `PascalCase` classes, `UPPER_SNAKE` constants.
- Import renames that break casing get a coded noqa: `lazy from x import URL as UserAgentURL  # noqa: N811`.
- Packages: dir `wd-<name>`, import `wd_<name>`, src layout.

## Verify before committing

```powershell
uv run ruff check <files> --fix --unsafe-fixes; uv run ruff format <files>
uvx pyrefly check <files>
uv run pytest -q
```

The source tree, not `docs/dev/`, is the style reference.
