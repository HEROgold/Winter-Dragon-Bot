from __future__ import annotations

from enum import StrEnum


class ImageHash:
    """https://docs.discord.com/developers/reference#image-formatting."""

    base_url = "https://cdn.discordapp.com/"


class ImageFormats(StrEnum):
    """Valid image formats supported by Discord."""

    JPG = ".jpg"
    JPEG = ".jpeg"
    """Could be either .jpg or .jpeg."""
    PNG = ".png"
    WebP = ".webp"
    GIF = ".gif"
    Lottie = ".json"
