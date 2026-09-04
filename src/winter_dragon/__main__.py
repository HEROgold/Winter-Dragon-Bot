"""Live smoke driver for the in-house Discord client (wd-discord).

Run from the repo root with: uv run python .claude/skills/run-wd-discord/driver.py

Reads the bot token from config.ini [Tokens] discord_token, then:
1. REST:    GET /users/@me and /gateway/bot via wd_discord.client.Client
2. Gateway: connect + IDENTIFY, wait for READY, then close cleanly

Exits 0 only if both surfaces worked. Never prints the token.
"""

from __future__ import annotations

lazy import asyncio
lazy import configparser
lazy import sys

lazy from wd_discord.client import Client
lazy from wd_discord.gateway import Gateway
lazy from wd_discord.gateway.sharding import GatewayBotInfo
lazy from wd_discord.user.user import User


def load_token() -> str:
    """Read the bot token lazy from config.ini, refusing the '!!' first-launch sentinel."""
    parser = configparser.ConfigParser()
    parser.read("config.ini")
    token = parser.get("Tokens", "discord_token", fallback="!!").strip('"')
    if token in ("!!", ""):
        sys.exit(2)
    return token


async def main() -> int:
    """Drive REST and gateway once; return a process exit code."""
    token = load_token()

    async with Client(token) as client:
        me = await client.get_current_user()
        if not isinstance(me, User):
            return 1

        gw_info = await client.get_gateway_bot()
        if not isinstance(gw_info, GatewayBotInfo):
            return 1

    gateway = Gateway(token)
    await asyncio.wait_for(gateway.connect(), timeout=30)
    await gateway.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
