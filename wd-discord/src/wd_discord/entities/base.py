"""Bases of the high-level API: client-bound entities and the stores that create them.

wd-discord has three levels, and a consumer picks the one it needs:

- **Transport**: :class:`~wd_discord.client.Client`'s ``request``/``get``/``post``/... plus the pure
  pydantic data models (``wd_discord.resources.*``, ``wd_discord.gateway.events``).
- **Stores**: one per resource kind on the client (``client.users``, ``client.global_commands``, ...).
  A store creates, fetches and lists, since no entity exists yet to act on.
- **Entities**: objects that carry their client, so acting on them needs nothing else
  (``await interaction.defer()``, ``await user.send(...)``, ``await command.delete()``).

A ``Partial*`` entity is an ID-only handle that acts without fetching first. The full entity wraps
the fetched data model, which stays reachable as ``entity.model``.

Every method returns failures as values (:data:`~wd_discord.client.NetworkError`), never raises.
"""

from __future__ import annotations

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING

lazy from wd_discord.client import is_network_error


if TYPE_CHECKING:
    from wd_discord.client import Client, NetworkError, RequestResult
    from wd_discord.models import DiscordModel


@dataclass(frozen=True)
class Store:
    """Client-scoped access point for one resource kind."""

    client: Client


@dataclass(frozen=True)
class Entity[M: DiscordModel]:
    """A Discord object bound to the client that can act on it."""

    client: Client
    model: M
    """The low-level data this entity wraps."""


def parse[M: DiscordModel](result: RequestResult, model: type[M]) -> M | NetworkError:
    """Return the failure in ``result``, or its JSON body validated as ``model``."""
    if is_network_error(result):
        return result
    return model.model_validate(result.json())


def no_content(result: RequestResult) -> NetworkError | None:
    """Return the failure in ``result``, or ``None`` for an endpoint that answers without a body."""
    return result if is_network_error(result) else None
