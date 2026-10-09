"""Unit tests: CHANNEL, ROLE and MENTIONABLE options, and limiting a channel option to some channel types (no network)."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING, Annotated

lazy import pytest
lazy from wd_bot.commands import ChannelTypes, Command

# Command resolves option annotations from module globals at runtime, so these must be available here.
lazy from wd_discord import Channel
lazy from wd_discord import User as BoundUser
lazy from wd_discord.gateway.events import InteractionDataOption, ResolvedData
lazy from wd_discord.interactions import ApplicationCommandOptionType
lazy from wd_discord.permissions import ChannelType
lazy from wd_discord.resources.channel import Channel as ChannelModel
lazy from wd_discord.resources.guild import Role
lazy from wd_discord.resources.user import User


if TYPE_CHECKING:
    lazy from conftest import InteractionFactory
    lazy from wd_discord import CommandInteraction


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
CATEGORY = ChannelModel.model_validate({"id": "9", "type": 4, "name": "Games", "permissions": "16"})
TARGET = User.model_validate({"id": "4", "username": "target", "discriminator": "0"})
RESOLVED = ResolvedData(users={"4": TARGET}, roles={"8": ROLE}, channels={"9": CATEGORY})


async def _invoke(command: Command, make_interaction: InteractionFactory, option_type: int, value: str) -> None:
    interaction = make_interaction(
        "cmd", options=[InteractionDataOption(name="target", type=option_type, value=value)], resolved=RESOLVED
    )
    assert await command.invoke(object(), interaction)


def test_channel_option_limited_to_categories() -> None:
    async def handler(
        self: object, interaction: CommandInteraction, target: Annotated[Channel, ChannelTypes(ChannelType.GUILD_CATEGORY)]
    ) -> None:
        """Handle."""

    (option,) = Command(handler, name="cmd", description="d").options()
    assert option.type is ApplicationCommandOptionType.CHANNEL
    assert option.channel_types == [ChannelType.GUILD_CATEGORY]
    assert option.required is True


def test_optional_annotated_channel_option() -> None:
    async def handler(
        self: object,
        interaction: CommandInteraction,
        target: Annotated[ChannelModel, ChannelTypes(ChannelType.GUILD_VOICE)] | None = None,
    ) -> None:
        """Handle."""

    (option,) = Command(handler, name="cmd", description="d").options()
    assert (option.type, option.channel_types, option.required) == (
        ApplicationCommandOptionType.CHANNEL,
        [ChannelType.GUILD_VOICE],
        False,
    )


def test_channel_types_on_a_non_channel_parameter_is_refused() -> None:
    async def handler(
        self: object, interaction: CommandInteraction, target: Annotated[str, ChannelTypes(ChannelType.GUILD_TEXT)]
    ) -> None:
        """Handle."""

    with pytest.raises(TypeError, match="ChannelTypes"):
        Command(handler, name="cmd", description="d")


async def test_channel_option_resolves_to_a_bound_channel(make_interaction: InteractionFactory) -> None:
    received: list[Channel] = []

    async def handler(self: object, interaction: CommandInteraction, target: Channel) -> None:  # noqa: ARG001
        received.append(target)

    await _invoke(Command(handler, name="cmd", description="d"), make_interaction, 7, "9")
    (channel,) = received
    assert isinstance(channel, Channel)
    assert (channel.name, channel.type) == ("Games", ChannelType.GUILD_CATEGORY)


async def test_role_option_resolves_to_the_role(make_interaction: InteractionFactory) -> None:
    received: list[Role] = []

    async def handler(self: object, interaction: CommandInteraction, target: Role) -> None:  # noqa: ARG001
        received.append(target)

    command = Command(handler, name="cmd", description="d")
    assert next(command.options()).type is ApplicationCommandOptionType.ROLE
    await _invoke(command, make_interaction, 8, "8")
    assert received == [ROLE]


@pytest.mark.parametrize(("value", "expected"), [("4", "target"), ("8", "Members")])
async def test_mentionable_option_resolves_a_user_or_a_role(
    make_interaction: InteractionFactory, value: str, expected: str
) -> None:
    received: list[BoundUser | Role] = []

    async def handler(self: object, interaction: CommandInteraction, target: BoundUser | Role) -> None:  # noqa: ARG001
        received.append(target)

    command = Command(handler, name="cmd", description="d")
    assert next(command.options()).type is ApplicationCommandOptionType.MENTIONABLE
    await _invoke(command, make_interaction, 9, value)
    (target,) = received
    assert (target.username if isinstance(target, BoundUser) else target.name) == expected


def test_optional_mentionable_option() -> None:
    async def handler(self: object, interaction: CommandInteraction, target: User | Role | None = None) -> None:
        """Handle."""

    (option,) = Command(handler, name="cmd", description="d").options()
    assert (option.type, option.required) == (ApplicationCommandOptionType.MENTIONABLE, False)
