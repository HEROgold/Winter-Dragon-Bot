"""Location where all endpoints to the discord API are stored."""

from __future__ import annotations

lazy from dataclasses import dataclass
lazy from typing import Protocol


class UserInfoHelpers(Protocol):
    """Protocol for URL userinfo helpers."""

    @property
    def username(self) -> str | None:
        """The username component of the URL.

        This method is merely a helper, and *may* not be present
        """

    @property
    def password(self) -> str | None:
        """The password component of the URL.

        This method is merely a helper, and *may* not be present
        """


class URLSpec(Protocol):
    """Protocol for URL schema representation."""

    @property
    def scheme(self) -> str:
        """The scheme of the URL (e.g., 'http', 'https')."""

    @property
    def userinfo(self) -> bytes | None:
        """The userinfo component of the URL.

        Combines username and password, if present, in the format 'username:password'.
        """

    @property
    def host(self) -> str:
        """The host component of the URL."""

    @property
    def port(self) -> int | None:
        """The port component of the URL."""

    @property
    def netloc(self) -> bytes:
        """The network location component of the URL."""

    @property
    def path(self) -> str:
        """The path component of the URL."""

    @property
    def query(self) -> bytes | None:
        """The query component of the URL."""

    @property
    def raw_path(self) -> bytes:
        """The raw path component of the URL."""

    @property
    def fragment(self) -> str | None:
        """The fragment component of the URL."""

    @property
    def params(self) -> object | None:
        """The parameters component of the URL."""


class UrlSpecWithUserInfo(URLSpec, UserInfoHelpers, Protocol):
    """Protocol for URL schema representation with userinfo helpers."""

@dataclass
class Endpoint:
    """Represents a single API endpoint."""

    url: URLSpec
