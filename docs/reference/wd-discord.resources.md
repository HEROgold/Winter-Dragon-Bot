<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_discord.resources` (wd-discord)
Discord API resource models (https://docs.discord.com/developers/resources).

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_discord.resources` — `wd-discord/src/wd_discord/resources/__init__.py`

- exports: Application, ApplicationIntegrationTypeConfig, Avatar, Channel, Collectibles,
  DefaultMessageNotificationLevel, DefaultReaction, Emoji, Entitlement, EntitlementType, ExplicitContentFilterLevel,
  ForumLayoutType, ForumTag, Guild, GuildFeature, GuildMember, GuildMemberFlags, IncidentsData, InstallParams, Invite,
  MFALevel, MembershipState, NSFWLevel, NamePlate, OverwriteType, PartialGuild, PermissionOverwrite, PremiumTier, Role,
  RoleColors, RoleTags, SortOrderType, Sticker, StickerFormatType, StickerType, SystemChannelFlags, Team, TeamMember,
  ThreadMember, ThreadMetadata, User, VerificationLevel, VideoQualityMode, WelcomeScreen, WelcomeScreenChannel

## `wd_discord.resources.application` — `wd-discord/src/wd_discord/resources/application/__init__.py`
Discord Application object and related team/install models.

- exports: Application, ApplicationIntegrationTypeConfig, InstallParams, MembershipState, Team, TeamMember

## `wd_discord.resources.application.application` — `wd-discord/src/wd_discord/resources/application/application.py`
Discord Application object.

### `class Application(DiscordModel)`
https://docs.discord.com/developers/resources/application#application-object.

- fields: id: Snowflake, name: str, icon: ImageHash | None, description: str, rpc_origins: list[str] | None, bot_public:
  bool, bot_require_code_grant: bool, bot: User | None, terms_of_service_url: str | None, privacy_policy_url: str |
  None, owner: User | None, verify_key: str, team: Team | None, guild_id: Snowflake | None, guild: Guild | None,
  primary_sku_id: Snowflake | None, slug: str | None, cover_image: ImageHash | None, flags: int | None,
  approximate_guild_count: int | None, approximate_user_install_count: int | None, redirect_uris: list[str] | None,
  interactions_endpoint_url: str | None, role_connections_verification_url: str | None, event_webhooks_url: str | None,
  event_webhooks_status: int | None, event_webhooks_types: list[str] | None, tags: list[str] | None, install_params:
  InstallParams | None, integration_types_config: dict[str, ApplicationIntegrationTypeConfig] | None,
  custom_install_url: str | None

## `wd_discord.resources.application.install_params` — `wd-discord/src/wd_discord/resources/application/install_params.py`
Discord application install parameters.

### `class InstallParams(DiscordModel)`
https://docs.discord.com/developers/resources/application#install-params-object.

- fields: scopes: list[str], permissions: PermissionsField

### `class ApplicationIntegrationTypeConfig(DiscordModel)`
https://docs.discord.com/developers/resources/application#application-object-application-integration-type-configuration-object.

- fields: oauth2_install_params: InstallParams | None

## `wd_discord.resources.application.team` — `wd-discord/src/wd_discord/resources/application/team.py`
Discord Team object and its members.

### `class MembershipState(IntEnum)`
State of a team member's invitation.

- attributes: INVITED, ACCEPTED

### `class TeamMember(DiscordModel)`
https://docs.discord.com/developers/topics/teams#data-models-team-member-object.

- fields: membership_state: MembershipState, team_id: Snowflake, user: User, role: str

### `class Team(DiscordModel)`
https://docs.discord.com/developers/topics/teams#data-models-team-object.

- fields: icon: ImageHash | None, id: Snowflake, members: list[TeamMember], name: str, owner_user_id: Snowflake
- `@property owner -> TeamMember | None` — Return the owner of the team, if they are a member.

## `wd_discord.resources.channel` — `wd-discord/src/wd_discord/resources/channel/__init__.py`
Pydantic v2 models for the Discord v10 Channel object.

