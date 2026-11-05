"""Reference links: how a dashboard page shows a Discord ID, as the entity's name linking to its card.

A page never prints an ID. It asks :class:`References` for a link and puts that in its context; the template
renders it with the ``reference`` macro from ``_references.html``. When Discord can't name the ID, the link says so
and shows the plain ID instead of an error page.
"""

from dataclasses import dataclass
from enum import StrEnum, auto
lazy from typing import TYPE_CHECKING, Protocol

lazy from anyio import from_thread


if TYPE_CHECKING:
    from collections.abc import Iterable

    from wd_discord.snowflake import Snowflake


class ReferenceKind(StrEnum):
    """What a reference link points at; the path segment of its card is the value."""

    USER = "user"
    CHANNEL = "channel"
    ROLE = "role"
    GUILD = "guild"


class LookupStatus(StrEnum):
    """How asking Discord for an entity's name went."""

    FOUND = auto()
    """Discord named it."""
    UNKNOWN = auto()
    """Discord has no such entity: deleted, or never existed."""
    UNAVAILABLE = auto()
    """Discord couldn't be asked right now: a rate limit, an outage or a missing permission."""


@dataclass(frozen=True)
class Named:
    """What Discord said about one entity: its status, and its name and picture when found."""

    status: LookupStatus
    name: str | None = None
    image_url: str | None = None
    guild_id: "Snowflake | None" = None
    """The guild the entity is in, for a channel or role; ``None`` for a user or guild."""


@dataclass(frozen=True)
class ReferenceLink:
    """One Discord ID as a page shows it: the entity's name linking to its card, or the plain ID with a note."""

    kind: ReferenceKind
    id: "Snowflake"
    status: LookupStatus
    name: str | None = None
    href: str | None = None
    """The card's address; ``None`` when the entity wasn't found, so the page links nowhere."""

    @property
    def label(self) -> str:
        """The entity's name, or the plain ID when there is no name."""
        return self.name if self.name is not None else str(self.id)

    @property
    def note(self) -> str | None:
        """A short remark for a reference that couldn't be named; ``None`` when it could."""
        match self.status:
            case LookupStatus.FOUND:
                return None
            case LookupStatus.UNKNOWN:
                return "Not found on Discord."
            case LookupStatus.UNAVAILABLE:
                return "Couldn't load the name right now."


def card_path(kind: ReferenceKind, id: "Snowflake", guild_id: "Snowflake | None" = None) -> str:  # noqa: A002 - Discord's name for it
    """Return the address of the card of ``id``; a role's includes its ``guild_id``, which Discord needs to fetch it."""
    if kind is ReferenceKind.ROLE:
        if guild_id is None:
            message = "A role's card needs the guild the role is in."
            raise ValueError(message)
        return f"/cards/role/{guild_id}/{id}"
    return f"/cards/{kind}/{id}"


def link(kind: ReferenceKind, id: "Snowflake", named: Named, *, guild_id: "Snowflake | None" = None) -> ReferenceLink:  # noqa: A002 - Discord's name for it
    """Return the reference link for ``id``, given what Discord said about it."""
    if named.status is not LookupStatus.FOUND:
        return ReferenceLink(kind, id, named.status)
    target = guild_id if guild_id is not None else named.guild_id
    return ReferenceLink(kind, id, named.status, named.name, card_path(kind, id, target))


class Directory(Protocol):
    """Asks Discord for the names of entities; the web app's :class:`~winter_dragon.web.discord_lookup.DiscordLookup`."""

    async def users(self, ids: "Iterable[Snowflake]") -> "dict[Snowflake, Named]":
        """Return what Discord says about each user."""
        ...


@dataclass(frozen=True)
class References:
    """Builds the reference links of a page, from a sync page builder that runs in a worker thread.

    ``directory`` is the web app's name lookup; ``None`` (no bot token) makes every link a plain ID.
    """

    directory: Directory | None = None

    def users(self, ids: "Iterable[Snowflake]") -> tuple[ReferenceLink, ...]:
        """Return a reference link for each user ID, in order."""
        wanted = tuple(ids)
        if self.directory is None:
            found: dict[Snowflake, Named] = {}
        else:
            found = from_thread.run(self.directory.users, wanted)
        unavailable = Named(LookupStatus.UNAVAILABLE)
        return tuple(link(ReferenceKind.USER, user, found.get(user, unavailable)) for user in wanted)

    def user(self, id: "Snowflake") -> ReferenceLink:  # noqa: A002 - Discord's name for it
        """Return the reference link of one user."""
        return self.users((id,))[0]
