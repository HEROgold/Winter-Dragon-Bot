"""Unit tests: the admin bot-commands cog's status formatting and handlers (no network)."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING
lazy from unittest.mock import AsyncMock

lazy from wd_bot.cogs import Cog
lazy from wd_bot.commands import CommandGroup
lazy from wd_bot.registry import GLOBAL, CommandRegistry
lazy from wd_bot.testing import detached_cog
lazy from wd_discord.interactions import ApplicationCommand, InteractionContextType
lazy from wd_discord.permissions import Permissions

lazy from winter_dragon.cogs.bot_commands import BotCommands, describe_sync_status


if TYPE_CHECKING:
    lazy from conftest import InteractionFactory
    lazy from wd_discord import CommandInteraction
    lazy from wd_discord.testing import RecordingClient


OWNER_ID = "3"
"""The default invoking user of ``make_interaction``, made the application's owner by :func:`_owned_by`."""


def _owned_by(discord_client: RecordingClient, owner_id: str) -> None:
    """Make Discord report ``owner_id`` as the owner of the bot's application."""
    application = {
        "id": "2",
        "name": "bot",
        "icon": None,
        "description": "",
        "bot_public": True,
        "bot_require_code_grant": False,
        "verify_key": "k",
        "team": None,
        "owner": {"id": owner_id, "username": "owner", "discriminator": "0"},
    }
    discord_client.reply("GET", "/applications/@me", application)


class _Commands(Cog, auto_load=False):
    @Cog.command(name="ping", description="d")
    async def ping(self, interaction: CommandInteraction) -> None:
        """Handle /ping."""

    @Cog.command(name="other", description="d")
    async def other(self, interaction: CommandInteraction) -> None:
        """Handle /other."""


def _registry(**reported_ping: str) -> CommandRegistry:
    """Return a registry holding /ping and /other, of which Discord has reported only /ping (as ``reported_ping``)."""
    registry = CommandRegistry()
    registry.register(_Commands.__new__(_Commands))
    ping = {**_Commands.ping.params().to_json(), "id": "1", "application_id": "2", "version": "1", **reported_ping}
    registry.apply(GLOBAL, [ApplicationCommand.model_validate(ping)])
    return registry


def test_describe_sync_status_reports_synced_and_pending() -> None:
    assert list(describe_sync_status(_registry())) == ["other (global): pending", "ping (global): synced"]


def test_describe_sync_status_reports_a_changed_definition_as_pending() -> None:
    assert "ping (global): pending" in list(describe_sync_status(_registry(description="older")))


def test_group_is_gated_to_manage_guild() -> None:
    (group,) = BotCommands.app_commands()
    assert isinstance(group, CommandGroup)
    assert group.name == "bot-commands"
    assert group.default_member_permissions == Permissions.MANAGE_GUILD
    assert sorted(group.subcommands) == ["list", "resync"]
    assert all(command.default_member_permissions is None for command in group.subcommands.values())


async def test_list_commands_replies_with_status_embed(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    cog = detached_cog(BotCommands, registry=_registry(), client=discord_client)

    await BotCommands.list_commands.invoke(cog, make_interaction("bot-commands", guild_id=1))

    (response,) = discord_client.interaction_responses()
    assert response["data"]["embeds"][0]["description"] == "other (global): pending\nping (global): synced"


async def test_resync_responds_then_rereads_discord_before_syncing(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    responses_before_sync: list[int] = []
    sync = AsyncMock(side_effect=lambda *_a, **_k: responses_before_sync.append(len(discord_client.interaction_responses())))
    registry = _registry()
    _owned_by(discord_client, OWNER_ID)
    cog = detached_cog(BotCommands, registry=registry, client=discord_client, sync_commands=sync)

    await BotCommands.resync.invoke(cog, make_interaction("bot-commands", guild_id=1))

    assert responses_before_sync == [1]
    sync.assert_awaited_once_with(discord_client)
    assert not registry.is_known(GLOBAL)
    assert discord_client.interaction_responses() == [{"type": 4, "data": {"content": "Resyncing commands…"}}]
    (finished,) = discord_client.requests_to("POST", "/webhooks/2/tok")
    assert finished.json == {"content": "Resync finished."}


async def test_resync_is_for_bot_owners_only(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    sync = AsyncMock()
    registry = _registry()
    _owned_by(discord_client, "99")
    cog = detached_cog(BotCommands, registry=registry, client=discord_client, sync_commands=sync)

    await BotCommands.resync.invoke(cog, make_interaction("bot-commands", guild_id=1))

    sync.assert_not_awaited()
    assert registry.is_known(GLOBAL)
    assert discord_client.interaction_responses()[0]["data"]["content"] == "Only the bot's owners can do that."


def test_group_is_guild_only() -> None:
    """Discord doesn't enforce default_member_permissions in DMs, so the admin group must not show up there."""
    (group,) = BotCommands.app_commands()
    assert group.params().contexts == [InteractionContextType.GUILD]


def test_resync_description() -> None:
    assert BotCommands.resync.description == "Re-read the commands from Discord and push any differences"
