# User Tools

Features that belong to an individual member rather than to a server: personal notifications, personal data, lookups, and small utilities.

Audience: server members.

---

## Steam sales

The bot's most substantial user-facing subsystem. It scrapes the Steam store on a schedule and notifies subscribed members about sales — free games in particular — instead of requiring them to check.

The scraping side is split by page type, sharing a common fetch/parse base:

- **Sale listings** — discovers discounted titles from a configured search URL.
- **App pages** — details for an individual store app.
- **Bundle pages** — expands a bundle or sub into the games it contains.
- **Search results** — walks paginated search output.

On top of that sits per-user subscription state: members opt in to notifications, filter by tag, browse current sales through a paginated menu, and opt out again. A notifier composes the embed and delivers it to everyone whose filters match.

Surface: `/steam add | remove | …`

**Status:** ✅ Ported for the stateless helpers — the scraper base, Steam URL handling, and tag definitions carry no `winter_dragon.*` imports (`wd-cogs/src/wd_cogs/user/steam/`, plus `wd-bot/src/wd_bot/steam_url.py`). 🟡 for the concrete scrapers, the sales cog, its menu, and the notifier, all of which depend on the Steam sale/user tables.
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
