"""Embeds and buttons that show Steam sales: the pages of /steam show and the sale DMs."""

from __future__ import annotations

lazy from textwrap import dedent
lazy from typing import TYPE_CHECKING

lazy from wd_config.bot import Settings
lazy from wd_discord.components import ActionRow, Button, ButtonStyle
lazy from wd_discord.embed import MAX_EMBED_CHARACTERS, MAX_EMBED_FIELDS, Embed, EmbedField, EmbedFooter

lazy from winter_dragon.cogs.steam.models import SaleTypes


if TYPE_CHECKING:
    lazy from collections.abc import Mapping, Sequence

    lazy from wd_bot.components import ComponentHandler

    lazy from winter_dragon.cogs.steam.models import SteamSale


ITEMS_PER_PAGE = 5
MAX_FIELD_NAME_LENGTH = 256
"""Discord's limit on an embed field's name."""
HTTP_SCHEMES = ("https://", "http://")
"""The URL schemes Discord renders masked links for."""


def format_sale(sale: SteamSale, properties: set[SaleTypes]) -> str:
    """Describe one sale: link, discount, price, kind, when it was last seen, and an install link for apps."""
    text = dedent(f"""\
        [{sale.title}]({sale.url})
        Sale: {sale.sale_percent}%
        Price: {sale.final_price}
        DLC: {SaleTypes.DLC in properties}
        Bundle: {SaleTypes.BUNDLE in properties}
        Last Checked: <t:{int(sale.update_datetime.timestamp())}:F>""")
    if sale.sale_end is not None:
        text += f"\nSale ends: <t:{int(sale.sale_end.timestamp())}:R>"
    if (app_id := sale.steam_url.app_id) is not None and (install_url := _install_url(app_id)) is not None:
        text += f"\nInstall game: [Click here]({install_url})"
    return text


def _install_url(app_id: int) -> str | None:
    """Return the link installing ``app_id`` through :attr:`Settings.steam_redirect`, or ``None`` without one.

    Discord only renders masked links to http(s) URLs, so a bare ``steam://`` redirect would show as raw markdown.
    """
    redirect = str(Settings.steam_redirect).rstrip("/")
    if not redirect.startswith(HTTP_SCHEMES):
        return None
    return f"{redirect}/install/{app_id}"


def _sale_field(name: str, sale: SteamSale, properties: Mapping[int, set[SaleTypes]]) -> EmbedField:
    """Build the embed field describing ``sale``."""
    return EmbedField(name=name[:MAX_FIELD_NAME_LENGTH], value=format_sale(sale, properties.get(sale.id or 0, set())))


def page_count(total: int) -> int:
    """Return how many /steam show pages ``total`` sales take; at least one."""
    return max(1, -(-total // ITEMS_PER_PAGE))


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
    start = page * ITEMS_PER_PAGE
    on_page = sales[start : start + ITEMS_PER_PAGE]
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
        field = _sale_field(f"Game {index}", sale, properties)
        if Embed(title=title, fields=[*fields, field]).character_count() > MAX_EMBED_CHARACTERS:
            break
        fields.append(field)
    return Embed(title=title, color=color, fields=fields)
