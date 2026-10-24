"""Unit tests: Color validates 24-bit RGB and stays an int on the wire."""

lazy import pytest
lazy from hypothesis import given
lazy from hypothesis import strategies as st
lazy from pydantic import ValidationError
lazy from wd_discord.color import MAX_COLOR, Color
lazy from wd_discord.embed import Embed
lazy from wd_discord.testing.strategies import colors


@given(colors())
def test_a_color_is_its_int_and_prints_as_hex(value: int) -> None:
    color = Color(value)
    assert color == value
    assert str(color) == f"#{value:06x}"


@given(colors(), st.sampled_from(["#{:06x}", "{:06x}", "0x{:06x}", "#{:06X}"]))
def test_from_hex_reads_every_common_spelling(value: int, spelling: str) -> None:
    assert Color.from_hex(spelling.format(value)) == value


@given(st.integers(max_value=-1) | st.integers(min_value=MAX_COLOR + 1))
def test_out_of_range_is_rejected(value: int) -> None:
    with pytest.raises(ValueError, match="A color is between"):
        Color(value)
    with pytest.raises(ValidationError):
        Embed(color=value)


@given(colors())
def test_embed_color_round_trips_as_a_plain_int(value: int) -> None:
    embed = Embed(color=value)
    assert isinstance(embed.color, Color)
    assert embed.model_dump(mode="json", exclude_none=True) == {"color": value}
    assert type(embed.model_dump(mode="json")["color"]) is int
