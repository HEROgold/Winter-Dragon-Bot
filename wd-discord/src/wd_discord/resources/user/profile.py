"""User profile sub-objects: avatar decoration and nameplate collectibles."""

from __future__ import annotations

lazy from enum import auto

from wd_discord.image import ImageHash
from wd_discord.models import DiscordModel
from wd_discord.open_enum import OpenStrEnum
from wd_discord.snowflake import Snowflake


class Avatar(DiscordModel):
    """https://docs.discord.com/developers/resources/user#avatar-decoration-data-object."""

    asset: ImageHash
    """the avatar decoration hash"""
    sku_id: Snowflake
    """id of the avatar decoration's SKU"""
    expires_at: int | None = None
    """When the decoration expires, as a Unix timestamp. Sent by Discord, but not documented."""


class DisplayNameStyles(DiscordModel):
    """How a user's display name is drawn: its font, effect and colors. Sent by Discord, but not documented."""

    font_id: int | None = None
    effect_id: int | None = None
    colors: list[int] | None = None
    """The colors the effect uses, as integers."""


class NamePlateBackgroundColor(OpenStrEnum):
    """Background color of the nameplate.

    https://docs.discord.com/developers/resources/user#nameplate
    """

    CRIMSON = auto()
    BERRY = auto()
    SKY = auto()
    TEAL = auto()
    FOREST = auto()
    BUBBLE_GUM = auto()
    VIOLET = auto()
    COBALT = auto()
    CLOVER = auto()
    LEMON = auto()
    WHITE = auto()
    BLACK = auto()
    """Sent by Discord, but not documented."""


class NamePlate(DiscordModel):
    """https://docs.discord.com/developers/resources/user#nameplate."""

    sku_id: Snowflake
    """id of the nameplate SKU"""
    asset: ImageHash
    """path to the nameplate asset"""
    label: str
    """the label of this nameplate. Currently unused"""
    palette: NamePlateBackgroundColor
    """background color of the nameplate"""
    expires_at: int | None = None
    """When the nameplate expires, as a Unix timestamp. Sent by Discord, but not documented."""
