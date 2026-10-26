"""Unit tests: Command's option derivation and interaction-option resolution (no network)."""

lazy import os
lazy import subprocess
lazy import sys
lazy from typing import TYPE_CHECKING

lazy from wd_bot.commands import Command, CommandDefinition, CommandGroup
lazy from wd_bot.testing import cog_command

# Command resolves option annotations from module globals at runtime, so BoundUser must be available here.
lazy from wd_discord import User as BoundUser  # noqa: TC002
lazy from wd_discord.gateway.events import InteractionDataOption, ResolvedData
lazy from wd_discord.interactions import ApplicationCommandOptionType, InteractionContextType
lazy from wd_discord.permissions import Permissions
lazy from wd_discord.resources.user import User
lazy from wd_discord.snowflake import Snowflake


if TYPE_CHECKING:
    lazy from pathlib import Path

    lazy import pytest
    lazy from conftest import InteractionFactory
    lazy from wd_discord import CommandInteraction


def make_user(user_id: str, username: str) -> User:
    """Build a minimal User."""
    return User.model_validate({"id": user_id, "username": username, "discriminator": "0"})


async def percentage(self: object, interaction: CommandInteraction, user: User) -> None:
    """Handle a command with one required user option."""


def test_options_derived_from_annotations() -> None:
    """Options are derived from the handler's resolved annotations."""
    command = cog_command(percentage, CommandDefinition("percentage", "Calculate a percentage"))
    options = list(command.options())
    assert len(options) == 1
    assert options[0].name == "user"
    assert options[0].type is ApplicationCommandOptionType.USER
    assert options[0].required is True


def test_signature_reflects_the_wrapped_function() -> None:
    """The signature string mentions the handler's parameters."""
    command = cog_command(percentage, CommandDefinition("percentage", "d"))
    assert "user" in command.signature()


async def test_invoke_resolves_user_option_from_resolved_data(make_interaction: InteractionFactory) -> None:
    """A USER option's snowflake is resolved to the full User from resolved data."""
    calls: list[tuple[object, object, dict[str, object]]] = []

    async def handler(self: object, interaction: CommandInteraction, user: User) -> None:
        """Record the call."""
        calls.append((self, interaction, {"user": user}))

    command = cog_command(handler, CommandDefinition("percentage", "d"))
    target = make_user("4", "target")
    interaction = make_interaction(
        "percentage",
        options=[InteractionDataOption(name="user", type=6, value="4")],
        resolved=ResolvedData(users={"4": target}),
    )

    cog = object()
    await command.invoke(cog, interaction)

    assert calls == [(cog, interaction, {"user": target})]


async def test_invoke_binds_a_user_option_annotated_with_the_bound_user(make_interaction: InteractionFactory) -> None:
    """A parameter annotated with wd_discord.User gets the resolved user bound to the interaction's client."""
    received: list[BoundUser] = []

    async def handler(self: object, interaction: CommandInteraction, user: BoundUser) -> None:  # noqa: ARG001
        """Record the user."""
        received.append(user)

    command = cog_command(handler, CommandDefinition("percentage", "d"))
    assert next(command.options()).type is ApplicationCommandOptionType.USER
    target = make_user("4", "target")
    interaction = make_interaction(
        "percentage",
        options=[InteractionDataOption(name="user", type=6, value="4")],
        resolved=ResolvedData(users={"4": target}),
    )

    await command.invoke(object(), interaction)

    assert [(user.model, user.client) for user in received] == [(target, interaction.client)]


async def test_invoke_skips_unresolved_user_option(make_interaction: InteractionFactory) -> None:
    """An unresolvable user id is skipped, so the handler's default applies."""
    calls: list[User | None] = []

    async def handler(self: object, interaction: CommandInteraction, user: User | None = None) -> None:  # noqa: ARG001
        """Record the user."""
        calls.append(user)

    command = cog_command(handler, CommandDefinition("c", "d"))
    option = next(command.options())
    assert option.type is ApplicationCommandOptionType.USER
    assert option.required is False

    interaction = make_interaction(
        options=[InteractionDataOption(name="user", type=6, value="4")],
        resolved=ResolvedData(users={}),
    )
    await command.invoke(object(), interaction)
    assert calls == [None]


async def test_invoke_skips_unknown_option(capsys: pytest.CaptureFixture[str], make_interaction: InteractionFactory) -> None:
    """An option the handler doesn't declare is skipped with a warning instead of raising TypeError."""
    calls: list[int] = []

    async def handler(self: object, interaction: CommandInteraction, count: int) -> None:  # noqa: ARG001
        """Record the count."""
        calls.append(count)

    command = cog_command(handler, CommandDefinition("c", "d"))
    interaction = make_interaction(
        options=[InteractionDataOption(name="count", type=4, value=3), InteractionDataOption(name="stale", type=3, value="x")],
    )
    assert await command.invoke(object(), interaction) is True
    assert calls == [3]
    assert "Unknown option 'stale'" in capsys.readouterr().err


