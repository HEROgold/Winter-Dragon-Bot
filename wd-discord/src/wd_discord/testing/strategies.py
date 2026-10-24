"""Hypothesis strategies that draw Discord JSON payloads, shaped and limited as the Discord docs describe them.

Each strategy is written from the docs page it links, not from wd-discord's models, so a model that drifts from the
docs fails the tests that parse these payloads. Required fields are always present; optional ones (``?`` in the docs)
sometimes are; nullable ones are sometimes ``null``. IDs are decimal strings, as Discord sends them::

    @given(role=roles())
    def test_a_role_parses(role: dict[str, Any]) -> None:
        assert Role.model_validate(role).name == role["name"]

Needs ``hypothesis``, a dev dependency: import this module from tests only.
"""

lazy from datetime import UTC, datetime
lazy from typing import Any

lazy from hypothesis import strategies as st

lazy from wd_discord.color import MAX_COLOR
lazy from wd_discord.permissions import ChannelType, Permissions


type Json = dict[str, Any]

_EARLIEST = datetime(2015, 1, 1)  # noqa: DTZ001 - hypothesis wants naive bounds and adds the timezone itself
_LATEST = datetime(2100, 1, 1)  # noqa: DTZ001 - as above
_GUILD_CHANNEL_TYPES = (
    ChannelType.GUILD_TEXT,
    ChannelType.GUILD_VOICE,
    ChannelType.GUILD_CATEGORY,
    ChannelType.GUILD_ANNOUNCEMENT,
    ChannelType.GUILD_STAGE_VOICE,
    ChannelType.GUILD_FORUM,
    ChannelType.GUILD_MEDIA,
)


def snowflakes() -> st.SearchStrategy[str]:
    """Draw an ID as Discord sends it: a 64-bit unsigned integer as a decimal string.

    https://docs.discord.com/developers/reference#snowflakes
    """
    return st.integers(min_value=0, max_value=2**64 - 1).map(str)


def timestamps() -> st.SearchStrategy[str]:
    """Draw an ISO8601 timestamp in UTC, between Discord's epoch (2015) and 2100.

    https://docs.discord.com/developers/reference#iso8601-datetime
    """
    return st.datetimes(min_value=_EARLIEST, max_value=_LATEST, timezones=st.just(UTC)).map(datetime.isoformat)


def colors() -> st.SearchStrategy[int]:
    """Draw a 24-bit RGB color integer, as embeds and roles carry it.

    https://docs.discord.com/developers/resources/message#embed-object-embed-structure
    """
    return st.integers(min_value=0, max_value=MAX_COLOR)


def permissions() -> st.SearchStrategy[str]:
    """Draw a permission bit set as Discord serializes it: a decimal string of known bits.

    https://docs.discord.com/developers/topics/permissions#permissions
    """
    return st.integers(min_value=0, max_value=int(Permissions.all())).map(lambda bits: str(bits & Permissions.all()))


def image_hashes() -> st.SearchStrategy[str]:
    """Draw an image hash: 32 hex digits, prefixed with ``a_`` when the image is animated.

    https://docs.discord.com/developers/reference#image-formatting
    """
    digits = st.text(alphabet="0123456789abcdef", min_size=32, max_size=32)
    return digits | digits.map(lambda hash_: f"a_{hash_}")


def users() -> st.SearchStrategy[Json]:
    """Draw a user object.

    https://docs.discord.com/developers/resources/user#user-object
    """
    return st.fixed_dictionaries(
        {
            "id": snowflakes(),
            "username": st.text(min_size=2, max_size=32),
            "discriminator": st.just("0"),
            "global_name": st.none() | st.text(min_size=1, max_size=32),
            "avatar": st.none() | image_hashes(),
        },
        optional={
            "bot": st.booleans(),
            "system": st.booleans(),
            "banner": st.none() | image_hashes(),
            "accent_color": st.none() | colors(),
            "public_flags": st.integers(min_value=0, max_value=2**31 - 1),
        },
    )


def roles(*, role_id: st.SearchStrategy[str] | None = None) -> st.SearchStrategy[Json]:
    """Draw a role object; ``role_id`` draws its ID (any snowflake by default).

    https://docs.discord.com/developers/topics/permissions#role-object
    """
    return st.fixed_dictionaries(
        {
            "id": snowflakes() if role_id is None else role_id,
            "name": st.text(min_size=1, max_size=100),
            "color": colors(),
            "hoist": st.booleans(),
            "position": st.integers(min_value=0, max_value=250),
            "permissions": permissions(),
            "managed": st.booleans(),
            "mentionable": st.booleans(),
            "flags": st.sampled_from([0, 1]),
        },
        optional={"icon": st.none() | image_hashes(), "unicode_emoji": st.none() | st.just("🐉")},
    )


