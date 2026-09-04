"""Verify every currently-implemented Client REST method against the live Discord API.

Run from the repo root: uv run python .claude/skills/run-wd-discord/verify_rest.py

Exercises the errors-as-values getters (isinstance guards, never try/except) plus the one mutating
call (modify_current_user) with a same-value username so the bot profile does not visibly change.
Each request is also traced into logs/Client.log by the new Client logging.
"""
from __future__ import annotations

lazy import asyncio
lazy import sys

lazy from _common import load_token, support_guild_id
lazy from httpxyz import RequestError, Response
lazy from wd_discord import ApiResponseError, Client
lazy from wd_discord.application import Application
lazy from wd_discord.channel import Channel
lazy from wd_discord.gateway.sharding import GatewayBotInfo
lazy from wd_discord.guild import Guild
lazy from wd_discord.user import User


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
    """Call every Client resource method once."""
    async with Client(load_token()) as client:
        me = await client.get_current_user()
        if not _ok(me, User, "get_current_user() /users/@me"):
            return 1
        assert isinstance(me, User)  # noqa: S101 - narrow for the calls below
        my_id: str = me.model_dump(mode="json")["id"]  # Snowflake -> decimal string

        if not _ok(await client.get_current_application(), Application, "get_current_application() /applications/@me"):
            return 1
        if not _ok(await client.get_gateway_bot(), GatewayBotInfo, "get_gateway_bot() /gateway/bot"):
            return 1
        if not _ok(await client.get_user(my_id), User, f"get_user({my_id})"):
            return 1

        gid = support_guild_id()
        if gid:
            if not _ok(await client.get_guild(gid), Guild, f"get_guild({gid})"):
                return 1
            channels = await client.get(f"/guilds/{gid}/channels")
            if isinstance(channels, Response) and channels.json():
                first = channels.json()[0]["id"]
                if not _ok(await client.get_channel(first), Channel, f"get_channel({first})"):
                    return 1
            else:
                print(f"REST SKIP: no channels listed for guild {gid} ({channels!r})")
        else:
            print("REST SKIP: no support_guild_id in config; skipped get_guild/get_channel")

        # Mutating call: same-value username patch (no visible change), verifies the PATCH path.
        patched = await client.modify_current_user(username=me.username)
        if not _ok(patched, Response, "modify_current_user(username=<current>) PATCH /users/@me"):
            return 1

    print("REST OK: all resource methods exercised")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