- exports: Channel, ChannelParams, DefaultReaction, ForumLayoutType, ForumTag, GuildChannelParams, OverwriteParams,
  OverwriteType, PermissionOverwrite, SortOrderType, ThreadMember, ThreadMetadata, VideoQualityMode

## `wd_discord.resources.channel.channel` — `wd-discord/src/wd_discord/resources/channel/channel.py`
The Discord Channel object model.

### `class Channel(DiscordModel)`
https://docs.discord.com/developers/resources/channel#channel-object.

- fields: id: Snowflake, type: ChannelType, guild_id: Snowflake | None, position: int | None, permission_overwrites:
  list[PermissionOverwrite] | None, name: str | None, topic: str | None, nsfw: bool | None, last_message_id: Snowflake |
  None, bitrate: int | None, user_limit: int | None, rate_limit_per_user: int | None, recipients: list[User] | None,
  icon: ImageHash | None, owner_id: Snowflake | None, application_id: Snowflake | None, managed: bool | None, parent_id:
  Snowflake | None, last_pin_timestamp: datetime | None, rtc_region: str | None, video_quality_mode: VideoQualityMode |
  None, message_count: int | None, member_count: int | None, thread_metadata: ThreadMetadata | None, member:
  ThreadMember | None, default_auto_archive_duration: int | None, permissions: PermissionsField | None, app_permissions:
  PermissionsField | None, flags: int | None, total_message_sent: int | None, available_tags: list[ForumTag] | None,
  applied_tags: list[Snowflake] | None, default_reaction_emoji: DefaultReaction | None,
  default_thread_rate_limit_per_user: int | None, default_sort_order: SortOrderType | None, default_forum_layout:
  ForumLayoutType | None
- `@property applied_forum_tags -> Generator[ForumTag]` — The ForumTag objects for ``applied_tags``, resolved against ``available_tags``.

## `wd_discord.resources.channel.forum` — `wd-discord/src/wd_discord/resources/channel/forum.py`
Forum and voice related models and enums for the Discord Channel object.

### `class VideoQualityMode(IntEnum)`
The camera video quality mode of a voice channel.

- attributes: AUTO, FULL

### `class SortOrderType(IntEnum)`
The default sort order used to order posts in a forum or media channel.

- attributes: LATEST_ACTIVITY, CREATION_DATE

### `class ForumLayoutType(IntEnum)`
The default layout used to display posts in a forum channel.

- attributes: NOT_SET, LIST_VIEW, GALLERY_VIEW

### `class ForumTag(DiscordModel)`
https://docs.discord.com/developers/resources/channel#forum-tag-object.

- fields: id: Snowflake, name: str, moderated: bool, emoji_id: Snowflake | None, emoji_name: str | None
- `@property emoji -> PartialEmoji | None` — The tag's emoji, or ``None`` if none is set.

### `class DefaultReaction(DiscordModel)`
https://docs.discord.com/developers/resources/channel#default-reaction-object.

- fields: emoji_id: Snowflake | None, emoji_name: str | None
- `@property emoji -> PartialEmoji | None` — The default reaction's emoji, or ``None`` if none is set.

## `wd_discord.resources.channel.overwrite` — `wd-discord/src/wd_discord/resources/channel/overwrite.py`
Permission overwrite models for the Discord Channel object.

### `class OverwriteType(IntEnum)`
Whether a permission overwrite targets a role or a member.

- attributes: ROLE, MEMBER

### `class PermissionOverwrite(DiscordModel)`
https://docs.discord.com/developers/resources/channel#overwrite-object.

- fields: id: Snowflake, type: OverwriteType, allow: PermissionsField, deny: PermissionsField

## `wd_discord.resources.channel.params` — `wd-discord/src/wd_discord/resources/channel/params.py`
Request bodies for creating and modifying guild channels.

- module names: MAX_USER_LIMIT
- `type ChannelName = str`

### `class OverwriteParams(BaseModel)`
One permission overwrite to set on a channel: what a role or member is explicitly allowed and denied.

- fields: id: Snowflake, type: OverwriteType, allow: Permissions, deny: Permissions
- attributes: model_config
- `to_json() -> OverwritePayload` — Return the overwrite as Discord's JSON body.

