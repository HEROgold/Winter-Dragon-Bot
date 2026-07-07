from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto
from typing import TYPE_CHECKING

from wd_discord import Snowflake
from wd_discord.image import ImageHash


if TYPE_CHECKING:
    from wd_discord import Snowflake
    from wd_discord.image import ImageHash


class Avatar:
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


@dataclass
class NamePlate:
    """https://docs.discord.com/developers/resources/user#nameplate."""

    sku_id: Snowflake
    """id of the nameplate SKU"""
    asset: ImageHash
    """path to the nameplate asset"""
    label: str
    """the label of this nameplate. Currently unused"""
    palette: NamePlateBackgroundColor
    """background color of the nameplate"""
