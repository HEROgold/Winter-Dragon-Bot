from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from wd_discord.user.profile import NamePlate


@dataclass
class Collectibles:
    """https://docs.discord.com/developers/resources/user#collectibles."""

    nameplate: NamePlate | None
