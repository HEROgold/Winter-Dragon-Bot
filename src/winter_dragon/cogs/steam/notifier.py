"""DM subscribers the Steam sales they haven't been told about yet."""

lazy from dataclasses import KW_ONLY, dataclass
lazy from typing import TYPE_CHECKING

lazy from herogold.log import LoggerMixin
lazy from wd_discord import is_network_error

lazy from winter_dragon.cogs.steam.models import SaleNotification
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

        Each delivered DM logs one :class:`SaleNotification` per sale. The caller commits, so a failed commit
        sends the same DMs again on the next run.

        A subscriber whose DM fails (e.g. DMs closed) keeps their ``last_notification``, so they get the sales on
        a later run instead of losing them.
        """
        notified = 0
        users = self.store.subscribers()
        if not users:
            return notified
        # one query for everything any subscriber could be owed, then each subscriber's share is filtered from it
        recent = self.store.new_since(min(user.last_notification for user in users), 0)
        properties = self.store.properties(recent)
        for user in users:
            sales = [
                sale
                for sale in recent
                if sale.discovered_at > user.last_notification and sale.sale_percent >= user.sale_threshold
            ]
            if not sales:
                continue
            embed = build_notification(sales, properties, color=self.color)
            if await self._send(user, content, embed):
                self.store.session.add_all(
                    SaleNotification(
                        user_id=user.id,
                        sale_id=sale.id,
                        title=sale.title,
                        sale_percent=sale.sale_percent,
                        sale_threshold=user.sale_threshold,
                        sent_at=now,
                    )
                    for sale in sales
                    if sale.id is not None
                )
                user.last_notification = now
                self.store.session.add(user)
                notified += 1
        return notified

    async def _send(self, user: SteamUsers, content: str, embed: Embed) -> bool:
        """DM ``user`` the notification; ``False`` (after logging) when Discord refused it."""
        message = await self.client.users.partial(user.id).send(content, embeds=[embed])
        if is_network_error(message):
            self.logger.warning(t"Could not DM Steam sales to {user.id}: {message}")
            return False
        return True
