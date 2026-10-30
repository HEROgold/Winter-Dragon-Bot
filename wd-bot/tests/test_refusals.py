"""Unit tests: guild-only handlers get guild interactions, and a refused action answers the user privately."""

lazy import asyncio
lazy import logging
lazy from typing import TYPE_CHECKING, ClassVar

lazy import pytest
lazy from wd_bot.bot import Bot
lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_bot.guard import dispatch_guard
lazy from wd_discord import (
    GuildCommandInteraction,
    GuildComponentInteraction,
    narrow_to_guild,
)
lazy from wd_discord.errors import ApiResponseError, JsonErrorCode
lazy from wd_discord.gateway import EventName
lazy from wd_discord.gateway.events import Message as MessageModel
lazy from wd_discord.interactions import InteractionContextType
lazy from wd_discord.permissions import Permissions
lazy from wd_discord.testing import message_json, user_json
lazy from wd_errors import Refused, unwrap


if TYPE_CHECKING:
    lazy from conftest import ComponentInteractionFactory, InteractionFactory
    lazy from wd_discord import CommandInteraction, ComponentInteraction, Message
    lazy from wd_discord.testing import RecordingClient

EPHEMERAL = 1 << 6
GUILD = [InteractionContextType.GUILD]


class _Server(Cog, auto_load=False):
    """A guild-only cog recording who invoked it, from where."""

    seen: list[tuple[int, int]]

    @Cog.command(name="where", description="d", contexts=GUILD)
    async def where(self, interaction: GuildCommandInteraction) -> None:
        self.seen.append((int(interaction.guild_id), int(interaction.user.id)))
        await interaction.respond("here")

    @Cog.command(name="purge", description="d", contexts=GUILD, requires=Permissions.MANAGE_MESSAGES)
    async def purge(self, interaction: GuildCommandInteraction) -> None:
        await interaction.respond("purged")

    @Cog.command(name="slow", description="d", contexts=GUILD)
    async def slow(self, interaction: GuildCommandInteraction) -> None:
        await interaction.defer()
        msg = "Not today."
        raise Refused(msg)

    @Cog.component("knock")
    async def knock(self, interaction: GuildComponentInteraction) -> None:
        self.seen.append((int(interaction.guild_id), int(interaction.user.id)))


def _server() -> _Server:
    cog = _Server.__new__(_Server)
    cog.seen = []
    return cog


def _only_answer(client: RecordingClient) -> dict[str, object]:
    (response,) = client.interaction_responses()
    return response["data"]


async def test_a_guild_only_command_gets_the_guild_and_member(make_interaction: InteractionFactory) -> None:
    cog = _server()

    await _Server.where.invoke(cog, make_interaction("where", guild_id=7))

    assert cog.seen == [(7, 3)]


