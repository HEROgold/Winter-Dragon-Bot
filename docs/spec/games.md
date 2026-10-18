# Games

Things members play together in a guild.

## Tournaments

A guild runs one team tournament at a time, in the channel it was opened in: sign-up, a single-elimination bracket, and per match a draft and votes.

- **Who:** the **tournament organiser** opens, starts, runs and cancels it; members sign up; team captains draft.
- **Commands:** `/tournament create`, `join`, `leave`, `team-create`, `team-add`, `team-remove`, `start`, `bracket`, `cancel`, `match`, `ban`, `pick`, `vote`.
- **Stores:** the tournament, its teams and players, its matches, their draft choices, votes and ballots.
- **Rules:**
  - Teams are formed one of two ways: players sign up alone and are shuffled into teams at the start, or captains register teams and add their players.
  - A match moves from waiting for its teams, through the draft, to live and decided; a forfeit decides it too.
  - A vote offers 2 to 10 answers.
- **Settings:** `TournamentSettings`: `max_name_length` (100), `max_team_size` (25).
- **Dashboard:** the Tournaments page: a public bracket that refreshes itself, the teams, and for the organiser the controls of the live match (report a winner, record a forfeit).
- **Status:** Live, [tournament/](../../src/winter_dragon/cogs/tournament/__init__.py).

## Game registry and looking for group

A shared catalogue of games that members match up in.

- **Who:** members.
- **Commands:** `/games list`, `/games suggest`; `/lfg join` (queue for a game), `/lfg leave` (leave every queue).
- **Stores:** the games; suggestions; who is queued for which game.
- **Rules:** members waiting for the same game are matched with each other; other features refer to games in the registry, not free text.
- **Status:** Port.

## Hangman

Multiplayer hangman in a channel, guessed through buttons and a modal.

- **Who:** members.
- **Stores:** each member's games played, for their stats.
- **Status:** Port.

## Question games

Party games that draw from a shared pool of questions, such as Never Have I Ever. Members draw a question, and contribute new ones.

- **Who:** members.
- **Stores:** the question pools and who contributed each question.
- **Status:** Port.

## Love meter

- **Commands:** `/love`: a playful compatibility score between two members, the same for the same pair every time.
- **Status:** Live, [percentage.py](../../src/winter_dragon/cogs/percentage.py).

## League of Legends

A member links their Riot account once (a **linked account**), and League features use it in every guild.

- **Who:** members.
- **Stores:** each member's linked accounts.
- **Dashboard:** Your data lists and unlinks them.
- **Status:** Port. It is the base of [Ranked tracking](ranked-tracking.md).

## Clash

Tooling around Riot's Clash tournaments.

- **Status:** Port, redesigned later, after Ranked tracking. The Riot Clash API client is already in `wd-cogs`.

## Dropped

- **Incremental game** (`main`).
