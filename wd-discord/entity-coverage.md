# Entity coverage

This page tracks which Discord objects wd-discord has as entities in `src/wd_discord/entities/`, and which ones are still missing. An object counts when it has its own ID or REST routes, following Discord's docs at <https://docs.discord.com/developers>.

Small value objects carried inside another object (embed fields, role tags, thread metadata, forum tags, install params) don't count. They stay data models and are reached through the entity that carries them.

How an entity returns a related object: if the full object can be built from data already in hand, without a request, it's built automatically (for example `GatewayGuild.owner` → `Member`). Otherwise the entity returns the `Partial` (for example `Guild.owner` → `PartialMember`), and the caller decides when to `.fetch()` it.

## Totals

| Status | Count |
| --- | --- |
| Entity done | 22 |
| Model exists, no entity yet | 0 |
| No model yet, so no entity | 26 |
| **Total tracked** | **48** |

## Done (22)

| Discord object | Entity | Model gaps that limit the entity |
| --- | --- | --- |
| Application | `Application`, `CurrentApplication` | none |
| Team | `Team` | none |
| Team Member | `TeamMember` | none |
| Application Command | `GlobalCommand`, `GuildCommand` (+ partials, stores) | none |
| Interaction | `CommandInteraction`, `ComponentInteraction`, `AutocompleteInteraction`, `UnknownInteraction` | PING and MODAL_SUBMIT have no model of their own |
| Resolved Data | `Resolved` | `members`, `messages` and `attachments` aren't modeled |
| Ready | `Ready` | `application` is kept as a bare ID string |
| Channel (threads included) | `Channel`, `PartialChannel` | `applied_tags` stay IDs |
| Permission Overwrite | `PermissionOverwrite` | none |
| Thread Member | `ThreadMember` | the nested guild `member` is left out |
| Emoji | `Emoji` | none |
| Sticker | `Sticker` | none |
| Entitlement | `Entitlement` | its SKU stays an ID, since SKU has no model |
| Guild | `Guild`, `GatewayGuild`, `PartialGuild` | GUILD_CREATE `presences` are raw; stage instances, scheduled events and soundboard sounds aren't modeled |
| Guild Member | `Member`, `PartialMember` | none |
| Role | `Role`, `PartialRole` | none |
| Welcome Screen | `WelcomeScreen`, `WelcomeScreenChannel` | none |
| Invite | `Invite` | `guild`, `channel` and `inviter` arrive as raw mappings, and invite metadata is a subset |
| Message | `Message`, `PartialMessage` | the model is thin: no attachments, embeds, mentions, reactions, reference, components or poll |
| User | `User`, `CurrentUser`, `PartialUser` | none |
| Voice State | `VoiceState` | none |
| Unavailable Guild | `Ready.guilds` → `PartialGuild` | none (it's only an ID) |

## Missing: no model yet (26)

Each of these needs a data model in `resources/` first, then an entity.

| Discord object | Docs page |
| --- | --- |
| Application Role Connection Metadata | resources/application-role-connection-metadata |
| Audit Log | resources/audit-log |
| Audit Log Entry | resources/audit-log |
| Auto Moderation Rule | resources/auto-moderation |
| Followed Channel | resources/channel |
| Guild Preview | resources/guild |
| Guild Widget | resources/guild |
| Guild Widget Settings | resources/guild |
| Integration | resources/guild |
| Ban | resources/guild |
| Guild Onboarding | resources/guild |
| Guild Scheduled Event | resources/guild-scheduled-event |
| Guild Template | resources/guild-template |
| Lobby | resources/lobby |
| Reaction | resources/message |
| Attachment | resources/message |
| Poll | resources/poll |
| SKU | resources/sku |
| Soundboard Sound | resources/soundboard |
| Stage Instance | resources/stage-instance |
| Sticker Pack | resources/sticker |
| Subscription | resources/subscription |
| Connection | resources/user |
| Voice Region | resources/voice |
| Webhook | resources/webhook |
| Application Command Permissions | interactions/application-commands |

## Entities in, entities out

Entity methods take entities, not IDs: `member.add_role(role)`, `channel.set_permissions(member, deny=...)`, `channel.fetch_messages(before=message)`. Raw IDs go only into the methods that turn an ID into a handle without a request (`client.guilds.partial(id)`, `guild.role(id)`, `guild.member(id)`, `channel.message(id)`) and into lookups by ID (`guild.get_role(id)`, `resolved.user(id)`). If you pass an object from the wrong guild or channel, nothing checks it on our side: the request goes out and Discord's error comes back as a value.

Still exposed or taken as IDs, and what blocks each one:

| Where | Blocked by |
| --- | --- |
| `CommandInteraction.command_id` | the interaction's `data.guild_id`, which says whether it's a guild or a global command, isn't modeled |
| `Interaction.application_id`, `Ready.application_id` | `Application` has no partial entity; an application-by-ID handle would need routes that work for other apps |
| `Entitlement.sku_id` | SKU has no model |
| `Channel.applied_tags` (forum tag IDs) | the tags live on the parent forum, which is only known as a partial |
| `GuildChannelParams.parent_id`, `GuildChannelParams.permission_overwrites`, `ChannelParams` | these are request-body models; taking entities there means an entity-level `create_channel(..., parent=...)` |
| `Guild.create_channel(params)` | same: it takes the request-body model as is |

## Actions blocked on a params model

These routes exist for objects that are already entities, but they need a request-body model that doesn't exist yet:

- Edit a guild, and create a role or edit one (`PATCH /guilds/{id}`, `POST`/`PATCH /guilds/{id}/roles`)
- Create or edit an emoji or sticker
- Edit the application (`PATCH /applications/@me`) and the welcome screen
- Start a thread, and list active or archived threads (their response wraps threads and members together)
- List a channel's pins (the response wraps the messages) and a guild's bans