def test_command_tolerates_unimportable_non_option_annotations() -> None:
    """Annotations of self/interaction that cannot be resolved at runtime are ignored."""

    async def handler(self: object, interaction: NotImported, count: int) -> None:  # noqa: F821
        """Handle."""

    command = cog_command(handler, CommandDefinition("c", "d"))
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
        "from wd_bot.commands import CommandDefinition\n"
        "from wd_bot.testing import cog_command\n"
        "command = cog_command(lazy_handler_module.handler, CommandDefinition('c', 'd'))\n"
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
    first = cog_command(percentage, CommandDefinition("percentage", "one"))
    second = cog_command(percentage, CommandDefinition("percentage", "two"))
    assert first.signature() != second.signature()


def test_signature_changes_with_default_member_permissions() -> None:
    plain = cog_command(percentage, CommandDefinition("percentage", "d"))
    gated = cog_command(
        percentage,
        CommandDefinition("percentage", "d", default_member_permissions=Permissions.MANAGE_GUILD),
    )
    assert plain.default_member_permissions is None
    assert gated.default_member_permissions == Permissions.MANAGE_GUILD
    assert plain.signature() != gated.signature()


def test_signature_changes_with_contexts() -> None:
    anywhere = cog_command(percentage, CommandDefinition("percentage", "d"))
    guild_only = cog_command(percentage, CommandDefinition("percentage", "d", contexts=(InteractionContextType.GUILD,)))
    assert anywhere.signature() != guild_only.signature()


def test_params_carry_the_definition() -> None:
    command = cog_command(
        percentage,
        CommandDefinition(
            "percentage",
            "d",
            default_member_permissions=Permissions.MANAGE_GUILD,
            contexts=(InteractionContextType.GUILD,),
        ),
    )
    params = command.params()
    assert params.name == "percentage"
    assert params.default_member_permissions == Permissions.MANAGE_GUILD
    assert params.contexts == [InteractionContextType.GUILD]
    assert [option.name for option in params.options or []] == [option.name for option in command.options()]


async def test_invoke_reports_success_and_failure(make_interaction: InteractionFactory) -> None:
    """Invoking returns True when the handler completes and False (after logging) when it raises."""

    async def ok(self: object, interaction: CommandInteraction) -> None:
        """Succeed."""

    async def boom(self: object, interaction: CommandInteraction) -> None:  # noqa: ARG001
        """Fail."""
        msg = "handler broke"
        raise RuntimeError(msg)

    interaction = make_interaction()
    assert await cog_command(ok, CommandDefinition("c", "d")).invoke(object(), interaction) is True
    assert await cog_command(boom, CommandDefinition("c", "d")).invoke(object(), interaction) is False


async def _noop(self: object, interaction: CommandInteraction) -> None:
    """Handle a subcommand with no options."""


async def _count_handler(self: object, interaction: CommandInteraction, count: int) -> None:
    """Handle a subcommand with one required integer option."""


def _group(*subcommands: Command) -> CommandGroup:
    return CommandGroup(CommandDefinition("g", "group"), subcommands)


def test_group_options_nest_subcommand_options() -> None:
    group = _group(cog_command(_count_handler, CommandDefinition("add", "Add")), cog_command(_noop, CommandDefinition("list", "List")))
    options = list(group.options())
    assert [(o.name, o.type) for o in options] == [
        ("add", ApplicationCommandOptionType.SUB_COMMAND),
        ("list", ApplicationCommandOptionType.SUB_COMMAND),
    ]
    assert [o.name for o in options[0].options or []] == ["count"]
    assert options[1].options is None


def test_group_signature_changes_with_a_subcommand() -> None:
    before = _group(cog_command(_noop, CommandDefinition("list", "one")))
    after = _group(cog_command(_noop, CommandDefinition("list", "two")))
    assert before.signature() != after.signature()


async def test_group_invoke_routes_nested_options_to_the_subcommand(make_interaction: InteractionFactory) -> None:
    calls: list[int] = []

    async def add(self: object, interaction: CommandInteraction, count: int) -> None:  # noqa: ARG001
        calls.append(count)

    group = _group(cog_command(add, CommandDefinition("add", "Add")))
    sub = InteractionDataOption(name="add", type=1, options=[InteractionDataOption(name="count", type=4, value=5)])
    assert await group.invoke(object(), make_interaction(options=[sub])) is True
    assert calls == [5]


async def test_group_invoke_rejects_unknown_subcommand(make_interaction: InteractionFactory) -> None:
    group = _group(cog_command(_noop, CommandDefinition("list", "List")))
    sub = InteractionDataOption(name="gone", type=1)
    assert await group.invoke(object(), make_interaction(options=[sub])) is False


def test_definition_is_one_frozen_value() -> None:
    """A definition built from any iterables holds them as tuples, so it compares and hashes as a value."""
    built = CommandDefinition.of("c", "d", contexts=[InteractionContextType.GUILD], guild_ids=["1", 2])
    expected = CommandDefinition("c", "d", contexts=(InteractionContextType.GUILD,), guild_ids=(Snowflake(1), Snowflake(2)))
    assert built == expected
    assert hash(built) == hash(CommandDefinition.of("c", "d", contexts=(InteractionContextType.GUILD,), guild_ids=[1, "2"]))
