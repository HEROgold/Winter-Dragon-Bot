from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated

from herogold.supports import IsAnnotated
from pydantic import BaseModel

from wd_discord.oauth import OAuthScopes
from wd_discord.utils.strings import LimitedString


if TYPE_CHECKING:
    from wd_discord import Snowflake
    from wd_discord.image import ImageHash

    from .collectibles import Collectibles
    from .profile import Avatar


class UserPrimaryGuild(BaseModel):
    """https://docs.discord.com/developers/resources/user#user-object-user-primary-guild."""

    identity_guild_id: Snowflake | None = None
    """the id of the user's primary guild"""
    identity_enabled: bool | None = None
    """whether the user is displaying the primary guild's server tag. This can be null if the system clears the identity, e.g. the server no longer supports tags. This will be false if the user manually removes their tag."""
    tag: LimitedString | None = LimitedString(max_length=4)
    """the text of the user's server tag. Limited to 4 characters"""
    badge: ImageHash | None = None
    """the server tag badge hash"""

@dataclass
class User:
    """https://docs.discord.com/developers/resources/user#user-object."""

    id: Annotated[Snowflake, OAuthScopes.IDENTIFY]
    """the user's id"""
    username: Annotated[str, OAuthScopes.IDENTIFY]
    """the user's username, not unique across the platform"""
    discriminator: Annotated[str, OAuthScopes.IDENTIFY]
    """the user's Discord-tag"""
    global_name: Annotated[str | None, OAuthScopes.IDENTIFY]
    """the user's display name, if it is set"""
    avatar: Annotated[str | None, OAuthScopes.IDENTIFY]
    """the user's avatar hash"""
    bot: Annotated[bool | None, OAuthScopes.IDENTIFY]
    """whether the user belongs to an OAuth2 application"""
    system: Annotated[bool | None, OAuthScopes.IDENTIFY]
    """whether the user is an Official Discord System user (part of the urgent message system)"""
    mfa_enabled: Annotated[bool | None, OAuthScopes.IDENTIFY]
    """whether the user has two factor enabled on their account"""
    banner: Annotated[str | None, OAuthScopes.IDENTIFY]
    """the user's banner hash"""
    accent_color: Annotated[int | None, OAuthScopes.IDENTIFY]
    """the user's banner color encoded as an integer representation of hexadecimal color code"""
    locale: Annotated[str | None, OAuthScopes.IDENTIFY]
    """the user's chosen language option"""
    verified: Annotated[bool | None, OAuthScopes.EMAIL]
    """whether the email on this account has been verified"""
    email: Annotated[str | None, OAuthScopes.EMAIL]
    """the user's email"""
    flags: Annotated[int | None, OAuthScopes.IDENTIFY]
    """the flags on a user's account"""
    premium_type: Annotated[int | None, OAuthScopes.IDENTIFY, OAuthScopes.PREMIUM]
    """the type of Nitro subscription on a user's account."""
    public_flags: Annotated[int | None, OAuthScopes.IDENTIFY]
    """the public flags on a user's account"""
    avatar_decoration_data: Annotated[Avatar | None, OAuthScopes.IDENTIFY]
    """data for the user's avatar decoration"""
    collectibles: Annotated[Collectibles | None, OAuthScopes.IDENTIFY]
    """data for the user's collectibles"""
    primary_guild: Annotated[UserPrimaryGuild | None, OAuthScopes.IDENTIFY]
    """the user's primary guild"""

    def validate_scopes(self, allowed_scopes: set[OAuthScopes]) -> bool:
        """Check if the scopes required are enabled."""
        for field in self.__dataclass_fields__.values():
            if isinstance(field, IsAnnotated):
                scopes = field.__metadata__
                if len(scopes) == 1:
                    if scopes[0] not in allowed_scopes:
                        return False
                elif not any(scope in allowed_scopes for scope in scopes):
                    # All scopes are required, but even one is missing, return False
                    return False
        return True
