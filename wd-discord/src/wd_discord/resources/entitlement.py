"""Discord entitlement model (https://docs.discord.com/developers/resources/entitlement)."""

from __future__ import annotations

from datetime import datetime
lazy from enum import IntEnum

from wd_discord.models import DiscordModel
from wd_discord.snowflake import Snowflake


class EntitlementType(IntEnum):
    """https://docs.discord.com/developers/resources/entitlement#entitlement-object-entitlement-types."""

    PURCHASE = 1
    """Entitlement was purchased by the user."""
    PREMIUM_SUBSCRIPTION = 2
    """Entitlement for a Discord Nitro subscription."""
    DEVELOPER_GIFT = 3
    """Entitlement was gifted by the developer."""
    TEST_MODE_PURCHASE = 4
    """Entitlement was purchased by a dev in application test mode."""
    FREE_PURCHASE = 5
    """Entitlement was granted when the SKU was free."""
    USER_GIFT = 6
    """Entitlement was gifted by another user."""
    PREMIUM_PURCHASE = 7
    """Entitlement was claimed by the user for free as a Nitro subscriber."""
    APPLICATION_SUBSCRIPTION = 8
    """Entitlement was purchased as an app subscription."""


class Entitlement(DiscordModel):
    """https://docs.discord.com/developers/resources/entitlement#entitlement-object."""

    id: Snowflake
    """ID of the entitlement."""
    sku_id: Snowflake
    """ID of the SKU."""
    application_id: Snowflake
    """ID of the parent application."""
    user_id: Snowflake | None = None
    """ID of the user that is granted access to the entitlement's SKU."""
    type: EntitlementType
    """Type of entitlement."""
    deleted: bool
    """Whether the entitlement was deleted."""
    starts_at: datetime | None
    """Start date at which the entitlement is valid."""
    ends_at: datetime | None
    """Date at which the entitlement is no longer valid."""
    guild_id: Snowflake | None = None
    """ID of the guild that is granted access to the entitlement's SKU."""
    consumed: bool | None = None
    """For consumable items, whether or not the entitlement has been consumed."""
