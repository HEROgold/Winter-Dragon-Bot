"""Embeds and buttons that show Steam sales: the pages of /steam show and the sale DMs."""

lazy from textwrap import dedent
lazy from typing import TYPE_CHECKING

lazy from wd_discord.components import ActionRow, Button, ButtonStyle
lazy from wd_discord.embed import (
    MAX_EMBED_CHARACTERS,
    MAX_EMBED_FIELD_NAME_LENGTH,
    MAX_EMBED_FIELD_VALUE_LENGTH,
    MAX_EMBED_FIELDS,
    Embed,
    EmbedField,
    EmbedFooter,
)
lazy from wd_discord.timestamp import DiscordTime

lazy from winter_dragon.cogs.steam.models import SaleTypes
lazy from winter_dragon.cogs.steam.settings import SteamSettings
lazy from winter_dragon.config import Settings
lazy from winter_dragon.redirect_link import RedirectLink, UnsafeLinkError


if TYPE_CHECKING:
    lazy from collections.abc import Mapping, Sequence

    lazy from wd_bot.components import ComponentHandler

    lazy from winter_dragon.cogs.steam.models import SteamSale


HTTP_SCHEMES = ("https://", "http://")
"""The URL schemes Discord renders masked links for."""


def format_sale(sale: SteamSale, properties: set[SaleTypes], *, open_in_steam: bool = False) -> str:
    """Describe one sale: link, discount, price, kind, when it was last seen, and an install link for apps.

    With ``open_in_steam``, also link to the dashboard's redirect page, which opens the sale in the Steam app, if the
    link fits in an embed field.
    """
    text = dedent(f"""\
        [{sale.title}]({sale.url})
        Sale: {sale.sale_percent}%
        Price: {sale.final_price}
        DLC: {SaleTypes.DLC in properties}
        Bundle: {SaleTypes.BUNDLE in properties}
        Last Checked: {DiscordTime(sale.update_datetime):F}""")
    if sale.sale_end is not None:
        text += f"\nSale ends: {DiscordTime(sale.sale_end):R}"
    if (app_id := sale.steam_url.app_id) is not None and (install_url := _install_url(app_id)) is not None:
        text += f"\nInstall game: [Click here]({install_url})"
    if open_in_steam and (open_url := _open_url(sale)) is not None:
        line = f"\nOpen in Steam: [Click here]({open_url})"
        if len(text) + len(line) <= MAX_EMBED_FIELD_VALUE_LENGTH:
            text += line
    return text


def _open_url(sale: SteamSale) -> str | None:
    """Return the redirect page opening ``sale`` in the Steam app, or ``None`` without one.

    Desktops open the page in the Steam client; phones open the store page, which the Steam mobile app handles. There
    is none without an http(s) :attr:`Settings.dashboard_url`, or for a store URL the redirect page would refuse.
    """
    dashboard = str(Settings.dashboard_url)
    if not dashboard.startswith(HTTP_SCHEMES):
        return None
    store = sale.steam_url
    try:
        link = RedirectLink(store.client_url, mobile=store, fallback=store)
    except UnsafeLinkError:
        return None
    return link.on(dashboard)


def _install_url(app_id: int) -> str | None:
    """Return the link installing ``app_id`` through :attr:`SteamSettings.steam_redirect`, or ``None`` without one.

    Discord only renders masked links to http(s) URLs, so a bare ``steam://`` redirect would show as raw markdown.
    """
    redirect = str(SteamSettings.steam_redirect).rstrip("/")
    if not redirect.startswith(HTTP_SCHEMES):
        return None
    return f"{redirect}/install/{app_id}"


def _sale_field(
    name: str,
    sale: SteamSale,
    properties: Mapping[int, set[SaleTypes]],
    *,
    open_in_steam: bool = False,
) -> EmbedField:
    """Build the embed field describing ``sale``."""
    value = format_sale(sale, properties.get(sale.id or 0, set()), open_in_steam=open_in_steam)
    return EmbedField(name=name[:MAX_EMBED_FIELD_NAME_LENGTH], value=value)


def page_count(total: int) -> int:
    """Return how many /steam show pages ``total`` sales take; at least one."""
    return max(1, -(-total // SteamSettings.items_per_page))


def build_page(
    sales: Sequence[SteamSale],
    properties: Mapping[int, set[SaleTypes]],
    *,
    page: int,
    color: int,
) -> Embed:
    """Build page ``page`` (0-based, clamped to the valid range) of the /steam show listing of ``sales``."""
    pages = page_count(len(sales))
    page = min(max(page, 0), pages - 1)
    per_page = SteamSettings.items_per_page
    start = page * per_page
    on_page = sales[start : start + per_page]
    return Embed(
        title=f"🎮 Steam Sales - Page {page + 1}",
        description="New free and discounted games on Steam",
        color=color,
        fields=[_sale_field(f"{start + index}. {sale.title}", sale, properties) for index, sale in enumerate(on_page, 1)],
        footer=EmbedFooter(text=f"Page {page + 1}/{pages} • {len(sales)} games total"),
    )


def page_buttons(handler: ComponentHandler, *, owner_id: int, percent: int, page: int, pages: int) -> list[ActionRow]:
    """Build the previous / page counter / next buttons under page ``page`` of ``pages``.

    Each button's ``custom_id`` carries the listing's owner, percentage and target page, so a click rebuilds the
    page without any stored state. The disabled counter targets the current page, which keeps all three IDs unique.
    """
    return [
        ActionRow(
            components=[
                Button(
                    style=ButtonStyle.SECONDARY,
                    label="◀ Previous",
                    custom_id=handler.custom_id(owner_id, percent, page - 1),
                    disabled=page <= 0,
                ),
                Button(
                    style=ButtonStyle.SECONDARY,
                    label=f"{page + 1}/{pages}",
                    custom_id=handler.custom_id(owner_id, percent, page),
                    disabled=True,
                ),
                Button(
                    style=ButtonStyle.SECONDARY,
                    label="Next ▶",
                    custom_id=handler.custom_id(owner_id, percent, page + 1),
                    disabled=page >= pages - 1,
                ),
            ],
        ),
    ]


def build_notification(sales: Sequence[SteamSale], properties: Mapping[int, set[SaleTypes]], *, color: int) -> Embed:
    """Build the DM embed announcing ``sales``, dropping trailing sales that don't fit Discord's embed limits."""
    title = "🎮 New Steam Sales"
    fields: list[EmbedField] = []
    for index, sale in enumerate(sales[:MAX_EMBED_FIELDS], 1):
        field = _sale_field(f"Game {index}", sale, properties, open_in_steam=True)
        if Embed(title=title, fields=[*fields, field]).character_count() > MAX_EMBED_CHARACTERS:
            break
        fields.append(field)
    return Embed(title=title, color=color, fields=fields)
