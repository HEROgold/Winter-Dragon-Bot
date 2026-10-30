"""Location for all authentication related functions and classes."""

lazy from base64 import b64encode
lazy from enum import StrEnum
lazy from typing import TYPE_CHECKING, Any, Self, override

lazy from pydantic_core import core_schema


if TYPE_CHECKING:
    lazy from string.templatelib import Template

    lazy from pydantic import GetCoreSchemaHandler
    lazy from pydantic_core import CoreSchema

    lazy from wd_discord.snowflake import SnowflakeLike


class _ModelStr(str):
    """A ``str`` subclass pydantic validates from a plain string and serialises back to one."""

    __slots__ = ()

    @classmethod
    def __get_pydantic_core_schema__(cls, source: type[Any], handler: GetCoreSchemaHandler) -> CoreSchema:
        """Validate a ``str`` and wrap it in ``cls``."""
        return core_schema.no_info_after_validator_function(cls._wrap, core_schema.str_schema())

    @classmethod
    def _wrap(cls, value: str) -> Self:
        return cls(value)


class Token(_ModelStr):
    """A Discord secret: a bot token, an interaction or gateway token, or an OAuth access or refresh token.

    ``repr`` hides the value, so a token never shows up in a log line or a traceback's locals.
    """

    __slots__ = ()

    @override
    def __repr__(self) -> str:
        """Name the type without the secret."""
        return f"{type(self).__name__}(<hidden>)"


class TokenType(StrEnum):
    """Represents the type of token being used for authentication.

    https://docs.discord.com/developers/reference#authentication
    """

    BOT = "Bot"
    """Discord's authentication scheme is case-sensitive; it must be ``Bot``, not ``bot``."""
    BEARER = "Bearer"
    """An OAuth2 access token, acting as the user who granted it."""
    BASIC = "Basic"
    """The application's :func:`client_credentials`, which OAuth2's token endpoints take."""


class UserAgentVersion(str):
    """Represents the version of the user agent being used for authentication."""

    __slots__ = ()


class URL(_ModelStr):
    """Represents a URL."""

    __slots__ = ()


class MetaData(str):
    """Represents metadata for the user agent."""

    __slots__ = ()


class ContentType(StrEnum):
    """Represents a content type."""

    json = "application/json"
    urlencoded = "application/x-www-form-urlencoded"
    multipart = "multipart/form-data"


def get_auth_header(type_: TokenType, token: Token) -> Template:
    """Get the authorization header for a given token."""
    return t"Authorization: {type_} {token}"


def client_credentials(application_id: SnowflakeLike, secret: Token) -> Token:
    """Return the application's ID and OAuth2 client ``secret`` as the token of :attr:`TokenType.BASIC` auth.

    https://docs.discord.com/developers/topics/oauth2#authorization-code-grant-access-token-exchange-example
    """
    return Token(b64encode(f"{application_id}:{secret}".encode()).decode())


def user_agent(url: URL, version: UserAgentVersion, metadata: MetaData) -> Template:
    """Get the user agent header for a given URL and version."""
    # Client requests that do not have a valid User Agent specified may be blocked and return a Cloudflare error.
    return t"User-Agent: DiscordBot ({url}, {version}) {metadata}"


def content_type(content_type: ContentType) -> Template:
    """Get the content type header for a given content type.

    Failing to do so will result in a 50035 “Invalid form body” error.
    """
    return t"Content-Type: {content_type}"


def render(template: Template) -> str:
    """Render a PEP 750 ``Template`` into a plain string.

    ``str(template)`` does *not* interpolate values, so we interleave the literal
    string parts with the interpolation values, converted (``!r``/``!s``/``!a``) and formatted like an f-string.
    """
    parts: list[str] = []
    for item in template:
        if isinstance(item, str):
            parts.append(item)
        else:  # Interpolation
            value = item.value if item.conversion is None else _CONVERSIONS[item.conversion](item.value)
            parts.append(format(value, item.format_spec))
    return "".join(parts)


_CONVERSIONS = {"r": repr, "s": str, "a": ascii}
"""What an interpolation's ``!r``, ``!s`` or ``!a`` conversion applies before formatting."""


def render_header(template: Template) -> tuple[str, str]:
    """Render a ``"Key: Value"`` header template into a ``(name, value)`` pair for httpxyz."""
    name, _, value = render(template).partition(": ")
    return name, value
