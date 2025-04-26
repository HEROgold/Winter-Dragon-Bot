"""Module that contains the Guild class, which is a subclass of discord.Guild.

It provides additional functionality for managing and retrieving channels of different types within a Discord guild.
"""
from collections.abc import Generator
from typing import Any

from discord import CategoryChannel, StageChannel, TextChannel, Thread, VoiceChannel
from discord import Guild as DCGuild


class Guild(DCGuild):
    """A class representing a Discord guild (server). With added functionality over the default Discord class."""

    def _gen_typed_channels(self, channel_type: type) -> Generator[int, Any]:
        """Get channels of a specific type from the guild."""
        for channel in self._channels:
            if isinstance(channel, channel_type):
                yield channel

    def gen_text_channels(self) -> Generator[int, Any]:
        """Get all text channels in the guild."""
        yield from self._gen_typed_channels(TextChannel)

    def gen_voice_channels(self) -> Generator[int, Any]:
        """Get all voice channels in the guild."""
        yield from self._gen_typed_channels(VoiceChannel)

    def gen_category_channels(self) -> Generator[int, Any]:
        """Get all category channels in the guild."""
        yield from self._gen_typed_channels(CategoryChannel)

    def gen_stage_channels(self) -> Generator[int, Any]:
        """Get all stage channels in the guild."""
        yield from self._gen_typed_channels(StageChannel)

    def _get_type_mismatch_message(self, expected_type: type, actual_type: type) -> str:
        """Generate an error message for type mismatches."""
        return f"Expected {expected_type}, but got {actual_type}."

    def get_text_channel(self, _id: int) -> TextChannel | None:
        """Get a text channel by its ID.

        Raises:
            TypeError: If the channel exists but is not a TextChannel.

        """
        channel = self.get_channel(_id)
        if isinstance(channel,TextChannel) or channel is None:
            return channel
        raise TypeError(self._get_type_mismatch_message(TextChannel, type(channel)))

    def get_voice_channel(self, _id: int) -> VoiceChannel | None:
        """Get a voice channel by its ID.

        Raises:
            TypeError: If the channel exists but is not a VoiceChannel.

        """
        channel = self.get_channel(_id)
        if isinstance(channel, VoiceChannel) or channel is None:
            return channel
        raise TypeError(self._get_type_mismatch_message(VoiceChannel, type(channel)))

    def get_category_channel(self, _id: int) -> CategoryChannel | None:
        """Get a category channel by its ID.

        Raises:
            TypeError: If the channel exists but is not a CategoryChannel.

        """
        channel = self.get_channel(_id)
        if isinstance(channel, CategoryChannel) or channel is None:
            return channel
        raise TypeError(self._get_type_mismatch_message(CategoryChannel, type(channel)))

    def get_stage_channel(self, _id: int) -> StageChannel | None:
        """Get a stage channel by its ID.

        Raises:
            TypeError: If the channel exists but is not a StageChannel.

        """
        channel = self.get_channel(_id)
        if isinstance(channel, StageChannel) or channel is None:
            return channel
        raise TypeError(self._get_type_mismatch_message(StageChannel, type(channel)))

    def get_tread(self, _id: int) -> Thread | None:
        """Get a thread by its ID.

        Raises:
            TypeError: If the channel exists but is not a Thread.

        """
        channel = self.get_channel(_id)
        if isinstance(channel, Thread) or channel is None:
            return channel
        raise TypeError(self._get_type_mismatch_message(Thread, type(channel)))
