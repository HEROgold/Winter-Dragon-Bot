"""Steam store URLs, and the IDs of the store items they point at."""

from __future__ import annotations

lazy import re
lazy from dataclasses import dataclass
lazy from enum import StrEnum


STORE_URL = "https://store.steampowered.com/"
APP_URL_PATTERN = re.compile(r"(?:https?://)?store\.steampowered\.com/app/(\d+)")
"""An app page, e.g. ``https://store.steampowered.com/app/1168660/Barro_2020/``."""
ITEM_URL_PATTERN = re.compile(r"(?:https?://)?store\.steampowered\.com/(app|sub|bundle)/(\d+)")
"""Any store item's page: an app, a package (``/sub/``) or a bundle."""


class StoreItemKind(StrEnum):
    """What a Steam store ID numbers; the value is the key Steam's store APIs take such an ID under."""

    APP = "appid"
    PACKAGE = "packageid"
    BUNDLE = "bundleid"

    @property
    def path(self) -> str:
        """The store URL path segment of this kind's pages."""
        return ITEM_PATHS[self]


ITEM_PATHS = {StoreItemKind.APP: "app", StoreItemKind.PACKAGE: "sub", StoreItemKind.BUNDLE: "bundle"}


@dataclass(frozen=True)
class StoreItemID:
    """One store item: app, package and bundle IDs are separate number ranges, so the kind is part of the ID."""

    kind: StoreItemKind
    id: int

    def as_request(self) -> dict[str, int]:
        """Return this ID the way Steam's store APIs take it, e.g. ``{"appid": 730}``."""
        return {self.kind.value: self.id}

    @property
    def url(self) -> SteamURL:
        """The item's store page."""
        return SteamURL(f"{STORE_URL}{self.kind.path}/{self.id}/")


class SteamURL(str):
    """A Steam store URL."""

    __slots__ = ()

    @property
    def app_id(self) -> int | None:
        """The app ID of an app page URL, or ``None`` for any other page (bundles, subs, search)."""
        match = APP_URL_PATTERN.match(self)
        return int(match[1]) if match else None

    @property
    def is_app(self) -> bool:
        """Whether this URL points at a single app's store page."""
        return self.app_id is not None

    @property
    def is_bundle(self) -> bool:
        """Whether this URL points at a bundle (``/bundle/``) or a package (``/sub/``)."""
        return "/bundle/" in self or "/sub/" in self

    @property
    def store_item(self) -> StoreItemID | None:
        """The store item this URL's page is for, or ``None`` for a page that isn't one item's."""
        if not (match := ITEM_URL_PATTERN.match(self)):
            return None
        kind = next(kind for kind, path in ITEM_PATHS.items() if path == match[1])
        return StoreItemID(kind, int(match[2]))
