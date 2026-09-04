"""Verify the Sentry telemetry pipeline end-to-end.

Run from the repo root: uv run python .claude/skills/run-wd-discord/verify_sentry.py

1. Construct wd_discord.Sentry() -> sentry_sdk.init with the configured DSN/environment.
2. Fire a probe capture_message (proves delivery independent of model parsing).
3. Validate a User payload carrying an unknown key -> drives DiscordModel._report_unknown_fields
   -> capture_message(level="warning"). This is the real telemetry path.

Run this FIRST in a full pass so sentry_sdk.init is live for the other drivers in the same process.
"""
from __future__ import annotations

lazy import sys

lazy import sentry_sdk
lazy from wd_config.sentry import SentrySettings
lazy from wd_discord import Sentry
lazy from wd_discord.user import User


def main() -> int:
    """Init Sentry and emit a probe + an unknown-field event."""
    Sentry()
    print(f"SENTRY OK: init environment={SentrySettings.environment.value} telemetry={SentrySettings.Telemetry}")

    probe_id = sentry_sdk.capture_message("wd-discord verify_sentry: probe", level="info")
    print(f"SENTRY OK: probe capture_message event_id={probe_id}")

    # Unknown-field telemetry path: __wd_probe__ is not a User field, so it lands in model_extra.
    user = User.model_validate(
        {"id": "1226868250713784331", "username": "probe", "discriminator": "0", "__wd_probe__": "x"},
    )
    if "__wd_probe__" not in (user.model_extra or {}):
        print("FAIL: unknown field was not captured in model_extra")
        return 1
    print("SENTRY OK: unknown-field warning emitted for User (see Sentry + logs/_global.log)")

    sentry_sdk.flush(timeout=5)
    print("SENTRY OK: flushed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
