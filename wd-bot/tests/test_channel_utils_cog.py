"""Unit tests: the /channel-utils commands, deleting a category and locking channels (no network)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import unquote

import pytest
from wd_bot.commands import CommandGroup
from wd_discord import PermissionOverwrite as BoundOverwrite
from wd_discord import User as BoundUser
from wd_discord.audit import REASON_HEADER
from wd_discord.errors import ApiResponseError, JsonErrorCode
from wd_discord.gateway.events import InteractionDataOption, ResolvedData
from wd_discord.interactions import ApplicationCommandOptionType
from wd_discord.permissions import ChannelType, Permissions
from wd_discord.resources.channel import Channel as ChannelModel
from wd_discord.resources.channel import PermissionOverwrite
from wd_discord.resources.guild import Role
from wd_discord.resources.user import User
from wd_discord.snowflake import Snowflake
from wd_discord.testing import GUILD_JSON, RecordingClient

from winter_dragon.cogs.channel_utils import DELETE_PERMISSIONS, ChannelUtils, deleted, locked_permissions


if TYPE_CHECKING:
    from collections.abc import Mapping

    from conftest import InteractionFactory
    from wd_discord import CommandInteraction


GUILD_ID = 1
CHANNEL_ID = 20
CATEGORY = {"id": "10", "type": 4, "name": "Games", "permissions": "16"}
ROLE = Role.model_validate(
    {
        "id": "8",
        "name": "Members",
        "color": 0,
        "hoist": False,
        "position": 1,
        "permissions": "0",
        "managed": False,
        "mentionable": True,
        "flags": 0,
    },
)
TARGET = User.model_validate({"id": "4", "username": "target", "discriminator": "0"})
SEND = int(Permissions.SEND_MESSAGES)
EVERYONE = {
    **ROLE.model_dump(mode="json"),
    "id": str(GUILD_ID),
    "name": "@everyone",
    "permissions": str(int(DELETE_PERMISSIONS)),
}
"""The ``@everyone`` role, letting the bot view and manage channels."""
BOT_MEMBER: Mapping[str, object] = {
    "user": {"id": "2", "username": "bot", "discriminator": "0", "bot": True},
    "roles": [],
    "joined_at": None,
    "deaf": False,
    "mute": False,
}
"""The bot's own member; its user ID is the interaction's application ID."""


def _cog() -> ChannelUtils:
    return ChannelUtils.__new__(ChannelUtils)


def _reply(discord_client: RecordingClient) -> str:
    return discord_client.interaction_responses()[-1]["data"]["content"]


def _text_channel(*overwrites: dict[str, object], kind: int = 0) -> dict[str, object]:
    return {
        "id": str(CHANNEL_ID),
        "type": kind,
        "guild_id": str(GUILD_ID),
        "name": "general",
        "permission_overwrites": list(overwrites),
    }


def test_commands_need_manage_channels_and_a_guild() -> None:
    (group,) = ChannelUtils.app_commands()
    assert isinstance(group, CommandGroup)
    assert group.default_member_permissions == Permissions.MANAGE_CHANNELS
    (category,) = group.subcommands["delete-category"].options()
    assert (category.type, category.channel_types) == (ApplicationCommandOptionType.CHANNEL, [ChannelType.GUILD_CATEGORY])
    assert next(group.subcommands["lock"].options()).type is ApplicationCommandOptionType.MENTIONABLE


def test_locked_permissions_keep_the_others() -> None:
    client = RecordingClient()
    model = PermissionOverwrite.model_validate({"id": "4", "type": 1, "allow": str(SEND | 1024), "deny": "64"})
    existing = BoundOverwrite(client, model, Snowflake(CHANNEL_ID), Snowflake(GUILD_ID))
    locked = locked_permissions([existing], BoundUser(client, TARGET), lock=True)
    assert locked == (Permissions(1024), Permissions(64) | Permissions.SEND_MESSAGES)
    denied = model.model_copy(update={"deny": Permissions(64) | Permissions.SEND_MESSAGES})
    _, deny = locked_permissions(
        [BoundOverwrite(client, denied, Snowflake(CHANNEL_ID), Snowflake(GUILD_ID))],
        BoundUser(client, TARGET),
        lock=False,
    )
    assert deny == Permissions(64)


def _delete_category(make_interaction: InteractionFactory, app_permissions: Permissions | None = None) -> CommandInteraction:
    return make_interaction(
        "channel-utils",
        options=[InteractionDataOption(name="category", type=7, value="10")],
        resolved=ResolvedData(channels={"10": ChannelModel.model_validate(CATEGORY)}),
        guild_id=GUILD_ID,
        app_permissions=app_permissions,
    )


def _serve_guild(discord_client: RecordingClient, *channels: Mapping[str, object]) -> None:
    discord_client.reply("GET", f"/guilds/{GUILD_ID}", {**GUILD_JSON, "roles": [EVERYONE]})
    discord_client.reply("GET", f"/guilds/{GUILD_ID}/members/2", BOT_MEMBER)
    discord_client.reply("GET", f"/guilds/{GUILD_ID}/channels", [CATEGORY, *channels])


def _followup(discord_client: RecordingClient) -> str:
    return discord_client.requests_to("POST", "/webhooks/2/tok")[-1].json["content"]


async def test_delete_category_deletes_its_channels_then_itself(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    inside = {"id": "21", "type": 0, "guild_id": "1", "name": "chat", "parent_id": "10"}
    outside = {"id": "22", "type": 0, "guild_id": "1", "name": "rules"}
    _serve_guild(discord_client, inside, outside)
    discord_client.reply("DELETE", "/channels/21", inside)
    discord_client.reply("DELETE", "/channels/10", CATEGORY)
    interaction = _delete_category(make_interaction, DELETE_PERMISSIONS)

    await ChannelUtils.delete_category.invoke(_cog(), interaction, interaction.options)

    deletes = [sent for sent in discord_client.sent if sent.method == "DELETE"]
    assert [sent.path for sent in deletes] == ["/channels/21", "/channels/10"]
    assert (
        unquote(deletes[0].headers[REASON_HEADER]) == "Deleted category Games by asker (3) using /channel-utils delete-category"
    )
    assert _followup(discord_client) == "Deleted the category Games and its channels."


async def test_delete_category_deletes_nothing_when_a_channel_is_hidden_from_the_bot(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    hide = {"id": str(GUILD_ID), "type": 0, "allow": "0", "deny": str(int(Permissions.VIEW_CHANNEL))}
    hidden = {"id": "21", "type": 0, "guild_id": "1", "name": "secret", "parent_id": "10", "permission_overwrites": [hide]}
    seen = {"id": "23", "type": 0, "guild_id": "1", "name": "chat", "parent_id": "10"}
    _serve_guild(discord_client, hidden, seen)
    interaction = _delete_category(make_interaction)

    await ChannelUtils.delete_category.invoke(_cog(), interaction, interaction.options)

    assert [sent.path for sent in discord_client.sent if sent.method == "DELETE"] == []
    assert _followup(discord_client).startswith("I can't see or manage: secret.")


async def test_delete_category_refuses_up_front_without_the_bot_permissions(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    interaction = _delete_category(make_interaction, Permissions.VIEW_CHANNEL)

    await ChannelUtils.delete_category.invoke(_cog(), interaction, interaction.options)

    assert [sent.method for sent in discord_client.sent if sent.method != "POST"] == []
    assert _reply(discord_client) == "I need the View Channels and Manage Channels permissions to do that."


def test_a_channel_already_gone_counts_as_deleted() -> None:
    assert deleted(ApiResponseError(code=JsonErrorCode.UNKNOWN_CHANNEL, message="Unknown Channel"))
    assert not deleted(ApiResponseError(code=JsonErrorCode.MISSING_ACCESS, message="Missing Access"))


@pytest.mark.parametrize(
    ("target", "option_type", "resolved", "overwrite_type"),
    [
        ("4", 6, ResolvedData(users={"4": TARGET}), 1),
        ("8", 8, ResolvedData(roles={"8": ROLE}), 0),
    ],
)
async def test_lock_denies_send_messages(  # noqa: PLR0913 - parametrized
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
    target: str,
    option_type: int,
    resolved: ResolvedData,
    overwrite_type: int,
) -> None:
    discord_client.reply("GET", f"/channels/{CHANNEL_ID}", _text_channel())
    interaction = make_interaction(
        "channel-utils",
        options=[InteractionDataOption(name="target", type=option_type, value=target)],
        resolved=resolved,
        guild_id=GUILD_ID,
        channel_id=CHANNEL_ID,
    )

    await ChannelUtils.lock.invoke(_cog(), interaction, interaction.options)

    (put,) = discord_client.requests_to("PUT", f"/channels/{CHANNEL_ID}/permissions/{target}")
    assert put.json == {"id": target, "type": overwrite_type, "allow": "0", "deny": str(SEND)}
    assert _reply(discord_client).startswith("Locked this channel for")


async def test_unlock_removes_an_overwrite_left_empty(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    discord_client.reply(
        "GET",
        f"/channels/{CHANNEL_ID}",
        _text_channel({"id": "4", "type": 1, "allow": "0", "deny": str(SEND)}),
    )
    interaction = make_interaction(
        "channel-utils",
        options=[InteractionDataOption(name="target", type=9, value="4")],
        resolved=ResolvedData(users={"4": TARGET}),
        channel_id=CHANNEL_ID,
    )

    await ChannelUtils.unlock.invoke(_cog(), interaction, interaction.options)

    assert len(discord_client.requests_to("DELETE", f"/channels/{CHANNEL_ID}/permissions/4")) == 1
    assert _reply(discord_client) == "Unlocked this channel for <@4>."


async def test_unlock_without_an_overwrite_changes_nothing(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    discord_client.reply("GET", f"/channels/{CHANNEL_ID}", _text_channel())
    interaction = make_interaction(
        "channel-utils",
        options=[InteractionDataOption(name="target", type=9, value="4")],
        resolved=ResolvedData(users={"4": TARGET}),
        channel_id=CHANNEL_ID,
    )

    await ChannelUtils.unlock.invoke(_cog(), interaction, interaction.options)

    assert [sent.method for sent in discord_client.sent if "/permissions/" in sent.path] == []


async def test_lock_refuses_threads(make_interaction: InteractionFactory, discord_client: RecordingClient) -> None:
    discord_client.reply("GET", f"/channels/{CHANNEL_ID}", _text_channel(kind=11))
    interaction = make_interaction(
        "channel-utils",
        options=[InteractionDataOption(name="target", type=9, value="4")],
        resolved=ResolvedData(users={"4": TARGET}),
        channel_id=CHANNEL_ID,
    )

    await ChannelUtils.lock.invoke(_cog(), interaction, interaction.options)

    assert _reply(discord_client) == "You can't lock or unlock this channel."
