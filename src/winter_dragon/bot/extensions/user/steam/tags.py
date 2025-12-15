"""Tags used in Steam HTML pages for scraping purposes."""

DISCOUNT_FINAL_PRICE = "discount_final_price"
DISCOUNT_PERCENT = "discount_pct"
SEARCH_GAME_TITLE = "title"
DATA_APPID = "data-ds-appid"
DISCOUNT_PRICES = "discount_prices"
GAME_BUY_AREA = "game_area_purchase_game_wrapper"
SINGLE_GAME_TITLE = "apphub_AppName"
GAME_RELEVANT = "block responsive_apppage_details_right heading responsive_hidden"
IS_DLC_RELEVANT_TO_YOU = "Is this DLC relevant to you?"
BUNDLE_TITLE = "pageheader"
BUNDLE_LINK = "tab_item_overlay"
BUNDLE_PRICE = "price bundle_final_package_price"
BUNDLE_DISCOUNT = "price bundle_discount"
BUNDLE_FINAL_PRICE = "price bundle_final_price_with_discount"
CURRENCY_LABELS = "-$€£¥₣₹د.كد.ك﷼₻₽₾₺₼₸₴₷฿원₫₮₯₱₳₵₲₪₰()"
BUNDLE_ITEM_CONTAINER = "package_landing_page_item_list"
BUNDLE_ITEM = "tab_item tablet_list_item"

def price_to_num(s: str) -> float:
    """Convert a price string to a float."""
    s = s.strip()
    try:
        return float(s)
    except ValueError:
        return float(s.strip(CURRENCY_LABELS))
