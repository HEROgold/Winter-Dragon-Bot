# The dashboard keeps no OAuth token: it keeps each session's shared guilds in memory and re-authorises silently

The dashboard revokes the Discord access token as soon as sign-in has read the user. A [card](../../GLOSSARY.md) must only open for an entity the viewer shares a guild with, so sign-in also asks for the `guilds` scope. The callback reads the viewer's guild list while the token is still valid, keeps the guilds the viewer and the bot are both in, and then revokes the token as before.

That set and the time it was read live in the web process's memory, keyed by session. They are not in the cookie or the database. A card request uses the set when it is under 15 minutes old. When it is missing or older (a restart, a session from before the `guilds` scope), the request redirects to Discord with `prompt=none` and returns to the card. Discord skips the consent screen for an app the viewer already approved. If that fails, the viewer goes through the normal sign-in and returns to the card. The return path goes through the existing redirect allow-list, which allows `/cards/`.

## Considered Options

- **Keep the access token and call Discord on each card request.** Rejected: the dashboard holds no token today, and storing one adds a secret to protect for a check that a short-lived guild set answers.
- **Store the set in the session cookie.** Rejected: a signed cookie is limited to about 4 KB, and a member in many shared guilds would exceed it.
- **Store memberships in the database.** Rejected for now: no table records which guilds a member is in, the privacy cog would have to delete those rows on a data-removal request, and a restart only costs one silent redirect per viewer. Revisit if the web app runs as several processes, since each would hold its own memory copy.

## Consequences

- Sessions from before the `guilds` scope keep working on every page that opens no card. Only cards ask them to sign in again.
- A restart makes every viewer's next card open one extra redirect.
