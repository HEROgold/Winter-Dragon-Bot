"""The parts of Steam's store web APIs the sale finder reads.

Field names mirror Steam's ``StoreItem`` messages, as SteamDB documents them in its Protobufs repo
(``webui/service_storebrowse.proto``, ``webui/service_storequery.proto``). Unknown fields are ignored.
"""

from __future__ import annotations

# pydantic resolves field annotations when the models are defined, so these imports can't be lazy.
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from winter_dragon.cogs.steam.urls import STORE_URL, SteamURL, StoreItemID, StoreItemKind


ITEM_KINDS = {0: StoreItemKind.APP, 1: StoreItemKind.PACKAGE, 2: StoreItemKind.BUNDLE}
"""``EStoreItemType``: the kind of store item each ``item_type`` stands for."""
DLC_APP_TYPE = 4
"""The ``EStoreAppType`` of a DLC."""
FOUND = 1
"""The ``success`` (an ``EResult``) of an item Steam knows; other values mean it doesn't (15: no such item)."""


class SteamModel(BaseModel):
    """A part of a Steam store API answer."""

    model_config = ConfigDict(extra="ignore", frozen=True)


class ActiveDiscount(SteamModel):
    """One discount applied to a purchase option."""

    discount_end_date: datetime | None = None


class PurchaseOption(SteamModel):
    """The cheapest way to buy a store item, and the discount it gets."""

    final_price_in_cents: int = 0
    discount_pct: int = 0
    active_discounts: list[ActiveDiscount] = Field(default_factory=list[ActiveDiscount])
    is_free_to_keep: bool = False
    """Whether this is a free giveaway, kept forever when claimed before :attr:`free_to_keep_ends`."""
    free_to_keep_ends: datetime | None = None

    @property
    def discount_end(self) -> datetime | None:
        """When the discount ends: its first discount to run out, or the end of a free giveaway."""
        ends = [discount.discount_end_date for discount in self.active_discounts if discount.discount_end_date is not None]
        if self.free_to_keep_ends is not None:
            ends.append(self.free_to_keep_ends)
        return min(ends, default=None)


class StoreItem(SteamModel):
    """An app, package or bundle on the Steam store."""

    item_type: int = 0
    id: int
    success: int = 0
    name: str = ""
    store_url_path: str = ""
    type: int = 0
    """The ``EStoreAppType`` of an app."""
    best_purchase_option: PurchaseOption | None = None

    @property
    def item_id(self) -> StoreItemID | None:
        """The item's ID, or ``None`` for an ``item_type`` the sale finder doesn't know."""
        kind = ITEM_KINDS.get(self.item_type)
        return None if kind is None else StoreItemID(kind, self.id)

    @property
    def url(self) -> SteamURL | None:
        """The item's store page."""
        if self.store_url_path:
            return SteamURL(f"{STORE_URL}{self.store_url_path}")
        item_id = self.item_id
        return None if item_id is None else item_id.url


class QueryMetadata(SteamModel):
    """How many items a store query matches in total."""

    total_matching_records: int = 0


class QueryResult(SteamModel):
    """One page of ``IStoreQueryService/Query`` results."""

    metadata: QueryMetadata = QueryMetadata()
    store_items: list[StoreItem] = Field(default_factory=list[StoreItem])


class QueryResponse(SteamModel):
    """The answer of ``IStoreQueryService/Query``."""

    response: QueryResult


class ItemsResult(SteamModel):
    """The items ``IStoreBrowseService/GetItems`` looked up."""

    store_items: list[StoreItem] = Field(default_factory=list[StoreItem])


class ItemsResponse(SteamModel):
    """The answer of ``IStoreBrowseService/GetItems``."""

    response: ItemsResult
