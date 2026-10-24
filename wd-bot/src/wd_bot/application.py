"""The bot's application ID: asked from Discord once at startup, never configured."""

lazy from typing import TYPE_CHECKING, ClassVar

lazy from wd_discord import is_network_error
lazy from wd_errors.startup import StartupError


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
