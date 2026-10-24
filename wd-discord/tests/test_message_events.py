"""Unit tests: message, reaction, typing, emoji and sticker gateway events parse into their models."""

from __future__ import annotations

lazy from wd_discord.gateway import EventName, parse_dispatch
lazy from wd_discord.gateway.events import (
    GuildEmojisUpdate,
    GuildStickersUpdate,
    MessageDelete,
    MessageDeleteBulk,
    MessageReactionAdd,
    MessageReactionRemove,
    MessageReactionRemoveAll,
    MessageReactionRemoveEmoji,
    MessageUpdate,
    TypingStart,
)
lazy from wd_discord.testing import message_json, user_json


AUTHOR = user_json(id="5", avatar=None)


def test_message_update_parses_the_full_message() -> None:
    event = parse_dispatch(
        EventName.MESSAGE_UPDATE,
        message_json(
            id="1",
            channel_id="2",
            author=AUTHOR,
            content="edited",
            timestamp="2026-10-22T00:00:00+00:00",
            edited_timestamp="2026-10-22T00:01:00+00:00",
        ),
    )
    assert isinstance(event, MessageUpdate)
    assert event.content == "edited"


def test_message_delete_and_bulk_delete() -> None:
    single = parse_dispatch(EventName.MESSAGE_DELETE, {"id": "1", "channel_id": "2", "guild_id": "3"})
    bulk = parse_dispatch(EventName.MESSAGE_DELETE_BULK, {"ids": ["1", "4"], "channel_id": "2"})
    assert isinstance(single, MessageDelete)
    assert isinstance(bulk, MessageDeleteBulk)
    assert [int(i) for i in bulk.ids] == [1, 4]


def test_reaction_events() -> None:
    emoji = {"id": None, "name": "🔥"}
    ids = {"user_id": "1", "channel_id": "2", "message_id": "3", "guild_id": "4"}
    added = parse_dispatch(EventName.MESSAGE_REACTION_ADD, {**ids, "emoji": emoji, "burst": True, "type": 1})
    removed = parse_dispatch(EventName.MESSAGE_REACTION_REMOVE, {**ids, "emoji": emoji})
    cleared = parse_dispatch(EventName.MESSAGE_REACTION_REMOVE_ALL, {"channel_id": "2", "message_id": "3"})
    one_emoji = parse_dispatch(EventName.MESSAGE_REACTION_REMOVE_EMOJI, {"channel_id": "2", "message_id": "3", "emoji": emoji})
    assert isinstance(added, MessageReactionAdd)
    assert added.burst
    assert isinstance(removed, MessageReactionRemove)
    assert isinstance(cleared, MessageReactionRemoveAll)
    assert isinstance(one_emoji, MessageReactionRemoveEmoji)


def test_typing_start() -> None:
    event = parse_dispatch(EventName.TYPING_START, {"channel_id": "2", "user_id": "1", "timestamp": 1792614230})
    assert isinstance(event, TypingStart)
    assert event.timestamp == 1792614230


def test_guild_emojis_and_stickers_update() -> None:
    emojis = parse_dispatch(EventName.GUILD_EMOJIS_UPDATE, {"guild_id": "4", "emojis": [{"id": "9", "name": "wave"}]})
    stickers = parse_dispatch(EventName.GUILD_STICKERS_UPDATE, {"guild_id": "4", "stickers": []})
    assert isinstance(emojis, GuildEmojisUpdate)
    assert isinstance(stickers, GuildStickersUpdate)
