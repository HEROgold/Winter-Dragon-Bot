"""A dispatch reaching the archive's gateway is queued raw and typed, and both end up in the database."""

import asyncio
from typing import TYPE_CHECKING, cast

from sqlmodel import Session, select
from wd_discord.intents import Intents

from archive import models as db
from archive.gateway import ArchiveGateway
from archive.writer import Writer


if TYPE_CHECKING:
    from sqlalchemy import Engine
    from wd_discord.gateway.connection import GatewayFrame


def test_a_dispatch_is_stored_raw_and_typed(engine: Engine) -> None:
    async def receive() -> Writer:
        writer = Writer(engine)
        gateway = ArchiveGateway("token", intents=Intents.none(), writer=writer)
        frame = {"op": 0, "t": "TYPING_START", "s": 7, "d": {"channel_id": "2", "user_id": "9", "timestamp": 1}}
        await gateway._handle(cast("GatewayFrame", frame), gateway.archive)  # noqa: SLF001 - the frame entry point under test
        return writer

    writer = asyncio.run(receive())
    with Session(engine) as session:
        writer.write(session, [writer.queue.get_nowait() for _ in range(writer.queue.qsize())])

    with Session(engine) as session:
        (raw,) = session.exec(select(db.GatewayEvent)).all()
        assert (raw.name, raw.sequence, raw.payload) == ("TYPING_START", 7, {"channel_id": "2", "user_id": "9", "timestamp": 1})
        (typing,) = session.exec(select(db.TypingStart)).all()
        assert (typing.channel_id, typing.user_id) == (2, 9)
