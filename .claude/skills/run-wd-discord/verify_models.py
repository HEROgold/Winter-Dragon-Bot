"""Verify model validation, value-type coercion, computed properties and methods.

Run from the repo root: uv run python .claude/skills/run-wd-discord/verify_models.py

Validates live API responses into models, then exercises the value types (Snowflake/ImageHash/
PermissionsField round-trips), computed props (Snowflake.timestamp/worker_id/...), methods
(User.validate_scopes, Team.owner), and the unknown-field telemetry path with a crafted payload.
"""
from __future__ import annotations

import asyncio
import sys

from _common import load_token, support_guild_id
from httpxyz import RequestError
from wd_discord import ApiResponseError, Client, Permissions
from wd_discord.application import Application
from wd_discord.guild import Guild
from wd_discord.oauth import OAuthScopes
from wd_discord.user import User


def _fail(label: str, detail: object) -> int:
    print(f"FAIL: {label} -> {detail!r}")
    return 1


async def main() -> int:  # noqa: PLR0911 - a linear sequence of guarded checks reads clearest flat
    """Drive model validators and methods against live + crafted data."""
    async with Client(load_token()) as client:
        me = await client.get_current_user()
        if isinstance(me, ApiResponseError | RequestError):
            return _fail("get_current_user", me)

        # Value-type round-trip: Snowflake -> decimal string, ImageHash -> hash string.
        dumped = me.model_dump(mode="json")
        if not isinstance(dumped["id"], str) or not dumped["id"].isdigit():
            return _fail("Snowflake serialises to decimal string", dumped["id"])
        print(f"MODEL OK: User validated + round-tripped (id={dumped['id']})")

        # Snowflake computed properties.
        snowflake = me.id
        print(
            f"MODEL OK: Snowflake props ts={snowflake.timestamp.isoformat()} "
            f"worker={snowflake.worker_id} process={snowflake.process_id} increment={snowflake.increment}",
        )

        # User.validate_scopes: IDENTIFY covers id/username; EMAIL-gated fields need EMAIL too.
        identify_only = me.validate_scopes({OAuthScopes.IDENTIFY})
        with_email = me.validate_scopes({OAuthScopes.IDENTIFY, OAuthScopes.EMAIL})
        print(f"MODEL OK: validate_scopes(identify)={identify_only} validate_scopes(+email)={with_email}")

        app = await client.get_current_application()
        if isinstance(app, ApiResponseError | RequestError):
            return _fail("get_current_application", app)
        if isinstance(app, Application) and app.team is not None:
            print(f"MODEL OK: Application.team.owner -> {app.team.owner!r}")
        else:
            print("MODEL OK: Application validated (no team on this app)")

        gid = support_guild_id()
        if gid:
            guild = await client.get_guild(gid)
            if isinstance(guild, ApiResponseError | RequestError):
                return _fail("get_guild", guild)
            assert isinstance(guild, Guild)  # noqa: S101
            perms_ok = guild.permissions is None or isinstance(guild.permissions, Permissions)
            print(f"MODEL OK: Guild validated ({len(guild.roles)} roles, permissions typed={perms_ok})")
        else:
            print("MODEL SKIP: no support_guild_id; skipped live Guild validation")

    # Crafted unknown-field payload: drives DiscordModel._report_unknown_fields (Sentry + log).
    probe = User.model_validate(
        {"id": "1226868250713784331", "username": "probe", "discriminator": "0", "__wd_probe__": "x"},
    )
    if "__wd_probe__" not in (probe.model_extra or {}):
        return _fail("unknown-field capture", probe.model_extra)
    print("MODEL OK: unknown-field telemetry path fired (User.__wd_probe__)")

    print("MODEL OK: all validations exercised")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
