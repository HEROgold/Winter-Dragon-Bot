"""Unit tests: guild and role fields reject values outside Discord's documented limits."""

lazy import pytest
lazy from pydantic import ValidationError
lazy from wd_discord.resources.guild.guild import Guild
lazy from wd_discord.resources.guild.role import Role
lazy from wd_discord.testing import GUILD_JSON, role_json




@pytest.mark.parametrize("name", ["a", "x" * 101])
def test_guild_name_outside_2_to_100_characters_is_rejected(name: str) -> None:
    with pytest.raises(ValidationError):
        Guild.model_validate({**GUILD_JSON, "name": name})


def test_guild_name_inside_the_limits_parses() -> None:
    assert Guild.model_validate({**GUILD_JSON, "name": "x" * 100}).name == "x" * 100


def test_role_position_rejects_negatives() -> None:
    with pytest.raises(ValidationError):
        Role.model_validate(role_json(position=-1))
    assert Role.model_validate(role_json()).position == 1
