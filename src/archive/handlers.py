"""What the archive writes for each gateway event.

Every dispatch is stored raw (:func:`store_raw`). An event with a wd-discord model is also written to the typed
tables by its handler in :data:`HANDLERS`; each handler gets the event's payload as JSON, after wd-discord has
validated it. An event without a handler is only stored raw.
"""

from typing import TYPE_CHECKING, Any

from sqlmodel import col, select
from wd_discord.gateway.events import EventName

from archive import models as db
from archive.store import append, soft_delete, upsert


if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from sqlmodel import Session
    from wd_discord.models import DiscordModel


type Payload = dict[str, Any]
type Handler = Callable[[Session, Payload], None]

GUILD_LISTS = ("channels", "threads", "roles", "emojis", "stickers", "members", "presences", "voice_states")
"""The lists inside a GUILD_CREATE that are stored as rows of their own, not as part of the guild."""


def payload_of(event: DiscordModel) -> Payload:
    """Return ``event`` as the JSON Discord sent: only the fields it carried, under Discord's names."""
    return event.model_dump(mode="json", by_alias=True, exclude_unset=True)


def store_raw(session: Session, name: str, sequence: int | None, data: Mapping[str, Any]) -> None:
    """Append one dispatch, exactly as received, to the raw events."""
    guild_id = data.get("id") if name.startswith("GUILD_") and "guild_id" not in data else data.get("guild_id")
    session.add(db.GatewayEvent(name=name, sequence=sequence, guild_id=_int(guild_id), payload=dict(data)))


def handle(session: Session, name: str, data: Payload) -> None:
    """Write ``data`` to the typed tables, when event ``name`` has a handler."""
    handler = HANDLERS.get(name)
    if handler is not None:
        handler(session, data)


# Shared by several events.


def save_user(session: Session, user: Payload) -> None:
    """Upsert a user from any payload that carries one; only its ID means there is nothing to write."""
    if len(user) > 1:
        upsert(session, db.User, user)


def save_member(session: Session, guild_id: object, member: Payload, user_id: object = None) -> None:
    """Upsert a member, and its user when the payload carries it."""
    user = member.get("user")
    if user is not None:
        save_user(session, user)
        user_id = user["id"]
    upsert(session, db.Member, without(member, "user", "guild_id"), guild_id=_int(guild_id), user_id=_int(user_id))


def save_presence(session: Session, presence: Payload, source: str, guild_id: object = None) -> None:
    """Append a presence, and upsert whatever of its user it carries."""
    user = presence["user"]
    save_user(session, user)
    guild_id = presence.get("guild_id", guild_id)
    known = {"source": source, "user_id": _int(user["id"]), "guild_id": _int(guild_id)}
    append(session, db.PresenceUpdate, without(presence, "user"), **known)


def save_voice_state(session: Session, state: Payload, source: str, guild_id: object = None) -> None:
    """Append a voice state, and upsert the member it carries."""
    guild_id = state.get("guild_id", guild_id)
    member = state.get("member")
    if member is not None and guild_id is not None:
        save_member(session, guild_id, member)
    append(session, db.VoiceStateUpdate, without(state, "member"), source=source, guild_id=_int(guild_id))


def save_message(session: Session, message: Payload) -> None:
    """Upsert a message, with its author and the author's membership."""
    author = message.get("author")
    if author is not None:
        save_user(session, author)
        if (member := message.get("member")) is not None and message.get("guild_id") is not None:
            save_member(session, message["guild_id"], member, user_id=author["id"])
    upsert(session, db.Message, without(message, "member"))


def replace_guild_set(session: Session, table: type[db.Emoji | db.Sticker], guild_id: object, items: list[Payload]) -> None:
    """Upsert a guild's full emoji or sticker list, and delete the ones no longer in it."""
    for item in items:
        upsert(session, table, item, guild_id=_int(guild_id))
    kept = {_int(item["id"]) for item in items}
    stored = session.exec(select(table).where(col(table.guild_id) == _int(guild_id), col(table.deleted_at).is_(None)))
    for row in stored:
        if row.id not in kept:
            soft_delete(session, table, id=row.id)


# One handler per event.


def on_ready(session: Session, data: Payload) -> None:
    """READY: the archive's own user."""
    save_user(session, data["user"])


