"""Discord JSON payloads for tests, shaped as the Discord docs describe each object.

Each builder returns a new dict with the object's required fields, set to one small guild's values: guild 7,
text channel 5 ("general"), thread 6 in it, user 3 ("someone") holding role 8 ("mods"), and the bot, user 2. Keyword
arguments replace or add fields, so a test only spells out what it is about::

    client.reply("GET", "/guilds/7/roles", [role_json(), role_json(id="9", name="admins")])
    client.receive(parse_dispatch(EventName.GUILD_CREATE, guild_create_json(members=[])))

IDs are strings, as Discord sends them.
"""

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Mapping


GUILD_JSON: Mapping[str, object] = {
    "id": "1",
    "name": "My Guild",
    "icon": None,
    "splash": None,
    "discovery_splash": None,
    "owner_id": "9",
    "afk_channel_id": None,
    "afk_timeout": 300,
    "verification_level": 0,
    "default_message_notifications": 0,
    "explicit_content_filter": 0,
    "roles": [],
    "emojis": [],
    "features": [],
    "mfa_level": 0,
    "application_id": None,
    "system_channel_id": None,
    "system_channel_flags": 0,
    "rules_channel_id": None,
    "vanity_url_code": None,
    "description": None,
    "banner": None,
    "premium_tier": 0,
    "preferred_locale": "en-US",
    "public_updates_channel_id": None,
    "nsfw_level": 0,
    "premium_progress_bar_enabled": False,
    "safety_alerts_channel_id": None,
    "incidents_data": None,
}
"""The smallest guild object Discord could send: every required field, nothing optional.

https://docs.discord.com/developers/resources/guild#guild-object
"""


def user_json(**fields: Any) -> dict[str, Any]:  # noqa: ANN401 - any JSON value
    """Return user 3, ``someone``, with ``fields`` changed.

    https://docs.discord.com/developers/resources/user#user-object
    """
    return {"id": "3", "username": "someone", "discriminator": "0", **fields}


def bot_user_json(**fields: Any) -> dict[str, Any]:  # noqa: ANN401 - any JSON value
    """Return the bot's own user, 2 (``RecordingClient``'s application ID), with ``fields`` changed.

    https://docs.discord.com/developers/resources/user#user-object
    """
    return user_json(**{"id": "2", "username": "bot", "bot": True, **fields})


def member_json(**fields: Any) -> dict[str, Any]:  # noqa: ANN401 - any JSON value
    """Return user 3 as a guild member without roles, with ``fields`` changed.

    https://docs.discord.com/developers/resources/guild#guild-member-object
    """
    return {"user": user_json(), "roles": [], "joined_at": None, "deaf": False, "mute": False, **fields}


def role_json(**fields: Any) -> dict[str, Any]:  # noqa: ANN401 - any JSON value
    """Return role 8, ``mods``, without permissions, with ``fields`` changed.

    https://docs.discord.com/developers/topics/permissions#role-object
    """
    return {
        "id": "8",
        "name": "mods",
        "color": 0,
        "hoist": False,
        "position": 1,
        "permissions": "0",
        "managed": False,
        "mentionable": True,
        "flags": 0,
        **fields,
    }


def channel_json(**fields: Any) -> dict[str, Any]:  # noqa: ANN401 - any JSON value
    """Return text channel 5, ``general``, in guild 7, with ``fields`` changed.

    https://docs.discord.com/developers/resources/channel#channel-object
    """
    return {"id": "5", "type": 0, "guild_id": "7", "name": "general", **fields}


def thread_json(**fields: Any) -> dict[str, Any]:  # noqa: ANN401 - any JSON value
    """Return public thread 6 in channel 5, open, with ``fields`` changed.

    https://docs.discord.com/developers/resources/channel#channel-object and
    https://docs.discord.com/developers/resources/channel#thread-metadata-object
    """
    metadata = {
        "archived": False,
        "auto_archive_duration": 60,
        "archive_timestamp": "2026-10-10T12:00:00+00:00",
        "locked": False,
    }
    return channel_json(**{"id": "6", "type": 11, "parent_id": "5", "name": "a thread", "thread_metadata": metadata, **fields})


def voice_state_json(**fields: Any) -> dict[str, Any]:  # noqa: ANN401 - any JSON value
    """Return user 3 connected to channel 5, nothing muted, with ``fields`` changed.

    https://docs.discord.com/developers/resources/voice#voice-state-object
    """
    return {
        "channel_id": "5",
        "user_id": "3",
        "session_id": "s",
        "deaf": False,
        "mute": False,
        "self_deaf": False,
        "self_mute": False,
        "self_video": False,
        "suppress": False,
        "request_to_speak_timestamp": None,
        **fields,
    }


def message_json(**fields: Any) -> dict[str, Any]:  # noqa: ANN401 - any JSON value
    """Return message 5 the bot sent in channel 6, without content, with ``fields`` changed.

    https://docs.discord.com/developers/resources/message#message-object
    """
    return {
        "id": "5",
        "channel_id": "6",
        "author": bot_user_json(),
        "content": "",
        "timestamp": "2026-10-08T12:00:00+00:00",
        "tts": False,
        "mention_everyone": False,
        **fields,
    }


def guild_create_json(**fields: Any) -> dict[str, Any]:  # noqa: ANN401 - any JSON value
    """Return guild 7 as GUILD_CREATE sends it, with ``fields`` changed.

    It holds role 8, channel 5 with thread 6, member 3 with role 8 in voice in channel 5, and no presences.
    Channels in this event leave out their ``guild_id``.

    https://docs.discord.com/developers/events/gateway-events#guild-create
    """
    channel = {key: value for key, value in channel_json().items() if key != "guild_id"}
    return {
        **GUILD_JSON,
        "id": "7",
        "roles": [role_json()],
        "large": False,
        "channels": [channel],
        "threads": [thread_json()],
        "members": [member_json(roles=["8"])],
        "voice_states": [voice_state_json()],
        "presences": [],
        **fields,
    }
