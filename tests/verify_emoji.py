"""Verify PartialEmoji resolution against live guild data.

Run from the repo root: uv run python .claude/skills/run-wd-discord/verify_emoji.py

Reads the support guild (Guild.emojis) and its welcome screen (WelcomeScreen.welcome_channels[*].emoji),
then exercises PartialEmoji.from_fields / is_custom / is_unicode on real values. Falls back to crafted
custom + unicode pairs so the PartialEmoji logic is always covered even if the guild has no emojis.
"""
from __future__ import annotations

import asyncio
import sys

from _common import load_token, support_guild_id
from httpxyz import RequestError
from wd_discord import ApiResponseError, Client
from wd_discord.guild import Guild
from wd_discord.guild.welcome_screen import WelcomeScreen
from wd_discord.partial_emoji import PartialEmoji
from wd_discord.snowflake import Snowflake


def _check_partial_emoji_logic() -> bool:
    """Cover PartialEmoji.from_fields / is_custom / is_unicode with crafted pairs."""
    custom = PartialEmoji.from_fields(Snowflake(123), "blob")
    unicode_ = PartialEmoji.from_fields(None, "🔥")
    empty = PartialEmoji.from_fields(None, None)
    if custom is None or not custom.is_custom or custom.is_unicode:
        print(f"FAIL: custom PartialEmoji -> {custom!r}")
        return False
    if unicode_ is None or unicode_.is_custom or not unicode_.is_unicode:
        print(f"FAIL: unicode PartialEmoji -> {unicode_!r}")
        return False
    if empty is not None:
        print(f"FAIL: empty PartialEmoji should be None -> {empty!r}")
        return False
    print("EMOJI OK: PartialEmoji.from_fields / is_custom / is_unicode (crafted custom + unicode + empty)")
    return True


async def main() -> int:
    """Resolve emojis from live guild data plus crafted pairs."""
    if not _check_partial_emoji_logic():
        return 1

    gid = support_guild_id()
    if not gid:
        print("EMOJI SKIP: no support_guild_id in config; only crafted PartialEmoji checks ran")
        return 0

    async with Client(load_token()) as client:
        guild = await client.get_guild(gid)
        if isinstance(guild, ApiResponseError | RequestError):
            print(f"FAIL: get_guild -> {guild!r}")
            return 1
        assert isinstance(guild, Guild)  # noqa: S101
        print(f"EMOJI OK: guild has {len(guild.emojis)} custom emoji(s)")

        welcome = await client.get(f"/guilds/{gid}/welcome-screen")
        if isinstance(welcome, ApiResponseError | RequestError):
            print(f"EMOJI SKIP: welcome screen unavailable ({welcome!r})")
            return 0
        screen = WelcomeScreen.model_validate(welcome.json())
        resolved = [ch.emoji for ch in screen.welcome_channels if ch.emoji is not None]
        print(f"EMOJI OK: welcome screen validated, {len(resolved)} channel emoji(s) resolved")
        for emoji in resolved:
            print(f"EMOJI OK:   {emoji!r} custom={emoji.is_custom} unicode={emoji.is_unicode}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
