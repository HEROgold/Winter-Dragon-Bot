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

Whether a page has forms doesn't change where it goes. A Profile page may show history, take actions, or both.

A Profile page registers itself with `profile_page` from `src/winter_dragon/web/profile.py`; extra routes go in its
`router`, mounted under the page's path. The `/guilds` section is reserved: no page lives there yet.

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
