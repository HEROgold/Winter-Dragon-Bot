"""Unit tests: the percentage command's calculation is deterministic and its embed matches the legacy love meter."""

from __future__ import annotations

lazy import random

lazy from wd_discord.resources.user import User

lazy from winter_dragon.cogs.percentage import build_love_embed, calculate_percentage


MAX_PERCENT = 100
LOVE_COLOR = 0xFF0000


def test_percentage_is_deterministic_for_the_same_pair() -> None:
    assert calculate_percentage(1, 2) == calculate_percentage(1, 2)


def test_percentage_is_order_independent() -> None:
    assert calculate_percentage(1, 2) == calculate_percentage(2, 1)


def test_percentage_is_within_bounds() -> None:
    value = calculate_percentage(123, 456)
    assert 0 <= value <= MAX_PERCENT


def test_percentage_matches_manual_seed() -> None:
    expected = random.Random(1 + 2).randint(0, 100)  # noqa: S311 - mirrors the implementation
    assert calculate_percentage(1, 2) == expected


def test_love_embed_uses_global_name() -> None:
    target = User(id=2, username="bob", discriminator="0", global_name="Bobby")
    embed = build_love_embed(target, 42)
    assert embed.title == "Love Meter"
    assert embed.description == " "
    assert embed.color == LOVE_COLOR
    assert embed.fields is not None
    assert len(embed.fields) == 1
    field = embed.fields[0]
    assert field.name == "Bobby"
    assert field.value == "Your compatibility with Bobby is 42%"
    assert field.inline is True


def test_love_embed_falls_back_to_username() -> None:
    target = User(id=2, username="bob", discriminator="0")
    embed = build_love_embed(target, 7)
    assert embed.fields is not None
    assert embed.fields[0].name == "bob"
    assert embed.fields[0].value == "Your compatibility with bob is 7%"
