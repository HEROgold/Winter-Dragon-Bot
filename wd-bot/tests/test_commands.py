"""Unit tests: Command's option derivation and interaction-option resolution (no network)."""

from __future__ import annotations

lazy import os
lazy import subprocess
lazy import sys
lazy from typing import TYPE_CHECKING

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


if TYPE_CHECKING:
    lazy from pathlib import Path


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


def _interaction(options: list[InteractionDataOption], resolved: ResolvedData | None) -> Interaction:
    """Build an application-command interaction with the given options."""
    return Interaction(
        id="1",
        application_id="2",
        type=InteractionType.APPLICATION_COMMAND,
        token="tok",  # noqa: S106
        version=1,
        user=make_user("3", "asker"),
        data=InteractionData(id="10", name="c", type=1, options=options, resolved=resolved),
    )


async def test_invoke_skips_unresolved_user_option() -> None:
    """An unresolvable user id is skipped, so the handler's default applies."""
    calls: list[User | None] = []

    async def handler(self: object, interaction: Interaction, user: User | None = None) -> None:  # noqa: ARG001
        """Record the user."""
        calls.append(user)

    command = Command(handler, name="c", description="d")
    option = next(command.options())
    assert option.type is ApplicationCommandOptionType.USER
    assert option.required is False

    interaction = _interaction([InteractionDataOption(name="user", type=6, value="4")], ResolvedData(users={}))
    await command.invoke(object(), interaction)
    assert calls == [None]


def test_command_tolerates_unimportable_non_option_annotations() -> None:
    """Annotations of self/interaction that cannot be resolved at runtime are ignored."""

    async def handler(self: object, interaction: NotImported, count: int) -> None:  # noqa: F821
        """Handle."""

    command = Command(handler, name="c", description="d")
    assert [o.name for o in command.options()] == ["count"]


def test_command_reifies_lazy_import_annotations(tmp_path: Path) -> None:
    """Option annotations that are still-unresolved lazy imports are reified before the type lookup.

    Runs in a fresh interpreter so nothing has touched ``User`` (or loaded its module) beforehand.
    """
    (tmp_path / "lazy_handler_module.py").write_text(
        "from __future__ import annotations\n"
        "lazy from wd_discord.resources.user import User\n"
        "async def handler(self, interaction, a: User, b: User | None = None) -> None: ...\n",
    )
    script = (
        "import lazy_handler_module\n"
        "from wd_bot.commands import Command\n"
        "command = Command(lazy_handler_module.handler, name='c', description='d')\n"
        "print([(o.name, o.type.name, o.required) for o in command.options()])\n"
    )
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[('a', 'USER', True), ('b', 'USER', False)]"
