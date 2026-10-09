"""Unit tests: the command registry, command mentions and the scope-by-scope syncer (no network)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import TYPE_CHECKING

from wd_bot.auto_sync import CommandSyncer
from wd_bot.cogs import Cog, GroupCog
from wd_bot.registry import GLOBAL, CommandPath, CommandRegistry, Scope, definition_matches
from wd_discord.errors.api import ApiResponseError
from wd_discord.interactions import ApplicationCommand, ApplicationCommandParams, InteractionContextType
from wd_discord.snowflake import Snowflake
from wd_discord.testing import RecordingClient


if TYPE_CHECKING:
    import pytest
    from wd_bot.commands import AppCommand
    from wd_discord import CommandInteraction


GLOBAL_ROUTE = "/applications/2/commands"
GUILD = Scope(Snowflake(9))
GUILD_ROUTE = "/applications/2/guilds/9/commands"


class _Ping(Cog, auto_load=False):
    @Cog.command(name="ping", description="d")
    async def ping(self, interaction: CommandInteraction, text: str) -> None:
        """Handle /ping."""


class _Steam(GroupCog, auto_load=False):
    """Steam sales."""

    @Cog.command(name="show", description="d")
    async def show(self, interaction: CommandInteraction) -> None:
        """Handle /steam show."""


class _GuildOnly(Cog, auto_load=False):
    @Cog.command(name="local", description="d", guild_ids=[9])
    async def local(self, interaction: CommandInteraction) -> None:
        """Handle /local."""


def _cog[C: Cog](cls: type[C], registry: CommandRegistry) -> C:
    """Build ``cls`` without Cog.__init__, on a bot that only has ``registry``."""
    cog = cls.__new__(cls)
    cog.bot = SimpleNamespace(registry=registry)  # pyright: ignore[reportAttributeAccessIssue]
    return cog


def _reported(params: ApplicationCommandParams, command_id: int = 42, **discord_fills: object) -> dict[str, object]:
    """Return ``params`` as Discord reports it back: with an ID and version, plus whatever Discord fills in."""
    return {**params.to_json(), "id": str(command_id), "application_id": "2", "version": "1", **discord_fills}


def _command(params: ApplicationCommandParams, command_id: int = 42, **discord_fills: object) -> ApplicationCommand:
    return ApplicationCommand.model_validate(_reported(params, command_id, **discord_fills))


def _params(command: AppCommand) -> ApplicationCommandParams:
    return command.params()


# --- registry -----------------------------------------------------------------------------------------------


def test_register_places_commands_in_their_declared_scopes() -> None:
    registry = CommandRegistry()
    assert registry.register(_cog(_Ping, registry)) == {GLOBAL}
    assert registry.register(_cog(_GuildOnly, registry)) == {GUILD}
    assert registry.scopes() == {GLOBAL, GUILD}


def test_unregister_removes_the_cogs_commands_and_returns_their_scopes() -> None:
    registry = CommandRegistry()
    cog = _cog(_GuildOnly, registry)
    registry.register(cog)

    assert registry.unregister(cog) == {GUILD}
    assert registry.entry("local", GUILD.guild_id) is None


def test_entry_prefers_the_guilds_own_command() -> None:
    registry = CommandRegistry()
    global_ping = _cog(_Ping, registry)
    registry.register(global_ping)

    from_guild = registry.entry("ping", Snowflake(9))
    assert from_guild is not None
    assert from_guild.cog is global_ping
    assert registry.entry("local", None) is None


def test_refresh_replaces_commands_after_the_placement_changes() -> None:
    registry = CommandRegistry()
    registry.register(_cog(_Ping, registry))
    registry.placement = lambda _command: frozenset({GUILD})

    assert registry.refresh() == {GLOBAL, GUILD}
    assert registry.entry("ping") is None
    assert registry.entry("ping", GUILD.guild_id) is not None


def test_scope_is_unknown_until_discord_reports_it() -> None:
    registry = CommandRegistry()
    registry.register(_cog(_Ping, registry))
    assert not registry.is_known(GLOBAL)
    assert not registry.in_sync(GLOBAL)

    registry.apply(GLOBAL, [_command(_params(_Ping.ping))])

    assert registry.is_known(GLOBAL)
    assert registry.in_sync(GLOBAL)


def test_scope_with_an_extra_or_missing_command_is_out_of_sync() -> None:
    registry = CommandRegistry()
    registry.register(_cog(_Ping, registry))
    extra = ApplicationCommandParams(name="gone", description="d")

    registry.apply(GLOBAL, [_command(_params(_Ping.ping)), _command(extra, 43)])
    assert not registry.in_sync(GLOBAL)
    registry.apply(GLOBAL, [])
    assert not registry.in_sync(GLOBAL)


# --- definition comparison ----------------------------------------------------------------------------------


def test_fields_discord_fills_in_still_match() -> None:
    local = _params(_Ping.ping)
    remote = _command(local, integration_types=[0], contexts=[0, 1, 2], nsfw=False)

    assert definition_matches(local, remote)


def test_unset_autocomplete_matches_discords_false() -> None:
    local = _params(_Ping.ping)
    options = [option.model_copy(update={"autocomplete": False}) for option in local.options or []]

    assert definition_matches(local, _command(local).model_copy(update={"options": options}))


def test_a_changed_definition_does_not_match() -> None:
    local = _params(_Ping.ping)

    assert not definition_matches(local, _command(local, description="older"))
    assert not definition_matches(local, _command(local, options=[]))
    explicit = local.model_copy(update={"contexts": [InteractionContextType.GUILD]})
    assert not definition_matches(explicit, _command(local, contexts=[0, 1, 2]))


# --- mentions -----------------------------------------------------------------------------------------------


def test_mention_is_plain_text_until_discord_reports_the_command() -> None:
    registry = CommandRegistry()
    cog = _cog(_Steam, registry)
    registry.register(cog)
    mention = cog.mention(_Steam.show)
    assert str(mention) == "`/steam show`"

    (group,) = _Steam.app_commands()
    registry.apply(GLOBAL, [_command(_params(group))])

    # The same mention object now renders the ID Discord reported: it is resolved when rendered.
    assert f"{mention}" == "</steam show:42>"


def test_mention_of_another_cogs_command_uses_that_cogs_path() -> None:
    registry = CommandRegistry()
    ping = _cog(_Ping, registry)

    assert ping.mention(_Steam.show).path == CommandPath("steam", "show")
    assert str(ping.mention(_Ping.ping)) == "`/ping`"


def test_mention_from_a_guild_prefers_the_guilds_own_command() -> None:
    registry = CommandRegistry()
    cog = _cog(_Ping, registry)
    registry.apply(GLOBAL, [_command(_params(_Ping.ping), 1)])
    registry.apply(GUILD, [_command(_params(_Ping.ping), 2)])

    assert str(cog.mention(_Ping.ping)) == "</ping:1>"
    assert str(cog.mention(_Ping.ping, guild=9)) == "</ping:2>"
    assert str(cog.mention(_Ping.ping, guild=10)) == "</ping:1>"


# --- syncer -------------------------------------------------------------------------------------------------


def _synced_registry(*cogs: type[Cog]) -> CommandRegistry:
    registry = CommandRegistry()
    for cls in cogs:
        registry.register(_cog(cls, registry))
    return registry


def _methods(client: RecordingClient) -> list[tuple[str, str]]:
    return [(sent.method, sent.path) for sent in client.sent]


async def test_restart_without_changes_reads_ids_and_writes_nothing() -> None:
    registry = _synced_registry(_Ping)
    client = RecordingClient()
    client.reply("GET", GLOBAL_ROUTE, [_reported(_params(_Ping.ping), integration_types=[0], contexts=[0, 1, 2])])

    await CommandSyncer(registry).sync(client, [GLOBAL])

    assert _methods(client) == [("GET", GLOBAL_ROUTE)]
    assert registry.command_id("ping") == Snowflake(42)


async def test_changed_scope_is_overwritten_and_takes_discords_answer() -> None:
    registry = _synced_registry(_Ping)
    client = RecordingClient()
    client.reply("GET", GLOBAL_ROUTE, [])
    client.reply("PUT", GLOBAL_ROUTE, [_reported(_params(_Ping.ping), 77)])

    await CommandSyncer(registry).sync(client, [GLOBAL])

    assert _methods(client) == [("GET", GLOBAL_ROUTE), ("PUT", GLOBAL_ROUTE)]
    assert client.sent[1].json == [_params(_Ping.ping).to_json()]
    assert registry.command_id("ping") == Snowflake(77)
    assert registry.in_sync(GLOBAL)


async def test_known_scope_in_sync_makes_no_calls() -> None:
    registry = _synced_registry(_Ping)
    registry.apply(GLOBAL, [_command(_params(_Ping.ping))])
    client = RecordingClient()

    await CommandSyncer(registry).sync(client, [GLOBAL])

    assert client.sent == []


async def test_known_scope_that_changed_is_written_without_reading_it_again() -> None:
    """After a hot reload the registry already knows Discord's state, so only the PUT is needed."""
    registry = _synced_registry(_Ping)
    registry.apply(GLOBAL, [_command(_params(_Ping.ping), description="older")])
    client = RecordingClient()
    client.reply("PUT", GLOBAL_ROUTE, [_reported(_params(_Ping.ping))])

    await CommandSyncer(registry).sync(client, [GLOBAL])

    assert _methods(client) == [("PUT", GLOBAL_ROUTE)]


