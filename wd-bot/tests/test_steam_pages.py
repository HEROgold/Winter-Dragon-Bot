"""Unit tests: the /steam show pages, their buttons, and the sale DM embed."""

from __future__ import annotations

from datetime import UTC, datetime

from wd_discord.components import ButtonStyle, components_payload
from wd_discord.embed import MAX_EMBED_CHARACTERS, MAX_EMBED_FIELDS

from winter_dragon.cogs.steam.cog import SteamSales
from winter_dragon.cogs.steam.models import SaleTypes, SteamSale
from winter_dragon.cogs.steam.pages import ITEMS_PER_PAGE, build_notification, build_page, format_sale, page_buttons


NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
COLOR = 0x094D7F


def sale(sale_id: int, *, title: str | None = None, url: str | None = None) -> SteamSale:
    """Build an unsaved sale."""
    return SteamSale(
        id=sale_id,
        title=title or f"Game {sale_id}",
        url=url or f"https://store.steampowered.com/app/{sale_id}/",
        sale_percent=100,
        final_price=0.0,
        update_datetime=NOW,
        discovered_at=NOW,
    )


def test_format_sale_lists_kind_and_install_link() -> None:
    text = format_sale(sale(10), {SaleTypes.DLC})
    assert "[Game 10](https://store.steampowered.com/app/10/)" in text
    assert "DLC: True" in text
    assert "Bundle: False" in text
    assert f"<t:{int(NOW.timestamp())}:F>" in text
    assert "/install/10)" in text


def test_bundles_get_no_install_link() -> None:
    text = format_sale(sale(555, url="https://store.steampowered.com/bundle/555/"), {SaleTypes.BUNDLE})
    assert "Install game" not in text


def test_build_page_numbers_sales_across_pages() -> None:
    sales = [sale(index) for index in range(12)]
    embed = build_page(sales, {}, page=1, color=COLOR)
    assert embed.fields is not None
    assert [field.name for field in embed.fields] == [f"{index}. Game {index - 1}" for index in range(6, 11)]
    assert embed.footer is not None
    assert embed.footer.text == "Page 2/3 • 12 games total"


def test_build_page_clamps_out_of_range_pages() -> None:
    sales = [sale(index) for index in range(ITEMS_PER_PAGE + 1)]
    assert build_page(sales, {}, page=99, color=COLOR).title == "🎮 Steam Sales - Page 2"
    assert build_page(sales, {}, page=-1, color=COLOR).title == "🎮 Steam Sales - Page 1"


def test_page_buttons_carry_owner_percent_and_target_page() -> None:
    (row,) = page_buttons(SteamSales.show_page, owner_id=3, percent=90, page=0, pages=3)
    previous, counter, following = row.components
    assert [button.custom_id for button in row.components] == ["steam-show:3:90:-1", "steam-show:3:90:0", "steam-show:3:90:1"]
    assert previous.disabled
    assert counter.disabled
    assert counter.label == "1/3"
    assert not following.disabled
    assert all(button.style is ButtonStyle.SECONDARY for button in row.components)
    components_payload([row])  # unique IDs, within Discord's limits


def test_last_page_disables_next() -> None:
    (row,) = page_buttons(SteamSales.show_page, owner_id=3, percent=90, page=2, pages=3)
    assert not row.components[0].disabled
    assert row.components[2].disabled


def test_notification_stops_at_25_fields() -> None:
    embed = build_notification([sale(index) for index in range(40)], {}, color=COLOR)
    assert embed.fields is not None
    assert len(embed.fields) == MAX_EMBED_FIELDS


def test_notification_stays_within_6000_characters() -> None:
    sales = [sale(index, title="x" * 400) for index in range(20)]
    embed = build_notification(sales, {}, color=COLOR)
    assert embed.fields is not None
    assert 0 < len(embed.fields) < len(sales)
    assert embed.character_count() <= MAX_EMBED_CHARACTERS


def test_format_sale_shows_a_known_end_relative_to_now() -> None:
    ending = sale(10)
    ending.sale_end = datetime(2026, 10, 15, 17, tzinfo=UTC)
    assert f"Sale ends: <t:{int(ending.sale_end.timestamp())}:R>" in format_sale(ending, set())
    assert "Sale ends" not in format_sale(sale(11), set())
