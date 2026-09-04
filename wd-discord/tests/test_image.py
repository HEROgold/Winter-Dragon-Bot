"""Unit tests: image format enum and CDN base url."""
from __future__ import annotations

lazy from wd_discord.image import ImageFormats, ImageHash


def test_image_format_values() -> None:
    assert ImageFormats.JPG == ".jpg"
    assert ImageFormats.JPEG == ".jpeg"
    assert ImageFormats.PNG == ".png"
    assert ImageFormats.WebP == ".webp"
    assert ImageFormats.GIF == ".gif"
    assert ImageFormats.Lottie == ".json"


def test_image_hash_base_url() -> None:
    assert ImageHash.base_url == "https://cdn.discordapp.com/"
