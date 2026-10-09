"""Unit tests: the /channel-utils commands, deleting a category and locking channels (no network)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import unquote

import pytest
from wd_bot.commands import CommandGroup
from wd_discord import User as BoundUser
from wd_discord.audit import REASON_HEADER
from wd_discord.gateway.events import InteractionDataOption, ResolvedData
from wd_discord.interactions import ApplicationCommandOptionType
from wd_discord.permissions import ChannelType, Permissions
from wd_discord.resources.channel import Channel as ChannelModel
from wd_discord.resources.channel import PermissionOverwrite
from wd_discord.resources.guild import Role
from wd_discord.resources.user import User
from wd_discord.testing import RecordingClient

from winter_dragon.cogs.channel_utils import ChannelUtils, locked_overwrite


if TYPE_CHECKING:
    from conftest import InteractionFactory


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


def test_locked_overwrite_keeps_other_permissions() -> None:
    existing = PermissionOverwrite.model_validate({"id": "4", "type": 1, "allow": str(SEND | 1024), "deny": "64"})
    locked = locked_overwrite([existing], BoundUser(RecordingClient(), TARGET), lock=True)
    assert (locked.allow, locked.deny) == (Permissions(1024), Permissions(64) | Permissions.SEND_MESSAGES)
    unlocked = locked_overwrite(
        [existing.model_copy(update={"deny": Permissions(64) | Permissions.SEND_MESSAGES})],
        BoundUser(RecordingClient(), TARGET),
        lock=False,
    )
    assert unlocked.deny == Permissions(64)


async def test_delete_category_deletes_its_channels_then_itself(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    inside = {"id": "21", "type": 0, "guild_id": "1", "name": "chat", "parent_id": "10"}
    outside = {"id": "22", "type": 0, "guild_id": "1", "name": "rules"}
    discord_client.reply("GET", f"/guilds/{GUILD_ID}/channels", [CATEGORY, inside, outside])
    discord_client.reply("DELETE", "/channels/21", inside)
    discord_client.reply("DELETE", "/channels/10", CATEGORY)
    interaction = make_interaction(
        "channel-utils",
        options=[InteractionDataOption(name="category", type=7, value="10")],
        resolved=ResolvedData(channels={"10": ChannelModel.model_validate(CATEGORY)}),
        guild_id=GUILD_ID,
    )

    await ChannelUtils.delete_category.invoke(_cog(), interaction, interaction.options)

    deletes = [sent for sent in discord_client.sent if sent.method == "DELETE"]
    assert [sent.path for sent in deletes] == ["/channels/21", "/channels/10"]
    assert (
        unquote(deletes[0].headers[REASON_HEADER]) == "Deleted category Games by asker (3) using /channel-utils delete-category"
    )
    assert (
        discord_client.requests_to("POST", "/webhooks/2/tok")[-1].json["content"]
        == "Deleted the category Games and its channels."
    )


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
        "GET", f"/channels/{CHANNEL_ID}", _text_channel({"id": "4", "type": 1, "allow": "0", "deny": str(SEND)})
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
