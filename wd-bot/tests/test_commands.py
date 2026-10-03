"""Unit tests: Command's option derivation and interaction-option resolution (no network)."""

from __future__ import annotations

lazy from wd_bot.commands import Command
lazy from wd_discord.gateway.events import (
    Interaction,
    InteractionData,
    InteractionDataOption,
    InteractionType,
    ResolvedData,
)
lazy from wd_discord.interactions import ApplicationCommandOptionType
lazy from wd_discord.resources.user import User


def make_user(user_id: str, username: str) -> User:
    """Build a minimal User."""
    return User.model_validate({"id": user_id, "username": username, "discriminator": "0"})


async def percentage(self: object, interaction: Interaction, user: User) -> None:
    """Handle a command with one required user option."""


def test_options_derived_from_annotations() -> None:
    """Options are derived from the handler's resolved annotations."""
    command = Command(percentage, name="percentage", description="Calculate a percentage")
    options = list(command.options())
    assert len(options) == 1
    assert options[0].name == "user"
    assert options[0].type is ApplicationCommandOptionType.USER
    assert options[0].required is True


def test_signature_reflects_the_wrapped_function() -> None:
    """The signature string mentions the handler's parameters."""
    command = Command(percentage, name="percentage", description="d")
    assert "user" in command.signature()


async def test_invoke_resolves_user_option_from_resolved_data() -> None:
    """A USER option's snowflake is resolved to the full User from resolved data."""
    calls: list[tuple[object, object, dict[str, object]]] = []

    async def handler(self: object, interaction: Interaction, user: User) -> None:
        """Record the call."""
        calls.append((self, interaction, {"user": user}))

    command = Command(handler, name="percentage", description="d")
    target = make_user("4", "target")
    interaction = Interaction(
        id="1",
        application_id="2",
        type=InteractionType.APPLICATION_COMMAND,
        token="tok",  # noqa: S106
        version=1,
        user=make_user("3", "asker"),
        data=InteractionData(
            id="10",
            name="percentage",
            type=1,
            options=[InteractionDataOption(name="user", type=6, value="4")],
            resolved=ResolvedData(users={"4": target}),
        ),
    )

    cog = object()
    await command.invoke(cog, interaction)

    assert calls == [(cog, interaction, {"user": target})]