### `class ChannelParams(_ChannelSettings)`
The channel settings to change; the rest stay as they are.

- fields: name: ChannelName | None

### `class GuildChannelParams(_ChannelSettings)`
A new guild channel or category; Discord requires its name.

- fields: name: ChannelName, type: ChannelType

## `wd_discord.resources.channel.thread` — `wd-discord/src/wd_discord/resources/channel/thread.py`
Thread metadata and member models for the Discord Channel object.

### `class ThreadMetadata(DiscordModel)`
https://docs.discord.com/developers/resources/channel#thread-metadata-object.

- fields: archived: bool, auto_archive_duration: int, archive_timestamp: datetime, locked: bool, invitable: bool | None,
  create_timestamp: datetime | None

### `class ThreadMember(DiscordModel)`
https://docs.discord.com/developers/resources/channel#thread-member-object.

- fields: id: Snowflake | None, user_id: Snowflake | None, join_timestamp: datetime, flags: int

## `wd_discord.resources.entitlement` — `wd-discord/src/wd_discord/resources/entitlement.py`
Discord entitlement model (https://docs.discord.com/developers/resources/entitlement).

### `class EntitlementType(IntEnum)`
https://docs.discord.com/developers/resources/entitlement#entitlement-object-entitlement-types.

- attributes: PURCHASE, PREMIUM_SUBSCRIPTION, DEVELOPER_GIFT, TEST_MODE_PURCHASE, FREE_PURCHASE, USER_GIFT,
  PREMIUM_PURCHASE, APPLICATION_SUBSCRIPTION

### `class Entitlement(DiscordModel)`
https://docs.discord.com/developers/resources/entitlement#entitlement-object.

- fields: id: Snowflake, sku_id: Snowflake, application_id: Snowflake, user_id: Snowflake | None, type: EntitlementType,
  deleted: bool, starts_at: datetime | None, ends_at: datetime | None, guild_id: Snowflake | None, consumed: bool | None

## `wd_discord.resources.guild` — `wd-discord/src/wd_discord/resources/guild/__init__.py`
Pydantic v2 models for the Discord v10 Guild object and its related structures.

- exports: DefaultMessageNotificationLevel, Emoji, ExplicitContentFilterLevel, Guild, GuildFeature, GuildMember,
  GuildMemberFlags, IncidentsData, MFALevel, NSFWLevel, PartialGuild, PremiumTier, Role, RoleColors, RoleTags, Sticker,
  StickerFormatType, StickerType, SystemChannelFlags, VerificationLevel, WelcomeScreen, WelcomeScreenChannel

## `wd_discord.resources.guild.emoji` — `wd-discord/src/wd_discord/resources/guild/emoji.py`
Discord emoji model.

### `class Emoji(DiscordModel)`
https://docs.discord.com/developers/resources/emoji#emoji-object.

- fields: id: Snowflake | None, name: str | None, roles: list[Snowflake] | None, user: User | None, require_colons: bool
  | None, managed: bool | None, animated: bool | None, available: bool | None

## `wd_discord.resources.guild.features` — `wd-discord/src/wd_discord/resources/guild/features.py`
Discord guild enums and flags (features, levels, and system channel flags).

### `class GuildFeature(StrEnum)`
https://docs.discord.com/developers/resources/guild#guild-object-guild-features.

- attributes: ANIMATED_BANNER, ANIMATED_ICON, APPLICATION_COMMAND_PERMISSIONS_V2, AUTO_MODERATION, BANNER, COMMUNITY,
  CREATOR_MONETIZABLE_PROVISIONAL, CREATOR_STORE_PAGE, DEVELOPER_SUPPORT_SERVER, DISCOVERABLE, FEATURABLE,
  INVITES_DISABLED, INVITE_SPLASH, MEMBER_VERIFICATION_GATE_ENABLED, MORE_STICKERS, NEWS, PARTNERED, PREVIEW_ENABLED,
  RAID_ALERTS_DISABLED, ROLE_ICONS, ROLE_SUBSCRIPTIONS_AVAILABLE_FOR_PURCHASE, ROLE_SUBSCRIPTIONS_ENABLED,
  TICKETED_EVENTS_ENABLED, VANITY_URL, VERIFIED, VIP_REGIONS, WELCOME_SCREEN_ENABLED

### `class VerificationLevel(IntEnum)`
https://docs.discord.com/developers/resources/guild#guild-object-verification-level.

- attributes: NONE, LOW, MEDIUM, HIGH, VERY_HIGH

### `class DefaultMessageNotificationLevel(IntEnum)`
https://docs.discord.com/developers/resources/guild#guild-object-default-message-notification-level.

- attributes: ALL_MESSAGES, ONLY_MENTIONS

### `class ExplicitContentFilterLevel(IntEnum)`
https://docs.discord.com/developers/resources/guild#guild-object-explicit-content-filter-level.

- attributes: DISABLED, MEMBERS_WITHOUT_ROLES, ALL_MEMBERS

### `class MFALevel(IntEnum)`
https://docs.discord.com/developers/resources/guild#guild-object-mfa-level.

- attributes: NONE, ELEVATED

### `class PremiumTier(IntEnum)`
https://docs.discord.com/developers/resources/guild#guild-object-premium-tier.

- attributes: NONE, TIER_1, TIER_2, TIER_3

### `class NSFWLevel(IntEnum)`
https://docs.discord.com/developers/resources/guild#guild-object-guild-nsfw-level.

- attributes: DEFAULT, EXPLICIT, SAFE, AGE_RESTRICTED

### `class SystemChannelFlags(IntFlag)`
https://docs.discord.com/developers/resources/guild#guild-object-system-channel-flags.

- attributes: SUPPRESS_JOIN_NOTIFICATIONS, SUPPRESS_PREMIUM_SUBSCRIPTIONS, SUPPRESS_GUILD_REMINDER_NOTIFICATIONS,
  SUPPRESS_JOIN_NOTIFICATION_REPLIES, SUPPRESS_ROLE_SUBSCRIPTION_PURCHASE_NOTIFICATIONS,
  SUPPRESS_ROLE_SUBSCRIPTION_PURCHASE_NOTIFICATION_REPLIES

## `wd_discord.resources.guild.guild` — `wd-discord/src/wd_discord/resources/guild/guild.py`
Discord guild model.

### `class Guild(DiscordModel)`
https://docs.discord.com/developers/resources/guild#guild-object.

- fields: id: Snowflake, name: str, icon: ImageHash | None, icon_hash: ImageHash | None, splash: ImageHash | None,
  discovery_splash: ImageHash | None, owner: bool | None, owner_id: Snowflake, permissions: PermissionsField | None,
  afk_channel_id: Snowflake | None, afk_timeout: int, widget_enabled: bool | None, widget_channel_id: Snowflake | None,
  verification_level: VerificationLevel, default_message_notifications: DefaultMessageNotificationLevel,
  explicit_content_filter: ExplicitContentFilterLevel, roles: list[Role], emojis: list[Emoji], features: list[str],
  mfa_level: MFALevel, application_id: Snowflake | None, system_channel_id: Snowflake | None, system_channel_flags:
  SystemChannelFlags, rules_channel_id: Snowflake | None, max_presences: int | None, max_members: int | None,
  vanity_url_code: str | None, description: str | None, banner: ImageHash | None, premium_tier: PremiumTier,
  premium_subscription_count: int | None, preferred_locale: str, public_updates_channel_id: Snowflake | None,
  max_video_channel_users: int | None, max_stage_video_channel_users: int | None, approximate_member_count: int | None,
  approximate_presence_count: int | None, welcome_screen: WelcomeScreen | None, nsfw_level: NSFWLevel, stickers:
  list[Sticker] | None, premium_progress_bar_enabled: bool, safety_alerts_channel_id: Snowflake | None, incidents_data:
  IncidentsData | None

## `wd_discord.resources.guild.incidents_data` — `wd-discord/src/wd_discord/resources/guild/incidents_data.py`
Discord guild incidents data model.

### `class IncidentsData(DiscordModel)`
https://docs.discord.com/developers/resources/guild#incidents-data-object.

- fields: invites_disabled_until: datetime | None, dms_disabled_until: datetime | None, dm_spam_detected_at: datetime |
  None, raid_detected_at: datetime | None

## `wd_discord.resources.guild.member` — `wd-discord/src/wd_discord/resources/guild/member.py`
Discord guild member model (https://docs.discord.com/developers/resources/guild#guild-member-object).

### `class GuildMemberFlags(IntFlag)`
https://docs.discord.com/developers/resources/guild#guild-member-object-guild-member-flags.

- attributes: DID_REJOIN, COMPLETED_ONBOARDING, BYPASSES_VERIFICATION, STARTED_ONBOARDING, IS_GUEST,
  STARTED_HOME_ACTIONS, COMPLETED_HOME_ACTIONS, AUTOMOD_QUARANTINED_USERNAME, DM_SETTINGS_UPSELL_ACKNOWLEDGED,
  AUTOMOD_QUARANTINED_GUILD_TAG

### `class GuildMember(DiscordModel)`
https://docs.discord.com/developers/resources/guild#guild-member-object.

- fields: user: User | None, nick: str | None, avatar: ImageHash | None, banner: ImageHash | None, roles:
  list[Snowflake], joined_at: datetime | None, premium_since: datetime | None, deaf: bool, mute: bool, flags:
  GuildMemberFlags, pending: bool | None, permissions: PermissionsField | None, communication_disabled_until: datetime |
  None, avatar_decoration_data: Avatar | None, collectibles: Collectibles | None

## `wd_discord.resources.guild.partial_guild` — `wd-discord/src/wd_discord/resources/guild/partial_guild.py`
The partial guild Discord sends inside an interaction (https://docs.discord.com/developers/interactions/receiving-and-responding#interaction-object).

### `class PartialGuild(DiscordModel)`
The guild an interaction was sent from: only its ID, preferred locale and features.

- fields: id: Snowflake, locale: Locale, features: list[str]

## `wd_discord.resources.guild.role` — `wd-discord/src/wd_discord/resources/guild/role.py`
Discord role models (role, role tags, and role colors).

### `class RoleTags(DiscordModel)`
https://docs.discord.com/developers/topics/permissions#role-object-role-tags-structure.

- fields: bot_id: Snowflake | None, integration_id: Snowflake | None, premium_subscriber: bool | None,
  subscription_listing_id: Snowflake | None, available_for_purchase: bool | None, guild_connections: bool | None

### `class RoleColors(DiscordModel)`
https://docs.discord.com/developers/topics/permissions#role-object-role-colors-object.

- fields: primary_color: int, secondary_color: int | None, tertiary_color: int | None

### `class Role(DiscordModel)`
https://docs.discord.com/developers/topics/permissions#role-object.

- fields: id: Snowflake, name: str, color: int, colors: RoleColors | None, hoist: bool, icon: ImageHash | None,
  unicode_emoji: str | None, position: int, permissions: PermissionsField, managed: bool, mentionable: bool, tags:
  RoleTags | None, flags: int

## `wd_discord.resources.guild.sticker` — `wd-discord/src/wd_discord/resources/guild/sticker.py`
Discord sticker models and enums.

### `class StickerType(IntEnum)`
https://docs.discord.com/developers/resources/sticker#sticker-object-sticker-types.

- attributes: STANDARD, GUILD

### `class StickerFormatType(IntEnum)`
https://docs.discord.com/developers/resources/sticker#sticker-object-sticker-format-types.

- attributes: PNG, APNG, LOTTIE, GIF

### `class Sticker(DiscordModel)`
https://docs.discord.com/developers/resources/sticker#sticker-object.

- fields: id: Snowflake, pack_id: Snowflake | None, name: str, description: str | None, tags: str, type: StickerType,
  format_type: StickerFormatType, available: bool | None, guild_id: Snowflake | None, user: User | None, sort_value: int
  | None

## `wd_discord.resources.guild.welcome_screen` — `wd-discord/src/wd_discord/resources/guild/welcome_screen.py`
Discord welcome screen models.

### `class WelcomeScreenChannel(DiscordModel)`
https://docs.discord.com/developers/resources/guild#welcome-screen-object-welcome-screen-channel-structure.

- fields: channel_id: Snowflake, description: str, emoji_id: Snowflake | None, emoji_name: str | None
- `@property emoji -> PartialEmoji | None` — Emoji object representing the emoji for this welcome screen channel, or ``None`` if unset.

### `class WelcomeScreen(DiscordModel)`
https://docs.discord.com/developers/resources/guild#welcome-screen-object.

- fields: description: str | None, welcome_channels: list[WelcomeScreenChannel]

## `wd_discord.resources.invite` — `wd-discord/src/wd_discord/resources/invite.py`
The Discord invite resource.

### `class Invite(DiscordModel)`
A guild invite (subset - https://docs.discord.com/developers/resources/invite).

- fields: code: str, guild: Mapping[str, object] | None, channel: Mapping[str, object] | None, inviter: Mapping[str,
  object] | None, uses: int | None, max_uses: int | None, max_age: int | None, temporary: bool | None, created_at: str |
  None
- `@property url -> str` — The invite's shareable URL.

## `wd_discord.resources.user` — `wd-discord/src/wd_discord/resources/user/__init__.py`
https://docs.discord.com/developers/resources/user#user-object.

- exports: Avatar, Collectibles, NamePlate, User

## `wd_discord.resources.user.collectibles` — `wd-discord/src/wd_discord/resources/user/collectibles.py`
User collectibles sub-object.

### `class Collectibles(DiscordModel)`
https://docs.discord.com/developers/resources/user#collectibles.

- fields: nameplate: NamePlate | None

## `wd_discord.resources.user.profile` — `wd-discord/src/wd_discord/resources/user/profile.py`
User profile sub-objects: avatar decoration and nameplate collectibles.

### `class Avatar(DiscordModel)`
https://docs.discord.com/developers/resources/user#avatar-decoration-data-object.

- fields: asset: ImageHash, sku_id: Snowflake

### `class NamePlateBackgroundColor(StrEnum)`
Background color of the nameplate.

- attributes: CRIMSON, BERRY, SKY, TEAL, FOREST, BUBBLE_GUM, VIOLET, COBALT, CLOVER, LEMON, WHITE

### `class NamePlate(DiscordModel)`
https://docs.discord.com/developers/resources/user#nameplate.

- fields: sku_id: Snowflake, asset: ImageHash, label: str, palette: NamePlateBackgroundColor

## `wd_discord.resources.user.user` — `wd-discord/src/wd_discord/resources/user/user.py`
https://docs.discord.com/developers/resources/user#user-object.

### `class UserPrimaryGuild(DiscordModel)`
https://docs.discord.com/developers/resources/user#user-object-user-primary-guild.

- fields: identity_guild_id: Snowflake | None, identity_enabled: bool | None, tag: str | None, badge: ImageHash | None

### `class User(DiscordModel)`
https://docs.discord.com/developers/resources/user#user-object.

- fields: id: Snowflake, username: str, discriminator: str, global_name: str | None, avatar: ImageHash | None, bot: bool
  | None, system: bool | None, mfa_enabled: bool | None, banner: ImageHash | None, accent_color: int | None, locale: str
  | None, verified: bool | None, email: str | None, flags: int | None, premium_type: int | None, public_flags: int |
  None, avatar_decoration_data: Avatar | None, collectibles: Collectibles | None, primary_guild: UserPrimaryGuild | None
- `validate_scopes(allowed_scopes: set[OAuthScopes]) -> bool` — Check that every scope-gated field is covered by ``allowed_scopes``.

## `wd_discord.resources.voice` — `wd-discord/src/wd_discord/resources/voice.py`
Discord voice state model (https://docs.discord.com/developers/resources/voice#voice-state-object).

### `class VoiceState(DiscordModel)`
A user's voice connection status: which voice channel they are in, and whether they're muted.

- fields: guild_id: Snowflake | None, channel_id: Snowflake | None, user_id: Snowflake, member: GuildMember | None,
  session_id: str, deaf: bool, mute: bool, self_deaf: bool, self_mute: bool, self_stream: bool | None, self_video: bool,
  suppress: bool, request_to_speak_timestamp: datetime | None
