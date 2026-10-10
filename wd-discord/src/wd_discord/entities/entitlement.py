"""Entitlements (https://docs.discord.com/developers/resources/entitlement)."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from wd_discord.entities.base import Entity, no_content
lazy from wd_discord.entities.guild import PartialGuild
lazy from wd_discord.entities.user import PartialUser
lazy from wd_discord.resources.entitlement import Entitlement as EntitlementModel


if TYPE_CHECKING:
    from datetime import datetime
    from string.templatelib import Template

    from wd_discord.client import NetworkError
    from wd_discord.resources.entitlement import EntitlementType
    from wd_discord.snowflake import Snowflake


class Entitlement(Entity[EntitlementModel]):
    """A user's or guild's access to one of the application's SKUs."""

    @property
    def id(self) -> Snowflake:
        """The entitlement's ID."""
        return self.model.id

    @property
    def sku_id(self) -> Snowflake:
        """The ID of the SKU it grants."""
        return self.model.sku_id

    @property
    def type(self) -> EntitlementType:
        """How the entitlement was obtained."""
        return self.model.type

    @property
    def user(self) -> PartialUser | None:
        """The user granted access; ``None`` for a guild's entitlement."""
        user_id = self.model.user_id
        return None if user_id is None else PartialUser(self.client, user_id)

    @property
    def guild(self) -> PartialGuild | None:
        """The guild granted access; ``None`` for a user's entitlement."""
        guild_id = self.model.guild_id
        return None if guild_id is None else PartialGuild(self.client, guild_id)

    @property
    def deleted(self) -> bool:
        """Whether the entitlement was deleted."""
        return self.model.deleted

    @property
    def consumed(self) -> bool:
        """Whether a consumable entitlement was used up."""
        return bool(self.model.consumed)

    @property
    def starts_at(self) -> datetime | None:
        """When the entitlement starts being valid."""
        return self.model.starts_at

    @property
    def ends_at(self) -> datetime | None:
        """When the entitlement stops being valid; ``None`` when it doesn't expire."""
        return self.model.ends_at

    @property
    def _path(self) -> Template:
        return t"/applications/{self.model.application_id}/entitlements/{self.id}"

    async def consume(self) -> NetworkError | None:
        """POST /applications/{application_id}/entitlements/{entitlement_id}/consume - mark a consumable as used."""
        return no_content(await self.client.post(self._path + t"/consume", json={}))

    async def delete(self) -> NetworkError | None:
        """DELETE /applications/{application_id}/entitlements/{entitlement_id} - remove a test entitlement."""
        return no_content(await self.client.delete(self._path, json={}))
