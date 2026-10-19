"""Verify the gateway connection + presence, and the pure sharding helpers.

Run from the repo root: uv run python .claude/skills/run-wd-discord/verify_gateway.py

connect() -> READY (with a 30s guard so a bad token can't hang), update_presence (op 3), close().
Also asserts the pure helpers build_identify/build_presence/parse_ready and the sharding maths
(shard_id_for_guild/identify_batches/GatewayBotInfo.connect_url) without opening extra sockets.
"""
from __future__ import annotations

import asyncio
import sys

from _common import load_token, support_guild_id
from wd_discord import Client
from wd_discord.gateway import Gateway, GatewayActivity, Status
from wd_discord.gateway.connection import build_identify, build_presence, parse_ready
from wd_discord.gateway.sharding import (
    GatewayBotInfo,
    fetch_gateway_bot,
    identify_batches,
    shard_id_for_guild,
)


def _check_pure_helpers() -> bool:
    """Assert the socket-free gateway/sharding helpers behave."""
    ready = parse_ready({"d": {"session_id": "s", "resume_gateway_url": "u"}})
    if ready.session_id != "s" or ready.resume_gateway_url != "u":
        print(f"FAIL: parse_ready -> {ready!r}")
        return False

    identify = build_identify("tok", 0, shard=(0, 2))
    if identify["shard"] != [0, 2] or identify["intents"] != 0:
        print(f"FAIL: build_identify -> {identify!r}")
        return False

    presence = build_presence([GatewayActivity("verifying")], Status.online)
    if presence["status"] != "online" or presence["activities"][0]["name"] != "verifying":
        print(f"FAIL: build_presence -> {presence!r}")
        return False

    if shard_id_for_guild(1, 1) != 0 or identify_batches([0, 1, 2], 2) != [[0, 1], [2]]:
        print("FAIL: sharding maths (shard_id_for_guild / identify_batches)")
        return False

    print("GATEWAY OK: pure helpers (parse_ready, build_identify, build_presence, sharding maths)")
    return True


async def main() -> int:
    """Drive a real gateway session plus the pure helpers."""
    token = load_token()

    if not _check_pure_helpers():
        return 1

    async with Client(token) as client:
        info = await fetch_gateway_bot(client)
        if not isinstance(info, GatewayBotInfo):
            print(f"FAIL: fetch_gateway_bot -> {info!r}")
            return 1
        print(f"GATEWAY OK: fetch_gateway_bot connect_url={info.connect_url} shards={info.shards}")

    gateway = Gateway(token)
    ready = await asyncio.wait_for(gateway.connect(), timeout=30)
    print(f"GATEWAY OK: READY session {ready.session_id[:8]}..., user {ready.user.get('username')}")

    await gateway.update_presence([GatewayActivity("wd-discord verify")], Status.online)
    print("GATEWAY OK: presence update (op 3) sent")

    await gateway.close()
    print("GATEWAY OK: closed cleanly")

    if (gid := support_guild_id()) is not None:
        print(f"GATEWAY OK: shard_id_for_guild({gid}, shards=1) = {shard_id_for_guild(int(gid), 1)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
