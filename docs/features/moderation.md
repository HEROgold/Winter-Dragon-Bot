# Moderation & Logging

Everything that watches a server for things happening and either records them or acts on them. This is the bot's largest single subsystem, built around Discord's audit log.

Audience: server moderators and admins.

---

## Audit-log event pipeline

The backbone of server logging. When Discord emits an audit-log entry, a listener hands it to a factory that resolves the entry's action to the event classes registered for it; each event then renders itself as an embed and decides where it should be delivered. Adding coverage for a new audit action means declaring a new event class — the listener and dispatcher do not change.

A diffing helper computes what actually changed between an entry's before/after states (including role additions and removals), so log embeds show the delta rather than a full object dump.

**Status:** ✅ Ported for the pipeline itself — `wd-core/src/wd_core/events.py` holds the event base, factory, handler, and diff utilities. 🟡 for the listener cog that feeds it.
**Source on `main`:** `src/winter_dragon/bot/events/`, `extensions/server/audit_event_listener.py`

## Log channels

Provisions and maintains the channels audit events are written to. A server can have log channels detected from an existing setup (`/logchannels detect`), created, updated, or removed, and the bot keeps the channel↔action mapping in the database so events route to the right place.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/server/log_channels.py`

## Aggregated log view

An alternative to one channel per action type: a single persistent message on a global log channel that holds a rolling cache of recent audit embeds, paginated in place. Moderators page through history without the server accumulating a dozen log channels.

**Status:** 🟡 Copied, unwired — depends on the missing UI toolkit's paginator.
**Source on `main`:** `src/winter_dragon/bot/extensions/server/log_aggregator.py`

## Gatekeeper

Raid and spam-account mitigation. When enabled for a guild, new joiners are gated behind a role-based check before they reach the rest of the server; `/gatekeeper setup` creates the roles the system needs, and it can be enabled or disabled per guild.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/server/gatekeeper.py`

## Infractions

Tracks Discord AutoMod actions against users and assigns each rule action a severity (blocking a message weighs more than sending an alert), with the intent of banning a user once they accumulate a configurable threshold per guild.

!!! note "Incomplete on `main`"
    The severity map and command scaffolding exist, but the rule registration, infraction accrual, and threshold enforcement are still open TODOs on `main`. This is not a porting gap.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/server/infractions.py`

## Synced bans

Opt-in ban sharing across servers. A guild joins the network (`/syncban sync join`), and can then pull in bans issued by every other subscribed guild — so an account banned elsewhere in the network can be banned locally too. Leaving the network stops the sharing.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/server/sync_ban.py`

## Message purge

Bulk message deletion (`/purge`) with a history-based path for messages older than Discord's bulk-delete window, which the API refuses to delete in bulk.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/server/purge.py`

## Channel utilities

Moderation actions on channels themselves: lock and unlock a channel — optionally scoped to a single role or member rather than everyone — and delete a category together with every channel inside it.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/server/channel_utils.py`

## Forum duplicate detection

Flags likely-duplicate forum posts by comparing a new post's title against existing ones with a similarity ratio above a threshold.

!!! note "Incomplete on `main`"
    Known post titles are held in an in-memory list that is never populated from the database, so the detector has nothing to compare against in practice.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/server/forum_dupe_finder.py`
