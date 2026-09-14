"""User profile sub-objects: avatar decoration and nameplate collectibles."""
from __future__ import annotations

lazy from enum import StrEnum, auto

lazy from wd_discord.image import ImageHash
lazy from wd_discord.models import DiscordModel
lazy from wd_discord.snowflake import Snowflake


class Avatar(DiscordModel):
    """https://docs.discord.com/developers/resources/user#avatar-decoration-data-object."""

    asset: ImageHash
    """the avatar decoration hash"""
    sku_id: Snowflake
    """id of the avatar decoration's SKU"""


class NamePlateBackgroundColor(StrEnum):
    """Background color of the nameplate."""

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
