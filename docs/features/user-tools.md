# User Tools

Features that belong to an individual member rather than to a server: personal notifications, personal data, lookups, and small utilities.

Audience: server members.

---

## Steam sales

The bot's most substantial user-facing subsystem. It asks Steam's store web APIs for sales on a schedule and notifies subscribed members about them — free games in particular — instead of requiring them to check.

A background loop queries `IStoreQueryService/Query`, which filters on discount on Steam's side and sorts by top sellers, 1000 items per request, without an API key. Each scrape stores every sale from `complete_percent` up, and the `top_sellers` best-selling sales below that, down to `stored_percent` (lower if a subscriber's threshold is lower). Each item comes with its price (in the `country_code` store region), its discount and when that ends, including the claim deadline of free giveaways. The loop scrapes on load, then every `update_interval` or 5 minutes after Steam's daily rollover (17:00 UTC), whichever comes first, and logs when the next scrape is. A minute after a sale's end it's checked again through `IStoreBrowseService/GetItems`, 200 items per request. Shown sales that a scrape no longer lists are checked the same way, unless their end is known; those stay listed until they end and are checked then. All requests to Steam share one throttle (`request_interval` apart), and a 429 pauses every request for its `Retry-After`, or a backoff that doubles from 5 minutes. A sale that has ended is removed, one that continues is updated, and a sale nobody could confirm is hidden after `outdated_after`.

Members opt in to DMs, set the minimum discount they care about, and browse current sales a page at a time. The page buttons only respond to the member who ran the command. After each scrape, every subscriber gets one DM with the sales above their threshold that they haven't been told about yet.

Surface: `/steam add | percentage | remove | show`

Settings (`[SteamSettings]` in `config.ini`): `country_code`, `stored_percent`, `complete_percent`, `top_sellers`, `request_interval`, `update_interval`, `outdated_after`, `recheck_delay`, `embed_color`. The install link needs `[Settings] steam_redirect` to be an https redirect to `steam://`; Discord won't render a raw `steam://` link.

**Status:** ✅ Ported to `src/winter_dragon/cogs/steam/`.
**Source on `main`:** `src/winter_dragon/bot/extensions/user/steam/`

## Reminders

Personal reminders, one-shot or repeating on an interval, with a command to cancel one. Reminders are DMed by the cog's own background task, which looks for due ones every `check_interval` seconds; they're stored, so they survive a restart. A repeating reminder that came due while the bot was offline is sent once, then moves on to its next time. A reminder that can't be DMed (closed DMs) is dropped rather than retried forever. Cancelling autocompletes the member's own reminders.

Surface: `/reminder add | repeat | remove`

Settings (`[ReminderSettings]` in `config.ini`): `check_interval`.

**Status:** ✅ Ported to `src/winter_dragon/cogs/reminder.py`; it keeps `main`'s `reminder`/`timedreminder` tables.
**Source on `main`:** `src/winter_dragon/bot/extensions/user/reminder.py`

## Fuel tracking

A personal log for vehicle refuelling — record a fill-up (`/fuel add`) and render a graph of distance travelled per unit of fuel over time (`/fuel efficiency`), sent as a PNG attachment. An unusual feature for a Discord bot, and entirely per-user.

**Status:** ✅ Ported to `src/winter_dragon/cogs/fuel.py`; it keeps `main`'s `carfuels` table. `/fuel graph efficiency` became `/fuel efficiency`: wd_bot has no nested subcommand groups.
**Source on `main`:** `src/winter_dragon/bot/extensions/user/car_fuel.py`

## Urban Dictionary

Look up a term, or pull random definitions (`/urban search | random`), rendered as embeds in-channel. Long definitions are cut to fit Discord's embed limits.

Settings (`[UrbanSettings]` in `config.ini`): `allow_random`, `max_definitions`.

**Status:** ✅ Ported to `src/winter_dragon/cogs/urban.py`.
**Source on `main`:** `src/winter_dragon/bot/extensions/user/urban.py`

---

## Utilities

Small, self-contained commands.

- **Invites** (`/invite bot`, `/invite guild`) — a link to add the bot to another server, and an invite to the official support guild. The bot builds its own invite URL from its configured permission set, so the link cannot drift from what the bot actually needs.
- **Uptime** (`/uptime bot`) — how long the current process has been running.
- **Team splitting** (`/team voice | text | lobby`) — randomly divide members into teams, either everyone in the caller's voice channel or a set shown in a message, with a lobby channel found or created for the purpose.

**Status:** ✅ Invites and uptime ported to `src/winter_dragon/cogs/invite.py` and `uptime.py`; 🟡 team splitting copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/utility/`
