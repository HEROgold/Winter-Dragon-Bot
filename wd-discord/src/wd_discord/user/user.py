"""https://docs.discord.com/developers/resources/user#user-object."""
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from wd_discord.image import ImageHash
from wd_discord.models import DiscordModel
from wd_discord.oauth import OAuthScopes
from wd_discord.snowflake import Snowflake
from wd_discord.user.collectibles import Collectibles
from wd_discord.user.profile import Avatar


class UserPrimaryGuild(DiscordModel):
    """https://docs.discord.com/developers/resources/user#user-object-user-primary-guild."""

    identity_guild_id: Snowflake | None = None
    """the id of the user's primary guild"""
    identity_enabled: bool | None = None
    """whether the user is displaying the primary guild's server tag.

    Null if the system clears the identity (e.g. the server no longer supports tags); false if the
    user manually removes their tag.
    """
    tag: str | None = Field(default=None, max_length=4)
    """the text of the user's server tag. Limited to 4 characters"""
    badge: ImageHash | None = None
    """the server tag badge hash"""


class User(DiscordModel):
    """https://docs.discord.com/developers/resources/user#user-object."""

    id: Annotated[Snowflake, OAuthScopes.IDENTIFY]
    """the user's id"""
    username: Annotated[str, OAuthScopes.IDENTIFY]
    """the user's username, not unique across the platform"""
    discriminator: Annotated[str, OAuthScopes.IDENTIFY]
    """the user's Discord-tag"""
    global_name: Annotated[str | None, OAuthScopes.IDENTIFY] = None
    """the user's display name, if it is set"""
    avatar: Annotated[ImageHash | None, OAuthScopes.IDENTIFY] = None
    """the user's avatar hash"""
    bot: Annotated[bool | None, OAuthScopes.IDENTIFY] = None
    """whether the user belongs to an OAuth2 application"""
    system: Annotated[bool | None, OAuthScopes.IDENTIFY] = None
    """whether the user is an Official Discord System user (part of the urgent message system)"""
    mfa_enabled: Annotated[bool | None, OAuthScopes.IDENTIFY] = None
    """whether the user has two factor enabled on their account"""
    banner: Annotated[ImageHash | None, OAuthScopes.IDENTIFY] = None
    """the user's banner hash"""
    accent_color: Annotated[int | None, OAuthScopes.IDENTIFY] = None
    """the user's banner color encoded as an integer representation of hexadecimal color code"""
    locale: Annotated[str | None, OAuthScopes.IDENTIFY] = None
    """the user's chosen language option"""
    verified: Annotated[bool | None, OAuthScopes.EMAIL] = None
    """whether the email on this account has been verified"""
    email: Annotated[str | None, OAuthScopes.EMAIL] = None
    """the user's email"""
    flags: Annotated[int | None, OAuthScopes.IDENTIFY] = None
    """the flags on a user's account"""
    premium_type: Annotated[int | None, OAuthScopes.IDENTIFY, OAuthScopes.PREMIUM] = None
    """the type of Nitro subscription on a user's account."""
    public_flags: Annotated[int | None, OAuthScopes.IDENTIFY] = None
    """the public flags on a user's account"""
    avatar_decoration_data: Annotated[Avatar | None, OAuthScopes.IDENTIFY] = None
    """data for the user's avatar decoration"""
    collectibles: Annotated[Collectibles | None, OAuthScopes.IDENTIFY] = None
    """data for the user's collectibles"""
    primary_guild: Annotated[UserPrimaryGuild | None, OAuthScopes.IDENTIFY] = None
    """the user's primary guild"""

    def validate_scopes(self, allowed_scopes: set[OAuthScopes]) -> bool:
        """Check that every scope-gated field is covered by ``allowed_scopes``.

        A field is scope-gated when its :class:`~typing.Annotated` metadata carries one or more
        :class:`~wd_discord.oauth.OAuthScopes`. All scopes on such a field must intersect
        ``allowed_scopes``; a field with none is always allowed.
        """
        for field in type(self).model_fields.values():
            scopes = [meta for meta in field.metadata if isinstance(meta, OAuthScopes)]
            if scopes and not any(scope in allowed_scopes for scope in scopes):
                return False
        return True
