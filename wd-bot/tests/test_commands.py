"""Unit tests: Command's option derivation and interaction-option resolution (no network)."""

from __future__ import annotations

lazy import os
lazy import subprocess
lazy import sys
lazy from typing import TYPE_CHECKING

lazy from wd_bot.commands import Command, CommandGroup
lazy from wd_discord.gateway.events import (
    Interaction,
    InteractionData,
    InteractionDataOption,
    InteractionType,
    ResolvedData,
)
lazy from wd_discord.interactions import ApplicationCommandOptionType
lazy from wd_discord.permissions import Permissions
lazy from wd_discord.resources.user import User


if TYPE_CHECKING:
    lazy from pathlib import Path

    lazy import pytest


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


async def test_invoke_skips_unknown_option(capsys: pytest.CaptureFixture[str]) -> None:
    """An option the handler doesn't declare is skipped with a warning instead of raising TypeError."""
    calls: list[int] = []

    async def handler(self: object, interaction: Interaction, count: int) -> None:  # noqa: ARG001
        """Record the count."""
        calls.append(count)

    command = Command(handler, name="c", description="d")
    interaction = _interaction(
        [InteractionDataOption(name="count", type=4, value=3), InteractionDataOption(name="stale", type=3, value="x")],
        None,
    )
    assert await command.invoke(object(), interaction) is True
    assert calls == [3]
    assert "Unknown option 'stale'" in capsys.readouterr().err


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
        env={**os.environ, "PYTHONPATH": os.pathsep.join(filter(None, (str(tmp_path), os.environ.get("PYTHONPATH"))))},
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[('a', 'USER', True), ('b', 'USER', False)]"


def test_signature_changes_with_description() -> None:
    first = Command(percentage, name="percentage", description="one")
    second = Command(percentage, name="percentage", description="two")
    assert first.signature() != second.signature()


def test_signature_changes_with_default_member_permissions() -> None:
    plain = Command(percentage, name="percentage", description="d")
    gated = Command(percentage, name="percentage", description="d", default_member_permissions=Permissions.MANAGE_GUILD)
    assert plain.default_member_permissions is None
    assert gated.default_member_permissions == Permissions.MANAGE_GUILD
    assert plain.signature() != gated.signature()


async def test_invoke_reports_success_and_failure() -> None:
    """Invoking returns True when the handler completes and False (after logging) when it raises."""

    async def ok(self: object, interaction: Interaction) -> None:
        """Succeed."""

    async def boom(self: object, interaction: Interaction) -> None:  # noqa: ARG001
        """Fail."""
        msg = "handler broke"
        raise RuntimeError(msg)

    interaction = _interaction([], None)
    assert await Command(ok, name="c", description="d").invoke(object(), interaction) is True
    assert await Command(boom, name="c", description="d").invoke(object(), interaction) is False


async def _noop(self: object, interaction: Interaction) -> None:
    """Handle a subcommand with no options."""


async def _count_handler(self: object, interaction: Interaction, count: int) -> None:
    """Handle a subcommand with one required integer option."""


def _group(*subcommands: Command) -> CommandGroup:
    return CommandGroup(name="g", description="group", subcommands=subcommands)


def test_group_options_nest_subcommand_options() -> None:
    group = _group(Command(_count_handler, name="add", description="Add"), Command(_noop, name="list", description="List"))
    options = list(group.options())
    assert [(o.name, o.type) for o in options] == [
        ("add", ApplicationCommandOptionType.SUB_COMMAND),
        ("list", ApplicationCommandOptionType.SUB_COMMAND),
    ]
    assert [o.name for o in options[0].options or []] == ["count"]
    assert options[1].options is None


def test_group_signature_changes_with_a_subcommand() -> None:
    before = _group(Command(_noop, name="list", description="one"))
    after = _group(Command(_noop, name="list", description="two"))
    assert before.signature() != after.signature()


async def test_group_invoke_routes_nested_options_to_the_subcommand() -> None:
    calls: list[int] = []

    async def add(self: object, interaction: Interaction, count: int) -> None:  # noqa: ARG001
        calls.append(count)

    group = _group(Command(add, name="add", description="Add"))
    sub = InteractionDataOption(name="add", type=1, options=[InteractionDataOption(name="count", type=4, value=5)])
    assert await group.invoke(object(), _interaction([sub], None)) is True
    assert calls == [5]


async def test_group_invoke_rejects_unknown_subcommand() -> None:
    group = _group(Command(_noop, name="list", description="List"))
    sub = InteractionDataOption(name="gone", type=1)
    assert await group.invoke(object(), _interaction([sub], None)) is False
