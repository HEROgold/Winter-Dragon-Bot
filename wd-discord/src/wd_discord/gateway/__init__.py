"""Discord gateway (WebSocket) support: connection, payload helpers, and sharding."""

lazy from .connection import (
    Gateway,
    GatewayActivity,
    Opcode,
    build_identify,
    build_presence,
    parse_ready,
)
lazy from .dispatch import parse_dispatch
lazy from .events import EventName, GuildCreate, Message, RawEvent, Ready, UnavailableGuild
lazy from .presence import Status
lazy from .sharding import (
    GatewayBotInfo,
    SessionStartLimit,
    ShardManager,
    fetch_gateway_bot,
    identify_batches,
    parse_gateway_bot,
    rate_limit_key,
    shard_id_for_guild,
)


__all__ = [
    "EventName",
    "Gateway",
    "GatewayActivity",
    "GatewayBotInfo",
    "GuildCreate",
    "Message",
    "Opcode",
    "RawEvent",
    "Ready",
    "SessionStartLimit",
    "ShardManager",
    "Status",
    "UnavailableGuild",
    "build_identify",
    "build_presence",
    "fetch_gateway_bot",
    "identify_batches",
    "parse_dispatch",
    "parse_gateway_bot",
    "parse_ready",
    "rate_limit_key",
    "shard_id_for_guild",
]
