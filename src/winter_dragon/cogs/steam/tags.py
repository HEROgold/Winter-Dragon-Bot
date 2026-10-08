"""The HTML classes and attributes Steam's store pages are scraped by."""

from __future__ import annotations

lazy import re


DISCOUNT_FINAL_PRICE = "discount_final_price"
DISCOUNT_PERCENT = "discount_pct"
SEARCH_GAME_TITLE = "title"
DATA_APPID = "data-ds-appid"
DISCOUNT_PRICES = "discount_prices"
GAME_BUY_AREA = "game_area_purchase_game_wrapper"
ADD_TO_CART = "btn_addtocart"
SINGLE_GAME_TITLE = "apphub_AppName"
DLC_BANNER = "game_area_dlc_bubble"
CURRENCY_LABELS = "-$€£¥₣₹د.كد.ك﷼₻₽₾₺₼₸₴₷฿원₫₮₯₱₳₵₲₪₰() "

SALE_END_TIMESTAMP = re.compile(r"InitDailyDealTimer\(\s*\$DiscountCountdown\s*,\s*(\d+)\s*\)")
"""The exact end of a sale, as a unix timestamp in the countdown script of a buy area."""
SALE_END_DATE = re.compile(r"Offer ends (\d{1,2} [A-Z][a-z]+)")
"""The end date of a sale without a countdown, e.g. ``Offer ends 15 October``."""
SALE_END_HOUR_UTC = 17
"""The hour (UTC) sales end on when Steam only shows a date: 10:00 Pacific during daylight saving time."""


def price_to_num(price: str) -> float:
    """Convert a displayed price such as ``"€4,99"`` or ``"$0.99 USD"`` to a number; ``Free`` is ``0``."""
    cleaned = price.strip().removesuffix("USD").strip(CURRENCY_LABELS).replace(",", ".")
    if not cleaned or cleaned.casefold() == "free":
        return 0.0
    return float(cleaned)
