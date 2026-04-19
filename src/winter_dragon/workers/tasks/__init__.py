"""Worker tasks for distributed processing."""

from __future__ import annotations

from .steam_scraper import scrape_single_game, scrape_steam_sales


__all__ = [
    "scrape_single_game",
    "scrape_steam_sales",
]
