"""Discord Permissions.

https://docs.discord.com/developers/topics/permissions#permissions
"""

from __future__ import annotations

from enum import IntEnum, IntFlag
from typing import TYPE_CHECKING, Annotated


if TYPE_CHECKING:
    from herogold.supports import IsAnnotated


class ChannelType(IntEnum):
    """Represents the different types of channels in Discord.

    Each channel type is represented by an integer value, allowing for easy identification and categorization of channels.
    """

    GUILD_TEXT = 0
    """A text channel within a server"""
    DM = 1
    """A direct message between users"""
    GUILD_VOICE = 2
    """A voice channel within a server"""
    GROUP_DM = 3
    """A direct message between multiple users"""
    GUILD_CATEGORY = 4
    """An organizational category that contains up to 50 channels"""
    GUILD_ANNOUNCEMENT = 5
    """A text channel that is primarily for announcements"""
    ANNOUNCEMENT_THREAD = 10
    """A temporary sub-channel within an announcement channel"""
    PUBLIC_THREAD = 11
    """A temporary sub-channel within a text channel that is open to all members of the server"""
    PRIVATE_THREAD = 12
    """A temporary sub-channel within a text channel that is only accessible to invited members"""
    GUILD_STAGE_VOICE = 13
    """A voice channel for hosting events with an audience"""
    GUILD_DIRECTORY = 14
    """The guild directory channel type, which allows users to discover and join servers"""
    GUILD_FORUM = 15
    """A text channel that is primarily for discussions and community engagement"""
    GUILD_MEDIA = 16
    """A text channel that is primarily for sharing media content"""

    T = Text = GUILD_TEXT | GUILD_ANNOUNCEMENT | GUILD_FORUM | GUILD_MEDIA
    V = Voice = GUILD_VOICE
    S = Stage = GUILD_STAGE_VOICE


_CommonChannelTypes = ChannelType.T | ChannelType.V | ChannelType.S
_VideoChannelTypes = ChannelType.V | ChannelType.S


