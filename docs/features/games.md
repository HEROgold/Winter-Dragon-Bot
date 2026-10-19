# Games

Entertainment and community features, plus the League of Legends integration — the largest third-party surface the bot has.

Audience: server members.

---

## Game registry

A shared catalogue of known games (`/games list`) that members can extend by suggesting additions (`/games suggest`). Other features — matchmaking, looking-for-group — reference this catalogue rather than free-text game names.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/games/games.py`

## Hangman

Multiplayer hangman played in-channel through buttons and a guess modal, with words fetched from an external word source and per-user participation tracked in the database.

**Status:** 🟡 Copied, unwired — depends on the missing UI toolkit and hangman tables.
**Source on `main`:** `src/winter_dragon/bot/extensions/games/hangman.py`

## Incremental game

A persistent idle/incremental game. Players buy generators that produce currency over time and check their progress; generators are bought through a shop menu rather than by typing IDs.

It also carries an admin surface for tuning the game economy live — defining and updating generators, listing them, granting currency to a user, and setting generation rates — so balance changes do not require a deploy.

Surface: `/incremental buy | progress`, plus `admin generator-*`, `currency add`, `rate add` subgroups.

**Status:** 🟡 Copied, unwired — depends on the missing UI toolkit and the incremental tables (player, currency, generators, rates).
**Source on `main`:** `src/winter_dragon/bot/extensions/games/incremental.py`, `games/incremental_ui.py`

## Looking for group

Per-game matchmaking queues. Members join the queue for a game (`/lfg join`) and are matched with others waiting for the same one; leaving drops them from every queue at once.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/games/looking_for_group.py`

## Question games

A shared base for questionnaire-style party games: a pool of questions stored in the database, a command to draw one, and commands to contribute new questions to the pool. Two games are built on it — **Never Have I Ever** and **Would You Rather** — and a third would be a subclass, not a new implementation.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/games/questions/`

## Love meter

A novelty command (`/love`) that scores compatibility between two members.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/games/love_meter.py`

---

## League of Legends

Account linking plus read-only Riot data, so a member's Discord identity maps to their League account once and every other command uses it.

- **Linking** (`/lol link`, `/lol unlink`) — associate a Riot account with the Discord user.
- **Profile** (`/lol profile`) — rank and summoner information, for yourself or another member.
- **Match history** (`/lol match-history`) — recent games.
- **Champion mastery** (`/lol champion-mastery`) — mastery standing per champion.

**Status:** 🟡 Copied, unwired.
**Source on `main`:** `src/winter_dragon/bot/extensions/games/league_of_legends.py`

!!! note "Stray file on `main`"
    `extensions/games/league_of_legends.py.tmp` is an accidental duplicate committed to `main`. Ignore it; do not port it.

## Clash

Tooling around Riot's Clash tournament mode, built on a dedicated Riot Clash API client:

- **Schedule** — upcoming Clash tournaments for a platform region.
- **Team analysis** — evaluates a Clash team's composition.
- **Champion suggestions** — recommends picks in the context of that composition.
- **Stats** — a member's Clash record.

Requires a Riot API key, supplied through configuration.

**Status:** ✅ Ported for the API client (`wd-cogs/src/wd_cogs/games/riot_clash_api.py` — self-contained, no `winter_dragon.*` imports). 🟡 for the Clash cog and its settings.
**Source on `main`:** `src/winter_dragon/bot/extensions/games/lol_clash.py`, `games/riot_clash_api.py`, `games/clash_settings.py`

---

## Tournaments

Team tournaments with a single-elimination bracket; a guild runs one at a time, in the channel it was opened in. The organiser (whoever opened it, or anyone who can manage the server) opens sign-up with a team size and one of two ways to form teams:

- **Solo:** players join alone (a Join button on the sign-up card, or `/tournament join`); starting the tournament shuffles them into teams of the team size, players left over joining the first teams, and the first player drawn into a team captains it.
- **Captains:** a captain registers a team and adds or removes its players, up to the team size. A captain leaving disbands their team.

Starting draws the seeds and lays out every round. The bracket is padded to a power of two with byes for the top seeds, which win at once, so two byes never meet. Each match card walks through ready → bans → picks → live, and the organiser's buttons move it on, report the winner once it's live, or record a forfeit at any point. A team's captain bans and picks with commands during those phases, and the card lists them. Winners move on to their next match, and the final's winner is the champion.

The organiser can open a vote for a match (e.g. which map), answered with buttons by that match's players only. Voting again changes your answer, and the organiser closes the vote to show the final tally.

Everything is stored, so a tournament survives a restart.

Surface: `/tournament create | join | leave | team-create | team-add | team-remove | start | bracket | match | ban | pick | vote | cancel`; the match options autocomplete the undecided matches.

**Status:** ✅ Rebuilt in `src/winter_dragon/cogs/tournament/` (tables in `models.py`, bracket arithmetic in `bracket.py`, actions in `service.py`, messages in `cards.py`). The match phases replace `wd-cogs`' in-memory state machine and registry; voting, empty on `main`, is new. Linking the tournament store to an API service is still open (HER-355).
**Source on `main`:** `src/winter_dragon/bot/extensions/tournament/`
