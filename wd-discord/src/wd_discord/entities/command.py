"""Global application commands (https://docs.discord.com/developers/interactions/application-commands).

Guild-scoped commands are not covered yet; a ``GuildCommandStore`` reached through a guild would mirror
:class:`GlobalCommandStore` with a guild segment in the path.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
lazy from typing import TYPE_CHECKING

lazy from wd_discord.client import is_network_error
lazy from wd_discord.entities.base import Entity, Store, no_content, parse
lazy from wd_discord.interactions import ApplicationCommand
lazy from wd_discord.snowflake import Snowflake


if TYPE_CHECKING:
    from collections.abc import Generator

    from wd_discord.client import Client, NetworkError
    from wd_discord.interactions import ApplicationCommandParams
    from wd_discord.snowflake import SnowflakeLike


class BaseGlobalCommand(ABC):
    """What can be done to a global command knowing only its ID: read it again, edit it, delete it."""

    client: Client

    @property
    @abstractmethod
    def id(self) -> Snowflake:
        """The command's ID."""

    async def _path(self) -> str | NetworkError:
        return await self.client.global_commands.path(self.id)

    async def fetch(self) -> GlobalCommand | NetworkError:
        """GET /applications/{application_id}/commands/{command_id}."""
        path = await self._path()
        if is_network_error(path):
            return path
        return self._bind(parse(await self.client.get(path), ApplicationCommand))

    async def edit(self, params: ApplicationCommandParams) -> GlobalCommand | NetworkError:
        """PATCH /applications/{application_id}/commands/{command_id} - replace the command's definition."""
        path = await self._path()
        if is_network_error(path):
            return path
        return self._bind(parse(await self.client.patch(path, json=params.to_json()), ApplicationCommand))

    async def delete(self) -> NetworkError | None:
        """DELETE /applications/{application_id}/commands/{command_id}."""
        path = await self._path()
        if is_network_error(path):
            return path
        return no_content(await self.client.delete(path, json={}))

    def _bind(self, model: ApplicationCommand | NetworkError) -> GlobalCommand | NetworkError:
        return model if is_network_error(model) else GlobalCommand(self.client, model)


@dataclass(frozen=True)
class PartialGlobalCommand(BaseGlobalCommand):
    """A global command known only by ID, e.g. one stored from an earlier sync."""

    client: Client
    command_id: Snowflake

    @property
    def id(self) -> Snowflake:
        """The command's ID."""
        return self.command_id


class GlobalCommand(Entity[ApplicationCommand], BaseGlobalCommand):
    """A registered global command, as Discord returned it."""

    @property
    def id(self) -> Snowflake:
        """The command's ID."""
        return self.model.id

    @property
    def name(self) -> str:
        """The command's name."""
        return self.model.name

    @property
    def version(self) -> Snowflake:
        """Discord's auto-incrementing version of the definition; changes on every edit."""
        return self.model.version

    @property
    def mention(self) -> str:
        """A clickable mention of the command, as ``</name:id>``."""
        return f"</{self.name}:{self.id}>"


@dataclass(frozen=True)
class GlobalCommandStore(Store):
    """The application's global commands: register, fetch and list them."""

    async def path(self, command_id: SnowflakeLike | None = None) -> str | NetworkError:
        """Return the global-commands route, or one command's, or the failure looking up the application ID."""
        application_id = await self.client.application.id()
        if is_network_error(application_id):
            return application_id
        path = f"/applications/{application_id}/commands"
        return path if command_id is None else f"{path}/{command_id}"

    def partial(self, command_id: SnowflakeLike) -> PartialGlobalCommand:
        """Return a handle on the command ``command_id``, without fetching it."""
        return PartialGlobalCommand(self.client, Snowflake.coerce(command_id))

    async def create(self, params: ApplicationCommandParams) -> GlobalCommand | NetworkError:
        """POST /applications/{application_id}/commands - register a new global command.

        Discord overwrites an existing command of the same name and type instead of adding a second one.
        """
        path = await self.path()
        if is_network_error(path):
            return path
        command = parse(await self.client.post(path, json=params.to_json()), ApplicationCommand)
        return command if is_network_error(command) else GlobalCommand(self.client, command)

    async def fetch(self, command_id: SnowflakeLike) -> GlobalCommand | NetworkError:
        """GET /applications/{application_id}/commands/{command_id}."""
        return await self.partial(command_id).fetch()

    async def fetch_all(self) -> Generator[GlobalCommand] | NetworkError:
        """GET /applications/{application_id}/commands - every registered global command."""
        path = await self.path()
        if is_network_error(path):
            return path
        result = await self.client.get(path)
        if is_network_error(result):
            return result
        return (GlobalCommand(self.client, ApplicationCommand.model_validate(item)) for item in result.json())
