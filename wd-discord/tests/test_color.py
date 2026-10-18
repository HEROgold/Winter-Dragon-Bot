"""Unit tests: Color validates 24-bit RGB and stays an int on the wire."""

from __future__ import annotations

lazy import pytest
lazy from pydantic import ValidationError
lazy from wd_discord.color import MAX_COLOR, Color
lazy from wd_discord.embed import Embed


def test_color_is_an_int_and_prints_as_hex() -> None:
    color = Color(0x00FF00)
    assert color == 0x00FF00
    assert str(color) == "#00ff00"


@pytest.mark.parametrize("text", ["#00ff00", "00ff00", "0x00ff00"])
def test_from_hex_accepts_common_spellings(text: str) -> None:
    assert Color.from_hex(text) == 0x00FF00


@pytest.mark.parametrize("value", [-1, MAX_COLOR + 1])
def test_out_of_range_is_rejected(value: int) -> None:
    with pytest.raises(ValueError, match="A color is between"):
        Color(value)
    with pytest.raises(ValidationError):
        Embed(color=value)


def test_embed_color_round_trips_as_a_plain_int() -> None:
    embed = Embed(color=0xFF69B4)
    assert isinstance(embed.color, Color)
    assert embed.model_dump(mode="json", exclude_none=True) == {"color": 0xFF69B4}
    assert type(embed.model_dump(mode="json")["color"]) is int
