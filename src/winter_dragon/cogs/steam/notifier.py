"""DM subscribers the Steam sales they haven't been told about yet."""

lazy from dataclasses import KW_ONLY, dataclass
lazy from typing import TYPE_CHECKING

lazy from herogold.log import LoggerMixin
lazy from wd_discord import is_network_error

lazy from winter_dragon.cogs.steam.models import SaleNotification
lazy from winter_dragon.cogs.steam.pages import build_notification
lazy from winter_dragon.cogs.steam.store import SteamSaleStore


if TYPE_CHECKING:
    lazy from collections.abc import Iterable
    lazy from datetime import datetime

    lazy from sqlalchemy import Engine
    lazy from wd_discord import Client
    lazy from wd_discord.embed import Embed


@dataclass(frozen=True)
class _Delivery:
    """One DM a subscriber is owed, copied out of the session that decided it."""

    user_id: int
    threshold: int
    sales: tuple[tuple[int, str, int], ...]
    """The ``(sale ID, title, discount)`` of each sale the DM names."""
    embed: Embed


@dataclass
class SteamSaleNotifier(LoggerMixin):
    """Sends each subscriber one DM with the sales above their threshold discovered since their last notification."""

    client: Client
    engine: Engine
    _: KW_ONLY
    color: int

    async def notify(self, *, now: datetime, content: str) -> int:
        """DM every subscriber with new sales, with ``content`` above the embed; return how many were notified.

        Reads what each subscriber is owed in one scope, sends the DMs with no session open, then records the
        delivered ones in a second scope: one :class:`SaleNotification` per sale, and a new ``last_notification``.
        A crash between a send and that record sends the same DM again on the next run.

        A subscriber whose DM fails (e.g. DMs closed) keeps their ``last_notification``, so they get the sales on
        a later run instead of losing them.
        """
        with SteamSaleStore.begin(self.engine) as store:
            owed = self._owed(store)
        delivered = [delivery for delivery in owed if await self._send(delivery, content)]
        if delivered:
            with SteamSaleStore.begin(self.engine) as store:
                self._record(store, delivered, now)
        return len(delivered)

    def _owed(self, store: SteamSaleStore) -> list[_Delivery]:
        """Return the DM each subscriber with new sales is owed."""
        users = store.subscribers()
        if not users:
            return []
        # one query for everything any subscriber could be owed, then each subscriber's share is filtered from it
        recent = store.new_since(min(user.last_notification for user in users), 0)
        properties = store.properties(recent)
        owed: list[_Delivery] = []
        for user in users:
            sales = [
                sale
                for sale in recent
                if sale.discovered_at > user.last_notification and sale.sale_percent >= user.sale_threshold
            ]
            if not sales:
                continue
            named = tuple((sale.id, sale.title, sale.sale_percent) for sale in sales if sale.id is not None)
            owed.append(_Delivery(user.id, user.sale_threshold, named, build_notification(sales, properties, color=self.color)))
        return owed

    @staticmethod
    def _record(store: SteamSaleStore, delivered: Iterable[_Delivery], now: datetime) -> None:
        """Log the sales each delivered DM named, and move its subscriber's ``last_notification`` up to ``now``."""
        users = {user.id: user for user in store.subscribers()}
        for delivery in delivered:
            user = users.get(delivery.user_id)
            if user is None:  # unsubscribed while the DM was on its way
                continue
            store.session.add_all(
                SaleNotification(
                    user_id=user.id,
                    sale_id=sale_id,
                    title=title,
                    sale_percent=percent,
                    sale_threshold=delivery.threshold,
                    sent_at=now,
                )
                for sale_id, title, percent in delivery.sales
            )
            user.last_notification = now
            store.session.add(user)

    async def _send(self, delivery: _Delivery, content: str) -> bool:
        """DM the subscriber the notification; ``False`` (after logging) when Discord refused it."""
        message = await self.client.users.partial(delivery.user_id).send(content, embeds=[delivery.embed])
        if is_network_error(message):
            self.logger.warning(t"Could not DM Steam sales to {delivery.user_id}: {message}")
            return False
        return True
