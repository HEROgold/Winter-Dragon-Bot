"""Application commands (https://docs.discord.com/developers/interactions/application-commands).

Reached through the application, like Discord's routes: ``client.application.commands`` for global commands,
``client.application.guild_commands(guild)`` for one guild's.
"""

from __future__ import annotations

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, override

lazy from wd_discord.client import is_network_error
lazy from wd_discord.entities.base import ClientBound, Entity, EntityStore, Partial, Store, no_content
lazy from wd_discord.entities.guild import PartialGuild
lazy from wd_discord.interactions import ApplicationCommand
lazy from wd_discord.snowflake import Snowflake


if TYPE_CHECKING:
    from collections.abc import Generator, Iterable
    from string.templatelib import Template

    from wd_discord.client import NetworkError
    from wd_discord.interactions import (
        ApplicationCommandOption,
        ApplicationCommandParams,
        ApplicationCommandType,
        InteractionContextType,
    )
    from wd_discord.permissions import Permissions
    from wd_discord.snowflake import SnowflakeLike


class BaseGlobalCommand(ClientBound):
    """What can be done to a global command knowing only its ID: read it again, edit it, delete it."""

    if TYPE_CHECKING:

        @property
        def id(self) -> Snowflake:
            """The ID this object acts on."""

    async def _path(self) -> Template | NetworkError:
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


class CommandEntity(Entity[ApplicationCommand]):
    """The fields every registered command shares, global or guild."""

    @property
    def id(self) -> Snowflake:
        """The command's ID."""
        return self.model.id

    @property
    def name(self) -> str:
        """The command's name."""
        return self.model.name

    @property
    def description(self) -> str:
        """The command's description; empty for user and message commands."""
        return self.model.description

    @property
    def type(self) -> ApplicationCommandType:
        """Whether it's a slash, user or message command."""
        return self.model.type

    @property
    def options(self) -> list[ApplicationCommandOption]:
        """The command's options, or its subcommands."""
        return self.model.options

    @property
    def default_member_permissions(self) -> Permissions | None:
        """The permissions a member needs to see the command by default; ``None`` for everyone."""
        return self.model.default_member_permissions

    @property
    def nsfw(self) -> bool:
        """Whether the command only shows in age-restricted channels."""
        return self.model.nsfw

    @property
    def contexts(self) -> list[InteractionContextType] | None:
        """Where the command can be used: guilds, the bot's DM, other DMs."""
        return self.model.contexts

    @property
    def version(self) -> Snowflake:
        """Discord's auto-incrementing version of the definition; changes on every edit."""
        return self.model.version

    @property
    def mention(self) -> str:
        """A clickable mention of the command, as ``</name:id>``."""
        return f"</{self.name}:{self.id}>"

    def to_params(self) -> ApplicationCommandParams:
        """Return the definition the command was registered with, to compare or re-register it."""
        return self.model.to_params()


class GlobalCommand(CommandEntity, BaseGlobalCommand):
    """A registered global command, as Discord returned it."""


class PartialGlobalCommand(BaseGlobalCommand, Partial[GlobalCommand]):
    """A global command known only by ID, e.g. one stored from an earlier sync."""


@dataclass(frozen=True)
class GlobalCommandStore(EntityStore[PartialGlobalCommand]):
    """The application's global commands: register, fetch and list them."""

    async def path(self, command_id: SnowflakeLike | None = None) -> Template | NetworkError:
        """Return the global-commands route, or one command's, or the failure looking up the application ID."""
        application_id = await self.client.application.id()
        if is_network_error(application_id):
            return application_id
        path = t"/applications/{application_id}/commands"
        return path if command_id is None else path + t"/{command_id}"

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

    async def overwrite(self, params: Iterable[ApplicationCommandParams]) -> Generator[GlobalCommand] | NetworkError:
        """PUT /applications/{application_id}/commands - replace every global command with ``params``.

        Commands missing from ``params`` are deleted. A command whose name is unchanged keeps its ID.
        """
        path = await self.path()
        if is_network_error(path):
            return path
        body = [command.to_json() for command in params]
        return self._entities(await self.client.put(path, json=body), ApplicationCommand, GlobalCommand)


