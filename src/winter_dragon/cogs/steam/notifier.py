"""DM subscribers the Steam sales they haven't been told about yet."""

from __future__ import annotations

lazy from dataclasses import KW_ONLY, dataclass
lazy from typing import TYPE_CHECKING

lazy from herogold.log import LoggerMixin
lazy from wd_discord.client import is_network_error

lazy from winter_dragon.cogs.steam.pages import build_notification


if TYPE_CHECKING:
    lazy from datetime import datetime

    lazy from wd_discord import Client
    lazy from wd_discord.embed import Embed

    lazy from winter_dragon.cogs.steam.models import SteamUsers
    lazy from winter_dragon.cogs.steam.store import SteamSaleStore


@dataclass
class SteamSaleNotifier(LoggerMixin):
    """Sends each subscriber one DM with the sales above their threshold discovered since their last notification."""

    client: Client
    store: SteamSaleStore
    _: KW_ONLY
    color: int

    async def notify(self, *, now: datetime, content: str) -> int:
        """DM every subscriber with new sales, with ``content`` above the embed; return how many were notified.

        A subscriber whose DM fails (e.g. DMs closed) keeps their ``last_notification``, so they get the sales on
        a later run instead of losing them.
        """
        notified = 0
        for user in self.store.subscribers():
            sales = self.store.new_since(user.last_notification, user.sale_threshold)
            if not sales:
                continue
            embed = build_notification(sales, self.store.properties(sales), color=self.color)
            if await self._send(user, content, embed):
                user.last_notification = now
                self.store.session.add(user)
                self.store.session.commit()
                notified += 1
        return notified

    async def _send(self, user: SteamUsers, content: str, embed: Embed) -> bool:
        """DM ``user`` the notification; ``False`` (after logging) when Discord refused it."""
        channel = await self.client.create_dm(user.id)
        if is_network_error(channel):
            self.logger.warning(t"Could not open a DM with {user.id}: {channel}")
            return False
        message = await self.client.create_message(str(channel.id), content, embeds=[embed])
        if is_network_error(message):
            self.logger.warning(t"Could not DM Steam sales to {user.id}: {message}")
            return False
        return True
