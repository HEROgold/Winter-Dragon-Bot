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

Self-service temporary voice channels. An admin marks a channel as the "hub"; joining it creates a personal channel for that member, which is cleaned up when it empties. Members control their own channel's name and user limit, and admins can cap how many auto-channels the guild allows in total. A guided setup command wires the whole thing up.

Surface: `/autochannel setup | mark | guild_limit | limit | name`

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/server/autochannel.py`

## Welcome messages

Configurable greeting for new members, set up through an interactive menu (`/welcome`) rather than a wall of arguments — channel, message, and whether it fires at all are stored per guild.

**Status:** 🟡 Copied, unwired — also depends on the missing UI toolkit's menu.
**Source on `main`:** `src/winter_dragon/bot/extensions/server/welcome.py`

## Guild statistics

Live server statistics, both on demand (`/stats show`) and as self-updating stat channels whose names carry counts such as members online. Includes commands to (re)create the channels and to reset stored stats.

**Status:** 🟡 Copied, unwired.
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
