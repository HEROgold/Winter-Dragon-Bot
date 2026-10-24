"""Shared fixtures for the wd-bot test suite: an in-memory database, a recording client, and interaction builders."""

lazy from typing import TYPE_CHECKING, Protocol

lazy import pytest
lazy from sqlalchemy import BigInteger
lazy from sqlalchemy.ext.compiler import compiles
lazy from sqlalchemy.pool import StaticPool
lazy from sqlmodel import SQLModel, create_engine
lazy from wd_discord import CommandInteraction, ComponentInteraction
lazy from wd_discord.components import ComponentType
lazy from wd_discord.gateway.events import CommandInteraction as CommandInteractionModel
lazy from wd_discord.gateway.events import ComponentInteraction as ComponentInteractionModel
lazy from wd_discord.gateway.events import InteractionData, InteractionType, MessageComponentData
lazy from wd_discord.permissions import Permissions
lazy from wd_discord.resources.guild import GuildMember
lazy from wd_discord.resources.user import User
lazy from wd_discord.testing import RecordingClient


if TYPE_CHECKING:
    lazy from collections.abc import Sequence

    lazy from sqlalchemy import Engine
    lazy from wd_discord.gateway.events import InteractionDataOption, ResolvedData


@compiles(BigInteger, "sqlite")
def _bigint_as_integer(_type: BigInteger, _compiler: object, **_kwargs: object) -> str:
    """Render BigInteger as INTEGER on sqlite.

    wd_db's SQLModel.id is a BigInteger primary key, which sqlite only autoincrements when the
    column type is exactly INTEGER. Postgres (production) is unaffected.
    """
    return "INTEGER"


@pytest.fixture
def discord_client() -> RecordingClient:
    """Return a client that records requests instead of sending them; the builders' interactions use it."""
    return RecordingClient()


@pytest.fixture
def engine() -> Engine:
    """Return an in-memory sqlite engine with every table created, shared across threads."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return engine


class InteractionFactory(Protocol):
    """Builds an application-command interaction, as the ``make_interaction`` fixture returns."""

    def __call__(  # noqa: PLR0913 - mirrors the fixture's builder
        self,
        name: str = "c",
        *,
        options: Sequence[InteractionDataOption] = (),
        resolved: ResolvedData | None = None,
        user: User | None = ...,
        guild_id: int | None = None,
        channel_id: int | None = None,
        permissions: Permissions | None = None,
        app_permissions: Permissions | None = None,
    ) -> CommandInteraction:
        """Build the interaction."""
        ...


ASKER = User.model_validate({"id": "3", "username": "asker", "discriminator": "0"})
"""The default invoking user of :func:`make_interaction`."""

_ERROR_REPLY = {
    "embeds": [
        {
            "title": "Something went wrong",
            "description": "Something went wrong running this command.",
            "color": 0xFF0000,
            "footer": {"text": "If it keeps happening, tell the bot's owners this ID: 1"},
        },
    ],
    "flags": 64,
}
"""The ephemeral error reply to interaction 1 (the ID ``make_interaction`` and ``make_component_interaction`` give)."""


@pytest.fixture
def error_reply() -> dict[str, object]:
    """Return the ephemeral error reply wd-bot sends to interaction 1 when its handler raises."""
    return _ERROR_REPLY

DEFAULT_GUILD_ID = 1
"""The guild a :func:`make_interaction` member is in when the test names none: Discord sends members with their guild."""
DEFAULT_CHANNEL_ID = 2
"""The channel a guild interaction comes from when a test doesn't say."""


def _sender(
    user: User | None,
    guild_id: int | None,
    channel_id: int | None,
    permissions: Permissions | None,
) -> dict[str, object]:
    """Return who sent an interaction from where, as Discord does: from a guild, the user comes inside ``member``."""
    if guild_id is None and permissions is None:
        return {"user": user, "channel_id": channel_id}
    member = GuildMember(user=user, roles=[], joined_at=None, deaf=False, mute=False, permissions=permissions)
    channel = channel_id if channel_id is not None else DEFAULT_CHANNEL_ID
    return {"member": member, "guild_id": DEFAULT_GUILD_ID if guild_id is None else guild_id, "channel_id": channel}


@pytest.fixture
def make_interaction(discord_client: RecordingClient) -> InteractionFactory:
    """Return a builder for a ``/name`` interaction with the given options, invoked by ``user``, bound to ``discord_client``.

    ``guild_id`` and ``channel_id`` say where it was sent from; by default, nowhere in particular. From a guild,
    ``user`` is a member holding ``permissions``; ``app_permissions`` are the bot's in that channel.
    """

    def build(  # noqa: PLR0913 - one keyword per interaction field a test may set
        name: str = "c",
        *,
        options: Sequence[InteractionDataOption] = (),
        resolved: ResolvedData | None = None,
        user: User | None = ASKER,
        guild_id: int | None = None,
        channel_id: int | None = None,
        permissions: Permissions | None = None,
        app_permissions: Permissions | None = None,
    ) -> CommandInteraction:
        model = CommandInteractionModel(
            id="1",
            application_id="2",
            type=InteractionType.APPLICATION_COMMAND,
            token="tok",  # noqa: S106
            version=1,
            **_sender(user, guild_id, channel_id, permissions),  # pyright: ignore[reportArgumentType]
            app_permissions=app_permissions,
            data=InteractionData(id="10", name=name, type=1, options=list(options), resolved=resolved),
        )
        return CommandInteraction(discord_client, model)

    return build


class ComponentInteractionFactory(Protocol):
    """Builds a button-click interaction, as the ``make_component_interaction`` fixture returns."""

    def __call__(
        self,
        custom_id: str,
        *,
        user: User | None = ...,
        guild_id: int | None = None,
        permissions: Permissions | None = None,
    ) -> ComponentInteraction:
        """Build the interaction."""
        ...


@pytest.fixture
def make_component_interaction(discord_client: RecordingClient) -> ComponentInteractionFactory:
    """Return a builder for a click on the button ``custom_id``, by ``user``, bound to ``discord_client``.

    ``guild_id`` makes it a click on a message in that guild, by a member holding ``permissions``.
    """

    def build(
        custom_id: str,
        *,
        user: User | None = ASKER,
        guild_id: int | None = None,
        permissions: Permissions | None = None,
    ) -> ComponentInteraction:
        model = ComponentInteractionModel(
            id="1",
            application_id="2",
            type=InteractionType.MESSAGE_COMPONENT,
            token="tok",  # noqa: S106
            version=1,
            **_sender(user, guild_id, None, permissions),  # pyright: ignore[reportArgumentType]
            data=MessageComponentData(custom_id=custom_id, component_type=ComponentType.BUTTON),
            message={"id": "11"},
        )
        return ComponentInteraction(discord_client, model)

    return build
