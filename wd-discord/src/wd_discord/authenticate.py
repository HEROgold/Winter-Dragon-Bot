"""Location for all authentication related functions and classes."""
from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from string.templatelib import Template


class Token(str):
    """Represents a Discord bot token."""

    __slots__ = ()

class TokenType(StrEnum):
    """Represents the type of token being used for authentication."""

    BOT = "Bot"
    """Discord's authentication scheme is case-sensitive; it must be ``Bot``, not ``bot``."""

class UserAgentVersion(str):
    """Represents the version of the user agent being used for authentication."""

    __slots__ = ()

class URL(str):
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

def get_bearer(token: Token) -> Template:
    """Get the bearer token header for a given token."""
    return t"Authorization: Bearer {token}"

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
    string parts with the (formatted) interpolation values ourselves.
    """
    parts: list[str] = []
    for item in template:
        if isinstance(item, str):
            parts.append(item)
        else:  # Interpolation
            value = format(item.value, item.format_spec) if item.format_spec else str(item.value)
            parts.append(value)
    return "".join(parts)

def render_header(template: Template) -> tuple[str, str]:
    """Render a ``"Key: Value"`` header template into a ``(name, value)`` pair for httpxyz."""
    name, _, value = render(template).partition(": ")
    return name, value
