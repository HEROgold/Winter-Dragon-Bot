# Server Management

Automation that shapes a server: roles handed out on join, channels that create themselves, member greetings, live statistics, and one-shot server scaffolding.

Audience: server admins configuring their guild.

---

## Auto-assign roles

Give every new member one or more roles automatically on join (`/autoassign …`). Admins can inspect the current selection, add roles, and remove them. Removes the usual manual step of welcoming someone into a role.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/server/auto_assign.py`

## Role re-assignment on rejoin

Remembers which roles a member held when they left — including when they were kicked or banned — and restores them if they come back. Enabled or disabled per guild.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/server/role_reminder.py`

## Automatic channels

Self-service temporary voice channels. An admin marks a channel as the "hub"; joining it creates a personal channel for that member in the hub's category and moves them in, and the channel is deleted once everyone has left. A member who already has a channel is moved back into it instead. The owner gets an overwrite to run their channel (rename, limit, move/mute members) but not to change who may see it. Members set their channel's name and user limit once, applied to their current channel and every later one; admins can cap how many auto-channels the guild allows at once. A guided setup command creates the category and hub.

Who is in which voice channel is tracked in memory from GUILD_CREATE's voice states and every VOICE_STATE_UPDATE; on startup, channels that emptied while the bot was offline are deleted.

Surface: `/autochannel setup | mark | guild-limit | limit | name` (`setup`, `mark` and `guild-limit` need Manage Server).

**Status:** ✅ Ported to `src/winter_dragon/cogs/autochannel.py`, with cog-local `autochannelhub`, `autochannel` and `autochannelsettings` tables. `guild_limit` became `guild-limit`, and now caps the number of channels (on `main` it was stored but never enforced).
**Source on `main`:** `src/winter_dragon/bot/extensions/server/autochannel.py`

## Welcome messages

Configurable greeting for new members, set up through an interactive menu (`/welcome`) rather than a wall of arguments — channel, message, and whether it fires at all are stored per guild.

**Status:** 🟡 Copied, unwired — also depends on the missing UI toolkit's menu.
**Source on `main`:** `src/winter_dragon/bot/extensions/server/welcome.py`

## Guild statistics

Live server statistics, both on demand (`/stats show`) and as a locked "Stats" category of voice channels whose names carry the counts: total users, online users, bots, creation date and peak online. Counts come from Discord's approximate member and presence counts plus a paged member listing for the bots; bots are taken to be online, so online users is presences minus bots. The peak is stored, not read back from a channel name. The cog's own background task renames only the channels whose name changed, every `update_interval` seconds (Discord allows two renames per channel per 10 minutes), and forgets channels deleted by hand.

Everyone can use `show`; `add` and `remove` need Manage Channels, checked per subcommand since Discord only gates the group as a whole; `reset` recreates every guild's stats channels and is for the bot's owners (the application owner or its team).

Surface: `/stats show | add | remove | reset`

Settings (`[StatsSettings]` in `config.ini`): `update_interval`.

**Status:** ✅ Ported to `src/winter_dragon/cogs/stats.py`, with cog-local `statchannel` and `peakonline` tables replacing `main`'s tagged channels.
**Source on `main`:** `src/winter_dragon/bot/extensions/server/stats.py`

## Announcements

Two distinct surfaces, deliberately separated:

- **Guild announcement** (`/announcement`) — restricted to users who can already mention everyone; wraps their message in a clean embed and pings the server.
- **Global announcement** (`/announce`) — bot-owner only; broadcasts a message about the bot to every server it runs on.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/server/announcement.py`, `extensions/bot_extension/bot_control.py`

## Guild scaffolding

Bootstraps a freshly created server into a usable shape — generating the baseline channels and roles in one command (`/generate`) instead of by hand.

Disabled by default on `main` (it does not auto-load), since it makes sweeping changes to a guild.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/user/guild_creator.py`
