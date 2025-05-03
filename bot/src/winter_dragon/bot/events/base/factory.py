"""Module for creating audit events from audit log entries."""

from discord import AuditLogEntry
from winter_dragon.bot.enums.channels import LogCategories
from winter_dragon.bot.events.base.audit_event import AuditEvent


def AuditEvent_factory(entry: AuditLogEntry) -> AuditEvent:  # noqa: C901, N802, PLR0911, PLR0912, PLR0915
    """Get the correct AuditEvent class from audit event."""
    category = LogCategories.from_AuditLogAction(entry.action)
    # Use match case here, to import only te required classes.
    # Using a dict would make it easier to read, but would require importing all classes at once.
    # Because this factory is as "simple" as it is, readability is not that important.
    match category:
        case LogCategories.GUILD_UPDATE:
            from winter_dragon.bot.events.guild_update import GuildUpdate
            return GuildUpdate(entry)
        case LogCategories.CHANNEL_CREATE:
            from winter_dragon.bot.events.channel_create import ChannelCreate
            return ChannelCreate(entry)
        case LogCategories.CHANNEL_UPDATE:
            from winter_dragon.bot.events.channel_update import ChannelUpdate
            return ChannelUpdate(entry)
        case LogCategories.CHANNEL_DELETE:
            from winter_dragon.bot.events.channel_delete import ChannelDelete
            return ChannelDelete(entry)
        case LogCategories.OVERWRITE_CREATE:
            from winter_dragon.bot.events.overwrite_create import OverwriteCreate
            return OverwriteCreate(entry)
        case LogCategories.OVERWRITE_UPDATE:
            from winter_dragon.bot.events.overwrite_update import OverwriteUpdate
            return OverwriteUpdate(entry)
        case LogCategories.OVERWRITE_DELETE:
            from winter_dragon.bot.events.overwrite_delete import OverwriteDelete
            return OverwriteDelete(entry)
        case LogCategories.KICK:
            from winter_dragon.bot.events.kick import Kick
            return Kick(entry)
        case LogCategories.MEMBER_PRUNE:
            from winter_dragon.bot.events.member_prune import MemberPrune
            return MemberPrune(entry)
        case LogCategories.BAN:
            from winter_dragon.bot.events.ban import Ban
            return Ban(entry)
        case LogCategories.UNBAN:
            from winter_dragon.bot.events.unban import Unban
            return Unban(entry)
        case LogCategories.MEMBER_UPDATE:
            from winter_dragon.bot.events.member_update import MemberUpdate
            return MemberUpdate(entry)
        case LogCategories.MEMBER_ROLE_UPDATE:
            from winter_dragon.bot.events.member_role_update import MemberRoleUpdate
            return MemberRoleUpdate(entry)
        case LogCategories.MEMBER_MOVE:
            from winter_dragon.bot.events.member_move import MemberMove
            return MemberMove(entry)
        case LogCategories.MEMBER_DISCONNECT:
            from winter_dragon.bot.events.member_disconnect import MemberDisconnect
            return MemberDisconnect(entry)
        case LogCategories.BOT_ADD:
            from winter_dragon.bot.events.bot_add import BotAdd
            return BotAdd(entry)
        case LogCategories.ROLE_CREATE:
            from winter_dragon.bot.events.role_create import RoleCreate
            return RoleCreate(entry)
        case LogCategories.ROLE_UPDATE:
            from winter_dragon.bot.events.role_update import RoleUpdate
            return RoleUpdate(entry)
        case LogCategories.ROLE_DELETE:
            from winter_dragon.bot.events.role_delete import RoleDelete
            return RoleDelete(entry)
        case LogCategories.INVITE_CREATE:
            from winter_dragon.bot.events.invite_create import InviteCreate
            return InviteCreate(entry)
        case LogCategories.INVITE_UPDATE:
            from winter_dragon.bot.events.invite_update import InviteUpdate
            return InviteUpdate(entry)
        case LogCategories.INVITE_DELETE:
            from winter_dragon.bot.events.invite_delete import InviteDelete
            return InviteDelete(entry)
        case LogCategories.WEBHOOK_CREATE:
            from winter_dragon.bot.events.webhook_create import WebhookCreate
            return WebhookCreate(entry)
        case LogCategories.WEBHOOK_UPDATE:
            from winter_dragon.bot.events.webhook_update import WebhookUpdate
            return WebhookUpdate(entry)
        case LogCategories.WEBHOOK_DELETE:
            from winter_dragon.bot.events.webhook_delete import WebhookDelete
            return WebhookDelete(entry)
        case LogCategories.EMOJI_CREATE:
            from winter_dragon.bot.events.emoji_create import EmojiCreate
            return EmojiCreate(entry)
        case LogCategories.EMOJI_UPDATE:
            from winter_dragon.bot.events.emoji_update import EmojiUpdate
            return EmojiUpdate(entry)
        case LogCategories.EMOJI_DELETE:
            from winter_dragon.bot.events.emoji_delete import EmojiDelete
            return EmojiDelete(entry)
        case LogCategories.MESSAGE_DELETE:
            from winter_dragon.bot.events.message_delete import MessageDelete
            return MessageDelete(entry)
        case LogCategories.MESSAGE_BULK_DELETE:
            from winter_dragon.bot.events.message_bulk_delete import MessageBulkDelete
            return MessageBulkDelete(entry)
        case LogCategories.MESSAGE_PIN:
            from winter_dragon.bot.events.message_pin import MessagePin
            return MessagePin(entry)
        case LogCategories.MESSAGE_UNPIN:
            from winter_dragon.bot.events.message_unpin import MessageUnpin
            return MessageUnpin(entry)
        case LogCategories.INTEGRATION_CREATE:
            from winter_dragon.bot.events.integration_create import IntegrationCreate
            return IntegrationCreate(entry)
        case LogCategories.INTEGRATION_UPDATE:
            from winter_dragon.bot.events.integration_update import IntegrationUpdate
            return IntegrationUpdate(entry)
        case LogCategories.INTEGRATION_DELETE:
            from winter_dragon.bot.events.integration_delete import IntegrationDelete
            return IntegrationDelete(entry)
        case LogCategories.STAGE_INSTANCE_CREATE:
            from winter_dragon.bot.events.stage_instance_create import StageInstanceCreate
            return StageInstanceCreate(entry)
        case LogCategories.STAGE_INSTANCE_UPDATE:
            from winter_dragon.bot.events.stage_instance_update import StageInstanceUpdate
            return StageInstanceUpdate(entry)
        case LogCategories.STAGE_INSTANCE_DELETE:
            from winter_dragon.bot.events.stage_instance_delete import StageInstanceDelete
            return StageInstanceDelete(entry)
        case LogCategories.STICKER_CREATE:
            from winter_dragon.bot.events.sticker_create import StickerCreate
            return StickerCreate(entry)
        case LogCategories.STICKER_UPDATE:
            from winter_dragon.bot.events.sticker_update import StickerUpdate
            return StickerUpdate(entry)
        case LogCategories.STICKER_DELETE:
            from winter_dragon.bot.events.sticker_delete import StickerDelete
            return StickerDelete(entry)
        case LogCategories.SCHEDULED_EVENT_CREATE:
            from winter_dragon.bot.events.scheduled_event_create import ScheduledEventCreate
            return ScheduledEventCreate(entry)
        case LogCategories.SCHEDULED_EVENT_UPDATE:
            from winter_dragon.bot.events.scheduled_event_update import ScheduledEventUpdate
            return ScheduledEventUpdate(entry)
        case LogCategories.SCHEDULED_EVENT_DELETE:
            from winter_dragon.bot.events.scheduled_event_delete import ScheduledEventDelete
            return ScheduledEventDelete(entry)
        case LogCategories.THREAD_CREATE:
            from winter_dragon.bot.events.thread_create import ThreadCreate
            return ThreadCreate(entry)
        case LogCategories.THREAD_UPDATE:
            from winter_dragon.bot.events.thread_update import ThreadUpdate
            return ThreadUpdate(entry)
        case LogCategories.THREAD_DELETE:
            from winter_dragon.bot.events.thread_delete import ThreadDelete
            return ThreadDelete(entry)
        case LogCategories.APP_COMMAND_PERMISSION_UPDATE:
            from winter_dragon.bot.events.app_command_permission_update import AppCommandPermissionUpdate
            return AppCommandPermissionUpdate(entry)
        case LogCategories.AUTOMOD_RULE_CREATE:
            from winter_dragon.bot.events.automod_rule_create import AutomodRuleCreate
            return AutomodRuleCreate(entry)
        case LogCategories.AUTOMOD_RULE_UPDATE:
            from winter_dragon.bot.events.automod_rule_update import AutomodRuleUpdate
            return AutomodRuleUpdate(entry)
        case LogCategories.AUTOMOD_RULE_DELETE:
            from winter_dragon.bot.events.automod_rule_delete import AutomodRuleDelete
            return AutomodRuleDelete(entry)
        case LogCategories.AUTOMOD_BLOCK_MESSAGE:
            from winter_dragon.bot.events.automod_block_message import AutomodBlockMessage
            return AutomodBlockMessage(entry)
        case LogCategories.AUTOMOD_FLAG_MESSAGE:
            from winter_dragon.bot.events.automod_flag_message import AutomodFlagMessage
            return AutomodFlagMessage(entry)
        case LogCategories.AUTOMOD_TIMEOUT_MEMBER:
            from winter_dragon.bot.events.automod_timeout_member import AutomodTimeoutMember
            return AutomodTimeoutMember(entry)
        case _:
            msg = f"Audit event for {category} not implemented"
            raise NotImplementedError(msg)