class Permissions(IntFlag):
    """Represents the permissions a member has in a guild or channel.

    Each permission is represented by a bit in an integer, allowing for efficient storage and manipulation of permissions.
    """

    # TODO(HEROgold):
    # * These permissions require the owner account to use two-factor authentication when used on a guild that has server-wide 2FA enabled.
    # ** See Permissions for Timed Out Members to understand how permissions are temporarily modified for timed out users.

    def validate_channel(self: IsAnnotated[Permissions, ChannelType] | Permissions, channel: ChannelType) -> bool:
        """Check if the permission is valid for the given channel type."""
        return (not hasattr(self, "__metadata__")) or channel in self.__metadata__

    CREATE_INSTANT_INVITE: Annotated[Permissions.CREATE_INSTANT_INVITE, _CommonChannelTypes] = 1 << 0
    """Allows creation of instant invites  T, V, S"""
    KICK_MEMBERS = 1 << 1
    """Allows kicking members  """
    BAN_MEMBERS = 1 << 2
    """Allows banning members  """
    ADMINISTRATOR = 1 << 3
    """Allows all permissions and bypasses channel permission overwrites  """
    MANAGE_CHANNELS: Annotated[Permissions.MANAGE_CHANNELS, _CommonChannelTypes] = 1 << 4
    """Allows management and editing of channels  T, V, S"""
    MANAGE_GUILD = 1 << 5
    """Allows management and editing of the guild  """
    ADD_REACTIONS = 1 << 6
    """Allows for adding new reactions to messages.
    This permission does not apply to reacting with an existing reaction on a message.  T, V, S"""
    VIEW_AUDIT_LOG = 1 << 7
    """Allows for viewing of audit logs  """
    PRIORITY_SPEAKER: Annotated[Permissions.PRIORITY_SPEAKER, ChannelType.V] = 1 << 8
    """Allows for using priority speaker in a voice channel  V"""
    STREAM: Annotated[Permissions.STREAM, _VideoChannelTypes] = 1 << 9
    """Allows the user to go live  V, S"""
    VIEW_CHANNEL: Annotated[Permissions.VIEW_CHANNEL, _CommonChannelTypes] = 1 << 10
    """Allows guild members to view a channel,
    which includes reading messages in text channels and joining voice channels  T, V, S"""
    SEND_MESSAGES: Annotated[Permissions.SEND_MESSAGES, _CommonChannelTypes] = 1 << 11
    """Allows for sending messages in a channel and creating threads in a forum
    (does not allow sending messages in threads)  T, V, S"""
    SEND_TTS_MESSAGES: Annotated[Permissions.SEND_TTS_MESSAGES, _CommonChannelTypes] = 1 << 12
    """Allows for sending of /tts messages  T, V, S"""
    MANAGE_MESSAGES: Annotated[Permissions.MANAGE_MESSAGES, _CommonChannelTypes] = 1 << 13
    """Allows for deletion of other users messages  T, V, S"""
    EMBED_LINKS: Annotated[Permissions.EMBED_LINKS, _CommonChannelTypes] = 1 << 14
    """Links sent by users with this permission will be auto-embedded  T, V, S"""
    ATTACH_FILES: Annotated[Permissions.ATTACH_FILES, _CommonChannelTypes] = 1 << 15
    """Allows for uploading images and files  T, V, S"""
    READ_MESSAGE_HISTORY: Annotated[Permissions.READ_MESSAGE_HISTORY, _CommonChannelTypes] = 1 << 16
    """Allows for reading of message history  T, V, S"""
    MENTION_EVERYONE: Annotated[Permissions.MENTION_EVERYONE, _CommonChannelTypes] = 1 << 17
    """Allows for using the @everyone tag to notify all users in a channel,
    and the @here tag to notify all online users in a channel  T, V, S"""
    USE_EXTERNAL_EMOJIS: Annotated[Permissions.USE_EXTERNAL_EMOJIS, _CommonChannelTypes] = 1 << 18
    """Allows the usage of custom emojis from other servers  T, V, S"""
    VIEW_GUILD_INSIGHTS: Annotated[Permissions.VIEW_GUILD_INSIGHTS, _CommonChannelTypes] = 1 << 19
    """Allows for viewing guild insights  """
    CONNECT: Annotated[Permissions.CONNECT, _VideoChannelTypes] = 1 << 20
    """Allows for joining of a voice channel  V, S"""
    SPEAK: Annotated[Permissions.SPEAK, ChannelType.V] = 1 << 21
    """Allows for speaking in a voice channel  V"""
    MUTE_MEMBERS: Annotated[Permissions.MUTE_MEMBERS, _VideoChannelTypes] = 1 << 22
    """Allows for muting members in a voice channel  V, S"""
    DEAFEN_MEMBERS: Annotated[Permissions.DEAFEN_MEMBERS, _VideoChannelTypes] = 1 << 23
    """Allows for deafening of members in a voice channel  V"""
    MOVE_MEMBERS: Annotated[Permissions.MOVE_MEMBERS, _VideoChannelTypes] = 1 << 24
    """Allows for moving of members between voice channels  V, S"""
    USE_VAD: Annotated[Permissions.USE_VAD, ChannelType.V] = 1 << 25
    """Allows for using voice-activity-detection in a voice channel  V"""
    CHANGE_NICKNAME = 1 << 26
    """Allows for modification of own nickname  """
    MANAGE_NICKNAMES = 1 << 27
    """Allows for modification of other users nicknames  """
    MANAGE_ROLES: Annotated[Permissions.MANAGE_ROLES, _CommonChannelTypes] = 1 << 28
    """Allows management and editing of roles  T, V, S"""
    MANAGE_WEBHOOKS: Annotated[Permissions.MANAGE_WEBHOOKS, _CommonChannelTypes] = 1 << 29
    """Allows management and editing of webhooks  T, V, S"""
    MANAGE_GUILD_EXPRESSIONS = 1 << 30
    """Allows for editing and deleting emojis, stickers, and soundboard sounds created by all users  """
    USE_APPLICATION_COMMANDS: Annotated[Permissions.USE_APPLICATION_COMMANDS, _CommonChannelTypes] = 1 << 31
    """Allows members to use application commands, including slash commands and context menu commands.  T, V, S"""
    REQUEST_TO_SPEAK: Annotated[Permissions.REQUEST_TO_SPEAK, ChannelType.S] = 1 << 32
    """Allows for requesting to speak in stage channels  S"""
    MANAGE_EVENTS: Annotated[Permissions.MANAGE_EVENTS, _VideoChannelTypes] = 1 << 33
    """Allows for editing and deleting scheduled events created by all users  V, S"""
    MANAGE_THREADS: Annotated[Permissions.MANAGE_THREADS, ChannelType.T] = 1 << 34
    """Allows for deleting and archiving threads, and viewing all private threads  T"""
    CREATE_PUBLIC_THREADS: Annotated[Permissions.CREATE_PUBLIC_THREADS, ChannelType.T] = 1 << 35
    """Allows for creating public and announcement threads  T"""
    CREATE_PRIVATE_THREADS: Annotated[Permissions.CREATE_PRIVATE_THREADS, ChannelType.T] = 1 << 36
    """Allows for creating private threads  T"""
    USE_EXTERNAL_STICKERS: Annotated[Permissions.USE_EXTERNAL_STICKERS, _CommonChannelTypes] = 1 << 37
    """Allows the usage of custom stickers from other servers  T, V, S"""
    SEND_MESSAGES_IN_THREADS: Annotated[Permissions.SEND_MESSAGES_IN_THREADS, ChannelType.T] = 1 << 38
    """Allows for sending messages in threads  T"""
    USE_EMBEDDED_ACTIVITIES: Annotated[Permissions.USE_EMBEDDED_ACTIVITIES, ChannelType.T, ChannelType.V] = 1 << 39
    """Allows for using Activities (applications with the EMBEDDED flag)  T, V"""
    MODERATE_MEMBERS = 1 << 40
    """Allows for timing out users to prevent them from sending or reacting to messages in chat and threads,
    and from speaking in voice and stage channels  """
    VIEW_CREATOR_MONETIZATION_ANALYTICS = 1 << 41
    """Allows for viewing role subscription insights  """
    USE_SOUNDBOARD: Annotated[Permissions.USE_SOUNDBOARD, ChannelType.V] = 1 << 42
    """Allows for using soundboard in a voice channel  V"""
    CREATE_GUILD_EXPRESSIONS = 1 << 43
    """Allows for creating emojis, stickers, and soundboard sounds,
    and editing and deleting those created by the current user."""
    CREATE_EVENTS: Annotated[Permissions.CREATE_EVENTS, _VideoChannelTypes] = 1 << 44
    """Allows for creating scheduled events, and editing and deleting those created by the current user.  V, S"""
    USE_EXTERNAL_SOUNDS: Annotated[Permissions.USE_EXTERNAL_SOUNDS, ChannelType.V] = 1 << 45
    """Allows the usage of custom soundboard sounds from other servers  V"""
    SEND_VOICE_MESSAGES: Annotated[Permissions.SEND_VOICE_MESSAGES, _CommonChannelTypes] = 1 << 46
    """Allows sending voice messages  T, V, S"""
    SET_VOICE_CHANNEL_STATUS: Annotated[Permissions.SET_VOICE_CHANNEL_STATUS, ChannelType.V] = 1 << 48
    """Allows setting voice channel status  V"""
    SEND_POLLS: Annotated[Permissions.SEND_POLLS, _CommonChannelTypes] = 1 << 49
    """Allows sending polls  T, V, S"""
    USE_EXTERNAL_APPS: Annotated[Permissions.USE_EXTERNAL_APPS, _CommonChannelTypes] = 1 << 50
    """Allows user-installed apps to send public responses. When disabled, users will still be allowed to use their apps
    but the responses will be ephemeral. This only applies to apps not also installed to the server.  T, V, S"""
    PIN_MESSAGES: Annotated[Permissions.PIN_MESSAGES, ChannelType.T] = 1 << 51
    """Allows pinning and unpinning messages  T"""
    BYPASS_SLOWMODE: Annotated[Permissions.BYPASS_SLOWMODE, _CommonChannelTypes] = 1 << 52
    """Allows bypassing slowmode restrictions  T, V, S"""
