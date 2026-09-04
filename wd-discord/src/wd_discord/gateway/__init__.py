"""Discord gateway (WebSocket) support: connection, payload helpers, and sharding."""
from __future__ import annotations

lazy from .connection import (
    DEFAULT_GATEWAY_URL,
    Gateway,
    GatewayActivity,
    Opcode,
    Ready,
    Status,
    build_identify,
    build_presence,
    parse_ready,
)
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
    "DEFAULT_GATEWAY_URL",
    "Gateway",
    "GatewayActivity",
    "GatewayBotInfo",
    "Opcode",
    "Ready",
    "SessionStartLimit",
    "ShardManager",
    "Status",
    "build_identify",
    "build_presence",
    "fetch_gateway_bot",
    "identify_batches",
    "parse_gateway_bot",
    "parse_ready",
    "rate_limit_key",
    "shard_id_for_guild",
]