class BaseGuildCommand(ClientBound):
    """What can be done to a guild command knowing only its guild and ID: read it again, edit it, delete it."""

    if TYPE_CHECKING:

        @property
        def id(self) -> Snowflake:
            """The ID this object acts on."""

        @property
        def guild_id(self) -> Snowflake:
            """The guild the command is registered in."""

    @property
    def guild(self) -> PartialGuild:
        """The guild the command is registered in."""
        return PartialGuild(self.client, self.guild_id)

    async def _path(self) -> Template | NetworkError:
        path = await self.client.application.guild_commands(self.guild).path()
        return path if is_network_error(path) else path + t"/{self.id}"

    async def fetch(self) -> GuildCommand | NetworkError:
        """GET /applications/{application_id}/guilds/{guild_id}/commands/{command_id}."""
        path = await self._path()
        if is_network_error(path):
            return path
        return self._entity(await self.client.get(path), ApplicationCommand, GuildCommand)

    async def edit(self, params: ApplicationCommandParams) -> GuildCommand | NetworkError:
        """PATCH /applications/{application_id}/guilds/{guild_id}/commands/{command_id} - replace the definition."""
        path = await self._path()
        if is_network_error(path):
            return path
        return self._entity(await self.client.patch(path, json=params.to_json()), ApplicationCommand, GuildCommand)

    async def delete(self) -> NetworkError | None:
        """DELETE /applications/{application_id}/guilds/{guild_id}/commands/{command_id}."""
        path = await self._path()
        if is_network_error(path):
            return path
        return no_content(await self.client.delete(path, json={}))


class GuildCommand(CommandEntity, BaseGuildCommand):
    """A command registered in one guild, as Discord returned it."""

    @property
    @override
    def guild_id(self) -> Snowflake:
        """The guild the command is registered in."""
        if self.model.guild_id is None:
            msg = "This guild command was sent without its guild"
            raise ValueError(msg)
        return self.model.guild_id


@dataclass(frozen=True)
class PartialGuildCommand(BaseGuildCommand, Partial[GuildCommand]):
    """A guild command known only by guild and ID."""

    guild_id: Snowflake
    """The guild the command is registered in."""


@dataclass(frozen=True)
class GuildCommandStore(Store):
    """One guild's commands for the application: list them, or replace them all."""

    guild_id: Snowflake

    async def path(self) -> Template | NetworkError:
        """Return the guild-commands route, or the failure looking up the application ID."""
        application_id = await self.client.application.id()
        if is_network_error(application_id):
            return application_id
        return t"/applications/{application_id}/guilds/{self.guild_id}/commands"

    def partial(self, command_id: SnowflakeLike) -> PartialGuildCommand:
        """Return a handle on the guild command ``command_id``, without fetching it."""
        return PartialGuildCommand(self.client, Snowflake.coerce(command_id), self.guild_id)

    async def fetch(self, command_id: SnowflakeLike) -> GuildCommand | NetworkError:
        """GET /applications/{application_id}/guilds/{guild_id}/commands/{command_id}."""
        return await self.partial(command_id).fetch()

    async def create(self, params: ApplicationCommandParams) -> GuildCommand | NetworkError:
        """POST /applications/{application_id}/guilds/{guild_id}/commands - register a command in the guild.

        Discord overwrites an existing command of the same name and type instead of adding a second one.
        """
        path = await self.path()
        if is_network_error(path):
            return path
        return self._entity(await self.client.post(path, json=params.to_json()), ApplicationCommand, GuildCommand)

    async def fetch_all(self) -> Generator[GuildCommand] | NetworkError:
        """GET /applications/{application_id}/guilds/{guild_id}/commands - every command registered in the guild."""
        path = await self.path()
        if is_network_error(path):
            return path
        return self._entities(await self.client.get(path), ApplicationCommand, GuildCommand)

    async def overwrite(self, params: Iterable[ApplicationCommandParams]) -> Generator[GuildCommand] | NetworkError:
        """PUT /applications/{application_id}/guilds/{guild_id}/commands - replace the guild's commands with ``params``.

        Commands missing from ``params`` are deleted. A command whose name is unchanged keeps its ID.
        """
        path = await self.path()
        if is_network_error(path):
            return path
        body = [command.to_json() for command in params]
        return self._entities(await self.client.put(path, json=body), ApplicationCommand, GuildCommand)
