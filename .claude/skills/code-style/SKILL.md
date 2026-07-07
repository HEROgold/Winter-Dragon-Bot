---
name: code-style
description: WinterDragonV2 code style and typing rules. Use when writing, editing, refactoring, or reviewing any Python code in this repo — formatting, imports, docstrings, type annotations, fixing pyright/ty/ruff errors, or deciding how to handle Any/cast/noqa.
---

# Code style & typing

Python **3.15**, ruff with `select = ["ALL"]` (only `D105`, `TD005` ignored), pyright **strict**, and astral `ty` all run in pre-commit. Assume every rule is on; write code that passes without suppressions, and suppress only with a specific code.

## Module skeleton

Every module, no exceptions (isort enforces the import; D-rules enforce the docstring):

```python
"""One-line module docstring."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from wd_config import Config


if TYPE_CHECKING:
    from collections.abc import Callable
```

- Line length **128**, 4-space indent, **double quotes**, magic trailing commas kept.
- **Two blank lines after the import block** (`lines-after-imports = 2` in [ruff.toml](../../../ruff.toml)).
- Imports only used for annotations go in `if TYPE_CHECKING:` — see [client.py](../../../wd-discord/src/wd_discord/client.py) for the idiom.
- Docstrings: PEP-257 imperative ("Send a GET request."), on all public classes/functions. Sphinx roles (`:class:`, `:mod:`) welcome in module docstrings.

## Typing rules

Use the modern forms only:

| Use | Never |
|---|---|
| `X \| None` | `Optional[X]`, `Union[X, Y]` |
| PEP 695 `type Alias = ...` | `Alias: TypeAlias = ...` |
| PEP 695 `class Store[T]:` / `def f[**P, T](...)` | module-level `TypeVar(...)` / `ParamSpec(...)` |
| `Self` for `__aenter__`, alt constructors | returning the class name |
| `@override` on every overriding method | silent overrides |

Reference examples: [wd-types/src/wd_types/alias.py](../../../wd-types/src/wd_types/alias.py) (bounded generics, ParamSpec, defaulted type params), [client.py:56](../../../wd-discord/src/wd_discord/client.py#L56) (`def returns_known_exception[**P, T, E: Exception]`).

Kwargs are typed with a `TypedDict` + `Unpack`, not `**kwargs: Any` — see `BotArgs` in [wd-bot/src/wd_bot/cogs.py:29](../../../wd-bot/src/wd_bot/cogs.py#L29) (`Required`/`NotRequired` per key).

## Errors as values, not exceptions

Functions that can fail return the error instead of raising; the return type is a union the caller must narrow:

```python
type RequestResult = Response | ApiResponseError | RequestError

result = await client.get(url)
if isinstance(result, ApiResponseError):
    ...handle...
```

The `returns_known_exception` decorator ([client.py:56](../../../wd-discord/src/wd_discord/client.py#L56)) converts a known exception into a return value; herogold's `with_known_exception` is the sync analog. Follow this contract when extending `wd-discord` or `wd-errors`; don't add bare `raise` paths for expected failures.

## Escape hatches — the discipline

- **No blanket suppressions.** Bare `# noqa` and bare `# type: ignore` are forbidden (pre-commit pygrep hook). Always use the coded form: `# noqa: ANN401`, `# noqa: N811`.
- `Any` only where genuinely unavoidable, always paired with `# noqa: ANN401` at that site.
- `cast` uses the string-literal target form — `cast("Guild", channel)` — and is reserved for third-party/dynamic objects (see [wd-cogs/src/wd_cogs/utility/team.py](../../../wd-cogs/src/wd_cogs/utility/team.py)). Prefer a `Protocol` over a `cast` when you control the call site (see the advanced-patterns skill).
- A justifying comment accompanies suppressions of behavior rules (e.g. `BLE001` blind-except in [client.py:82](../../../wd-discord/src/wd_discord/client.py#L82)).

## Naming

- Modules/functions `snake_case`, classes `PascalCase`, module constants `UPPER_SNAKE`.
- Renaming imports to satisfy casing rules gets a coded noqa: `from x import URL as UserAgentURL  # noqa: N811`.
- Packages: dir `wd-<name>`, import package `wd_<name>`, src-layout under `src/`.

## Verify before committing

```powershell
uv run ruff check .; uv run ruff format --check .; uv run pyright
```

`docs/dev/setup.md` code samples are stale (they use `Optional`) — the source tree, not the docs, is the style reference.
