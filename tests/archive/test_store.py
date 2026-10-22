"""Payloads are sorted into columns, child rows and custom data, and written naively but without erasing."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Session, col, select
from wd_db.extension.custom_data import get_custom_data

from archive import models
from archive.mapping import split
from archive.store import append, soft_delete, upsert


MESSAGE = {
    "id": "10",
    "channel_id": "20",
    "author": {"id": "30", "username": "someone"},
    "content": "hello",
    "timestamp": "2026-10-22T00:00:00+00:00",
    "embeds": [{"title": "embed", "footer": {"text": "foot", "unknown": 1}, "fields": [{"name": "a", "value": "b"}]}],
    "mention_roles": ["40", "41"],
    "message_reference": {"message_id": "9"},
    "brand_new_field": True,
}


def rows[T](session: Session, table: type[T]) -> list[T]:
    return list(session.exec(select(table)))


def test_split_sorts_columns_children_and_extra() -> None:
    part = split(models.Message, MESSAGE)

    assert part.values["id"] == 10
    assert part.values["author_id"] == 30
    assert part.values["message_reference_message_id"] == 9
    assert part.values["timestamp"] == datetime(2026, 10, 22, tzinfo=UTC)
    assert set(part.children) == {"embeds", "mention_roles"}
    assert part.extra == {"author": {"username": "someone"}, "brand_new_field": True}


def test_entity_fields_named_like_child_bookkeeping_are_columns() -> None:
    part = split(models.Channel, {"id": "1", "position": 3, "parent_id": "2", "owner_id": "4"})

    assert part.values == {"id": 1, "position": 3, "parent_id": 2, "owner_id": 4}
    assert part.extra == {}


def test_a_child_rows_bookkeeping_is_never_taken_from_the_payload() -> None:
    part = split(models.MessageEmbedField, {"name": "a", "position": 9, "owner_id": "1"})

    assert part.values == {"name": "a"}
    assert part.extra == {"position": 9, "owner_id": "1"}


def test_a_payload_id_never_overwrites_a_child_rows_own_id() -> None:
    part = split(models.MessageAttachment, {"id": "77", "filename": "a.png"})

    assert "id" not in part.values
    assert part.values["discord_id"] == 77


def test_upsert_writes_the_message_its_children_and_custom_data(session: Session) -> None:
    message = upsert(session, models.Message, MESSAGE)

    assert message.content == "hello"
    (embed,) = rows(session, models.MessageEmbed)
    assert (embed.title, embed.footer_text, embed.owner_id, embed.parent_id) == ("embed", "foot", 10, 10)
    (field,) = rows(session, models.MessageEmbedField)
    assert (field.name, field.owner_id, field.parent_id) == ("a", 10, embed.id)
    assert [r.role_id for r in rows(session, models.MessageMentionRole)] == [40, 41]
    assert get_custom_data(session, embed) == {"footer": {"unknown": 1}}
    assert get_custom_data(session, message)["brand_new_field"] is True


def test_a_partial_upsert_keeps_what_it_does_not_carry(session: Session) -> None:
    upsert(session, models.Message, MESSAGE)
    message = upsert(session, models.Message, {"id": "10", "content": "edited", "other_new_field": 1})

    assert message.content == "edited"
    assert message.author_id == 30
    assert len(rows(session, models.MessageEmbed)) == 1
    assert get_custom_data(session, message)["brand_new_field"] is True
    assert get_custom_data(session, message)["other_new_field"] == 1


def test_a_list_in_the_payload_replaces_the_stored_one(session: Session) -> None:
    upsert(session, models.Message, MESSAGE)
    upsert(session, models.Message, {"id": "10", "embeds": [{"title": "new"}]})

    assert [e.title for e in rows(session, models.MessageEmbed)] == ["new"]
    assert rows(session, models.MessageEmbedField) == []


def test_soft_delete_then_upsert_restores(session: Session) -> None:
    upsert(session, models.Message, MESSAGE)
    soft_delete(session, models.Message, id="10")
    deleted = session.get(models.Message, 10)
    assert deleted is not None
    assert deleted.deleted_at is not None

    upsert(session, models.Message, {"id": "10", "content": "back"})
    assert deleted.deleted_at is None


def test_composite_entities_upsert_by_natural_key(session: Session) -> None:
    upsert(session, models.Member, {"nick": "a", "roles": ["1"]}, guild_id=1, user_id=2)
    upsert(session, models.Member, {"nick": "b"}, guild_id=1, user_id=2)

    (member,) = rows(session, models.Member)
    assert member.nick == "b"
    assert [r.role_id for r in rows(session, models.MemberRole)] == [1]


def test_append_adds_a_row_each_time_with_children(session: Session) -> None:
    presence = {
        "status": "online",
        "client_status": {"desktop": "online"},
        "activities": [{"name": "Game", "type": 0, "buttons": ["Join"], "created_at": 5}],
    }
    append(session, models.PresenceUpdate, presence, user_id=2, source="PRESENCE_UPDATE")
    append(session, models.PresenceUpdate, presence, user_id=2, source="PRESENCE_UPDATE")

    assert len(rows(session, models.PresenceUpdate)) == 2
    first = rows(session, models.PresenceUpdate)[0]
    assert first.client_status_desktop == "online"
    activities = session.exec(select(models.Activity).where(col(models.Activity.owner_id) == first.id)).all()
    assert [(a.name, a.activity_created_at) for a in activities] == [("Game", 5)]
    assert [b.label for b in rows(session, models.ActivityButton)] == ["Join", "Join"]
