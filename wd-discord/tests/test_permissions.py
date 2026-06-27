"""Unit tests: permission bit values and channel-type concepts."""
from __future__ import annotations

from wd_discord import ChannelType, Permissions


def test_permission_bit_values() -> None:
    assert Permissions.CREATE_INSTANT_INVITE == 1 << 0
    assert Permissions.ADMINISTRATOR == 1 << 3
    assert Permissions.SEND_MESSAGES == 1 << 11
    assert Permissions.BYPASS_SLOWMODE == 1 << 52


def test_permission_combination() -> None:
    combined = Permissions.SEND_MESSAGES | Permissions.VIEW_CHANNEL
    assert Permissions.SEND_MESSAGES in combined
    assert Permissions.VIEW_CHANNEL in combined
    assert Permissions.ADMINISTRATOR not in combined


def test_channel_type_values() -> None:
    assert ChannelType.GUILD_TEXT == 0
    assert ChannelType.DM == 1
    assert ChannelType.GUILD_VOICE == 2
    assert ChannelType.GUILD_STAGE_VOICE == 13
    assert ChannelType.GUILD_MEDIA == 16


def test_channel_type_aliases() -> None:
    assert ChannelType.T is ChannelType.Text
    assert ChannelType.V is ChannelType.Voice
    assert ChannelType.S is ChannelType.Stage
    # The text alias is the OR of every text-like channel type.
    assert ChannelType.T == (
        ChannelType.GUILD_TEXT
        | ChannelType.GUILD_ANNOUNCEMENT
        | ChannelType.GUILD_FORUM
        | ChannelType.GUILD_MEDIA
    )
    assert ChannelType.V == ChannelType.GUILD_VOICE
    assert ChannelType.S == ChannelType.GUILD_STAGE_VOICE


def test_validate_channel_returns_bool() -> None:
    # Enum members carry no runtime Annotated metadata, so validation is permissive.
    assert Permissions.SEND_MESSAGES.validate_channel(ChannelType.GUILD_TEXT) is True
