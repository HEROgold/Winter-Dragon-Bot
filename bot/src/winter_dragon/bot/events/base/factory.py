"""Module for creating audit events from audit log entries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from winter_dragon.bot.enums.channels import LogCategories
from winter_dragon.bot.events.app_command_permission_update import AppCommandPermissionUpdate
from winter_dragon.bot.events.automod_block_message import AutomodBlockMessage
from winter_dragon.bot.events.automod_flag_message import AutomodFlagMessage
from winter_dragon.bot.events.automod_rule_create import AutomodRuleCreate
from winter_dragon.bot.events.automod_rule_delete import AutomodRuleDelete
from winter_dragon.bot.events.automod_rule_update import AutomodRuleUpdate
from winter_dragon.bot.events.automod_timeout_member import AutomodTimeoutMember
from winter_dragon.bot.events.ban import Ban
from winter_dragon.bot.events.bot_add import BotAdd
from winter_dragon.bot.events.channel_create import ChannelCreate
from winter_dragon.bot.events.channel_delete import ChannelDelete
from winter_dragon.bot.events.channel_update import ChannelUpdate
from winter_dragon.bot.events.emoji_create import EmojiCreate
from winter_dragon.bot.events.emoji_delete import EmojiDelete
from winter_dragon.bot.events.emoji_update import EmojiUpdate
from winter_dragon.bot.events.guild_update import GuildUpdate
from winter_dragon.bot.events.integration_create import IntegrationCreate
from winter_dragon.bot.events.integration_delete import IntegrationDelete
from winter_dragon.bot.events.integration_update import IntegrationUpdate
from winter_dragon.bot.events.invite_create import InviteCreate
from winter_dragon.bot.events.invite_delete import InviteDelete
from winter_dragon.bot.events.invite_update import InviteUpdate
from winter_dragon.bot.events.kick import Kick
from winter_dragon.bot.events.member_disconnect import MemberDisconnect
from winter_dragon.bot.events.member_move import MemberMove
from winter_dragon.bot.events.member_prune import MemberPrune
from winter_dragon.bot.events.member_role_update import MemberRoleUpdate
from winter_dragon.bot.events.member_update import MemberUpdate
from winter_dragon.bot.events.message_bulk_delete import MessageBulkDelete
from winter_dragon.bot.events.message_delete import MessageDelete
from winter_dragon.bot.events.message_pin import MessagePin
from winter_dragon.bot.events.message_unpin import MessageUnpin
from winter_dragon.bot.events.overwrite_create import OverwriteCreate
from winter_dragon.bot.events.overwrite_delete import OverwriteDelete
from winter_dragon.bot.events.overwrite_update import OverwriteUpdate
from winter_dragon.bot.events.role_create import RoleCreate
from winter_dragon.bot.events.role_delete import RoleDelete
from winter_dragon.bot.events.role_update import RoleUpdate
from winter_dragon.bot.events.scheduled_event_create import ScheduledEventCreate
from winter_dragon.bot.events.scheduled_event_delete import ScheduledEventDelete
from winter_dragon.bot.events.scheduled_event_update import ScheduledEventUpdate
from winter_dragon.bot.events.stage_instance_create import StageInstanceCreate
from winter_dragon.bot.events.stage_instance_delete import StageInstanceDelete
from winter_dragon.bot.events.stage_instance_update import StageInstanceUpdate
from winter_dragon.bot.events.sticker_create import StickerCreate
from winter_dragon.bot.events.sticker_delete import StickerDelete
from winter_dragon.bot.events.sticker_update import StickerUpdate
from winter_dragon.bot.events.thread_create import ThreadCreate
from winter_dragon.bot.events.thread_delete import ThreadDelete
from winter_dragon.bot.events.thread_update import ThreadUpdate
from winter_dragon.bot.events.unban import Unban
from winter_dragon.bot.events.webhook_create import WebhookCreate
from winter_dragon.bot.events.webhook_delete import WebhookDelete
from winter_dragon.bot.events.webhook_update import WebhookUpdate


if TYPE_CHECKING:
    from discord import AuditLogEntry
    from winter_dragon.bot.events.base.audit_event import AuditEvent


def AuditEvent_factory(entry: AuditLogEntry) -> AuditEvent:  # noqa: C901, N802, PLR0911, PLR0912, PLR0915
    """Get the correct AuditEvent class from audit event."""
    category = LogCategories.from_AuditLogAction(entry.action)
    # Use match case here, to import only te required classes.
    # Using a dict would make it easier to read, but would require importing all classes at once.
    # Because this factory is as "simple" as it is, readability is not that important.
    match category:
        case LogCategories.GUILD_UPDATE: return GuildUpdate(entry)
        case LogCategories.CHANNEL_CREATE: return ChannelCreate(entry)
        case LogCategories.CHANNEL_UPDATE: return ChannelUpdate(entry)
        case LogCategories.CHANNEL_DELETE: return ChannelDelete(entry)
        case LogCategories.OVERWRITE_CREATE: return OverwriteCreate(entry)
        case LogCategories.OVERWRITE_UPDATE: return OverwriteUpdate(entry)
        case LogCategories.OVERWRITE_DELETE: return OverwriteDelete(entry)
        case LogCategories.KICK: return Kick(entry)
        case LogCategories.MEMBER_PRUNE: return MemberPrune(entry)
        case LogCategories.BAN: return Ban(entry)
        case LogCategories.UNBAN: return Unban(entry)
        case LogCategories.MEMBER_UPDATE: return MemberUpdate(entry)
        case LogCategories.MEMBER_ROLE_UPDATE: return MemberRoleUpdate(entry)
        case LogCategories.MEMBER_MOVE: return MemberMove(entry)
        case LogCategories.MEMBER_DISCONNECT: return MemberDisconnect(entry)
        case LogCategories.BOT_ADD: return BotAdd(entry)
        case LogCategories.ROLE_CREATE: return RoleCreate(entry)
        case LogCategories.ROLE_UPDATE: return RoleUpdate(entry)
        case LogCategories.ROLE_DELETE: return RoleDelete(entry)
        case LogCategories.INVITE_CREATE: return InviteCreate(entry)
        case LogCategories.INVITE_UPDATE: return InviteUpdate(entry)
        case LogCategories.INVITE_DELETE: return InviteDelete(entry)
        case LogCategories.WEBHOOK_CREATE: return WebhookCreate(entry)
        case LogCategories.WEBHOOK_UPDATE: return WebhookUpdate(entry)
        case LogCategories.WEBHOOK_DELETE: return WebhookDelete(entry)
        case LogCategories.EMOJI_CREATE: return EmojiCreate(entry)
        case LogCategories.EMOJI_UPDATE: return EmojiUpdate(entry)
        case LogCategories.EMOJI_DELETE: return EmojiDelete(entry)
        case LogCategories.MESSAGE_DELETE: return MessageDelete(entry)
        case LogCategories.MESSAGE_BULK_DELETE: return MessageBulkDelete(entry)
        case LogCategories.MESSAGE_PIN: return MessagePin(entry)
        case LogCategories.MESSAGE_UNPIN: return MessageUnpin(entry)
        case LogCategories.INTEGRATION_CREATE: return IntegrationCreate(entry)
        case LogCategories.INTEGRATION_UPDATE: return IntegrationUpdate(entry)
        case LogCategories.INTEGRATION_DELETE: return IntegrationDelete(entry)
        case LogCategories.STAGE_INSTANCE_CREATE: return StageInstanceCreate(entry)
        case LogCategories.STAGE_INSTANCE_UPDATE: return StageInstanceUpdate(entry)
        case LogCategories.STAGE_INSTANCE_DELETE: return StageInstanceDelete(entry)
        case LogCategories.STICKER_CREATE: return StickerCreate(entry)
        case LogCategories.STICKER_UPDATE: return StickerUpdate(entry)
        case LogCategories.STICKER_DELETE: return StickerDelete(entry)
        case LogCategories.SCHEDULED_EVENT_CREATE: return ScheduledEventCreate(entry)
        case LogCategories.SCHEDULED_EVENT_UPDATE: return ScheduledEventUpdate(entry)
        case LogCategories.SCHEDULED_EVENT_DELETE: return ScheduledEventDelete(entry)
        case LogCategories.THREAD_CREATE: return ThreadCreate(entry)
        case LogCategories.THREAD_UPDATE: return ThreadUpdate(entry)
        case LogCategories.THREAD_DELETE: return ThreadDelete(entry)
        case LogCategories.APP_COMMAND_PERMISSION_UPDATE: return AppCommandPermissionUpdate(entry)
        case LogCategories.AUTOMOD_RULE_CREATE: return AutomodRuleCreate(entry)
        case LogCategories.AUTOMOD_RULE_UPDATE: return AutomodRuleUpdate(entry)
        case LogCategories.AUTOMOD_RULE_DELETE: return AutomodRuleDelete(entry)
        case LogCategories.AUTOMOD_BLOCK_MESSAGE: return AutomodBlockMessage(entry)
        case LogCategories.AUTOMOD_FLAG_MESSAGE: return AutomodFlagMessage(entry)
        case LogCategories.AUTOMOD_TIMEOUT_MEMBER: return AutomodTimeoutMember(entry)
        case _:
            msg = f"Audit event for {category} not implemented"
            raise NotImplementedError(msg)