async def test_a_guild_only_command_refuses_outside_a_server(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    cog = _server()

    await _Server.where.invoke(cog, make_interaction("where"))

    assert cog.seen == []
    assert _only_answer(discord_client) == {"content": "This only works in a server.", "flags": EPHEMERAL}


async def test_requires_names_the_missing_permission(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    held = Permissions.SEND_MESSAGES
    await _Server.purge.invoke(_server(), make_interaction("purge", guild_id=7, permissions=held))

    assert _only_answer(discord_client)["content"] == "You need the Manage Messages permission for that."


async def test_requires_lets_holders_and_administrators_through(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    for held in (Permissions.MANAGE_MESSAGES, Permissions.ADMINISTRATOR):
        await _Server.purge.invoke(_server(), make_interaction("purge", guild_id=7, permissions=held))

    assert [response["data"]["content"] for response in discord_client.interaction_responses()] == ["purged"] * 2


async def test_a_refusal_after_deferring_is_a_private_followup(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    await _Server.slow.invoke(_server(), make_interaction("slow", guild_id=7))

    (followup,) = discord_client.requests_to("POST", "/webhooks/2/tok")
    assert followup.json == {"content": "Not today.", "flags": EPHEMERAL}


async def test_a_component_inherits_its_cogs_guild_narrowing(
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    cog = _server()

    await _Server.knock.invoke(cog, make_component_interaction("knock", guild_id=7), [])
    await _Server.knock.invoke(cog, make_component_interaction("knock"), [])

    assert cog.seen == [(7, 3)]
    assert _only_answer(discord_client)["content"] == "This only works in a server."


async def test_add_cog_rejects_a_guild_handler_on_a_command_offered_everywhere() -> None:
    class Anywhere(Cog, auto_load=False):
        @Cog.command(name="anywhere", description="d")
        async def anywhere(self, interaction: GuildCommandInteraction) -> None: ...

    bot = Bot()
    bot.loop = asyncio.get_running_loop()

    with pytest.raises(TypeError, match="isn't registered with contexts=\\[GUILD\\]"):
        await bot.add_cog(Anywhere(bot=bot))


async def test_add_cog_rejects_a_guild_component_on_a_cog_offered_everywhere() -> None:
    class Mixed(Cog, auto_load=False):
        @Cog.command(name="dm", description="d")
        async def dm(self, interaction: CommandInteraction) -> None: ...

        @Cog.component("press")
        async def press(self, interaction: GuildComponentInteraction) -> None: ...

    bot = Bot()
    bot.loop = asyncio.get_running_loop()

    with pytest.raises(TypeError, match="the cog isn't guild-only"):
        await bot.add_cog(Mixed(bot=bot))


def test_narrowing_shares_the_response_state(make_interaction: InteractionFactory) -> None:
    interaction = make_interaction(guild_id=7)

    narrowed = narrow_to_guild(interaction)

    assert isinstance(narrowed, GuildCommandInteraction)
    assert narrowed._state is interaction._state  # noqa: SLF001 - the same interaction, two views
    assert narrow_to_guild(make_interaction()) is None


def test_unwrap_passes_values_and_refuses_failures() -> None:
    error = ApiResponseError(code=JsonErrorCode.MISSING_ACCESS, message="Missing Access")

    assert unwrap(5, "unused") == 5
    with pytest.raises(Refused, match="see that channel") as refused:
        unwrap(error, "I can't see that channel.")
    assert refused.value.cause is error


async def test_a_subcommand_of_a_guild_only_group_gets_a_guild_interaction(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    class Group(GroupCog, name="g", description="d", contexts=GUILD, auto_load=False):
        seen: list[int]

        @Cog.command(name="sub", description="d")
        async def sub(self, interaction: GuildCommandInteraction) -> None:
            self.seen.append(int(interaction.guild_id))

    cog = Group.__new__(Group)
    cog.seen = []

    await Group.sub.invoke(cog, make_interaction("g", guild_id=7))
    await Group.sub.invoke(cog, make_interaction("g"))

    assert cog.seen == [7]
    assert _only_answer(discord_client)["content"] == "This only works in a server."


class _Doorman(Cog, auto_load=False):
    """A cog whose command, button and listener all turn everyone away, or all break."""

    breaks: ClassVar[bool] = False

    @classmethod
    def _turn_away(cls) -> None:
        if cls.breaks:
            msg = "the door is stuck"
            raise RuntimeError(msg)
        msg = "Members only."
        raise Refused(msg)

    @Cog.command(name="enter", description="d")
    async def enter(self, interaction: CommandInteraction) -> None:  # noqa: ARG002
        self._turn_away()

    @Cog.component("enter")
    async def enter_button(self, interaction: ComponentInteraction) -> None:  # noqa: ARG002
        self._turn_away()

    @Cog.listener(EventName.MESSAGE_CREATE)
    async def on_message_create(self, message: Message) -> None:  # noqa: ARG002
        self._turn_away()


async def _knock_everywhere(
    make_interaction: InteractionFactory,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
    caplog: pytest.LogCaptureFixture,
) -> list[logging.LogRecord]:
    """Run ``/enter``, click the ``enter`` button and post a message through a Bot; return what wd-bot logged about them."""
    bot = Bot()
    bot.loop = asyncio.get_running_loop()
    bot.client = discord_client
    await bot.add_cog(_Doorman(bot=bot))
    data = message_json(id="1", channel_id="2", author=user_json(), content="hi", timestamp="2026-10-22T00:00:00+00:00")
    dispatch_guard.logger.addHandler(caplog.handler)
    try:
        await bot._dispatch_interaction(make_interaction("enter"))
        await bot._dispatch_interaction(make_component_interaction("enter"))
        await bot._dispatch(EventName.MESSAGE_CREATE, MessageModel.model_validate(data))
        await asyncio.gather(*(task for task in asyncio.all_tasks() if task is not asyncio.current_task()))
    finally:
        dispatch_guard.logger.removeHandler(caplog.handler)
    return caplog.records


async def test_a_component_and_a_listener_refuse_like_a_command(
    make_interaction: InteractionFactory,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _Doorman.breaks = False

    records = await _knock_everywhere(make_interaction, make_component_interaction, discord_client, caplog)

    assert [response["data"] for response in discord_client.interaction_responses()] == [
        {"content": "Members only.", "flags": EPHEMERAL},
    ] * 2
    assert [(record.levelno, record.getMessage().partition(" refused: ")[2]) for record in records] == [
        (logging.INFO, "Members only. (None)"),
    ] * 3


async def test_a_component_and_a_listener_report_a_crash_like_a_command(
    make_interaction: InteractionFactory,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
    caplog: pytest.LogCaptureFixture,
    error_reply: dict[str, object],
) -> None:
    _Doorman.breaks = True

    records = await _knock_everywhere(make_interaction, make_component_interaction, discord_client, caplog)

    assert [response["data"] for response in discord_client.interaction_responses()] == [error_reply] * 2
    assert [(record.levelno, record.getMessage().startswith("Unhandled exception in ")) for record in records] == [
        (logging.ERROR, True),
    ] * 3
    assert [str(record.exc_info[1]) for record in records if record.exc_info] == ["the door is stuck"] * 3
