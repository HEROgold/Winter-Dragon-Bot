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

An in-progress tournament system, modelled as a state machine over match phases — pre-match, team forming, ban phase, champion select, in progress, post-match, forfeit — with transitions driven by explicit events. Match information (teams, players, intended picks) hangs off that state.

!!! note "Incomplete on `main`"
    The state machine and match data model exist; `extensions/tournament/voting.py` is an empty file, and there are no tournament commands. Matchmaking tables (matches, teams, player stats, synergy, team compositions) exist in the database on `main` but are not driven by a cog.

**Status:** ✅ Ported for the state machine and store (`wd-cogs/src/wd_cogs/tournament/status.py`, `store.py`, `controller.py` — the latter two are new on `v2`, with no `main` counterpart). 🟡 for match information.
**Source on `main`:** `src/winter_dragon/bot/extensions/tournament/`
