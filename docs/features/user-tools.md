# User Tools

Features that belong to an individual member rather than to a server: personal notifications, personal data, lookups, and small utilities.

Audience: server members.

---

## Steam sales

The bot's most substantial user-facing subsystem. It scrapes the Steam store on a schedule and notifies subscribed members about sales — free games in particular — instead of requiring them to check.

A background loop scrapes Steam's specials search page every few hours, down to the lowest threshold any subscriber set. For each new sale it reads the app page to learn when the sale ends, then checks that page again a minute after the end. A sale that has ended is removed, and one that continues gets its new end.

Members opt in to DMs, set the minimum discount they care about, and browse current sales a page at a time. The page buttons only respond to the member who ran the command. After each scrape, every subscriber gets one DM with the sales above their threshold that they haven't been told about yet.

Surface: `/steam add | percentage | remove | show`

Settings (`[SteamSettings]` in `config.ini`): `search_url`, `update_interval`, `outdated_after`, `recheck_delay`, `embed_color`.

**Status:** ✅ Ported to `src/winter_dragon/cogs/steam/`.
**Source on `main`:** `src/winter_dragon/bot/extensions/user/steam/`

## Reminders

Personal reminders, one-shot (`/remind`) or repeating on an interval (`/timed_reminder`), with a command to cancel one. Delivery is driven by a background loop against stored reminders, so reminders survive a restart.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/user/reminder.py`

## Fuel tracking

A personal log for vehicle refuelling — record a fill-up (`/fuel add`) and render a graph of distance travelled per unit of fuel over time (`/fuel graph efficiency`). An unusual feature for a Discord bot, and entirely per-user.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/user/car_fuel.py`

## Urban Dictionary

Look up a term, or pull a random definition (`/urban …`), rendered as embeds in-channel.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/user/urban.py`

---

## Utilities

Small, self-contained commands.

- **Invites** (`/invite bot`, `/invite guild`) — a link to add the bot to another server, and an invite to the official support guild. The bot builds its own invite URL from its configured permission set, so the link cannot drift from what the bot actually needs.
- **Uptime** (`/uptime bot`) — how long the current process has been running.
- **Team splitting** (`/team voice | text | lobby`) — randomly divide members into teams, either everyone in the caller's voice channel or a set shown in a message, with a lobby channel found or created for the purpose.

**Status:** 🟡 Copied, unwired for all three.
**Source on `main`:** `src/winter_dragon/bot/extensions/utility/`
