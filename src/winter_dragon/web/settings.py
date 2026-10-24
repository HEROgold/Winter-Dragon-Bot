"""The dashboard's config scope, in ``dashboard.ini``; only the web process defines it, so the bot never asks for it."""

from uuid import uuid4
lazy from pathlib import Path

lazy from wd_config import Config
lazy from wd_config.parser import required


DASHBOARD_CONFIG_FILE = Path("dashboard.ini")


class DashboardConfig[T](Config[T]):
    """Config descriptor scoped to the dashboard settings file."""


DashboardConfig.bind(DASHBOARD_CONFIG_FILE, operator=True)


class DashboardSettings:
    """Where the dashboard is served, and how it signs people in with Discord."""

    host = DashboardConfig("127.0.0.1")
    """The address the web server listens on; ``0.0.0.0`` inside a container."""
    port = DashboardConfig(8001)
    """The port the web server listens on."""
    public_url = DashboardConfig("http://localhost:8001")
    """The address people open the dashboard on; its ``/auth/discord/callback`` must be one of the application's OAuth2
    redirects in the Discord developer portal."""
    client_secret = DashboardConfig(required("https://discord.com/developers/applications/<application_id>/oauth2"))
    """The application's OAuth2 client secret; the client ID is the bot's application ID, fetched at startup."""
    session_secret = DashboardConfig(uuid4().hex)
    """The key session cookies are signed with: any long random string. Changing it signs everyone out."""
    session_days = DashboardConfig(14)
    """Days a sign-in lasts."""

    @classmethod
    def https_only(cls) -> bool:
        """Whether the dashboard is served over HTTPS, so its session cookie is only ever sent over it."""
        return cls.public_url.startswith("https://")
