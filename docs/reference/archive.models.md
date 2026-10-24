<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `archive.models` (archive)
Every archive table. Importing this module registers them all with SQLModel's metadata (the migrations do).

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `archive.models` — `src/archive/models/__init__.py`

- exports: Activity, ActivityButton, ArchiveChild, ArchiveCompositeEntity, ArchiveEntity, ArchiveEvent, ArchiveTable,
  Channel, ChannelAppliedTag, ChannelPinsUpdate, Emoji, EmojiRole, ForumTag, GatewayEvent, Guild, GuildFeature,
  InteractionEvent, Member, MemberRole, Message, MessageAttachment, MessageComponent, MessageEmbed, MessageEmbedField,
  MessageMention, MessageMentionRole, MessagePoll, MessagePollAnswer, MessageReaction, MessageRevision,
  MessageSelectOption, MessageStickerItem, PermissionOverwrite, PresenceUpdate, ReactionEvent, Role, Sticker,
  ThreadMember, TypingStart, User, VoiceStateUpdate

## `archive.models.base` — `src/archive/models/base.py`
The four kinds of archive table, and the conventions :mod:`archive.mapping` relies on.

- `snowflake(*, index: bool=False) -> Any` — Return an optional Discord ID column.
- `moment() -> Any` — Return an optional timezone-aware timestamp column.
- `json_column() -> Any` — Return an optional JSON column (JSONB on PostgreSQL), for a payload kept whole.

### `class ArchiveTable`
What :mod:`archive.mapping` reads from every archive table.

- fields: children: ClassVar[dict[str, type[ArchiveChild]]], renames: ClassVar[dict[str, str]]

### `class ArchiveEntity(ArchiveTable, DiscordKeyedModel)`
The current state of one Discord object; ``id`` is its Discord ID.

### `class ArchiveCompositeEntity(ArchiveTable, LifecycleModel)`
The current state of an object identified by several Discord IDs (its :attr:`natural_key`), not one.

### `class ArchiveEvent(ArchiveTable, LifecycleModel)`
Something that happened, appended and never changed; ``created_at`` is when the archive received it.

- fields: renames: ClassVar[dict[str, str]]

### `class ArchiveChild(ArchiveTable, LifecycleModel)`
One item of a list inside an archived payload, at ``position`` in that list.

- fields: renames: ClassVar[dict[str, str]], scalar: ClassVar[str], owner_id: int, parent_id: int, position: int

## `archive.models.children` — `src/archive/models/children.py`
The lists inside archived payloads, one table per kind of list item.

### `class GuildFeature(ArchiveChild, table=True)`
One of a guild's feature flags, such as ``COMMUNITY``.

- fields: scalar: ClassVar, feature: str

### `class PermissionOverwrite(ArchiveChild, table=True)`
A role's or member's permission overwrite on a channel.

- fields: renames: ClassVar, target_id: int | None, type: int | None, allow: str | None, deny: str | None

### `class ForumTag(ArchiveChild, table=True)`
A tag a forum channel offers its posts.

- fields: discord_id: int | None, name: str | None, moderated: bool | None, emoji_id: int | None, emoji_name: str | None

### `class ChannelAppliedTag(ArchiveChild, table=True)`
A forum tag applied to a forum post.

- fields: scalar: ClassVar, tag_id: int

### `class MemberRole(ArchiveChild, table=True)`
A role a member has.

- fields: scalar: ClassVar, role_id: int

### `class EmojiRole(ArchiveChild, table=True)`
A role allowed to use an emoji.

- fields: scalar: ClassVar, role_id: int

### `class MessageAttachment(ArchiveChild, table=True)`
A file attached to a message.

- fields: discord_id: int | None, filename: str | None, title: str | None, description: str | None, content_type: str |
  None, size: int | None, url: str | None, proxy_url: str | None, height: int | None, width: int | None, duration_secs:
  float | None, flags: int | None

### `class MessageEmbedField(ArchiveChild, table=True)`
One name/value field of an embed.

- fields: name: str | None, value: str | None, inline: bool | None

### `class MessageEmbed(ArchiveChild, table=True)`
An embed in a message.

- fields: children: ClassVar, type: str | None, title: str | None, description: str | None, url: str | None, timestamp:
  datetime | None, color: int | None, author_name: str | None, author_url: str | None, author_icon_url: str | None,
  footer_text: str | None, footer_icon_url: str | None, image_url: str | None, thumbnail_url: str | None, video_url: str
  | None, provider_name: str | None, provider_url: str | None

### `class MessageSelectOption(ArchiveChild, table=True)`
An option of a select menu component.

- fields: label: str | None, value: str | None, description: str | None, default: bool | None, emoji_id: int | None,
  emoji_name: str | None

