"""Unit tests: CHANNEL, ROLE and MENTIONABLE options, and limiting a channel option to some channel types (no network)."""

lazy from typing import TYPE_CHECKING, Annotated

lazy import pytest
lazy from wd_bot.commands import ChannelTypes, Command, Describe
lazy from wd_bot.testing import cog_command

# Command resolves option annotations from module globals at runtime, so these must be available here.
lazy from wd_discord import Channel
lazy from wd_discord import User as BoundUser
lazy from wd_discord.gateway.events import InteractionDataOption, ResolvedData
lazy from wd_discord.interactions import ApplicationCommandOptionType
lazy from wd_discord.permissions import ChannelType
lazy from wd_discord.resources.channel import Channel as ChannelModel
lazy from wd_discord.resources.guild import Role
lazy from wd_discord.resources.user import User
lazy from wd_discord.testing import role_json, user_json


if TYPE_CHECKING:
    lazy from conftest import InteractionFactory
    lazy from wd_discord import CommandInteraction
    lazy from wd_discord.testing import RecordingClient


ROLE = Role.model_validate(role_json(name="Members"))
CATEGORY = ChannelModel.model_validate({"id": "9", "type": 4, "name": "Games", "permissions": "16"})
TARGET = User.model_validate(user_json(id="4", username="target"))
RESOLVED = ResolvedData(users={"4": TARGET}, roles={"8": ROLE}, channels={"9": CATEGORY})


async def _invoke(command: Command, make_interaction: InteractionFactory, option_type: int, value: str) -> None:
    interaction = make_interaction(
        "cmd",
        options=[InteractionDataOption(name="target", type=option_type, value=value)],
        resolved=RESOLVED,
        guild_id=1,
    )
    assert await command.invoke(object(), interaction)


def test_channel_option_limited_to_categories() -> None:
    async def handler(
        self: object,
        interaction: CommandInteraction,
        target: Annotated[Channel, ChannelTypes(ChannelType.GUILD_CATEGORY)],
    ) -> None:
        """Handle."""

    (option,) = cog_command(handler, name="cmd", description="d").options()
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

    (option,) = cog_command(handler, name="cmd", description="d").options()
    assert (option.type, option.channel_types, option.required) == (
        ApplicationCommandOptionType.CHANNEL,
        [ChannelType.GUILD_VOICE],
        False,
    )


def test_channel_types_on_a_non_channel_parameter_is_refused() -> None:
    async def handler(
        self: object,
        interaction: CommandInteraction,
        target: Annotated[str, ChannelTypes(ChannelType.GUILD_TEXT)],
    ) -> None:
        """Handle."""

    with pytest.raises(TypeError, match="ChannelTypes"):
        cog_command(handler, name="cmd", description="d")


async def test_channel_option_resolves_to_a_bound_channel(make_interaction: InteractionFactory) -> None:
    received: list[Channel] = []

    async def handler(self: object, interaction: CommandInteraction, target: Channel) -> None:  # noqa: ARG001
        received.append(target)

    await _invoke(cog_command(handler, name="cmd", description="d"), make_interaction, 7, "9")
    (channel,) = received
    assert isinstance(channel, Channel)
    assert (channel.name, channel.type) == ("Games", ChannelType.GUILD_CATEGORY)


