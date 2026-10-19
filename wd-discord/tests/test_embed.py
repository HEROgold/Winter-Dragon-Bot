"""Unit tests: the minimal Embed model."""

from __future__ import annotations

from wd_discord.embed import Embed, EmbedField, EmbedFooter


def test_embed_serializes_only_set_fields() -> None:
    embed = Embed(title="Percentage", description="You and @x are 73% compatible!", color=0xFF69B4)
    dumped = embed.model_dump(mode="json", exclude_none=True)
    assert dumped == {"title": "Percentage", "description": "You and @x are 73% compatible!", "color": 0xFF69B4}


def test_embed_with_fields() -> None:
    embed = Embed(title="Love Meter", fields=[EmbedField(name="target", value="73%", inline=True)])
    dumped = embed.model_dump(mode="json", exclude_none=True)
    assert dumped["fields"] == [{"name": "target", "value": "73%", "inline": True}]


def test_embed_footer_serializes() -> None:
    embed = Embed(title="Sales", footer=EmbedFooter(text="Page 1/3"))
    assert embed.model_dump(mode="json", exclude_none=True) == {"title": "Sales", "footer": {"text": "Page 1/3"}}


def test_character_count_sums_the_limited_parts() -> None:
    embed = Embed(
        title="abc",
        description="de",
        footer=EmbedFooter(text="f"),
        fields=[EmbedField(name="gh", value="ijk")],
    )
    assert embed.character_count() == len("abc" + "de" + "f" + "gh" + "ijk")
