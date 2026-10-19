---
name: dependencies
description: How to add, remove, or upgrade Python packages in the WinterDragonV2 uv workspace. Use whenever you need to change dependencies of any wd-* member — always via `uv add`/`uv remove`, never by hand-editing pyproject.toml or uv.lock.
---

# Dependencies — always through uv

This repo is a **uv workspace** (multiple `wd-*` members under one root `uv.lock`). Changing a
dependency is a resolver operation, not a text edit: `uv` updates the member's `pyproject.toml`
**and** re-resolves the shared lockfile atomically, and prints exactly what changed.

**Never hand-edit `pyproject.toml` `dependencies` or `uv.lock`.** A manual edit leaves the lock
stale (or wrong), and the next `uv sync`/`uv run` either ignores your change or fights it.

## Commands

```bash
# add to a specific workspace member (preferred — this is a monorepo)
uv add --package wd-discord "sentry-sdk>=2.61.0"

# remove from a member
uv remove --package wd-discord sentry-sdk

# dev-only dependency
uv add --package wd-discord --dev pytest-asyncio

# an internal workspace member as a dependency of another member
uv add --package wd-cogs wd-core        # then it appears under [tool.uv.sources] as { workspace = true }

# upgrade
uv lock --upgrade-package sentry-sdk
```

Run from the repo root; `--package <member>` targets the right `pyproject.toml`. Match an existing
pin when one package already depends on the library (e.g. `sentry-sdk` is pinned by `wd-core`).

## After changing deps

- `uv` writes both files — review the `pyproject.toml` diff and the `uv.lock` delta it reports.
- Declare internal cross-package deps you actually import (architecture skill: "declare every
  internal dep as `{ workspace = true }`"); `uv add --package X wd-Y` does this for you.
- `uv run pytest ...` / `uv run ruff check .` to confirm nothing broke.

Related: [run-tests](../run-tests/SKILL.md), [run-stack](../run-stack/SKILL.md) both drive `uv run`.
The `uv` binary is already on PATH (see the `uv-via-venv` project memory).
