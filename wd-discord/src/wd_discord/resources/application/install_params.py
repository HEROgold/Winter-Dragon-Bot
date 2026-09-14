"""Discord application install parameters."""

from __future__ import annotations

lazy from wd_discord.models import DiscordModel
lazy from wd_discord.permissions import PermissionsField


class InstallParams(DiscordModel):
    """https://docs.discord.com/developers/resources/application#install-params-object."""

    scopes: list[str]
    """The scopes to add the application to the server with."""
    permissions: PermissionsField
    """The permissions to request for the bot role."""


class ApplicationIntegrationTypeConfig(DiscordModel):
    """https://docs.discord.com/developers/resources/application#application-object-application-integration-type-configuration-object."""

    oauth2_install_params: InstallParams | None = None
    """Install params for each installation context's default in-app authorization link."""
