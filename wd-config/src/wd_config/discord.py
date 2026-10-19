"""Discord-scoped configuration, backed by its own discord.ini file.

discord.ini is internal-only and its existence is the switch: when it is absent the in-code defaults apply and
nothing is written; once it exists (even empty) it is read and confkit fills in any missing defaults.
"""

from __future__ import annotations

lazy from dataclasses import dataclass

lazy from .config import Config
lazy from .constants import DISCORD_CONFIG_FILE


class DiscordConfig[T](Config[T]):
    """Config descriptor scoped to the discord settings file."""


DiscordConfig.bind(DISCORD_CONFIG_FILE, optional=True)


@dataclass
class URLS:
    """Every Discord host the library talks to or links to, and the API version they speak.

    No Discord host is hardcoded outside these settings; URLs are built from them when they're needed.
    """

    base = DiscordConfig("https://discord.com/api")
    """The REST API root, without the version (https://docs.discord.com/developers/reference#api-reference-base-url)."""
    version = DiscordConfig(10)
    """The API version used for both the REST base and the gateway `?v=` query."""
    gateway = DiscordConfig("wss://gateway.discord.gg")
    """The gateway host used when `/gateway/bot` wasn't asked (https://docs.discord.com/developers/topics/gateway#connecting)."""
    cdn = DiscordConfig("https://cdn.discordapp.com")
    """The CDN host images are served from (https://docs.discord.com/developers/reference#image-formatting)."""
    web = DiscordConfig("https://discord.com")
    """The web client host: message jump links and the OAuth2 authorization URL live here."""
    invite = DiscordConfig("https://discord.gg")
    """The host invite links are shared on (https://docs.discord.com/developers/resources/invite)."""

    @property
    def api_version(self) -> str:
        """Get the API version as a string."""
        return f"v{self.version}"

    @property
    def gateway_query(self) -> str:
        """The `?v=...&encoding=json` query appended to a gateway URL (https://docs.discord.com/developers/topics/gateway#connecting)."""
        return f"?v={self.version}&encoding=json"

    @property
    def gateway_url(self) -> str:
        """The default gateway URL: the configured gateway host with the version and encoding query."""
        return f"{self.gateway}/{self.gateway_query}"

    @property
    def oauth2_authorize(self) -> str:
        """The OAuth2 authorization URL bot invites are built on (https://docs.discord.com/developers/topics/oauth2#authorization-url)."""
        return f"{self.web}/oauth2/authorize"


class RestCache:
    """How long a REST read asked to be cached is reused before it's sent again."""

    ttl = DiscordConfig(30.0)
    """Seconds a cached read stays valid; a write under the same guild, channel or user drops it sooner."""


class RateLimit:
    """How the REST client handles Discord's 429 responses."""

    max_retries = DiscordConfig(5)
    """Times a rate-limited request is retried before the 429 is handed back to the caller."""


class UserAgent:
    """The `User-Agent` header the REST client sends, in Discord's `DiscordBot (url, version)` form.

    Discord requires a valid user agent; requests without one may be blocked with a Cloudflare error.
    """

    url = DiscordConfig("https://github.com/HEROgold/WinterDragon")
    """The bot's homepage, the first part of the user agent."""
    version = DiscordConfig("0.1.0")
    """The bot's version, the second part of the user agent."""
