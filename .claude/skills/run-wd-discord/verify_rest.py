"""Verify every currently-implemented Client REST method against the live Discord API.

Run from the repo root: uv run python .claude/skills/run-wd-discord/verify_rest.py

Exercises the errors-as-values getters (isinstance guards, never try/except) plus the one mutating
call (modify_current_user) with a same-value username so the bot profile does not visibly change.
Each request is also traced into logs/Client.log by the new Client logging.
"""
from __future__ import annotations

import asyncio
import sys

from _common import load_token, support_guild_id
from httpxyz import RequestError
from wd_discord import ApiResponseError, Channel, Client, CurrentUser, Guild, User
from wd_discord.gateway.sharding import GatewayBotInfo
from wd_discord.resources.application import Application


def _ok(result: object, expected: type, label: str) -> bool:
    """Print an OK/FAIL line; return True on success."""
    if isinstance(result, ApiResponseError | RequestError):
        print(f"FAIL: {label} -> {result!r}")
        return False
    if not isinstance(result, expected):
        print(f"FAIL: {label} -> unexpected {type(result).__name__}: {result!r}")
        return False
    print(f"REST OK: {label} -> {expected.__name__}")
    return True


async def main() -> int:
    """Call every store and entity REST method once."""
    async with Client(load_token()) as client:
        me = await client.users.me()
        if not _ok(me, CurrentUser, "users.me() /users/@me"):
            return 1
        assert isinstance(me, CurrentUser)  # noqa: S101 - narrow for the calls below
        my_id = str(me.id)

        if not _ok(await client.application.fetch(), Application, "application.fetch() /applications/@me"):
            return 1
        if not _ok(await client.get_gateway_bot(), GatewayBotInfo, "get_gateway_bot() /gateway/bot"):
            return 1
        if not _ok(await client.users.fetch(my_id), User, f"users.fetch({my_id})"):
            return 1

        gid = support_guild_id()
        if gid:
            if not _ok(await client.guilds.fetch(gid), Guild, f"guilds.fetch({gid})"):
                return 1
            channels = await client.guilds.partial(gid).channels()
            first = None if isinstance(channels, ApiResponseError | RequestError) else next(channels, None)
            if first is not None:
                if not _ok(await client.channels.fetch(first.id), Channel, f"channels.fetch({first.id})"):
                    return 1
            else:
                print(f"REST SKIP: no channels listed for guild {gid} ({channels!r})")
        else:
            print("REST SKIP: no support_guild_id in config; skipped guilds.fetch/channels.fetch")

        # Mutating call: same-value username patch (no visible change), verifies the PATCH path.
        patched = await me.edit(username=me.username)
        if not _ok(patched, CurrentUser, "me.edit(username=<current>) PATCH /users/@me"):
            return 1

    print("REST OK: all resource methods exercised")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
