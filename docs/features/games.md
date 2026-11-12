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

## Teams

A lasting team is a group of members that exists apart from any tournament and may span guilds. You create one and become its captain, and anyone in it can leave. When the captain leaves, the longest-standing member takes over; when the last member leaves, the team is disbanded.

Surface: `/team create | show | leave | invite | kick | captain | disband | split`

An invite is a public message with a Join button that only the invitee can press. A member's data deletion takes them out of their teams with the same captain hand-over as leaving.

`/team split` picks members from a menu and posts random temporary teams, with a Keep button under each. Keep names the team and makes it lasting, with the presser as captain. A temporary team nobody keeps ends after `temporary_lifetime_hours` (24 by default).

`/voice split` splits the members of your voice channel into random teams and posts them in that channel's chat. Move on a team creates the team's voice channel on its first press and moves only the presser there. A team's channel is deleted once it is empty, and the team ends when it has no channel left. With `move:False` the post has only Keep buttons and no Move buttons.

**Status:** 🟡 New in `src/winter_dragon/cogs/team/` and `src/winter_dragon/cogs/voice.py`. Tournament entries follow in #429.

## Tournaments

Team tournaments with a single-elimination bracket. A guild can run several at once. A tournament isn't tied to a channel: `/tournament post` shows it in any channel (Manage Messages there), and every post is kept up to date as the tournament changes. The organiser (whoever opened it, or anyone who can manage the server) opens sign-up with a team size and one of two ways to form teams:

- **Solo:** players join alone (a Join button on the sign-up card, or `/tournament join`); starting the tournament shuffles them into teams of the team size, players left over joining the first teams, and the first player drawn into a team captains it. Each drawn team is a temporary team that ends when the tournament finishes or is cancelled.
- **Captains:** a captain enters one of their lasting teams with `/tournament enter`, then picks its players with `/tournament entry-add` and `/tournament entry-remove`, up to the team size. Players must be members of the server. A member can play for several entries of one tournament. A captain leaving the tournament withdraws their entry.

Starting draws the seeds and lays out every round. The bracket is padded to a power of two with byes for the top seeds, which win at once, so two byes never meet. Each match card walks through ready → bans → picks → live, and the organiser's buttons move it on, report the winner once it's live, or record a forfeit at any point. A team's captain bans and picks with commands during those phases, and the card lists them. Winners move on to their next match, and the final's winner is the champion.

Each match has a lineup: the players who play for each entry in that match. When a match becomes ready, it copies each entry's current players into its lineup. A captain changes an entry's lineup with `/tournament lineup-in` and `/tournament lineup-out`, for stand-ins or illness. `lineup-in` takes a server member, who doesn't need to be in the team. A change updates the entry's players and the lineup of its next match, while that match is ready or in its draft. A live or decided match keeps its lineup, so the change applies from the match after. Later matches copy the players as they are when they become ready.

A member in both lineups of a ready match is a clash. The match can't move on until the organiser, or a captain of either entry, drops the member from one side with the card's Drop clash button.

The organiser can open a vote for a match (e.g. which map), answered with buttons by that match's players only. Voting again changes your answer, and the organiser closes the vote to show the final tally.

Each match keeps an audit. A match records when it went live, when it was decided, and who decided it. Its events are the phase changes, draft choices, votes opened and closed, the reported winner, a forfeit, and a clash dropped, each with its actor and time. Lineup changes are logged with the entry, the member, in or out, who made the change, when, and the reason given (e.g. stand-in or illness). `/tournament log` shows a match's events and the lineup changes that applied to it. Only the organiser, guild admins and the captains of the match's two entries can see it. On a member's data deletion, their actions and places in this audit are anonymised, and the rows are kept.

Everything is stored, so a tournament survives a restart.

Surface: `/tournament create | post | join | leave | enter | entry-add | entry-remove | lineup-in | lineup-out | start | bracket | match | log | ban | pick | vote | cancel`. Commands take the tournament with autocomplete, and the match options autocomplete the undecided matches.

**Status:** ✅ Rebuilt in `src/winter_dragon/cogs/tournament/` (tables in `models.py`, bracket arithmetic in `bracket.py`, actions in `service.py`, messages in `cards.py`). The match phases replace `wd-cogs`' in-memory state machine and registry; voting, empty on `main`, is new. Linking the tournament store to an API service is still open.
**Source on `main`:** `src/winter_dragon/bot/extensions/tournament/`
