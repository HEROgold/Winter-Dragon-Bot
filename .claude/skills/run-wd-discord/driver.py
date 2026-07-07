"""Live smoke driver for the in-house Discord client (wd-discord).

Run from the repo root with: uv run python .claude/skills/run-wd-discord/driver.py

Reads the bot token from config.ini [Tokens] discord_token, then:
1. REST:    GET /users/@me and /gateway/bot via wd_discord.client.Client
2. Gateway: connect + IDENTIFY, wait for READY, then close cleanly

Exits 0 only if both surfaces worked. Never prints the token.
"""
from __future__ import annotations

import asyncio
import configparser
import sys

from wd_discord.client import Client
from wd_discord.gateway import Gateway
from wd_discord.gateway.sharding import GatewayBotInfo
from wd_discord.user.user import User


def load_token() -> str:
    """Read the bot token from config.ini, refusing the '!!' first-launch sentinel."""
    parser = configparser.ConfigParser()
    parser.read("config.ini")
    token = parser.get("Tokens", "discord_token", fallback="!!").strip('"')
    if token in ("!!", ""):
        print("FAIL: config.ini [Tokens] discord_token is unset ('!!' sentinel).")
        sys.exit(2)
    return token


async def main() -> int:
    """Drive REST and gateway once; return a process exit code."""
    token = load_token()

    async with Client(token) as client:
        me = await client.get_current_user()
        if not isinstance(me, User):
            print(f"FAIL: /users/@me -> {me!r}")
            return 1
        print(f"REST OK: authenticated as {me.username} (id {me.id})")

        gw_info = await client.get_gateway_bot()
        if not isinstance(gw_info, GatewayBotInfo):
            print(f"FAIL: /gateway/bot -> {gw_info!r}")
            return 1
        print(f"REST OK: gateway url {gw_info.url}, recommended shards {gw_info.shards}")

    gateway = Gateway(token)
    ready = await asyncio.wait_for(gateway.connect(), timeout=30)
    print(f"GATEWAY OK: READY session {ready.session_id[:8]}..., user {ready.user.get('username')}")
    await gateway.close()
    print("GATEWAY OK: closed cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