def members(
    *,
    user: st.SearchStrategy[Json] | None = None,
    role_ids: st.SearchStrategy[list[str]] | None = None,
) -> st.SearchStrategy[Json]:
    """Draw a guild member object; ``user`` and ``role_ids`` draw its user and the roles it holds.

    https://docs.discord.com/developers/resources/guild#guild-member-object
    """
    return st.fixed_dictionaries(
        {
            "user": users() if user is None else user,
            "roles": role_ids if role_ids is not None else st.lists(snowflakes(), max_size=5, unique=True),
            "joined_at": st.none() | timestamps(),
            "deaf": st.booleans(),
            "mute": st.booleans(),
        },
        optional={
            "nick": st.none() | st.text(min_size=1, max_size=32),
            "premium_since": st.none() | timestamps(),
            "pending": st.booleans(),
            "flags": st.integers(min_value=0, max_value=0x3FF),
        },
    )


def channels(*, channel_id: st.SearchStrategy[str] | None = None) -> st.SearchStrategy[Json]:
    """Draw a guild channel object (text, voice, category, announcement, stage, forum or media), without its ``guild_id``.

    https://docs.discord.com/developers/resources/channel#channel-object
    """
    return st.fixed_dictionaries(
        {
            "id": snowflakes() if channel_id is None else channel_id,
            "type": st.sampled_from(_GUILD_CHANNEL_TYPES).map(int),
            "name": st.text(min_size=1, max_size=100),
            "position": st.integers(min_value=0, max_value=500),
        },
        optional={
            "topic": st.none() | st.text(max_size=1024),
            "nsfw": st.booleans(),
            "rate_limit_per_user": st.integers(min_value=0, max_value=21600),
        },
    )


def voice_states(
    *,
    user_id: st.SearchStrategy[str] | None = None,
    channel_id: st.SearchStrategy[str] | None = None,
) -> st.SearchStrategy[Json]:
    """Draw a voice state; ``channel_id`` draws the channel the user is in (``null`` when they left).

    https://docs.discord.com/developers/resources/voice#voice-state-object
    """
    return st.fixed_dictionaries(
        {
            "channel_id": st.none() | (snowflakes() if channel_id is None else channel_id),
            "user_id": snowflakes() if user_id is None else user_id,
            "session_id": st.text(alphabet="0123456789abcdef", min_size=32, max_size=32),
            "deaf": st.booleans(),
            "mute": st.booleans(),
            "self_deaf": st.booleans(),
            "self_mute": st.booleans(),
            "self_video": st.booleans(),
            "suppress": st.booleans(),
            "request_to_speak_timestamp": st.none() | timestamps(),
        },
        optional={"self_stream": st.booleans()},
    )


@st.composite
def guild_creates(draw: st.DrawFn, *, guild: Json) -> Json:
    """Draw the GUILD_CREATE event for ``guild``, a guild object (``GUILD_JSON`` or one of its variants).

    Its parts refer to each other as on the gateway: members hold this guild's roles, and voice states are members'
    in this guild's channels. Roles, channels and members have distinct IDs.

    https://docs.discord.com/developers/events/gateway-events#guild-create
    """
    guild_roles = draw(st.lists(roles(), max_size=5, unique_by=lambda role: role["id"]))
    guild_channels = draw(st.lists(channels(), max_size=5, unique_by=lambda channel: channel["id"]))
    role_ids = [role["id"] for role in guild_roles]
    held = st.lists(st.sampled_from(role_ids), unique=True) if role_ids else st.just([])
    guild_members = draw(st.lists(members(role_ids=held), max_size=5, unique_by=lambda member: member["user"]["id"]))
    in_voice = (
        draw(st.lists(st.sampled_from(guild_members), unique_by=lambda member: member["user"]["id"]))
        if guild_members and guild_channels
        else []
    )
    channel_ids = st.sampled_from([channel["id"] for channel in guild_channels])
    states = [draw(voice_states(user_id=st.just(member["user"]["id"]), channel_id=channel_ids)) for member in in_voice]
    return {
        **guild,
        "roles": guild_roles,
        "joined_at": draw(timestamps()),
        "large": draw(st.booleans()),
        "unavailable": False,
        "member_count": len(guild_members),
        "channels": guild_channels,
        "threads": [],
        "members": guild_members,
        "voice_states": [{key: value for key, value in state.items() if key != "guild_id"} for state in states],
        "presences": [],
    }
