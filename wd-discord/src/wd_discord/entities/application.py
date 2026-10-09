"""The application behind the client's token (https://docs.discord.com/developers/resources/application)."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from wd_config.bot import Settings

lazy from wd_discord.client import is_network_error
lazy from wd_discord.entities.base import parse
lazy from wd_discord.entities.command import GlobalCommandStore, GuildCommandStore, PartialGlobalCommand
lazy from wd_discord.resources.application import Application
lazy from wd_discord.snowflake import Snowflake


if TYPE_CHECKING:
    from wd_discord.client import Client, NetworkError
    from wd_discord.snowflake import SnowflakeLike


class CurrentApplication:
    """The client's own application: its data, its ID (which application-scoped routes need) and its commands."""

    def __init__(self, client: Client, application_id: SnowflakeLike | None = None) -> None:
        """Bind to ``client``; without ``application_id``, the ID is looked up on first use."""
        self.client = client
        self._id = None if application_id is None else Snowflake.coerce(application_id)
        self.commands = GlobalCommandStore(client, PartialGlobalCommand)
        """The application's global commands."""

    async def fetch(self) -> Application | NetworkError:
        """GET /applications/@me - the application object."""
        return parse(await self.client.get("/applications/@me"), Application)

    async def id(self) -> Snowflake | NetworkError:
        """Return the application's ID, fetching and caching it when unknown.

        Prefers a configured ``Settings.application_id``. Otherwise fetches it once with :meth:`fetch` and
        writes it back into ``Settings``, so later clients don't fetch it again.
        """
        if self._id is not None:
            return self._id
        if Settings.application_id:
            self._id = Snowflake.coerce(Settings.application_id)
            return self._id
        application = await self.fetch()
        if is_network_error(application):
            return application
        self._id = application.id
        Settings().application_id = int(application.id)
        return self._id

    def guild_commands(self, guild_id: SnowflakeLike) -> GuildCommandStore:
        """Return the store of the application's commands registered in the guild ``guild_id``."""
        return GuildCommandStore(self.client, Snowflake.coerce(guild_id))