def on_guild_create(session: Session, data: Payload) -> None:
    """GUILD_CREATE / GUILD_UPDATE: the guild, and everything it lists, with presences and voice as a snapshot."""
    guild_id = data["id"]
    upsert(session, db.Guild, without(data, *GUILD_LISTS))
    for channel in [*data.get("channels", []), *data.get("threads", [])]:
        upsert(session, db.Channel, channel, guild_id=_int(guild_id))
    for role in data.get("roles", []):
        upsert(session, db.Role, role, guild_id=_int(guild_id))
    if "emojis" in data:
        replace_guild_set(session, db.Emoji, guild_id, data["emojis"])
    if "stickers" in data:
        replace_guild_set(session, db.Sticker, guild_id, data["stickers"])
    for member in data.get("members", []):
        save_member(session, guild_id, member)
    for presence in data.get("presences", []):
        save_presence(session, presence, "GUILD_CREATE", guild_id)
    for state in data.get("voice_states", []):
        save_voice_state(session, state, "GUILD_CREATE", guild_id)


def on_guild_delete(session: Session, data: Payload) -> None:
    """GUILD_DELETE: the archive left the guild; an outage (``unavailable``) is not a removal."""
    if not data.get("unavailable"):
        soft_delete(session, db.Guild, id=data["id"])


def on_channel(session: Session, data: Payload) -> None:
    """CHANNEL_CREATE / _UPDATE, THREAD_CREATE / _UPDATE and the voice channel status and start time updates."""
    upsert(session, db.Channel, without(data, "member"))


def on_channel_delete(session: Session, data: Payload) -> None:
    """CHANNEL_DELETE / THREAD_DELETE."""
    soft_delete(session, db.Channel, id=data["id"])


def on_channel_pins_update(session: Session, data: Payload) -> None:
    """CHANNEL_PINS_UPDATE."""
    append(session, db.ChannelPinsUpdate, data)


def on_thread_list_sync(session: Session, data: Payload) -> None:
    """THREAD_LIST_SYNC: the threads of some channels, and the archive's own membership of them."""
    for thread in data.get("threads", []):
        upsert(session, db.Channel, thread)
    for member in data.get("members", []):
        upsert(session, db.ThreadMember, member)


def on_thread_member_update(session: Session, data: Payload) -> None:
    """THREAD_MEMBER_UPDATE."""
    upsert(session, db.ThreadMember, without(data, "guild_id"))


def on_thread_members_update(session: Session, data: Payload) -> None:
    """THREAD_MEMBERS_UPDATE: who joined and left a thread."""
    upsert(session, db.Channel, {key: data[key] for key in ("id", "member_count") if key in data})
    for member in data.get("added_members") or []:
        upsert(session, db.ThreadMember, without(member, "member", "presence"))
    for user_id in data.get("removed_member_ids") or []:
        soft_delete(session, db.ThreadMember, thread_id=data["id"], user_id=user_id)


def on_member(session: Session, data: Payload) -> None:
    """GUILD_MEMBER_ADD / GUILD_MEMBER_UPDATE."""
    save_member(session, data["guild_id"], data)


def on_member_remove(session: Session, data: Payload) -> None:
    """GUILD_MEMBER_REMOVE."""
    save_user(session, data["user"])
    soft_delete(session, db.Member, guild_id=data["guild_id"], user_id=data["user"]["id"])


def on_members_chunk(session: Session, data: Payload) -> None:
    """GUILD_MEMBERS_CHUNK: members, and their presences as a snapshot."""
    for member in data.get("members", []):
        save_member(session, data["guild_id"], member)
    for presence in data.get("presences") or []:
        save_presence(session, presence, "GUILD_MEMBERS_CHUNK", data["guild_id"])


def on_role(session: Session, data: Payload) -> None:
    """GUILD_ROLE_CREATE / GUILD_ROLE_UPDATE."""
    upsert(session, db.Role, data["role"], guild_id=_int(data["guild_id"]))


def on_role_delete(session: Session, data: Payload) -> None:
    """GUILD_ROLE_DELETE."""
    soft_delete(session, db.Role, id=data["role_id"])


def on_emojis_update(session: Session, data: Payload) -> None:
    """GUILD_EMOJIS_UPDATE."""
    replace_guild_set(session, db.Emoji, data["guild_id"], data["emojis"])


def on_stickers_update(session: Session, data: Payload) -> None:
    """GUILD_STICKERS_UPDATE."""
    replace_guild_set(session, db.Sticker, data["guild_id"], data["stickers"])


def on_user_update(session: Session, data: Payload) -> None:
    """USER_UPDATE."""
    save_user(session, data)


def on_presence_update(session: Session, data: Payload) -> None:
    """PRESENCE_UPDATE."""
    save_presence(session, data, "PRESENCE_UPDATE")


def on_voice_state_update(session: Session, data: Payload) -> None:
    """VOICE_STATE_UPDATE."""
    save_voice_state(session, data, "VOICE_STATE_UPDATE")


def on_message_create(session: Session, data: Payload) -> None:
    """MESSAGE_CREATE."""
    save_message(session, data)


