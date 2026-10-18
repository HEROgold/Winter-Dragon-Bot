# Moderation

Features that help guild admins keep a guild in order. Like server management, their data belongs to the guild.

## Log channels

The guild's audit-log events (bans, role changes, channel edits, …) are posted as readable embeds to log channels.

- **Who:** guild admins set them up; whoever can see the channels reads them.
- **Commands:** `/logchannels` to detect an existing setup, create, update or remove the channels.
- **Stores:** each guild's log channels and which events go to which.
- **Status:** Port. The event pipeline is live in `wd-core` (`events.py`); the cog that listens and posts is to be rebuilt.

## Server log

A dashboard page holding the guild's recent audit-log events and bot setting changes, so guild admins can page through history without a log channel per event type. It replaces `main`'s aggregated log message.

- **Who:** guild admins.
- **Stores:** guild-setting changes are kept as history (a herogold `DataModel`, see [ADR 0003](../adr/0003-herogold-models-and-soft-delete.md)); audit events come from the same pipeline as log channels.
- **Dashboard:** the Server log page (later): filter by event type, member and date.
- **Status:** New.

## Infractions

The bot counts a member's AutoMod infractions in a guild, weighting each by how serious the AutoMod action was, and acts once a threshold is reached.

- **Who:** guild admins set the threshold and the action; members are the subject.
- **Rules:**
  - Blocking a message weighs more than sending an alert; each AutoMod action has a fixed weight.
  - At the threshold the bot does what the guild admin chose: **alert** (post to the log channel, the default), **timeout**, or **ban**.
- **Stores:** each infraction as history (a herogold `DataModel`); each guild's threshold and action.
- **Dashboard:** server settings: threshold and action; the server log shows the infractions.
- **Status:** Port; on `main` only the weights and command scaffolding existed.

## Ban networks

Guilds that trust each other share their bans through a **ban network**.

- **Who:** guild admins.
- **Rules:**
  - A guild admin creates a network and invites other guilds; an invited guild joins only when its guild admin accepts. A guild may be in several networks, and leave any time.
  - Each guild chooses per network to apply its bans **automatically** or to **review** them first.
  - There is no global network: a guild only receives bans from networks it accepted.
- **Stores:** networks, their guilds, invitations, each guild's apply-or-review choice, and shared bans.
- **Dashboard:** server settings: the guild's networks, invitations, and bans waiting for review.
- **Status:** Port, redesigned (`main` had one opt-in network for every guild).

## Purge

Bulk-delete a channel's recent messages, including ones older than Discord's two-week bulk-delete window, which are deleted one by one.

- **Who:** members with the Manage Messages permission.
- **Commands:** `/purge`.
- **Status:** Port.

## Channel utilities

- **Who:** guild admins.
- **Commands:** `/channel-utils delete-category` (a category and every channel in it), `/channel-utils lock` and `/channel-utils unlock` (deny or allow a role or member sending messages in this channel).
- **Status:** Live, [channel_utils.py](../../src/winter_dragon/cogs/channel_utils.py).

## Dropped

- **Gatekeeper** (`main`): Discord's verification levels and onboarding cover it.
- **Forum duplicate detection** (`main`).
