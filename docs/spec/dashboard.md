# Web dashboard

A website where members manage what the bot does for them, and guild admins configure their guilds. It is server-rendered by the FastAPI service with Jinja templates and htmx 4 ([ADR 0002](../adr/0002-htmx-jinja-dashboard.md)).

## Sign-in and access

- Members sign in with Discord (OAuth2). The callback sets an HttpOnly session cookie; the browser never holds a token. Every form that changes something is protected against cross-site requests.
- A **guild admin** is whoever has Discord's Manage Server permission in a guild, as Discord reports it at sign-in; server settings show only guilds where the member is one and the bot is present.
- The **bot owner** sees the owner panel; nobody else does.
- **Tournament organisers** see the controls of their tournament's live match.
- Every text says **server**, never guild.

## Pages

Built in this order; the later ones are specified now and built after the first five.

1. **Landing:** what the bot does, sign in with Discord, add the bot to a server, the support server.
2. **Your data:** everything stored about the member, grouped by feature, each group opening to its records; their voice-channel name and limit; command usage; linked accounts; and deleting all of it (see [Data and privacy](data-and-privacy.md#a-member-deletes-their-data)).
3. **Reminders:** upcoming reminders as a route grouped by day; add, edit, delete.
4. **Server settings**, per guild: automatic voice channel hub and limit, roles back on rejoin, roles on join, stats channels, welcome message, log channels, infraction threshold and action, command placement, ban networks, bot updates channel, tracking channel.
5. **Tournaments:** the guild's tournament as a public bracket that refreshes itself, its teams, and the organiser's controls.

Later:

6. **Server log:** audit events, setting changes and infractions, filtered by type, member and date.
7. **Fuel log:** refuels as an editable table, and an efficiency chart.
8. **Steam sales:** sales filtered and paged; the member's alert threshold.
9. **Status:** uptime, latency, and guild and member counts.
10. **Owner panel:** command sync and resync, latency and resource use, command usage, announcements to guilds.
11. **Climb** (with [Ranked tracking](ranked-tracking.md)): a Tracked Player's games, Attention Points and Notes.

## App links

Discord only makes `http(s)` links clickable, so the bot links app links like `steam://` through `/redirect?uri=<link>&mobile=<link>&fallback=<page>`. The page opens `uri`, or `mobile` on a phone, and shows a button in case the browser blocks the jump, plus the `fallback` web page. Anyone can open it without signing in. It refuses `http`, `javascript`, `data`, `vbscript`, `file`, `blob`, `ftp`, `ws` and `telnet` links, and a fallback that isn't `https`. The rules are in [redirect_link.py](../../src/winter_dragon/redirect_link.py). The bot builds these links on `Settings.dashboard_url` in `config.ini`, which has to match `public_url` in `dashboard.ini`.

## Design

The approved design is the "alpine route" in [sketches/dashboard/](../../sketches/dashboard/index.html): one family (Archivo, condensed for headings), snow and granite with route blue as the only accent and ember only for destructive actions, and the white-blue-white route marker meaning only "you are here" or "chosen". New pages reuse its stylesheet rather than inventing a new look.
