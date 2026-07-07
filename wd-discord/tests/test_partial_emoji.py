"""Unit tests: PartialEmoji and the emoji / applied_forum_tags helper properties."""
from __future__ import annotations

from wd_discord.channel.channel import Channel
from wd_discord.channel.forum import DefaultReaction, ForumTag
from wd_discord.guild.welcome_screen import WelcomeScreenChannel
from wd_discord.partial_emoji import PartialEmoji
from wd_discord.snowflake import Snowflake


def test_from_fields_custom() -> None:
    emoji = PartialEmoji.from_fields(Snowflake(123), "party_blob")
    assert emoji is not None
    assert emoji.is_custom is True
    assert emoji.is_unicode is False
    assert emoji.id == Snowflake(123)
    assert emoji.name == "party_blob"


def test_from_fields_unicode() -> None:
    emoji = PartialEmoji.from_fields(None, "\N{PARTY POPPER}")
    assert emoji is not None
    assert emoji.is_custom is False
    assert emoji.is_unicode is True
    assert emoji.id is None
    assert emoji.name == "\N{PARTY POPPER}"


def test_from_fields_none_when_unset() -> None:
    assert PartialEmoji.from_fields(None, None) is None


def test_welcome_screen_channel_emoji() -> None:
    channel = WelcomeScreenChannel.model_validate(
        {
            "channel_id": "1",
            "description": "Say hi",
            "emoji_id": "456",
            "emoji_name": "wave",
        },
    )
    emoji = channel.emoji
    assert emoji is not None
    assert emoji.id == Snowflake(456)
    assert emoji.name == "wave"
    assert emoji.is_custom is True


def test_welcome_screen_channel_emoji_none() -> None:
    channel = WelcomeScreenChannel.model_validate(
        {"channel_id": "1", "description": "d", "emoji_id": None, "emoji_name": None},
    )
    assert channel.emoji is None


def test_forum_tag_emoji() -> None:
    tag = ForumTag.model_validate(
        {"id": "1", "name": "Bug", "moderated": False, "emoji_id": None, "emoji_name": "\N{BUG}"},
    )
    emoji = tag.emoji
    assert emoji is not None
    assert emoji.is_unicode is True
    assert emoji.name == "\N{BUG}"


def test_default_reaction_emoji() -> None:
    reaction = DefaultReaction.model_validate({"emoji_id": "789", "emoji_name": None})
    emoji = reaction.emoji
    assert emoji is not None
    assert emoji.id == Snowflake(789)
    assert emoji.is_custom is True


def test_default_reaction_emoji_none() -> None:
    assert DefaultReaction.model_validate({"emoji_id": None, "emoji_name": None}).emoji is None


def _forum_channel() -> Channel:
    """A forum-style channel carrying available_tags and a subset applied_tags (out of order)."""
    return Channel.model_validate(
        {
            "id": "10",
            "type": 15,  # GUILD_FORUM
            "available_tags": [
                {"id": "100", "name": "Alpha", "moderated": False, "emoji_id": None, "emoji_name": None},
                {"id": "200", "name": "Beta", "moderated": False, "emoji_id": None, "emoji_name": None},
                {"id": "300", "name": "Gamma", "moderated": False, "emoji_id": None, "emoji_name": None},
            ],
            "applied_tags": ["300", "100"],
        },
    )


def test_applied_forum_tags_resolves_in_applied_order() -> None:
    resolved = _forum_channel().applied_forum_tags
    assert [tag.name for tag in resolved] == ["Gamma", "Alpha"]
    assert all(isinstance(tag, ForumTag) for tag in resolved)


def test_applied_forum_tags_empty_without_lists() -> None:
    channel = Channel.model_validate({"id": "10", "type": 15})
    assert channel.applied_forum_tags == []