def on_message_update(session: Session, data: Payload) -> None:
    """MESSAGE_UPDATE: the message, and its new content as a revision."""
    save_message(session, data)
    if "content" in data:
        revision = {key: data.get(key) for key in ("channel_id", "guild_id", "content", "edited_timestamp")}
        append(session, db.MessageRevision, revision, message_id=_int(data["id"]))


def on_message_delete(session: Session, data: Payload) -> None:
    """MESSAGE_DELETE."""
    soft_delete(session, db.Message, id=data["id"])


def on_message_delete_bulk(session: Session, data: Payload) -> None:
    """MESSAGE_DELETE_BULK."""
    for message_id in data["ids"]:
        soft_delete(session, db.Message, id=message_id)


def reaction(action: str) -> Handler:
    """Return the handler that appends a reaction event of ``action``."""

    def on_reaction(session: Session, data: Payload) -> None:
        """Append the reaction event, and upsert the member it carries."""
        if (member := data.get("member")) is not None and data.get("guild_id") is not None:
            save_member(session, data["guild_id"], member, user_id=data.get("user_id"))
        append(session, db.ReactionEvent, without(data, "member", "burst_colors"), action=action)

    return on_reaction


def on_typing_start(session: Session, data: Payload) -> None:
    """TYPING_START."""
    if (member := data.get("member")) is not None and data.get("guild_id") is not None:
        save_member(session, data["guild_id"], member, user_id=data["user_id"])
    append(session, db.TypingStart, without(data, "member"))


def on_interaction(session: Session, data: Payload) -> None:
    """INTERACTION_CREATE."""
    append(session, db.InteractionEvent, data)


HANDLERS: dict[str, Handler] = {
    EventName.READY: on_ready,
    EventName.GUILD_CREATE: on_guild_create,
    EventName.GUILD_UPDATE: on_guild_create,
    EventName.GUILD_DELETE: on_guild_delete,
    EventName.CHANNEL_CREATE: on_channel,
    EventName.CHANNEL_UPDATE: on_channel,
    EventName.CHANNEL_DELETE: on_channel_delete,
    EventName.CHANNEL_PINS_UPDATE: on_channel_pins_update,
    EventName.THREAD_CREATE: on_channel,
    EventName.THREAD_UPDATE: on_channel,
    EventName.THREAD_DELETE: on_channel_delete,
    EventName.THREAD_LIST_SYNC: on_thread_list_sync,
    EventName.THREAD_MEMBER_UPDATE: on_thread_member_update,
    EventName.THREAD_MEMBERS_UPDATE: on_thread_members_update,
    EventName.VOICE_CHANNEL_STATUS_UPDATE: on_channel,
    EventName.VOICE_CHANNEL_START_TIME_UPDATE: on_channel,
    EventName.GUILD_MEMBER_ADD: on_member,
    EventName.GUILD_MEMBER_UPDATE: on_member,
    EventName.GUILD_MEMBER_REMOVE: on_member_remove,
    EventName.GUILD_MEMBERS_CHUNK: on_members_chunk,
    EventName.GUILD_ROLE_CREATE: on_role,
    EventName.GUILD_ROLE_UPDATE: on_role,
    EventName.GUILD_ROLE_DELETE: on_role_delete,
    EventName.GUILD_EMOJIS_UPDATE: on_emojis_update,
    EventName.GUILD_STICKERS_UPDATE: on_stickers_update,
    EventName.USER_UPDATE: on_user_update,
    EventName.PRESENCE_UPDATE: on_presence_update,
    EventName.VOICE_STATE_UPDATE: on_voice_state_update,
    EventName.MESSAGE_CREATE: on_message_create,
    EventName.MESSAGE_UPDATE: on_message_update,
    EventName.MESSAGE_DELETE: on_message_delete,
    EventName.MESSAGE_DELETE_BULK: on_message_delete_bulk,
    EventName.MESSAGE_REACTION_ADD: reaction("add"),
    EventName.MESSAGE_REACTION_REMOVE: reaction("remove"),
    EventName.MESSAGE_REACTION_REMOVE_ALL: reaction("remove_all"),
    EventName.MESSAGE_REACTION_REMOVE_EMOJI: reaction("remove_emoji"),
    EventName.TYPING_START: on_typing_start,
    EventName.INTERACTION_CREATE: on_interaction,
}
"""The handler of every event with a wd-discord model."""


def without(payload: Mapping[str, Any], *keys: str) -> Payload:
    """Return ``payload`` without ``keys``."""
    return {key: value for key, value in payload.items() if key not in keys}


def _int(value: object) -> int | None:
    """Return a Discord ID as an int, or ``None``."""
    return None if value is None else int(str(value))