async def test_a_channel_of_another_type_is_refused(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    received: list[Channel] = []

    async def handler(
        self: object,
        interaction: CommandInteraction,  # noqa: ARG001
        target: Annotated[Channel, ChannelTypes(ChannelType.GUILD_VOICE)],
    ) -> None:
        received.append(target)

    await _invoke(cog_command(handler, name="cmd", description="d"), make_interaction, 7, "9")
    assert received == []
    assert discord_client.interaction_responses()[-1]["data"]["content"] == "Pick a voice channel for 'target'."


async def test_a_channel_of_an_allowed_type_is_passed_through(make_interaction: InteractionFactory) -> None:
    received: list[Channel] = []

    async def handler(
        self: object,
        interaction: CommandInteraction,  # noqa: ARG001
        target: Annotated[Channel, ChannelTypes(ChannelType.GUILD_VOICE, ChannelType.GUILD_CATEGORY)],
    ) -> None:
        received.append(target)

    await _invoke(cog_command(handler, name="cmd", description="d"), make_interaction, 7, "9")
    (channel,) = received
    assert channel.type is ChannelType.GUILD_CATEGORY


async def test_role_option_resolves_to_the_role(make_interaction: InteractionFactory) -> None:
    received: list[Role] = []

    async def handler(self: object, interaction: CommandInteraction, target: Role) -> None:  # noqa: ARG001
        received.append(target)

    command = cog_command(handler, name="cmd", description="d")
    assert next(command.options()).type is ApplicationCommandOptionType.ROLE
    await _invoke(command, make_interaction, 8, "8")
    assert received == [ROLE]


@pytest.mark.parametrize(("value", "expected"), [("4", "target"), ("8", "Members")])
async def test_mentionable_option_resolves_a_user_or_a_role(
    make_interaction: InteractionFactory,
    value: str,
    expected: str,
) -> None:
    received: list[BoundUser | Role] = []

    async def handler(self: object, interaction: CommandInteraction, target: BoundUser | Role) -> None:  # noqa: ARG001
        received.append(target)

    command = cog_command(handler, name="cmd", description="d")
    assert next(command.options()).type is ApplicationCommandOptionType.MENTIONABLE
    await _invoke(command, make_interaction, 9, value)
    (target,) = received
    assert (target.username if isinstance(target, BoundUser) else target.name) == expected


def test_optional_mentionable_option() -> None:
    async def handler(self: object, interaction: CommandInteraction, target: User | Role | None = None) -> None:
        """Handle."""

    (option,) = cog_command(handler, name="cmd", description="d").options()
    assert (option.type, option.required) == (ApplicationCommandOptionType.MENTIONABLE, False)


MAX_ITEMS = 25


def test_described_option_shows_its_description() -> None:
    async def handler(
        self: object,
        interaction: CommandInteraction,
        user: Annotated[BoundUser, Describe("Who to ban")],
        days: int,
    ) -> None:
        """Handle."""

    described, plain = cog_command(handler, name="cmd", description="d").options()
    assert described.description == "Who to ban"
    assert plain.description == "days"


def test_describe_inside_and_outside_the_optional_union() -> None:
    async def handler(
        self: object,
        interaction: CommandInteraction,
        inside: Annotated[str | None, Describe("Inside")] = None,
        outside: Annotated[str, Describe("Outside")] | None = None,
    ) -> None:
        """Handle."""

    inside, outside = cog_command(handler, name="cmd", description="d").options()
    assert (inside.type, inside.required, inside.description) == (ApplicationCommandOptionType.STRING, False, "Inside")
    assert (outside.type, outside.required, outside.description) == (ApplicationCommandOptionType.STRING, False, "Outside")


def test_describe_combines_with_channel_types() -> None:
    async def handler(
        self: object,
        interaction: CommandInteraction,
        target: Annotated[Channel, ChannelTypes(ChannelType.GUILD_CATEGORY), Describe("Where to move")],
    ) -> None:
        """Handle."""

    (option,) = cog_command(handler, name="cmd", description="d").options()
    assert (option.channel_types, option.description) == ([ChannelType.GUILD_CATEGORY], "Where to move")


def test_describe_renders_a_template_string() -> None:
    async def handler(
        self: object,
        interaction: CommandInteraction,
        count: Annotated[int, Describe(t"At most {MAX_ITEMS:03d}, like {'this'!r}")],
    ) -> None:
        """Handle."""

    (option,) = cog_command(handler, name="cmd", description="d").options()
    assert option.description == "At most 025, like 'this'"


def test_describe_keeps_the_template() -> None:
    describe = Describe(t"At most {MAX_ITEMS}")
    assert describe.template is not None
    assert describe.template.strings == ("At most ", "")
    assert Describe("plain").template is None


@pytest.mark.parametrize("text", ["", "x" * 101])
def test_describe_outside_discords_length_limit_is_refused(text: str) -> None:
    with pytest.raises(ValueError, match="1 to 100 characters"):
        Describe(text)


def test_two_describes_on_one_parameter_are_refused() -> None:
    async def handler(
        self: object,
        interaction: CommandInteraction,
        reason: Annotated[str, Describe("One"), Describe("Two")],
    ) -> None:
        """Handle."""

    with pytest.raises(TypeError, match="more than one Describe"):
        cog_command(handler, name="cmd", description="d")


def test_signature_changes_with_an_interpolated_description() -> None:
    def make(limit: int) -> Command:
        async def handler(
            self: object,
            interaction: CommandInteraction,
            count: Annotated[int, Describe(t"At most {limit}")],
        ) -> None:
            """Handle."""

        return cog_command(handler, name="cmd", description="d")

    assert make(5).signature() != make(10).signature()


def test_describe_naming_an_unknown_constant_fails_at_definition() -> None:
    async def handler(
        self: object,
        interaction: CommandInteraction,
        count: Annotated[int, Describe(t"At most {UNDEFINED_LIMIT}")],  # noqa: F821
    ) -> None:
        """Handle."""

    with pytest.raises(NameError, match="UNDEFINED_LIMIT"):
        cog_command(handler, name="cmd", description="d")
