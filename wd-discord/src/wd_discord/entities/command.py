"""Global application commands (https://docs.discord.com/developers/interactions/application-commands).

Reached through the application, like Discord's route: ``client.application.commands``. Guild-scoped commands
are not covered yet; a ``GuildCommandStore`` on a guild (``guild.commands``) would mirror
:class:`GlobalCommandStore` with a guild segment in the path.
"""

from __future__ import annotations

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, override

lazy from wd_discord.client import is_network_error
lazy from wd_discord.entities.base import ClientBound, Entity, EntityStore, Partial, no_content
lazy from wd_discord.interactions import ApplicationCommand


if TYPE_CHECKING:
    from collections.abc import Generator

    from wd_discord.client import NetworkError
    from wd_discord.interactions import ApplicationCommandParams
    from wd_discord.snowflake import Snowflake, SnowflakeLike


class BaseGlobalCommand(ClientBound):
    """What can be done to a global command knowing only its ID: read it again, edit it, delete it."""

    if TYPE_CHECKING:

        @property
        def id(self) -> Snowflake:
            """The ID this object acts on."""

    async def _path(self) -> str | NetworkError:
        return await self.client.application.commands.path(self.id)

    async def fetch(self) -> GlobalCommand | NetworkError:
        """GET /applications/{application_id}/commands/{command_id}."""
        path = await self._path()
        if is_network_error(path):
            return path
        return self._entity(await self.client.get(path), ApplicationCommand, GlobalCommand)

    async def edit(self, params: ApplicationCommandParams) -> GlobalCommand | NetworkError:
        """PATCH /applications/{application_id}/commands/{command_id} - replace the command's definition."""
        path = await self._path()
        if is_network_error(path):
            return path
        return self._entity(await self.client.patch(path, json=params.to_json()), ApplicationCommand, GlobalCommand)

    async def delete(self) -> NetworkError | None:
        """DELETE /applications/{application_id}/commands/{command_id}."""
        path = await self._path()
        if is_network_error(path):
            return path
        return no_content(await self.client.delete(path, json={}))


class GlobalCommand(Entity[ApplicationCommand], BaseGlobalCommand):
    """A registered global command, as Discord returned it."""

    @property
    @override
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


class PartialGlobalCommand(BaseGlobalCommand, Partial[GlobalCommand]):
    """A global command known only by ID, e.g. one stored from an earlier sync."""


@dataclass(frozen=True)
class GlobalCommandStore(EntityStore[PartialGlobalCommand]):
    """The application's global commands: register, fetch and list them."""

    async def path(self, command_id: SnowflakeLike | None = None) -> str | NetworkError:
        """Return the global-commands route, or one command's, or the failure looking up the application ID."""
        application_id = await self.client.application.id()
        if is_network_error(application_id):
            return application_id
        path = f"/applications/{application_id}/commands"
        return path if command_id is None else f"{path}/{command_id}"

    async def create(self, params: ApplicationCommandParams) -> GlobalCommand | NetworkError:
        """POST /applications/{application_id}/commands - register a new global command.

        Discord overwrites an existing command of the same name and type instead of adding a second one.
        """
        path = await self.path()
        if is_network_error(path):
            return path
        return self._entity(await self.client.post(path, json=params.to_json()), ApplicationCommand, GlobalCommand)

    async def fetch_all(self) -> Generator[GlobalCommand] | NetworkError:
        """GET /applications/{application_id}/commands - every registered global command."""
        path = await self.path()
        if is_network_error(path):
            return path
        return self._entities(await self.client.get(path), ApplicationCommand, GlobalCommand)
