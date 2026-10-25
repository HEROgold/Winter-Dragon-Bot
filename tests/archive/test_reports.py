"""The reports count changed fields per object, and what wd-discord doesn't model."""

from archive.reports.changing_fields import count_changes
from archive.reports.unmodelled import find_unmodelled


def test_changes_are_counted_per_field_and_a_missing_field_is_no_change() -> None:
    events = [
        ("CHANNEL_CREATE", {"id": "1", "type": 0, "name": "general", "topic": "a"}),
        ("CHANNEL_UPDATE", {"id": "1", "type": 0, "name": "general", "topic": "b"}),
        ("CHANNEL_UPDATE", {"id": "1", "type": 0, "name": "chat"}),
        ("CHANNEL_UPDATE", {"id": "2", "type": 0, "name": "other"}),
    ]
    result = count_changes(events)

    assert result.changes == {("Channel", "topic"): 1, ("Channel", "name"): 1}
    assert result.copies["Channel"] == 4


def test_guild_create_contributes_its_members_and_users() -> None:
    member = {"user": {"id": "9", "username": "a"}, "nick": "x", "roles": []}
    renamed = {"user": {"id": "9", "username": "b"}, "nick": "y", "roles": ["1"]}
    result = count_changes(
        [
            ("GUILD_CREATE", {"id": "1", "name": "g", "members": [member]}),
            ("GUILD_CREATE", {"id": "1", "name": "g", "members": [renamed]}),
        ],
    )

    assert result.changes == {("Member", "nick"): 1, ("User", "username"): 1}


def test_unmodelled_events_unknown_fields_and_unparsable_payloads() -> None:
    result = find_unmodelled(
        [
            ("WEBHOOKS_UPDATE", {"guild_id": "1", "channel_id": "2"}),
            ("SOMETHING_NEW", {}),
            ("TYPING_START", {"channel_id": "2", "user_id": "9", "timestamp": 1, "brand_new": True}),
            ("TYPING_START", {"channel_id": "2"}),
        ],
    )

    assert result.events == {"WEBHOOKS_UPDATE": 1, "SOMETHING_NEW": 1}
    assert result.fields == {("TypingStart", "brand_new"): 1}
    assert result.unparsable == {"TYPING_START": 1}
