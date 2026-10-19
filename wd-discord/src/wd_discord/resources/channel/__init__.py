"""Pydantic v2 models for the Discord v10 Channel object.

https://docs.discord.com/developers/resources/channel#channel-object.
"""

from __future__ import annotations

lazy from wd_discord.resources.channel.channel import Channel
lazy from wd_discord.resources.channel.forum import DefaultReaction, ForumLayoutType, ForumTag, SortOrderType, VideoQualityMode
lazy from wd_discord.resources.channel.overwrite import OverwriteType, PermissionOverwrite
lazy from wd_discord.resources.channel.params import ChannelParams, GuildChannelParams, OverwriteParams
lazy from wd_discord.resources.channel.thread import ThreadMember, ThreadMetadata


__all__ = [
    "Channel",
    "ChannelParams",
    "DefaultReaction",
    "ForumLayoutType",
    "ForumTag",
    "GuildChannelParams",
    "OverwriteParams",
    "OverwriteType",
    "PermissionOverwrite",
    "SortOrderType",
    "ThreadMember",
    "ThreadMetadata",
    "VideoQualityMode",
]
