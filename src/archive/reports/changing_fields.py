"""Which fields of which objects change most often, from the raw events.

Entity tables keep only an object's current state. This report decides which objects deserve their history:
it replays the raw events in order, keeps the last copy of each object, and counts every field whose value
differs from the previous copy. A field missing from a payload is not a change (payloads can be partial).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping


type Payload = Mapping[str, Any]
type Copy = tuple[str, str, Payload]
"""One copy of an object in an event: its kind, its key, and its fields."""


@dataclass
class FieldChanges:
    """Counts of field changes per kind of object."""

    changes: Counter[tuple[str, str]] = field(default_factory=Counter)
    """Changes per (kind, field)."""
    copies: Counter[str] = field(default_factory=Counter)
    """Copies seen per kind, to put the changes in proportion."""
    _last: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)

    def add(self, kind: str, key: str, payload: Payload) -> None:
        """Compare one copy of an object with its previous one, and keep it as the latest."""
        self.copies[kind] += 1
        last = self._last.setdefault((kind, key), {})
        for name, value in payload.items():
            if isinstance(value, list):
                continue
            if name in last and last[name] != value:
                self.changes[kind, name] += 1
            last[name] = value


def count_changes(events: Iterable[tuple[str, Payload]]) -> FieldChanges:
    """Count the field changes across ``events``, given in the order they were received as (name, payload)."""
    result = FieldChanges()
    for name, payload in events:
        for kind, key, copy in copies_in(name, payload):
            result.add(kind, key, copy)
    return result


def copies_in(name: str, data: Payload) -> Iterator[Copy]:  # noqa: C901 - one branch per kind of event, kept flat
    """Yield every object copy event ``name`` carries."""
    if name in ("GUILD_CREATE", "GUILD_UPDATE"):
        guild_id = data["id"]
        yield "Guild", guild_id, data
        for channel in [*data.get("channels", []), *data.get("threads", [])]:
            yield "Channel", channel["id"], channel
        for role in data.get("roles", []):
            yield "Role", role["id"], role
        for member in data.get("members", []):
            yield from _member(guild_id, member)
    elif name in ("CHANNEL_CREATE", "CHANNEL_UPDATE", "THREAD_CREATE", "THREAD_UPDATE"):
        yield "Channel", data["id"], data
    elif name in ("GUILD_ROLE_CREATE", "GUILD_ROLE_UPDATE"):
        yield "Role", data["role"]["id"], data["role"]
    elif name in ("GUILD_MEMBER_ADD", "GUILD_MEMBER_UPDATE"):
        yield from _member(data["guild_id"], data)
    elif name == "USER_UPDATE":
        yield "User", data["id"], data
    elif name == "PRESENCE_UPDATE" and len(data["user"]) > 1:
        yield "User", data["user"]["id"], data["user"]
    elif name in ("MESSAGE_CREATE", "MESSAGE_UPDATE"):
        yield "Message", data["id"], {key: value for key, value in data.items() if key not in ("author", "member")}
        if "author" in data:
            yield "User", data["author"]["id"], data["author"]


def _member(guild_id: str, member: Payload) -> Iterator[Copy]:
    """Yield a member's copy, and its user's when it carries one."""
    user = member.get("user")
    if user is None:
        return
    yield "Member", f"{guild_id}:{user['id']}", {key: value for key, value in member.items() if key != "user"}
    yield "User", user["id"], user


def render(result: FieldChanges, *, limit: int) -> str:
    """Return the ``limit`` most changed fields as a text table."""
    lines = [f"{'object':10} {'field':36} {'changes':>8} {'copies':>8}"]
    for (kind, name), changes in result.changes.most_common(limit):
        lines.append(f"{kind:10} {name:36} {changes:8} {result.copies[kind]:8}")
    if not result.changes:
        lines.append("(no field changed)")
    return "\n".join(lines)
