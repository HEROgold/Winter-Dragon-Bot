"""The application behind the client's token (https://docs.discord.com/developers/resources/application)."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from wd_config.bot import Settings

lazy from wd_discord.client import is_network_error
lazy from wd_discord.entities.base import Entity
lazy from wd_discord.entities.command import GlobalCommandStore, GuildCommandStore, PartialGlobalCommand
lazy from wd_discord.entities.entitlement import Entitlement
lazy from wd_discord.entities.guild import Guild, PartialGuild
lazy from wd_discord.entities.user import PartialUser, User
lazy from wd_discord.resources.application import Application as ApplicationModel
lazy from wd_discord.resources.application.team import Team as TeamModel
lazy from wd_discord.resources.application.team import TeamMember as TeamMemberModel
lazy from wd_discord.resources.entitlement import Entitlement as EntitlementModel
lazy from wd_discord.snowflake import Snowflake


if TYPE_CHECKING:
    from collections.abc import Generator

    from wd_discord.client import Client, NetworkError
    from wd_discord.entities.guild import BaseGuild
    from wd_discord.entities.user import BaseUser
    from wd_discord.image import ImageHash
    from wd_discord.resources.application import InstallParams
    from wd_discord.resources.application.team import MembershipState
    from wd_discord.snowflake import SnowflakeLike


class Application(Entity[ApplicationModel]):
    """An application, as Discord returned it."""

    @property
    def id(self) -> Snowflake:
        """The application's ID."""
        return self.model.id

    @property
    def name(self) -> str:
        """The application's name."""
        return self.model.name

    @property
    def description(self) -> str:
        """The application's description."""
        return self.model.description

    @property
    def icon(self) -> ImageHash | None:
        """The application's icon."""
        return self.model.icon

    @property
    def bot(self) -> User | None:
        """The application's bot user."""
        return None if self.model.bot is None else User(self.client, self.model.bot)

    @property
    def owner(self) -> User | None:
        """The user who owns the application; for a team-owned one, a placeholder user for the team."""
        return None if self.model.owner is None else User(self.client, self.model.owner)

    @property
    def team(self) -> Team | None:
        """The team that owns the application, if a team does."""
        return None if self.model.team is None else Team(self.client, self.model.team)

    @property
    def guild(self) -> Guild | PartialGuild | None:
        """The guild linked to the application, such as its support server."""
        if self.model.guild is not None:
            return Guild(self.client, self.model.guild)
        guild_id = self.model.guild_id
        return None if guild_id is None else PartialGuild(self.client, guild_id)

    @property
    def bot_public(self) -> bool:
        """Whether anyone, not only the owner, may add the bot to a guild."""
        return self.model.bot_public

    @property
    def approximate_guild_count(self) -> int | None:
        """Roughly how many guilds the application is in."""
        return self.model.approximate_guild_count

    @property
    def approximate_user_install_count(self) -> int | None:
        """Roughly how many users installed the application."""
        return self.model.approximate_user_install_count

    @property
    def tags(self) -> list[str]:
        """Up to 5 tags describing the application."""
        return self.model.tags or []

    @property
    def install_params(self) -> InstallParams | None:
        """The scopes and permissions of the application's default install link."""
        return self.model.install_params

    @property
    def custom_install_url(self) -> str | None:
        """The application's custom install link, if set."""
        return self.model.custom_install_url

    @property
    def terms_of_service_url(self) -> str | None:
        """The application's terms of service."""
        return self.model.terms_of_service_url

    @property
    def privacy_policy_url(self) -> str | None:
        """The application's privacy policy."""
        return self.model.privacy_policy_url


class Team(Entity[TeamModel]):
    """A developer team that owns applications (https://docs.discord.com/developers/topics/teams)."""

    @property
    def id(self) -> Snowflake:
        """The team's ID."""
        return self.model.id

    @property
    def name(self) -> str:
        """The team's name."""
        return self.model.name

    @property
    def icon(self) -> ImageHash | None:
        """The team's icon."""
        return self.model.icon

    @property
    def members(self) -> Generator[TeamMember]:
        """The team's members, invited ones included."""
        for member in self.model.members:
            yield TeamMember(self.client, member)

    @property
    def owner(self) -> User | PartialUser:
        """The team's owner; in full when they are among its members."""
        member = self.model.owner
        return PartialUser(self.client, self.model.owner_user_id) if member is None else User(self.client, member.user)


class TeamMember(Entity[TeamMemberModel]):
    """A user on a developer team."""

    @property
    def user(self) -> User:
        """The member's user."""
        return User(self.client, self.model.user)

    @property
    def role(self) -> str:
        """The member's role on the team: ``admin``, ``developer`` or ``read_only``."""
        return self.model.role

    @property
    def membership_state(self) -> MembershipState:
        """Whether the member accepted their invitation yet."""
        return self.model.membership_state


class CurrentApplication:
    """The client's own application: its data, its ID (which application-scoped routes need) and its commands."""

    def __init__(self, client: Client, application_id: SnowflakeLike | None = None) -> None:
        """Bind to ``client``; without ``application_id``, the ID is looked up on first use."""
        self.client = client
        self._id = None if application_id is None else Snowflake.coerce(application_id)
        self.commands = GlobalCommandStore(client, PartialGlobalCommand)
        """The application's global commands."""

    async def fetch(self) -> Application | NetworkError:
        """GET /applications/@me - the application object."""
        result = await self.client.get(t"/applications/@me")
        if is_network_error(result):
            return result
        return Application(self.client, ApplicationModel.model_validate(result.json()))

    async def id(self) -> Snowflake | NetworkError:
        """Return the application's ID, fetching and caching it when unknown.

        Prefers a configured ``Settings.application_id``. Otherwise fetches it once with :meth:`fetch` and
        writes it back into ``Settings``, so later clients don't fetch it again.
        """
        if self._id is not None:
            return self._id
        if Settings.application_id:
            self._id = Snowflake.coerce(Settings.application_id)
            return self._id
        application = await self.fetch()
        if is_network_error(application):
            return application
        self._id = application.id
        Settings().application_id = int(application.id)
        return self._id

    def guild_commands(self, guild: BaseGuild) -> GuildCommandStore:
        """Return the store of the application's commands registered in ``guild``."""
        return GuildCommandStore(self.client, guild.id)

    async def fetch_entitlements(
        self,
        *,
        user: BaseUser | None = None,
        guild: BaseGuild | None = None,
        exclude_ended: bool = False,
    ) -> Generator[Entitlement] | NetworkError:
        """GET /applications/{application_id}/entitlements - the application's entitlements, optionally for one owner."""
        application_id = await self.id()
        if is_network_error(application_id):
            return application_id
        params = {"exclude_ended": "true"} if exclude_ended else {}
        if user is not None:
            params["user_id"] = str(user.id)
        if guild is not None:
            params["guild_id"] = str(guild.id)
        result = await self.client.get(t"/applications/{application_id}/entitlements", params=params)
        if is_network_error(result):
            return result
        return (Entitlement(self.client, EntitlementModel.model_validate(item)) for item in result.json())
