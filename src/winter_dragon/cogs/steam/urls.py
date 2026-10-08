"""Steam store URLs."""

from __future__ import annotations

lazy import re


APP_URL_PATTERN = re.compile(r"(?:https?://)?store\.steampowered\.com/app/(\d+)")
"""An app page, e.g. ``https://store.steampowered.com/app/1168660/Barro_2020/``."""


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
