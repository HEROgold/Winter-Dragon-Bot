"""Cards: one dashboard page per Discord user, channel, role or guild, linked to from reference links.

A card shows what the viewer could already see in Discord or in Winter Dragon's own records, so each kind checks that
first. A viewer with no access, and an ID Discord doesn't know, both get the same "no such card" page, so a card never
reveals that an ID exists. The guilds the viewer shares with the bot come from sign-in (ADR 0006); when they are
missing or stale, the card sends the viewer through a silent sign-in and back.
"""

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING
lazy from urllib.parse import quote

from fastapi import APIRouter, Depends
lazy from fastapi import Request, status
lazy from sqlmodel import Session
lazy from starlette.concurrency import run_in_threadpool
lazy from starlette.responses import Response
lazy from wd_discord.snowflake import Snowflake

lazy from winter_dragon.cogs.team.models import TeamKind
lazy from winter_dragon.cogs.team.service import teams_of
lazy from winter_dragon.web.accounts import SignedIn, session_id, signed_in
lazy from winter_dragon.web.card_access import GuildMember, can_view_channel
lazy from winter_dragon.web.discord_lookup import named_channel, named_guild, named_role, named_user
lazy from winter_dragon.web.references import LookupStatus, Named, ReferenceKind, ReferenceLink, link
lazy from winter_dragon.web.responses import Database, render, see_other


if TYPE_CHECKING:
    from sqlalchemy import Engine

    from winter_dragon.web.discord_lookup import DiscordLookup


router = APIRouter(prefix="/cards", dependencies=[Depends(signed_in)])

LOGIN_PATH = "/auth/discord/login"
NO_SUCH_CARD = "There's no such card, or you can't see it."


@dataclass(frozen=True)
class CardFact:
    """One labelled line of a card."""

    label: str
    value: str


@dataclass(frozen=True)
class Card:
    """What a card page shows: what the entity is called, its picture, facts, related cards and shared teams."""

    kind: ReferenceKind
    title: str
    image_url: str | None = None
    facts: tuple[CardFact, ...] = ()
    related: tuple[tuple[str, ReferenceLink], ...] = ()
    """Cards this one belongs to, such as the guild of a channel, with what each one is to this card."""
    teams: tuple[str, ...] = ()
    """The names of the lasting teams the viewer and a user card's user are both in."""


@dataclass(frozen=True)
class Opened:
    """What a card request starts from: the name lookup, and the guilds the viewer shares with the bot."""

    lookup: DiscordLookup
    guilds: frozenset[Snowflake]


def _notice(request: Request, status_code: int, message: str) -> Response:
    """Render the page that stands in for a card that can't be shown."""
    return render(request, "cards/notice.html", status_code=status_code, message=message)


def _missing(request: Request) -> Response:
    """Render the page for a card that doesn't exist or isn't the viewer's to see."""
    return _notice(request, status.HTTP_404_NOT_FOUND, NO_SUCH_CARD)


def _unanswered(request: Request) -> Response:
    """Render the page for a card whose entity Discord couldn't be asked about."""
    return _notice(request, status.HTTP_503_SERVICE_UNAVAILABLE, "Discord didn't answer. Try again in a moment.")


def _failure(request: Request, lookup_status: LookupStatus) -> Response:
    """Render the notice for a lookup that found nothing."""
    return _missing(request) if lookup_status is LookupStatus.UNKNOWN else _unanswered(request)


def _open(request: Request) -> Opened | Response:
    """Return what the card needs, or the response to give instead: a silent sign-in when the guilds are stale."""
    lookup: DiscordLookup | None = request.app.state.lookup
    if lookup is None:
        return _notice(
            request,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Cards need the bot's Discord token, which this dashboard doesn't have.",
        )
    guilds = request.app.state.shared_guilds.current(session_id(request))
    if guilds is None:
        return see_other(f"{LOGIN_PATH}?next={quote(request.url.path)}")
    return Opened(lookup, guilds)


def _shared_teams(bind: Engine, viewer: Snowflake, subject: Snowflake) -> tuple[str, ...]:
    """Return the names of the lasting teams both members are in."""
    with Session(bind) as session:
        theirs = {team.id for team in teams_of(session, subject)}
        return tuple(team.name for team in teams_of(session, viewer) if team.kind is TeamKind.LASTING and team.id in theirs)


async def _shares_guild(opened: Opened, user: Snowflake) -> bool:
    """Whether ``user`` is a member of any guild the viewer shares with the bot."""
    found = await asyncio.gather(*(opened.lookup.member(guild, user) for guild in opened.guilds))
    return any(member.status is LookupStatus.FOUND for member in found)


def _guild_link(name: str | None, guild_id: Snowflake) -> ReferenceLink:
    """Return the reference link of a guild whose name is already known."""
    named = Named(LookupStatus.FOUND, name) if name is not None else Named(LookupStatus.UNAVAILABLE)
    return link(ReferenceKind.GUILD, guild_id, named)


