"""Unit tests: DMing subscribers the Steam sales above their threshold that they haven't seen yet."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session
from wd_discord.errors.api import ApiResponseError
from wd_discord.testing import RecordingClient

from winter_dragon.cogs.steam.models import SteamUsers
from winter_dragon.cogs.steam.notifier import SteamSaleNotifier
from winter_dragon.cogs.steam.scrapers import ScrapedSale
from winter_dragon.cogs.steam.store import SteamSaleStore
from winter_dragon.cogs.steam.urls import SteamURL


if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine


NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
EARLIER = NOW - timedelta(hours=3)
OPEN_DM = "/users/@me/channels"
SEND = "/channels/6/messages"
SENT = {
    "id": "5",
    "channel_id": "6",
    "author": {"id": "2", "username": "bot", "discriminator": "0"},
    "content": "",
    "timestamp": "2026-10-08T12:00:00+00:00",
    "tts": False,
    "mention_everyone": False,
}


@pytest.fixture
def store(engine: Engine) -> Generator[SteamSaleStore]:
    with Session(engine) as session:
        store = SteamSaleStore(session)
        for sale_id, percent in ((1, 100), (2, 60)):
            sale = ScrapedSale(
                id=sale_id,
                title=f"Game {sale_id}",
                url=SteamURL(f"https://store.steampowered.com/app/{sale_id}/"),
                sale_percent=percent,
                final_price=0.0,
            )
            store.record(sale, now=NOW, outdated_after=timedelta(hours=30))
        yield store


def _subscribe(store: SteamSaleStore, user_id: int, threshold: int, last_notification: datetime = EARLIER) -> SteamUsers:
    user = SteamUsers(id=user_id, sale_threshold=threshold, last_notification=last_notification)
    store.session.add(user)
    store.session.commit()
    return user


def _client() -> RecordingClient:
    client = RecordingClient()
    client.reply("POST", OPEN_DM, {"id": "6", "type": 1})
    client.reply("POST", SEND, SENT)
    return client


async def test_subscriber_gets_new_sales_above_their_threshold(store: SteamSaleStore) -> None:
    user = _subscribe(store, 7, threshold=90)
    client = _client()

    notified = await SteamSaleNotifier(client, store, color=0).notify(now=NOW, content="hi")

    assert notified == 1
    assert [sent.json for sent in client.requests_to("POST", OPEN_DM)] == [{"recipient_id": "7"}]
    (message,) = client.requests_to("POST", SEND)
    (embed,) = message.json["embeds"]
    assert message.json["content"] == "hi"
    assert [field["value"].splitlines()[0] for field in embed["fields"]] == ["[Game 1](https://store.steampowered.com/app/1/)"]
    assert user.last_notification == NOW


async def test_subscriber_already_notified_gets_nothing(store: SteamSaleStore) -> None:
    _subscribe(store, 7, threshold=0, last_notification=NOW)
    client = _client()

    assert await SteamSaleNotifier(client, store, color=0).notify(now=NOW, content="hi") == 0

    assert client.sent == []


async def test_failed_dm_keeps_the_sales_for_a_later_run(store: SteamSaleStore) -> None:
    user = _subscribe(store, 7, threshold=0)
    client = _client()
    client.fail("POST", SEND, ApiResponseError(code=50007, message="Cannot send messages to this user"))

    assert await SteamSaleNotifier(client, store, color=0).notify(now=NOW, content="hi") == 0

    assert user.last_notification == EARLIER
