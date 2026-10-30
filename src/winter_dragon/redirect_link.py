"""Links to the dashboard's ``/redirect`` page, which opens an app link (``steam://...``) Discord won't make clickable.

The bot builds these links and the dashboard serves them, so both read the rules from here: which schemes are refused,
and which query parameters the page takes.
"""

from dataclasses import dataclass
lazy import re
lazy from urllib.parse import urlencode


REDIRECT_PATH = "/redirect"
BLOCKED_SCHEMES = frozenset(
    {
        # Unencrypted.
        "http",
        "ftp",
        "ws",
        "telnet",
        # Run code in, or read through, the dashboard's page.
        "javascript",
        "data",
        "vbscript",
        "file",
        "blob",
        "view-source",
        "jar",
        "mhtml",
        # Windows handlers used to run code or fetch files from an attacker's share.
        "ms-msdt",
        "search",
        "search-ms",
        "ms-officecmd",
        "ms-cxh",
        "ms-cxh-full",
    },
)
"""Schemes the page never opens: unencrypted, able to run code in the dashboard's page, or known to run attacker code."""
FALLBACK_SCHEME = "https"
"""The only scheme a fallback page may have: it opens in the browser, for visitors without the app."""
_SCHEME = re.compile(r"([a-z][a-z0-9+.-]*):", re.IGNORECASE)
"""A URI's scheme, as RFC 3986 spells it, up to its colon."""


class UnsafeLinkError(ValueError):
    """A link the redirect page won't open; the message says why, for the visitor who followed it."""


def _scheme(link: str, name: str) -> str:
    """Return the lowercased scheme of ``link``, the page's ``name`` parameter.

    Raises:
        UnsafeLinkError: ``link`` is empty, holds whitespace or control characters, has no scheme, or a blocked one.

    """
    if not link:
        msg = f"The {name} link is empty."
        raise UnsafeLinkError(msg)
    if not link.isprintable() or any(char.isspace() for char in link):
        msg = f"The {name} link holds spaces or control characters."
        raise UnsafeLinkError(msg)
    if (match := _SCHEME.match(link)) is None:
        msg = f"The {name} link has no scheme, like steam:// or https://."
        raise UnsafeLinkError(msg)
    if (scheme := match[1].lower()) in BLOCKED_SCHEMES:
        msg = f"The {name} link uses {scheme}:, which isn't safe to open."
        raise UnsafeLinkError(msg)
    return scheme


@dataclass(frozen=True)
class RedirectLink:
    """Where the redirect page sends a visitor: ``uri``, ``mobile`` on a phone, and a ``fallback`` page without the app.

    Raises:
        UnsafeLinkError: a link has a blocked or no scheme, or ``fallback`` isn't https.

    """

    uri: str
    mobile: str | None = None
    fallback: str | None = None

    def __post_init__(self) -> None:
        """Refuse any link the page shouldn't open."""
        _scheme(self.uri, "uri")
        if self.mobile is not None:
            _scheme(self.mobile, "mobile")
        if self.fallback is not None and _scheme(self.fallback, "fallback") != FALLBACK_SCHEME:
            msg = "The fallback link has to be an https:// page."
            raise UnsafeLinkError(msg)

    def target(self, *, phone: bool) -> str:
        """Return the link to open: :attr:`mobile` on a phone when there is one, else :attr:`uri`."""
        return self.mobile if phone and self.mobile is not None else self.uri

    def on(self, dashboard_url: str) -> str:
        """Return the URL of this link's redirect page on the dashboard served at ``dashboard_url``."""
        query = {"uri": self.uri, "mobile": self.mobile, "fallback": self.fallback}
        return f"{dashboard_url.rstrip('/')}{REDIRECT_PATH}?{urlencode({k: v for k, v in query.items() if v is not None})}"