def _show(request: Request, card: Card) -> Response:
    """Render ``card``."""
    return render(request, "cards/card.html", card=card)


@router.get("/user/{user_id}")
async def user_card(request: Request, user_id: int, account: SignedIn, bind: Database) -> Response:
    """Show a user: to themselves, to someone on a lasting team with them, and to anyone who shares a guild with them."""
    if isinstance((opened := _open(request)), Response):
        return opened
    subject = Snowflake(user_id)
    teams = () if subject == account.id else await run_in_threadpool(_shared_teams, bind, account.id, subject)
    if subject != account.id and not teams and not await _shares_guild(opened, subject):
        return _missing(request)
    fetched = await opened.lookup.user(subject)
    if fetched.entity is None:
        return _failure(request, fetched.status)
    named = named_user(fetched)
    user = fetched.entity
    facts = (CardFact("Username", user.username),)
    if user.bot:
        facts += (CardFact("Account", "Bot"),)
    return _show(request, Card(ReferenceKind.USER, named.name or user.username, named.image_url, facts, teams=teams))


@router.get("/guild/{guild_id}")
async def guild_card(request: Request, guild_id: int) -> Response:
    """Show a guild the viewer shares with the bot."""
    if isinstance((opened := _open(request)), Response):
        return opened
    subject = Snowflake(guild_id)
    if subject not in opened.guilds:
        return _missing(request)
    fetched = await opened.lookup.guild(subject)
    if fetched.entity is None:
        return _failure(request, fetched.status)
    named = named_guild(fetched)
    guild = fetched.entity
    facts = tuple(
        CardFact(label, value)
        for label, value in (
            ("Description", guild.description),
            ("Members", None if guild.approximate_member_count is None else str(guild.approximate_member_count)),
        )
        if value
    )
    return _show(request, Card(ReferenceKind.GUILD, named.name or str(subject), named.image_url, facts))


@router.get("/role/{guild_id}/{role_id}")
async def role_card(request: Request, guild_id: int, role_id: int) -> Response:
    """Show a role of a guild the viewer shares with the bot."""
    if isinstance((opened := _open(request)), Response):
        return opened
    guild = Snowflake(guild_id)
    if guild not in opened.guilds:
        return _missing(request)
    fetched = await opened.lookup.role(guild, Snowflake(role_id))
    if fetched.entity is None:
        return _failure(request, fetched.status)
    role = fetched.entity
    guild_name = named_guild(await opened.lookup.guild(guild)).name
    facts = (
        CardFact("Colour", f"#{role.color:06x}" if role.color else "None"),
        CardFact("Shown separately", "Yes" if role.hoist else "No"),
        CardFact("Managed by an integration", "Yes" if role.managed else "No"),
    )
    related = (("Server", _guild_link(guild_name, guild)),)
    return _show(request, Card(ReferenceKind.ROLE, named_role(fetched).name or str(role.id), None, facts, related))


@router.get("/channel/{channel_id}")
async def channel_card(request: Request, channel_id: int, account: SignedIn) -> Response:
    """Show a channel of a guild the viewer shares with the bot, if the viewer could see it in Discord."""
    if isinstance((opened := _open(request)), Response):
        return opened
    fetched = await opened.lookup.channel(Snowflake(channel_id))
    if fetched.entity is None:
        return _failure(request, fetched.status)
    channel = fetched.entity
    guild_id = None if channel.guild is None else channel.guild.id
    if guild_id is None or guild_id not in opened.guilds or not await _may_see(opened, account.id, guild_id, channel):
        return _missing(request)
    guild_name = named_guild(await opened.lookup.guild(guild_id)).name
    facts = tuple(
        CardFact(label, value)
        for label, value in (
            ("Kind", channel.type.name.replace("_", " ").capitalize()),
            ("Topic", channel.topic),
            ("Age-restricted", "Yes" if channel.nsfw else None),
        )
        if value
    )
    related = (("Server", _guild_link(guild_name, guild_id)),)
    return _show(request, Card(ReferenceKind.CHANNEL, named_channel(fetched).name or str(channel.id), None, facts, related))


async def _may_see(opened: Opened, viewer: Snowflake, guild_id: Snowflake, channel: object) -> bool:
    """Whether the viewer could see ``channel`` in Discord: they are in its guild and hold View Channel there."""
    member, roles, guild = await asyncio.gather(
        opened.lookup.member(guild_id, viewer),
        opened.lookup.roles(guild_id),
        opened.lookup.guild(guild_id),
    )
    if member.entity is None or roles.entity is None or guild.entity is None:
        return False
    who = GuildMember(
        guild_id=guild_id,
        owner_id=guild.entity.owner.id,
        member_id=viewer,
        member_roles=list(member.entity.model.roles),
        role_permissions={role.id: role.permissions for role in roles.entity},
    )
    return can_view_channel(who, [overwrite.model for overwrite in channel.overwrites])  # type: ignore[attr-defined] - a Channel
