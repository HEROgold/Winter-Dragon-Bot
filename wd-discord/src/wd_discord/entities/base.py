"""Bases of the high-level API: client-bound entities and the stores that create them.

wd-discord has three levels, and a consumer picks the one it needs:

- **Transport**: :class:`~wd_discord.client.Client`'s ``request``/``get``/``post``/... plus the pure
  pydantic data models (``wd_discord.resources.*``, ``wd_discord.gateway.events``).
- **Stores**: one per resource kind (``client.users``, ``client.application.commands``, ...).
  A store creates, fetches and lists, since no entity exists yet to act on.
- **Entities**: objects that carry their client, so acting on them needs nothing else
  (``await interaction.defer()``, ``await user.send(...)``, ``await command.delete()``).

A :class:`Partial` entity is an ID-only handle that acts without fetching first. The full entity wraps
the fetched data model, which stays reachable as ``entity.model``.

Every method returns failures as values (:data:`~wd_discord.client.NetworkError`), never raises; a response that
can't be read as the expected model is a failure too (:data:`~wd_discord.errors.JsonErrorCode.GENERAL_ERROR`).

Entities expose their IDs and the actions they take; read the rest of what Discord sent from ``entity.model``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, Any, Protocol

lazy from herogold.errors import with_known_exception
lazy from herogold.log import getLogger

lazy from wd_discord.client import is_network_error
lazy from wd_discord.errors import ApiResponseError, JsonErrorCode
lazy from wd_discord.snowflake import Snowflake


if TYPE_CHECKING:
    from collections.abc import Generator

    from httpxyz import Response

    from wd_discord.client import Client, NetworkError, RequestResult
    from wd_discord.models import DiscordModel
    from wd_discord.snowflake import SnowflakeLike


logger = getLogger("wd_discord.entities")


@with_known_exception(ValueError)  # an empty or non-JSON body, and pydantic's ValidationError, are ValueErrors
def _validate[M: DiscordModel](response: Response, model: type[M]) -> M:
    return model.model_validate(response.json())


@with_known_exception(ValueError)
def _validate_all[M: DiscordModel](response: Response, model: type[M]) -> list[M]:
    return [model.model_validate(item) for item in response.json()]


def _unreadable(response: Response, model: type[DiscordModel], error: ValueError) -> ApiResponseError:
    """Return the failure of a response that can't be read as ``model``, after logging why."""
    logger.warning(t"Unreadable {model.__name__} response ({response.status_code}): {error}")
    message = f"Discord's {model.__name__} response couldn't be read"
    return ApiResponseError(code=JsonErrorCode.GENERAL_ERROR, message=message, status=response.status_code)


def parse[M: DiscordModel](result: RequestResult, model: type[M]) -> M | NetworkError:
    """Return the failure in ``result``, or its JSON body validated as ``model``; an unreadable body is a failure."""
    if is_network_error(result):
        return result
    parsed = _validate(result, model)
    return _unreadable(result, model, parsed) if isinstance(parsed, ValueError) else parsed


def parse_all[M: DiscordModel](result: RequestResult, model: type[M]) -> list[M] | NetworkError:
    """Return the failure in ``result``, or each item of its JSON array validated as ``model``.

    Validates every item up front, so a bad one is a failure here rather than an error while iterating.
    """
    if is_network_error(result):
        return result
    parsed = _validate_all(result, model)
    return _unreadable(result, model, parsed) if isinstance(parsed, ValueError) else parsed


def no_content(result: RequestResult) -> NetworkError | None:
    """Return the failure in ``result``, or ``None`` for an endpoint that answers without a body."""
    return result if is_network_error(result) else None


@dataclass(frozen=True)
class ClientBound:
    """Something that acts through a client, and wraps what the client returns in entities bound to it."""

    client: Client

    def _entity[M: DiscordModel, E: Entity[Any]](
        self,
        result: RequestResult,
        model: type[M],
        entity: type[E],
    ) -> E | NetworkError:
        """Return the failure in ``result``, or its body validated as ``model`` and wrapped in ``entity``."""
        parsed = parse(result, model)
        return parsed if is_network_error(parsed) else entity(self.client, parsed)

    def _entities[M: DiscordModel, E: Entity[Any]](
        self,
        result: RequestResult,
        model: type[M],
        entity: type[E],
    ) -> Generator[E] | NetworkError:
        """Return the failure in ``result``, or each item of its JSON array as ``model`` wrapped in ``entity``."""
        parsed = parse_all(result, model)
        return parsed if is_network_error(parsed) else (entity(self.client, item) for item in parsed)


@dataclass(frozen=True)
class Store(ClientBound):
    """Client-scoped access point for one resource kind."""


@dataclass(frozen=True)
class Entity[M: DiscordModel](ClientBound):
    """A Discord object bound to the client that can act on it."""

    model: M
    """The low-level data this entity wraps."""


@dataclass(frozen=True)
class Partial[E](ClientBound, ABC):
    """A Discord object known only by ID, which can act without fetching it first.

    A subclass lists its actions' mixin first (``class PartialUser(BaseUser, Partial[User])``), so the mixin's
    :meth:`fetch` is the one that runs.
    """

    id: Snowflake

    @abstractmethod
    async def fetch(self) -> E | NetworkError:
        """Fetch the full entity."""


class _PartialFactory[E](Protocol):
    def partial(self, id: SnowflakeLike, /) -> Partial[E]: ...  # noqa: A002 - mirrors EntityStore.partial


@dataclass(frozen=True)
class EntityStore[P: Partial[object]](Store):
    """A store of one kind of entity that can be handled by ID: ``partial(id)`` and ``fetch(id)``."""

    partial_type: type[P]

    def partial(self, id: SnowflakeLike) -> P:  # noqa: A002 - Discord's name for it
        """Return a handle on the object ``id``, without fetching it."""
        return self.partial_type(self.client, Snowflake.coerce(id))

    async def fetch[E](self: _PartialFactory[E], id: SnowflakeLike) -> E | NetworkError:  # noqa: A002 - Discord's name for it
        """Fetch the object ``id``."""
        return await self.partial(id).fetch()