### `class MessageComponent(ArchiveChild, table=True)`
A component in a message; components inside it (an action row's buttons) are its children.

- fields: type: int | None, discord_id: int | None, custom_id: str | None, style: int | None, label: str | None, url:
  str | None, disabled: bool | None, placeholder: str | None, min_values: int | None, max_values: int | None, content:
  str | None, emoji_id: int | None, emoji_name: str | None

### `class MessageMention(ArchiveChild, table=True)`
A user a message mentions.

- fields: renames: ClassVar, user_id: int | None, username: str | None

### `class MessageMentionRole(ArchiveChild, table=True)`
A role a message mentions.

- fields: scalar: ClassVar, role_id: int

### `class MessageReaction(ArchiveChild, table=True)`
One emoji's reaction count on a message, as the message last carried it.

- fields: renames: ClassVar, reaction_count: int | None, count_details_normal: int | None, count_details_burst: int |
  None, me: bool | None, me_burst: bool | None, emoji_id: int | None, emoji_name: str | None, emoji_animated: bool |
  None

### `class MessageStickerItem(ArchiveChild, table=True)`
A sticker sent in a message.

- fields: renames: ClassVar, sticker_id: int | None, name: str | None, format_type: int | None

### `class MessagePollAnswer(ArchiveChild, table=True)`
One answer of a poll.

- fields: answer_id: int | None, poll_media_text: str | None

### `class MessagePoll(ArchiveChild, table=True)`
A message's poll; a message has at most one, stored as a one-item list.

- fields: children: ClassVar, question_text: str | None, expiry: datetime | None, allow_multiselect: bool | None,
  layout_type: int | None

### `class ActivityButton(ArchiveChild, table=True)`
The label of a button an activity shows.

- fields: scalar: ClassVar, label: str

### `class Activity(ArchiveChild, table=True)`
One activity in a presence: a game, listening, streaming, a custom status.

- fields: renames: ClassVar, children: ClassVar, discord_id: str | None, type: int | None, name: str | None, url: str |
  None, details: str | None, state: str | None, application_id: int | None, activity_created_at: int | None,
  timestamps_start: int | None, timestamps_end: int | None, sync_id: str | None, session_id: str | None, platform: str |
  None, flags: int | None, status_display_type: int | None, emoji_id: int | None, emoji_name: str | None,
  emoji_animated: bool | None, party_id: str | None, assets_large_image: str | None, assets_large_text: str | None,
  assets_small_image: str | None, assets_small_text: str | None

## `archive.models.entities` — `src/archive/models/entities.py`
The current state of each Discord object the archive has seen.

### `class Guild(ArchiveEntity, table=True)`
A guild (https://docs.discord.com/developers/resources/guild#guild-object).

- fields: children: ClassVar, name: str | None, icon: str | None, splash: str | None, banner: str | None, description:
  str | None, owner_id: int | None, afk_channel_id: int | None, afk_timeout: int | None, system_channel_id: int | None,
  rules_channel_id: int | None, verification_level: int | None, default_message_notifications: int | None,
  explicit_content_filter: int | None, mfa_level: int | None, nsfw_level: int | None, premium_tier: int | None,
  premium_subscription_count: int | None, preferred_locale: str | None, vanity_url_code: str | None, max_members: int |
  None, member_count: int | None, large: bool | None, unavailable: bool | None, joined_at: datetime | None

### `class Channel(ArchiveEntity, table=True)`
A channel or thread (https://docs.discord.com/developers/resources/channel#channel-object).

- fields: children: ClassVar, type: int | None, guild_id: int | None, parent_id: int | None, owner_id: int | None, name:
  str | None, topic: str | None, position: int | None, nsfw: bool | None, flags: int | None, last_message_id: int |
  None, last_pin_timestamp: datetime | None, rate_limit_per_user: int | None, bitrate: int | None, user_limit: int |
  None, rtc_region: str | None, video_quality_mode: int | None, status: str | None, voice_start_time: int | None,
  default_auto_archive_duration: int | None, message_count: int | None, member_count: int | None, total_message_sent:
  int | None, thread_metadata_archived: bool | None, thread_metadata_locked: bool | None,
  thread_metadata_auto_archive_duration: int | None, thread_metadata_archive_timestamp: datetime | None,
  thread_metadata_create_timestamp: datetime | None

### `class Role(ArchiveEntity, table=True)`
A guild's role (https://docs.discord.com/developers/topics/permissions#role-object).

- fields: guild_id: int | None, name: str | None, color: int | None, colors_primary_color: int | None,
  colors_secondary_color: int | None, colors_tertiary_color: int | None, hoist: bool | None, icon: str | None,
  unicode_emoji: str | None, position: int | None, permissions: str | None, managed: bool | None, mentionable: bool |
  None, flags: int | None, tags_bot_id: int | None, tags_integration_id: int | None

### `class User(ArchiveEntity, table=True)`
A user (https://docs.discord.com/developers/resources/user#user-object).

- fields: username: str | None, discriminator: str | None, global_name: str | None, avatar: str | None, banner: str |
  None, accent_color: int | None, bot: bool | None, system: bool | None, public_flags: int | None

### `class Member(ArchiveCompositeEntity, table=True)`
A user's membership of a guild (https://docs.discord.com/developers/resources/guild#guild-member-object).

- fields: natural_key: ClassVar, children: ClassVar, guild_id: int, user_id: int, nick: str | None, avatar: str | None,
  banner: str | None, joined_at: datetime | None, premium_since: datetime | None, communication_disabled_until: datetime
  | None, deaf: bool | None, mute: bool | None, pending: bool | None, flags: int | None

### `class ThreadMember(ArchiveCompositeEntity, table=True)`
A user's membership of a thread (https://docs.discord.com/developers/resources/channel#thread-member-object).

- fields: natural_key: ClassVar, renames: ClassVar, thread_id: int, user_id: int, join_timestamp: datetime | None,
  flags: int | None

### `class Emoji(ArchiveEntity, table=True)`
A guild's custom emoji (https://docs.discord.com/developers/resources/emoji#emoji-object).

- fields: children: ClassVar, guild_id: int | None, name: str | None, user_id: int | None, require_colons: bool | None,
  managed: bool | None, animated: bool | None, available: bool | None

### `class Sticker(ArchiveEntity, table=True)`
A sticker (https://docs.discord.com/developers/resources/sticker#sticker-object).

- fields: guild_id: int | None, pack_id: int | None, name: str | None, description: str | None, tags: str | None, type:
  int | None, format_type: int | None, available: bool | None, user_id: int | None, sort_value: int | None

### `class Message(ArchiveEntity, table=True)`
A message, with its content (https://docs.discord.com/developers/resources/message#message-object).

- fields: children: ClassVar, channel_id: int | None, guild_id: int | None, author_id: int | None, content: str | None,
  timestamp: datetime | None, edited_timestamp: datetime | None, type: int | None, flags: int | None, tts: bool | None,
  mention_everyone: bool | None, pinned: bool | None, webhook_id: int | None, application_id: int | None, position: int
  | None, message_reference_type: int | None, message_reference_message_id: int | None, message_reference_channel_id:
  int | None, message_reference_guild_id: int | None

## `archive.models.history` — `src/archive/models/history.py`
What happened, appended and never changed; ``created_at`` is when the archive received it.

### `class GatewayEvent(ArchiveEvent, table=True)`
A raw event: one dispatch exactly as Discord sent it, kept for a limited number of days.

- fields: name: str, sequence: int | None, guild_id: int | None, payload: dict[str, Any] | None

### `class PresenceUpdate(ArchiveEvent, table=True)`
A user's status and activities in a guild, from a PRESENCE_UPDATE or a snapshot.

- fields: children: ClassVar, source: str, guild_id: int | None, user_id: int | None, status: str | None,
  client_status_desktop: str | None, client_status_mobile: str | None, client_status_web: str | None, client_status_vr:
  str | None

### `class VoiceStateUpdate(ArchiveEvent, table=True)`
A user's voice connection in a guild, from a VOICE_STATE_UPDATE or a snapshot.

- fields: source: str, guild_id: int | None, channel_id: int | None, user_id: int | None, session_id: str | None, deaf:
  bool | None, mute: bool | None, self_deaf: bool | None, self_mute: bool | None, self_stream: bool | None, self_video:
  bool | None, suppress: bool | None, request_to_speak_timestamp: datetime | None

### `class TypingStart(ArchiveEvent, table=True)`
A user started typing in a channel.

- fields: channel_id: int | None, guild_id: int | None, user_id: int | None, timestamp: int | None

### `class ReactionEvent(ArchiveEvent, table=True)`
A reaction added to or removed from a message, or a message's reactions cleared.

- fields: action: str, message_id: int | None, channel_id: int | None, guild_id: int | None, user_id: int | None,
  message_author_id: int | None, emoji_id: int | None, emoji_name: str | None, emoji_animated: bool | None, burst: bool
  | None, type: int | None

### `class MessageRevision(ArchiveEvent, table=True)`
A message's content after one of its edits.

- fields: message_id: int, channel_id: int | None, guild_id: int | None, content: str | None, edited_timestamp: datetime
  | None

### `class ChannelPinsUpdate(ArchiveEvent, table=True)`
A message was pinned or unpinned in a channel.

- fields: guild_id: int | None, channel_id: int | None, last_pin_timestamp: datetime | None

### `class InteractionEvent(ArchiveEvent, table=True)`
An interaction sent to the archive's application.

- fields: discord_id: int | None, type: int | None, application_id: int | None, guild_id: int | None, channel_id: int |
  None, locale: str | None
