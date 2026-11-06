# Dashboard layout

The dashboard is the FastAPI app in `src/winter_dragon/web/`, rendered with Jinja and htmx (see
[ADR 0002](../adr/0002-htmx-jinja-dashboard.md)). This page says where a feature's page goes.

## Where a feature page goes

Place a page by whose data it shows:

| The page shows | Route | Who sees it |
|---|---|---|
| Data the signed-in member owns, to read or to manage | `/profile/<slug>` | Only that member |
| Data of one guild, configured by its guild admin | `/guilds/<guild_id>/...` | Guild admins of that guild |
| Shared data anyone may browse | its own top-level route, such as `/teams` | Anyone |
| One Discord user, channel, role or guild | `/cards/<kind>/<id>` | A signed-in member who shares a guild with it |

Whether a page has forms doesn't change where it goes. A Profile page may show history, take actions, or both.

A Profile page registers itself with `profile_page` from `src/winter_dragon/web/profile.py`; extra routes go in its
`router`, mounted under the page's path. The `/guilds` section is reserved: no page lives there yet.

## Showing a Discord ID

A page never prints a Discord ID. A Profile page builder asks `context.references` for a `ReferenceLink` (see
`src/winter_dragon/web/references.py`) and puts it in the row it returns; the template renders it with the
`reference` macro from `templates/_references.html`. The link shows the entity's name and points to its card. When
Discord can't name the ID, it shows the plain ID and a short note instead. `test_web_teams_references.py` fails when
a template names an ID field or a page row holds a bare `Snowflake`.

Names come from `DiscordLookup` (`discord_lookup.py`), a REST-only bot client with a 5 minute cache. A card opens for
the guilds the member and the bot share; those are read at sign-in and kept in memory, not in the cookie or the
database ([ADR 0006](../adr/0006-dashboard-keeps-no-oauth-token.md)). A card with no current guilds sends the member
through `/auth/discord/login?next=<card>`, which asks Discord silently and returns to the card.

## Navigation

- The top nav lists sections: Profile, Your data, and later the shared and guild sections.
- A section's own pages appear in the second navbar, the `subnav` block of `base.html`, right under the site header.
  Pages outside a section leave it empty.
- `/profile` opens the Profile tab the member last opened, kept in the `profile_tab` cookie. Without one, or when that
  page no longer exists, it shows a short intro.

## Current pages

| Feature | Route | Why |
|---|---|---|
| Fuel, Hangman, Love, Steam, Urban Dictionary | `/profile/<slug>` | The member's own history |
| Incremental | `/profile/incremental` | The member's own save, which they play |
| Teams | `/profile/teams` | The lasting teams the member is on |
| Reminders | `/profile/reminders` | The member's own reminders, which they manage |
| All teams | `/teams` | Every lasting team; public |

Moving a page drops its old URLs without redirects: only the dashboard itself links to its routes.
