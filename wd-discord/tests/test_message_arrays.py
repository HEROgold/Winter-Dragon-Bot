"""Unit tests: a message's mentions, attachments, embeds and reactions parse into typed models."""

lazy from wd_discord import Message
lazy from wd_discord.entities import bind
lazy from wd_discord.gateway.dispatch import parse_dispatch
lazy from wd_discord.gateway.events import EventName
lazy from wd_discord.snowflake import Snowflake
lazy from wd_discord.testing import RecordingClient


USER_JSON = {"id": "9", "username": "owner", "discriminator": "0"}
MESSAGE_JSON = {
    "id": "50",
    "channel_id": "6",
    "guild_id": "1",
    "author": USER_JSON,
    "content": "hi <@9>",
    "timestamp": "2026-10-10T00:00:00+00:00",
    "tts": False,
    "mention_everyone": False,
    "mentions": [{**USER_JSON, "member": {"roles": ["5"], "joined_at": None, "deaf": False, "mute": False}}],
    "attachments": [
        {"id": "70", "filename": "cat.png", "size": 1024, "url": "https://cdn/cat.png", "proxy_url": "https://media/cat.png"},
    ],
    "embeds": [{"title": "Hello", "color": 65280}],
    "reactions": [
        {
            "count": 2,
            "count_details": {"burst": 0, "normal": 2},
            "me": False,
            "me_burst": False,
            "emoji": {"id": None, "name": "👍"},
            "burst_colors": [],
        },
    ],
}


def _message() -> Message:
    message = bind(RecordingClient(), parse_dispatch(EventName.MESSAGE_CREATE, MESSAGE_JSON))
    assert isinstance(message, Message)
    return message


def test_mentions_are_user_entities_with_their_member() -> None:
    (mentioned,) = _message().mentions
    assert mentioned.id == Snowflake(9)
    assert _message().model.mentions[0].member is not None


def test_attachments_embeds_and_reactions_parse() -> None:
    message = _message()
    (attachment,) = message.attachments
    (embed,) = message.embeds
    (reaction,) = message.reactions
    assert (attachment.filename, attachment.size) == ("cat.png", 1024)
    assert (embed.title, embed.color) == ("Hello", 0x00FF00)
    assert (reaction.count, reaction.emoji.name) == (2, "👍")


def test_a_message_without_the_arrays_still_parses() -> None:
    payload = {key: value for key, value in MESSAGE_JSON.items() if key not in {"mentions", "attachments", "embeds", "reactions"}}
    message = bind(RecordingClient(), parse_dispatch(EventName.MESSAGE_CREATE, payload))
    assert isinstance(message, Message)
    assert list(message.mentions) == []
