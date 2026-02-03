"""Enhanced Steam sales display using pagination."""

from textwrap import dedent

from discord import Embed
from sqlmodel import Session, select

from winter_dragon.bot.core.settings import Settings
from winter_dragon.bot.extensions.user.steam.steam_url import SteamURL
from winter_dragon.bot.ui import EmbedPageSource, Paginator
from winter_dragon.database.tables.steamsale import SaleTypes, SteamSale, SteamSaleProperties


class SteamSalesPageSource(EmbedPageSource):
    """Page source for displaying Steam sales."""

    def __init__(
        self,
        sales: list[SteamSale],
        session: Session,
        items_per_page: int = 5,
        color: int = 0x094D7F,
    ) -> None:
        """Initialize the Steam sales page source."""
        self.sales = sales
        self.session = session
        self.items_per_page = items_per_page
        self.color = color
        self.embeds: list[Embed] = []
        self._build_embeds()

    def _build_embeds(self) -> None:
        """Build paginated embeds from sales."""
        for page_num in range(0, len(self.sales), self.items_per_page):
            page_sales = self.sales[page_num : page_num + self.items_per_page]
            embed = self._create_page_embed(page_sales, page_num // self.items_per_page + 1)
            self.embeds.append(embed)

    def _create_page_embed(self, page_sales: list[SteamSale], page_number: int) -> Embed:
        """Create an embed for a page of sales."""
        embed = Embed(
            title=f"🎮 Steam Sales - Page {page_number}",
            description="New free and discounted games on Steam",
            color=self.color,
        )

        for idx, sale in enumerate(page_sales, 1):
            properties = self.session.exec(
                select(SteamSaleProperties).where(SteamSaleProperties.steam_sale_id == sale.id),
            ).all()

            property_types = {prop.property for prop in properties}

            # Build sales info
            sale_info = self._format_sale_summary(
                sale=sale,
                properties=property_types,
            )

            embed.add_field(
                name=f"{idx}. {sale.title}",
                value=sale_info,
                inline=False,
            )

        total_pages = (len(self.sales) + self.items_per_page - 1) // self.items_per_page
        embed.set_footer(text=f"Page {page_number}/{total_pages} • {len(self.sales)} games total")

        return embed

    def _format_sale_summary(
        self,
        sale: SteamSale,
        *,
        properties: set[SaleTypes],
    ) -> str:
        """Format sale information."""
        app_id = SteamURL(sale.url).app_id
        install_url = f"{Settings.steam_redirect}/install/{app_id}"
        embed_text = f"""
            [{sale.title}]({sale.url})
            Sale: {sale.sale_percent}%
            Price: {sale.final_price}
            DLC: {SaleTypes.DLC in properties}
            Bundle: {SaleTypes.BUNDLE in properties}
            Last Checked: <t:{int(sale.update_datetime.timestamp())}:F>
            Install game: [Click here]({install_url})
        """
        return dedent(embed_text)

    async def get_page(self, page_number: int) -> Embed:
        """Get a page embed."""
        return self.embeds[page_number] if page_number < len(self.embeds) else self.embeds[0]

    async def get_page_count(self) -> int:
        """Get total number of pages."""
        return len(self.embeds)

    async def format_page(self, page_data: Embed, page_number: int) -> tuple[str, Embed]:  # noqa: ARG002
        """Format the page."""
        return "", page_data


async def create_sales_paginator(
    sales: list[SteamSale],
    session: Session,
    color: int = 0x094D7F,
    items_per_page: int = 5,
) -> Paginator:
    """Create a paginator for Steam sales."""
    source = SteamSalesPageSource(
        sales=sales,
        session=session,
        items_per_page=items_per_page,
        color=color,
    )
    return Paginator(source, timeout=300.0)
