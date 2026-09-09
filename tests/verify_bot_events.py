"""Verify live gateway dispatch of GUILD_CREATE/MESSAGE_CREATE through parse_dispatch.

Run from the repo root: uv run python tests/verify_bot_events.py [seconds]

Unlike verify_gateway.py (which only proves connect/presence/close), this drives the same
Gateway.listen() + parse_dispatch() pipeline wd_bot.bot.Bot._dispatch ultimately runs on, and
prints every GUILD_CREATE/MESSAGE_CREATE it receives as the typed GuildCreate/Message models
from wd_discord.gateway.events - not just raw frames.

GUILD_CREATE arrives automatically right after IDENTIFY (once per guild the bot is in) - no
action needed. MESSAGE_CREATE only arrives once a real message is sent in a real channel the bot
can see, so this listens for `seconds` (default 180) rather than exiting the moment READY
resolves: send a message in the configured support guild (see config.ini [Settings]
support_guild_id) from another account while this is running.

Requires the GUILDS, GUILD_MESSAGES and MESSAGE_CONTENT intents - the last one is privileged and
must already be enabled for this bot application in the Discord developer portal, or IDENTIFY
will be rejected (disallowed intents close code).
"""
from __future__ import annotations

lazy import asyncio
lazy import sys

lazy from _common import load_token, support_guild_id
lazy from wd_core.intents import Intents
lazy from wd_discord.gateway import Gateway
lazy from wd_discord.gateway.events import GuildCreate, Message, RawEvent


DEFAULT_LISTEN_SECONDS = 180

REQUIRED_INTENTS = Intents.guilds | Intents.guild_messages | Intents.message_content


async def main() -> int:
    """Connect, then listen for real dispatch events for a configurable window."""
    token = load_token()
    listen_seconds = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LISTEN_SECONDS
    guild_id = support_guild_id()

    guilds_seen: list[GuildCreate] = []
    messages_seen: list[Message] = []
    raw_seen: set[str] = set()

    async def on_dispatch(name: str, payload: object) -> None:
        match payload:
            case GuildCreate():
                guilds_seen.append(payload)
                print(f"GUILD_CREATE OK: {payload.name!r} (id {payload.id})")
            case Message():
                messages_seen.append(payload)
                print(f"MESSAGE_CREATE OK: {payload.author.username}: {payload.content!r} (channel {payload.channel_id})")
            case RawEvent():
                raw_seen.add(name)

    gateway = Gateway(token, intents=REQUIRED_INTENTS)
    ready = await asyncio.wait_for(gateway.connect(), timeout=30)
    print(f"GATEWAY OK: READY session {ready.session_id[:8]}..., user {ready.user.username}")

    if guild_id is not None:
        print(f"Send a test message in guild {guild_id} now - listening for {listen_seconds}s...")
    else:
        print(f"Send a test message in any channel the bot can see - listening for {listen_seconds}s...")

    try:
        await asyncio.wait_for(gateway.listen(on_dispatch), timeout=listen_seconds)
    except TimeoutError:
        pass
    finally:
        await gateway.close()

    print(f"GATEWAY OK: closed cleanly after {listen_seconds}s")
    print(
        f"SUMMARY: {len(guilds_seen)} GUILD_CREATE, {len(messages_seen)} MESSAGE_CREATE, "
        f"{len(raw_seen)} distinct unmodeled event types seen",
    )

    if not guilds_seen:
        print("FAIL: no GUILD_CREATE received - check intents/guild membership.")
        return 1
    if not messages_seen:
        print("NOTE: no MESSAGE_CREATE received in the window - this is expected if nobody sent one; not a failure.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
