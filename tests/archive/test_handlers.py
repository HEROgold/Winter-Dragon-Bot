"""Each modelled gateway event lands in the right tables, through the same parse-then-dump path as live events."""

from typing import Any

from sqlmodel import Session, select
from wd_discord.gateway import EventName, parse_dispatch
from wd_discord.testing import GUILD_JSON, member_json, message_json, user_json

from archive import models as db
from archive.handlers import HANDLERS, handle, payload_of, store_raw


USER = user_json(id="9", username="owner", avatar=None)
MEMBER = member_json(user=USER, roles=["5"], joined_at="2026-01-01T00:00:00+00:00", flags=0)
GAME = {"name": "Game", "type": 0, "created_at": 1700000000000}
PRESENCE = {"user": {"id": "9"}, "status": "online", "activities": [GAME], "client_status": {"desktop": "online"}}
MESSAGE = message_json(
    id="100",
    channel_id="2",
    guild_id="1",
    author=USER,
    member={"roles": [], "joined_at": "2026-01-01T00:00:00+00:00", "deaf": False, "mute": False, "flags": 0},
    content="hi",
    timestamp="2026-10-22T00:00:00+00:00",
)


def dispatch(session: Session, name: str, data: dict[str, Any]) -> None:
    handle(session, name, payload_of(parse_dispatch(name, data)))
    session.flush()


def all_rows[T](session: Session, table: type[T]) -> list[T]:
    return list(session.exec(select(table)))


def test_every_modelled_event_has_a_handler() -> None:
    modelled = {event for event in EventName if event.model is not None}
    assert modelled <= HANDLERS.keys()


def test_guild_create_stores_the_guild_and_everything_it_lists(session: Session) -> None:
    guild = {
        **GUILD_JSON,
        "features": ["COMMUNITY"],
        "roles": [
            {
                "id": "5",
                "name": "Mod",
                "color": 0,
                "hoist": False,
                "position": 1,
                "permissions": "8",
                "managed": False,
                "mentionable": True,
                "flags": 0,
            },
        ],
        "channels": [{"id": "2", "type": 0, "name": "general"}],
        "members": [MEMBER],
        "presences": [PRESENCE],
        "voice_states": [
            {
                "user_id": "9",
                "channel_id": "3",
                "session_id": "s",
                "deaf": False,
                "mute": False,
                "self_deaf": False,
                "self_mute": False,
                "self_video": False,
                "suppress": False,
                "request_to_speak_timestamp": None,
            },
        ],
    }
    dispatch(session, EventName.GUILD_CREATE, guild)

    stored = session.get(db.Guild, 1)
    assert stored is not None
    assert stored.name == "My Guild"
    assert [f.feature for f in all_rows(session, db.GuildFeature)] == ["COMMUNITY"]
    channel = session.get(db.Channel, 2)
    assert channel is not None
    assert channel.guild_id == 1
    role = session.get(db.Role, 5)
    assert role is not None
    assert (role.guild_id, role.permissions) == (1, "8")
    (member,) = all_rows(session, db.Member)
    assert (member.guild_id, member.user_id) == (1, 9)
    assert session.get(db.User, 9) is not None
    (presence,) = all_rows(session, db.PresenceUpdate)
    assert (presence.source, presence.guild_id, presence.user_id) == ("GUILD_CREATE", 1, 9)
    assert [a.name for a in all_rows(session, db.Activity)] == ["Game"]
    (voice,) = all_rows(session, db.VoiceStateUpdate)
    assert (voice.source, voice.guild_id, voice.channel_id) == ("GUILD_CREATE", 1, 3)


def test_a_second_guild_create_overwrites_instead_of_duplicating(session: Session) -> None:
    guild = {**GUILD_JSON, "channels": [{"id": "2", "type": 0, "name": "general"}]}
    dispatch(session, EventName.GUILD_CREATE, guild)
    dispatch(session, EventName.GUILD_CREATE, {**guild, "channels": [{"id": "2", "type": 0, "name": "renamed"}]})

    (channel,) = all_rows(session, db.Channel)
    assert channel.name == "renamed"


