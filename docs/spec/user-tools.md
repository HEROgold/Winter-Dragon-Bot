# User tools

Features a member uses for themselves. Their data belongs to the member, not to a guild, so it survives a guild removing the bot and is deleted only by the member's own deletion request.

## Reminders

A member is reminded of something by DM, once or on repeat.

- **Who:** members.
- **Commands:** `/reminder add` (once, after a given time), `/reminder repeat` (every given time), `/reminder remove`.
- **Stores:** each reminder: its member, text, when it is due next, and for a repeating one its interval.
- **Rules and limits:** a reminder arrives at most one check interval late; it may be set at most `max_delay_days` ahead, and a repeating one may wait at most that long between reminders; its text is at most `max_content_length` characters. A reminder that can't be DMed (the member closed their DMs) is treated as sent, not retried: a one-off one is removed, a repeating one moves on to its next time.
- **Settings:** `ReminderSettings`: `check_interval` (60 s), `max_delay_days` (3650), `max_content_length` (1000).
- **Dashboard:** the Reminders page: a route of upcoming reminders grouped by day; add, edit and delete.
- **Status:** Live, [reminder/](../../src/winter_dragon/cogs/reminder/cog.py).

## Fuel log

A member logs their car's refuels and sees its fuel efficiency over time.

- **Who:** members.
- **Commands:** `/fuel add`, `/fuel efficiency` (a graph, sent as an image).
- **Stores:** each refuel: its member, fuel added, distance driven since the previous refuel, price paid, and when.
- **Settings:** `FuelSettings`: the graph's size and file name.
- **Dashboard:** the Fuel log page (later): the refuels as an editable table and an interactive efficiency chart.
- **Status:** Live, [fuel.py](../../src/winter_dragon/cogs/fuel.py).

## Steam sales

The bot finds Steam sales on a schedule; members list them, and get a DM when new ones reach their threshold.

- **Who:** members.
- **Commands:** `/steam show` (sales of at least a given discount), `/steam add` (alerts for free games), `/steam percentage` (alerts from a given discount), `/steam remove` (no more alerts).
- **Stores:** the sales found (shared, not personal); each subscriber and their threshold.
- **Rules and limits:**
  - Steam is asked every `update_interval`, and again just after its daily rollover and just after a known sale ends.
  - Every sale from `complete_percent` up is stored; below it only the `top_sellers` best-selling ones, down to `stored_percent`.
  - A subscriber is DMed once per new sale above their threshold; a threshold of 100 means free games only.
  - Requests to Steam are spaced `request_interval` apart and back off when Steam rate-limits.
- **Settings:** `SteamSettings` (region, thresholds, intervals, backoff, page size, embed color).
- **Dashboard:** the Steam sales page (later): sales filtered and paged by discount and kind; the member's alert threshold.
- **Status:** Live, [steam/](../../src/winter_dragon/cogs/steam/__init__.py).

## Urban Dictionary

Look up a term, or random terms, on Urban Dictionary.

- **Who:** members.
- **Commands:** `/urban search`, `/urban random`.
- **Rules:** at most `max_definitions` definitions per reply, cut to fit Discord's embed limits; `/urban random` can be turned off with `allow_random`, as random definitions are often not safe for work.
- **Settings:** `UrbanSettings`: `allow_random`, `max_definitions`, `request_timeout`.
- **Status:** Live, [urban.py](../../src/winter_dragon/cogs/urban.py).

## Invites

- **Commands:** `/invite bot` (the link that adds the bot to a server), `/invite guild` (a single-use, short-lived invite to the support server).
- **Settings:** `Settings.support_guild_id` in `config.ini`; `InviteSettings.support_invite_max_age`.
- **Dashboard:** the landing page's "Add to your server" and support links.
- **Status:** Live, [invite.py](../../src/winter_dragon/cogs/invite.py).

## Uptime

- **Commands:** `/uptime bot`: when the bot started.
- **Dashboard:** the status page (later).
- **Status:** Live, [uptime.py](../../src/winter_dragon/cogs/uptime.py).

## Dropped

- **Team splitting** (`main`): tournaments already split players into teams.
