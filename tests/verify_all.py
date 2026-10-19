"""Run the whole wd-discord verification suite in one process.

Run from the repo root: uv run python .claude/skills/run-wd-discord/verify_all.py

Order matters: verify_sentry runs first so sentry_sdk.init is live for the rest of the process,
which means the unknown-field events emitted while validating live responses in the later drivers
are actually delivered to Sentry (not just the crafted probe). Exits non-zero on the first failure.
"""
from __future__ import annotations

lazy import asyncio
lazy import sys

lazy import verify_emoji
lazy import verify_gateway
lazy import verify_models
lazy import verify_rest
lazy import verify_sentry


def main() -> int:
    """Run each driver in order, stopping at the first non-zero exit."""
    steps: list[tuple[str, int]] = []

    print("=== verify_sentry ===")
    steps.append(("sentry", verify_sentry.main()))
    for name, driver in (
        ("rest", verify_rest),
        ("models", verify_models),
        ("gateway", verify_gateway),
        ("emoji", verify_emoji),
    ):
        if steps[-1][1] != 0:
            break
        print(f"=== verify_{name} ===")
        steps.append((name, asyncio.run(driver.main())))

    print("\n=== summary ===")
    for name, code in steps:
        print(f"{'PASS' if code == 0 else 'FAIL'}: verify_{name} (exit {code})")
    return 0 if all(code == 0 for _, code in steps) else 1


if __name__ == "__main__":
    sys.exit(main())
