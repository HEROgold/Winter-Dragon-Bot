"""The MIT License (MIT).

Copyright (c) 2015-present Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, NotRequired, TypedDict, Union

from .components import ComponentBase


if TYPE_CHECKING:
    from .channel import ChannelTypeWithoutThread, GroupDMChannel, GuildChannel, InteractionDMChannel
    from .guild import GuildFeature
    from .member import Member
    from .message import Attachment, Message
    from .role import Role
    from .sku import Entitlement
    from .snowflake import Snowflake
    from .threads import ThreadMetadata, ThreadType
    from .user import User


InteractionType = Literal[1, 2, 3, 4, 5]
InteractionResponseType = Literal[
    1,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
]
InteractionContextType = Literal[0, 1, 2]
InteractionInstallationType = Literal[0, 1]


class _BasePartialChannel(TypedDict):
    id: Snowflake
    name: str
    permissions: str


class PartialChannel(_BasePartialChannel):
    type: ChannelTypeWithoutThread
    topic: NotRequired[str]
    position: int
    nsfw: bool
    flags: int
    rate_limit_per_user: int
    parent_id: Snowflake | None
    last_message_id: Snowflake | None
    last_pin_timestamp: NotRequired[str]


class PartialThread(_BasePartialChannel):
    type: ThreadType
    thread_metadata: ThreadMetadata
    parent_id: Snowflake
    applied_tags: NotRequired[list[Snowflake]]
    owner_id: Snowflake
    message_count: int
    member_count: int
    rate_limit_per_user: int
    last_message_id: NotRequired[Snowflake | None]
    flags: NotRequired[int]
    total_message_sent: int


class ResolvedData(TypedDict, total=False):
    users: dict[str, User]
    members: dict[str, Member]
    roles: dict[str, Role]
    channels: dict[str, PartialChannel | PartialThread]
    messages: dict[str, Message]
    attachments: dict[str, Attachment]


class PartialInteractionGuild(TypedDict):
    id: Snowflake
    locale: str
    features: list[GuildFeature]


class _BaseApplicationCommandInteractionDataOption(TypedDict):
    name: str


class _CommandGroupApplicationCommandInteractionDataOption(_BaseApplicationCommandInteractionDataOption):
    type: Literal[1, 2]
    options: list[ApplicationCommandInteractionDataOption]


class _BaseValueApplicationCommandInteractionDataOption(_BaseApplicationCommandInteractionDataOption, total=False):
    focused: bool


class _StringValueApplicationCommandInteractionDataOption(_BaseValueApplicationCommandInteractionDataOption):
    type: Literal[3]
    value: str


class _IntegerValueApplicationCommandInteractionDataOption(_BaseValueApplicationCommandInteractionDataOption):
    type: Literal[4]
    value: int


class _BooleanValueApplicationCommandInteractionDataOption(_BaseValueApplicationCommandInteractionDataOption):
    type: Literal[5]
    value: bool


class _SnowflakeValueApplicationCommandInteractionDataOption(_BaseValueApplicationCommandInteractionDataOption):
    type: Literal[6, 7, 8, 9, 11]
    value: Snowflake


class _NumberValueApplicationCommandInteractionDataOption(_BaseValueApplicationCommandInteractionDataOption):
    type: Literal[10]
    value: float


_ValueApplicationCommandInteractionDataOption = Union[
    _StringValueApplicationCommandInteractionDataOption,
    _IntegerValueApplicationCommandInteractionDataOption,
    _BooleanValueApplicationCommandInteractionDataOption,
    _SnowflakeValueApplicationCommandInteractionDataOption,
    _NumberValueApplicationCommandInteractionDataOption,
]


ApplicationCommandInteractionDataOption = Union[
    _CommandGroupApplicationCommandInteractionDataOption,
    _ValueApplicationCommandInteractionDataOption,
]


class _BaseApplicationCommandInteractionData(TypedDict):
    id: Snowflake
    name: str
    resolved: NotRequired[ResolvedData]
    guild_id: NotRequired[Snowflake]


class ChatInputApplicationCommandInteractionData(_BaseApplicationCommandInteractionData, total=False):
    type: Literal[1]
    options: list[ApplicationCommandInteractionDataOption]


class _BaseNonChatInputApplicationCommandInteractionData(_BaseApplicationCommandInteractionData):
    target_id: Snowflake


class UserApplicationCommandInteractionData(_BaseNonChatInputApplicationCommandInteractionData):
    type: Literal[2]


class MessageApplicationCommandInteractionData(_BaseNonChatInputApplicationCommandInteractionData):
    type: Literal[3]


ApplicationCommandInteractionData = Union[
    ChatInputApplicationCommandInteractionData,
    UserApplicationCommandInteractionData,
    MessageApplicationCommandInteractionData,
]


class _BaseMessageComponentInteractionData(TypedDict):
    custom_id: str


class ButtonMessageComponentInteractionData(_BaseMessageComponentInteractionData):
    component_type: Literal[2]


class SelectMessageComponentInteractionData(_BaseMessageComponentInteractionData):
    component_type: Literal[3, 5, 6, 7, 8]
    values: list[str]
    resolved: NotRequired[ResolvedData]


MessageComponentInteractionData = Union[ButtonMessageComponentInteractionData, SelectMessageComponentInteractionData]


class ModalSubmitTextInputInteractionData(ComponentBase):
    type: Literal[4]
    custom_id: str
    value: str


class ModalSubmitSelectInteractionData(ComponentBase):
    type: Literal[3, 5, 6, 7, 8]
    custom_id: str
    values: list[str]


class ModalSubmitFileUploadInteractionData(ComponentBase):
    type: Literal[19]
    custom_id: str
    values: list[str]


ModalSubmitComponentItemInteractionData = Union[
    ModalSubmitSelectInteractionData, ModalSubmitTextInputInteractionData, ModalSubmitFileUploadInteractionData
]


class ModalSubmitActionRowInteractionData(TypedDict):
    type: Literal[1]
    components: list[ModalSubmitComponentItemInteractionData]


class ModalSubmitTextDisplayInteractionData(ComponentBase):
    type: Literal[10]
    content: str


class ModalSubmitLabelInteractionData(ComponentBase):
    type: Literal[18]
    component: ModalSubmitComponentItemInteractionData


ModalSubmitComponentInteractionData = Union[
    ModalSubmitActionRowInteractionData,
    ModalSubmitTextDisplayInteractionData,
    ModalSubmitLabelInteractionData,
]


class ModalSubmitInteractionData(TypedDict):
    custom_id: str
    components: list[ModalSubmitComponentInteractionData]
    resolved: NotRequired[ResolvedData]


InteractionData = Union[
    ApplicationCommandInteractionData,
    MessageComponentInteractionData,
    ModalSubmitInteractionData,
]


class _BaseInteraction(TypedDict):
    id: Snowflake
    application_id: Snowflake
    token: str
    version: Literal[1]
    guild_id: NotRequired[Snowflake]
    guild: NotRequired[PartialInteractionGuild]
    channel_id: NotRequired[Snowflake]
    channel: GuildChannel | InteractionDMChannel | GroupDMChannel
    app_permissions: NotRequired[str]
    locale: NotRequired[str]
    guild_locale: NotRequired[str]
    entitlement_sku_ids: NotRequired[list[Snowflake]]
    entitlements: NotRequired[list[Entitlement]]
    authorizing_integration_owners: dict[Literal["0", "1"], Snowflake]
    context: NotRequired[InteractionContextType]
    attachment_size_limit: int


class PingInteraction(_BaseInteraction):
    type: Literal[1]


class ApplicationCommandInteraction(_BaseInteraction):
    type: Literal[2, 4]
    data: ApplicationCommandInteractionData


class MessageComponentInteraction(_BaseInteraction):
    type: Literal[3]
    data: MessageComponentInteractionData


class ModalSubmitInteraction(_BaseInteraction):
    type: Literal[5]
    data: ModalSubmitInteractionData


Interaction = Union[PingInteraction, ApplicationCommandInteraction, MessageComponentInteraction, ModalSubmitInteraction]


class MessageInteraction(TypedDict):
    id: Snowflake
    type: InteractionType
    name: str
    user: User
    member: NotRequired[Member]


class _MessageInteractionMetadata(TypedDict):
    id: Snowflake
    user: User
    authorizing_integration_owners: dict[Literal["0", "1"], Snowflake]
    original_response_message_id: NotRequired[Snowflake]


class _ApplicationCommandMessageInteractionMetadata(_MessageInteractionMetadata):
    type: Literal[2]
    # command_type: Literal[1, 2, 3, 4]


class UserApplicationCommandMessageInteractionMetadata(_ApplicationCommandMessageInteractionMetadata):
    # command_type: Literal[2]
    target_user: User


class MessageApplicationCommandMessageInteractionMetadata(_ApplicationCommandMessageInteractionMetadata):
    # command_type: Literal[3]
    target_message_id: Snowflake


ApplicationCommandMessageInteractionMetadata = Union[
    _ApplicationCommandMessageInteractionMetadata,
    UserApplicationCommandMessageInteractionMetadata,
    MessageApplicationCommandMessageInteractionMetadata,
]


class MessageComponentMessageInteractionMetadata(_MessageInteractionMetadata):
    type: Literal[3]
    interacted_message_id: Snowflake


class ModalSubmitMessageInteractionMetadata(_MessageInteractionMetadata):
    type: Literal[5]
    triggering_interaction_metadata: ApplicationCommandMessageInteractionMetadata | MessageComponentMessageInteractionMetadata


MessageInteractionMetadata = Union[
    ApplicationCommandMessageInteractionMetadata,
    MessageComponentMessageInteractionMetadata,
    ModalSubmitMessageInteractionMetadata,
]


class InteractionCallbackResponse(TypedDict):
    id: Snowflake
    type: InteractionType
    activity_instance_id: NotRequired[str]
    response_message_id: NotRequired[Snowflake]
    response_message_loading: NotRequired[bool]
    response_message_ephemeral: NotRequired[bool]


class InteractionCallbackActivity(TypedDict):
    id: str


class InteractionCallbackResource(TypedDict):
    type: InteractionResponseType
    activity_instance: NotRequired[InteractionCallbackActivity]
    message: NotRequired[Message]


class InteractionCallback(TypedDict):
    interaction: InteractionCallbackResponse
    resource: NotRequired[InteractionCallbackResource]