async def test_guild_scope_uses_the_guild_route() -> None:
    registry = _synced_registry(_GuildOnly)
    client = RecordingClient()
    client.reply("GET", GUILD_ROUTE, [])
    client.reply("PUT", GUILD_ROUTE, [_reported(_params(_GuildOnly.local), 5)])

    await CommandSyncer(registry).sync(client, [GUILD])

    assert _methods(client) == [("GET", GUILD_ROUTE), ("PUT", GUILD_ROUTE)]
    assert registry.command_id("local", Snowflake(9)) == Snowflake(5)


async def test_writes_disallowed_reads_but_never_puts(capsys: pytest.CaptureFixture[str]) -> None:
    registry = _synced_registry(_Ping)
    client = RecordingClient()
    client.reply("GET", GLOBAL_ROUTE, [_reported(_params(_Ping.ping), description="older")])

    await CommandSyncer(registry).sync(client, [GLOBAL], allow_writes=False)

    assert _methods(client) == [("GET", GLOBAL_ROUTE)]
    assert registry.command_id("ping") == Snowflake(42)
    assert "skipping the write" in capsys.readouterr().err


async def test_failed_read_writes_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    registry = _synced_registry(_Ping)
    client = RecordingClient()
    client.fail("GET", GLOBAL_ROUTE, ApiResponseError(code=0, message="Discord is down"))

    await CommandSyncer(registry).sync(client, [GLOBAL])

    assert _methods(client) == [("GET", GLOBAL_ROUTE)]
    assert not registry.is_known(GLOBAL)
    assert "Failed to fetch the commands in global" in capsys.readouterr().err


async def test_overlapping_syncs_of_one_scope_write_once() -> None:
    registry = _synced_registry(_Ping)
    client = RecordingClient()
    client.reply("GET", GLOBAL_ROUTE, [])
    client.reply("PUT", GLOBAL_ROUTE, [_reported(_params(_Ping.ping))])
    syncer = CommandSyncer(registry)

    await asyncio.gather(syncer.sync(client, [GLOBAL]), syncer.sync(client, [GLOBAL]))

    assert _methods(client) == [("GET", GLOBAL_ROUTE), ("PUT", GLOBAL_ROUTE)]