def test_guild_delete_for_an_outage_keeps_the_guild(session: Session) -> None:
    dispatch(session, EventName.GUILD_CREATE, dict(GUILD_JSON))
    dispatch(session, EventName.GUILD_DELETE, {"id": "1", "unavailable": True})
    guild = session.get(db.Guild, 1)
    assert guild is not None
    assert guild.deleted_at is None

    dispatch(session, EventName.GUILD_DELETE, {"id": "1"})
    assert guild.deleted_at is not None


def test_message_lifecycle(session: Session) -> None:
    dispatch(session, EventName.MESSAGE_CREATE, MESSAGE)
    dispatch(
        session,
        EventName.MESSAGE_UPDATE,
        {**MESSAGE, "content": "edited", "edited_timestamp": "2026-10-22T00:05:00+00:00"},
    )

    message = session.get(db.Message, 100)
    assert message is not None
    assert (message.content, message.author_id) == ("edited", 9)
    (member,) = all_rows(session, db.Member)
    assert (member.guild_id, member.user_id) == (1, 9)
    (revision,) = all_rows(session, db.MessageRevision)
    assert (revision.message_id, revision.content) == (100, "edited")

    dispatch(session, EventName.MESSAGE_DELETE, {"id": "100", "channel_id": "2"})
    assert message.deleted_at is not None
    assert message.content == "edited"


def test_reactions_and_typing_are_appended(session: Session) -> None:
    ids = {"user_id": "9", "channel_id": "2", "message_id": "100", "guild_id": "1"}
    dispatch(session, EventName.MESSAGE_REACTION_ADD, {**ids, "emoji": {"id": None, "name": "🔥"}})
    dispatch(session, EventName.MESSAGE_REACTION_REMOVE, {**ids, "emoji": {"id": None, "name": "🔥"}})
    dispatch(session, EventName.TYPING_START, {"channel_id": "2", "guild_id": "1", "user_id": "9", "timestamp": 1792614230})

    assert [(r.action, r.emoji_name) for r in all_rows(session, db.ReactionEvent)] == [("add", "🔥"), ("remove", "🔥")]
    (typing,) = all_rows(session, db.TypingStart)
    assert typing.timestamp == 1792614230


def test_presence_update_appends_and_updates_the_user(session: Session) -> None:
    dispatch(session, EventName.PRESENCE_UPDATE, {**PRESENCE, "guild_id": "1", "user": {"id": "9", "username": "renamed"}})

    (presence,) = all_rows(session, db.PresenceUpdate)
    assert (presence.source, presence.client_status_desktop) == ("PRESENCE_UPDATE", "online")
    user = session.get(db.User, 9)
    assert user is not None
    assert user.username == "renamed"


def test_member_remove_soft_deletes_the_member(session: Session) -> None:
    dispatch(session, EventName.GUILD_MEMBER_ADD, {**MEMBER, "guild_id": "1"})
    dispatch(session, EventName.GUILD_MEMBER_REMOVE, {"guild_id": "1", "user": USER})

    (member,) = all_rows(session, db.Member)
    assert member.deleted_at is not None


def test_raw_events_keep_the_payload_and_guild(session: Session) -> None:
    store_raw(session, "GUILD_CREATE", 2, {"id": "1", "name": "x"})
    store_raw(session, "TYPING_START", 3, {"guild_id": "1", "channel_id": "2"})
    store_raw(session, "RESUMED", 4, {})
    session.flush()

    assert [(e.name, e.sequence, e.guild_id) for e in all_rows(session, db.GatewayEvent)] == [
        ("GUILD_CREATE", 2, 1),
        ("TYPING_START", 3, 1),
        ("RESUMED", 4, None),
    ]
