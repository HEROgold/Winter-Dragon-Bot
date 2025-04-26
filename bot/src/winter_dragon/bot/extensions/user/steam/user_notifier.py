"""Module to Notify users about Steam sales."""
from contextlib import suppress
from textwrap import dedent

from discord import Embed
from winter_dragon.bot.constants import WEBSITE_URL
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.log import LoggerMixin
from winter_dragon.bot.extensions.user.steam.sale_scraper import SteamURL
from winter_dragon.database.tables.steamsale import SteamSale


class SteamSaleNotifier(LoggerMixin):
    """Steam Sale Notifier class."""

    # TODO: don't use list, use Generator.
    def populate_embed(self, embed: Embed, sales: list[SteamSale]) -> Embed:
        """Fill a given embed with sales, and then returns the populated embed."""
        if not sales:
            return embed

        with suppress(AttributeError):
            # Sort on sale percentage (int), so reverse to get highest first
            sales.sort(key=lambda x: x.sale_percent, reverse=True)

        for i, sale in enumerate(sales):
            install_url = f"{WEBSITE_URL}/redirect?redirect_url=steam://install/{SteamURL(sale.url).get_id_from_game_url()}"
            embed_text = f"""
                [{sale.title}]({sale.url})
                Sale: {sale.sale_percent}%
                Price: {sale.final_price}
                Dlc: {sale.is_dlc}
                Bundle: {sale.is_bundle}
                Last Checked: <t:{int(sale.update_datetime.timestamp())}:F>
                Install game: [Click here]({install_url})
            """
            embed.add_field(
                name = f"Game {i+1}",
                value = dedent(embed_text),
                inline = False,
            )
            self.logger.debug(f"Populated embed with: {sale=}")

        # embed size above 6000 characters.
        max_embed_length = 6000
        while len(str(embed.to_dict())) >= max_embed_length:
            self.logger.debug(f"size: {len(str(embed.to_dict()))}, removing to decrease size: {embed.fields[-1]=}")
            embed.remove_field(-1)

        self.logger.debug(f"Returning {embed}")
        return embed


async def setup(_bot: WinterDragon) -> None:
    """Set up function for the Steam Sale Notifier."""
    return
