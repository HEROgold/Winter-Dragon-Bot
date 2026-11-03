"""The bot's application ID and owners: asked from Discord once at startup, never configured."""

lazy from typing import TYPE_CHECKING, ClassVar

lazy from wd_discord import is_network_error
lazy from wd_errors.startup import StartupError

lazy from wd_bot.checks import owner_ids


if TYPE_CHECKING:
    lazy from wd_discord import Client
    lazy from wd_discord.snowflake import Snowflake


class ApplicationId:
    """The ID of the application the bot token belongs to, kept for the rest of the process.

    The bot's user shares this ID; OAuth2 calls it the client ID.
    """

    value: ClassVar[Snowflake | None] = None
    """The ID, once :meth:`load` fetched it; ``None`` before that."""

    @classmethod
    async def load(cls, client: Client) -> Snowflake:
        """Fetch the ID of ``client``'s application, keep it in :attr:`value` and return it.

        Raises:
            StartupError: Discord didn't answer with the application.

        """
        application_id = await client.application.id()
        if is_network_error(application_id):
            msg = "Failed to get the application from Discord API"
            raise StartupError(msg)
        cls.value = application_id
        return application_id

    @classmethod
    def get(cls) -> Snowflake:
        """Return the ID :meth:`load` fetched.

        Raises:
            RuntimeError: :meth:`load` hasn't run in this process.

        """
        if cls.value is None:
            msg = "The application ID isn't known until ApplicationId.load() has run."
            raise RuntimeError(msg)
        return cls.value


class ApplicationOwners:
    """The users owning the bot's application, asked from Discord once at startup, for a process without a gateway.

    The bot itself asks each time (:func:`~wd_bot.checks.is_owner`); the dashboard can't afford a request per page, so
    it reads these. A change to the application's team shows after a restart.
    """

    value: ClassVar[frozenset[Snowflake]] = frozenset()
    """The owners' IDs, once :meth:`load` fetched them; empty before that, so no one is an owner."""

    @classmethod
    async def load(cls, client: Client) -> frozenset[Snowflake]:
        """Fetch who owns ``client``'s application, keep their IDs in :attr:`value` and return them.

        Raises:
            StartupError: Discord didn't answer with the application.

        """
        application = await client.application.fetch()
        if is_network_error(application):
            msg = "Failed to get the application from Discord API"
            raise StartupError(msg)
        cls.value = frozenset(owner_ids(application))
        return cls.value
