"""Discord voice state model (https://docs.discord.com/developers/resources/voice#voice-state-object)."""

from __future__ import annotations

from datetime import datetime

from wd_discord.models import DiscordModel
from wd_discord.resources.guild.member import GuildMember
from wd_discord.snowflake import Snowflake


class VoiceState(DiscordModel):
    """A user's voice connection status: which voice channel they are in, and whether they're muted."""

    guild_id: Snowflake | None = None
    """The guild this voice state is for; left out of the voice states inside GUILD_CREATE."""
    channel_id: Snowflake | None
    """The voice channel the user is connected to; ``None`` once they disconnect."""
    user_id: Snowflake
    """The user this voice state is for."""
    member: GuildMember | None = None
    """The guild member this voice state is for."""
    session_id: str
    """The session ID for this voice state."""
    deaf: bool
    """Whether this user is deafened by the server."""
    mute: bool
    """Whether this user is muted by the server."""
    self_deaf: bool
    """Whether this user is locally deafened."""
    self_mute: bool
    """Whether this user is locally muted."""
    self_stream: bool | None = None
    """Whether this user is streaming using "Go Live"."""
    self_video: bool
    """Whether this user's camera is enabled."""
    suppress: bool
    """Whether this user's permission to speak is denied."""
    request_to_speak_timestamp: datetime | None
    """When the user requested to speak."""
