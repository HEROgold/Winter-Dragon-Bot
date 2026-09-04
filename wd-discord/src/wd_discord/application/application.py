"""Discord Application object."""

from __future__ import annotations

lazy from wd_discord.guild import Guild
lazy from wd_discord.image import ImageHash
lazy from wd_discord.models import DiscordModel
lazy from wd_discord.snowflake import Snowflake
lazy from wd_discord.user import User

lazy from .install_params import ApplicationIntegrationTypeConfig, InstallParams
lazy from .team import Team


# ``Guild`` lives in the sibling ``guild/`` subpackage, which does NOT import ``application`` -
# so a concrete import is safe (no cycle) and lets pydantic resolve the ``guild`` field directly.
class Application(DiscordModel):
    """https://docs.discord.com/developers/resources/application#application-object."""

    id: Snowflake
    """The id of the app."""
    name: str
    """The name of the app."""
    icon: ImageHash | None
    """The icon hash of the app."""
    description: str
    """The description of the app."""
    rpc_origins: list[str] | None = None
    """An array of rpc origin urls, if rpc is enabled."""
    bot_public: bool
    """When false, only the app owner can add the app to guilds."""
    bot_require_code_grant: bool
    """When true, the app's bot will only join upon completion of the full oauth2 code grant flow."""
    bot: User | None = None
    """Partial user object for the bot user associated with the app."""
    terms_of_service_url: str | None = None
    """The url of the app's terms of service."""
    privacy_policy_url: str | None = None
    """The url of the app's privacy policy."""
    owner: User | None = None
    """Partial user object for the owner of the app."""
    verify_key: str
    """The hex encoded key for verification in interactions and the gamesdk's getticket."""
    team: Team | None
    """If the app belongs to a team, this will be a list of the members of that team."""
    guild_id: Snowflake | None = None
    """Guild associated with the app. For example, a developer support server."""
    guild: Guild | None = None
    """Partial object of the associated guild."""
    primary_sku_id: Snowflake | None = None
    """If this app is a game sold on Discord, this field will be the id of the 'Game SKU' that is created, if exists."""
    slug: str | None = None
    """If this app is a game sold on Discord, this field will be the URL slug that links to the store page."""
    cover_image: ImageHash | None = None
    """The app's default rich presence invite cover image hash."""
    flags: int | None = None
    """The app's public flags."""
    approximate_guild_count: int | None = None
    """An approximate count of guilds the app has been added to."""
    approximate_user_install_count: int | None = None
    """An approximate count of users that have installed the app."""
    redirect_uris: list[str] | None = None
    """An array of redirect uris for the app."""
    interactions_endpoint_url: str | None = None
    """The interactions endpoint url for the app."""
    role_connections_verification_url: str | None = None
    """The role connection verification url for the app."""
    event_webhooks_url: str | None = None
    """The event webhooks url for the app to receive webhook events."""
    event_webhooks_status: int | None = None
    """If webhook events are enabled for the app."""
    event_webhooks_types: list[str] | None = None
    """List of Webhook event types the app subscribes to."""
    tags: list[str] | None = None
    """List of tags describing the content and functionality of the app. Max of 5 tags."""
    install_params: InstallParams | None = None
    """Settings for the app's default in-app authorization link, if enabled."""
    integration_types_config: dict[str, ApplicationIntegrationTypeConfig] | None = None
    """The default scopes and permissions for each supported installation context."""
    custom_install_url: str | None = None
    """The default custom authorization url for the app, if enabled."""
