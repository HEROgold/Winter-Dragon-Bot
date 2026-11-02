# Design: teams apart from tournaments (#353)

!!! warning "Not built yet"
    This page is the agreed plan from the #353 grilling session.
    Terms follow `GLOSSARY.md` (Team, Temporary team, Lasting team,
    Tournament entry, Lineup, Tournament post).

## What goes where

A Team is its own cog. The tournament cog and the voice split use it; nothing uses the tournament cog.
A tournament belongs to one guild, which can run several at once. It is tied to no channel. Teams belong to no guild.

```mermaid
flowchart LR
    subgraph bot["src/winter_dragon/cogs/"]
        team["team/<br/>Team, members, captain<br/>/team create, invite, leave,<br/>kick, captain, disband, show<br/>/team split (text)"]
        voice["voice/<br/>/voice split<br/>team channels, cleanup task"]
        tournament["tournament/<br/>Tournament, entries,<br/>matches, lineups, audit"]
    end
    profile["dashboard profile pages<br/>teams formed, tournaments played"]
    manage["dashboard management pages<br/>(parked, #417)"]

    voice --> team
    tournament --> team
    profile --> team
    profile --> tournament
    manage -.-> tournament
    manage -.-> team
```

## Data model

Tables and the links between them. Column names are indicative; the migration settles them.

```mermaid
erDiagram
    TEAM ||--o{ TEAM_MEMBER : has
    TEAM ||--o{ TEAM_VOICE_CHANNEL : "split into"
    TEAM ||--o{ TOURNAMENT_ENTRY : enters
    TOURNAMENT ||--o{ TOURNAMENT_ENTRY : has
    TOURNAMENT ||--o{ TOURNAMENT_SIGNUP : "solo signups"
    TOURNAMENT ||--o{ TOURNAMENT_POST : "posted in"
    TOURNAMENT ||--o{ MATCH : bracket
    TOURNAMENT_ENTRY ||--o{ ENTRY_PLAYER : "current lineup"
    MATCH ||--o{ MATCH_LINEUP : "who played"
    TOURNAMENT_ENTRY ||--o{ MATCH_LINEUP : "plays as"
    MATCH ||--o{ LINEUP_CHANGE : audit
    MATCH ||--o{ MATCH_EVENT : audit
    MATCH ||--o{ DRAFT_CHOICE : has
    MATCH ||--o{ MATCH_VOTE : has
    MATCH_VOTE ||--o{ MATCH_BALLOT : has

    TEAM {
        int id PK
        string name
        TeamKind kind "temporary or lasting"
        TeamOrigin origin "created, voice split, text split, solo tournament"
        bigint captain_id "nullable"
        datetime ended_at "temporary teams only"
    }
    TEAM_MEMBER {
        int team_id FK
        bigint user_id
        datetime joined_at "longest-standing takes over as captain"
    }
    TEAM_VOICE_CHANNEL {
        int team_id FK
        bigint guild_id
        bigint channel_id "deleted once empty"
    }
    TOURNAMENT {
        int id PK
        bigint guild_id "owner; several per guild"
        string name
        bigint organiser_id
        TeamMode mode "solo or captains"
        int team_size
        TournamentStatus status
        int winner_entry_id FK
    }
    TOURNAMENT_SIGNUP {
        int tournament_id FK
        bigint user_id "one signup per member"
    }
    TOURNAMENT_POST {
        int tournament_id FK
        bigint channel_id
        bigint message_id
    }
    TOURNAMENT_ENTRY {
        int id PK
        int tournament_id FK
        int team_id FK
        string name "unique within the tournament"
    }
    ENTRY_PLAYER {
        int entry_id FK
        bigint user_id "may be in other entries too"
    }
    MATCH {
        int id PK
        int tournament_id FK
        int round
        int slot
        int entry_a_id FK
        int entry_b_id FK
        MatchPhase phase
        int winner_entry_id FK
        datetime started_at
        datetime decided_at
        bigint decided_by
    }
    MATCH_LINEUP {
        int match_id FK
        int entry_id FK
        bigint user_id
    }
    LINEUP_CHANGE {
        int entry_id FK
        int match_id FK
        bigint user_id
        string change "in or out"
        bigint changed_by
        datetime changed_at
        string reason "optional: stand-in, illness"
    }
    MATCH_EVENT {
        int match_id FK
        string kind "phase, draft, vote, winner, forfeit"
        bigint actor_id
        datetime at
    }
    DRAFT_CHOICE {
        int match_id FK
        int entry_id FK
        DraftKind kind
        string value
    }
    MATCH_VOTE {
        int match_id FK
        string question
        string options
        bool open
    }
    MATCH_BALLOT {
        int vote_id FK
        bigint user_id
        int choice
    }
```

What changes compared to today's tables:

- `Tournament` keeps `guild_id` and loses `channel_id`. The one-active-tournament-per-guild rule goes. A tournament is found by name or id, not by channel.
- `TournamentTeam` becomes `TOURNAMENT_ENTRY` and points at a `TEAM`. The captain moves to the team.
- `TournamentPlayer` splits three ways. A solo signup becomes `TOURNAMENT_SIGNUP`. An entry's current players become `ENTRY_PLAYER`. Who played each match goes in `MATCH_LINEUP`.
- A member can be in several entries of one tournament, so `ENTRY_PLAYER` has no one-entry-per-member key.

## Team lifecycle

```mermaid
stateDiagram-v2
    [*] --> Temporary: /voice split, /team split,<br/>solo tournament starts
    [*] --> Lasting: /team create
    Temporary --> Lasting: a member presses Keep<br/>and names it
    Temporary --> Ended: voice channel empties,<br/>or one day passes (confkit),<br/>or its tournament ends
    Lasting --> Disbanded: /team disband
    Ended --> [*]
    Disbanded --> [*]

    note right of Ended
        Kept in the database, hidden from users.
        Brackets and match history still show it.
    end note
    note right of Lasting
        Only lasting teams count as teams formed.
    end note
```

Captain rules for a lasting team:

```mermaid
flowchart TD
    create["/team create"] --> cap["creator is captain"]
    cap -->|"/team captain @member"| other["another member is captain"]
    cap -->|captain leaves| oldest["longest-standing member is captain"]
    oldest -->|nobody left| gone["team disbanded"]
    keep["Keep button on a temporary team"] --> presser["the member who pressed is captain"]
```

A temporary team has no captain, except a solo tournament's, where the first player drawn captains it.

## Splitting into temporary teams

`/voice split` takes the caller's voice channel and posts the teams in that channel's chat. Each player presses Move to be moved, so nobody is moved without agreeing and the caller needs no Move Members permission. With `move=False` the post has no Move button. `/team split` takes members picked in a user select.

```mermaid
sequenceDiagram
    actor M as Member
    actor P as Player
    participant B as Bot
    participant D as Discord
    participant DB as Database

    M->>B: /voice split teams=2 move=True
    B->>DB: create temporary teams (origin voice split)
    B->>D: post the teams in the voice channel's chat,<br/>a Move button and a Keep button under each
    P->>B: press Move
    B->>D: create the team's voice channel next to the caller's,<br/>if it doesn't exist yet
    B->>DB: TEAM_VOICE_CHANNEL row
    B->>D: move the player who pressed
    Note over B,D: the voice cog's own asyncio task watches voice states
    D-->>B: VOICE_STATE_UPDATE, a team channel is empty
    B->>D: delete the channel
    B->>DB: end the team
    M->>B: press Keep on team 1
    B->>M: modal asking for a name
    M->>B: submit "Night Owls"
    B->>DB: team 1 becomes lasting, presser is captain
```

```mermaid
sequenceDiagram
    actor M as Member
    participant B as Bot
    participant DB as Database

    M->>B: /team split teams=3
    B->>M: user select, up to 25 members
    M->>B: pick members
    B->>DB: create temporary teams (origin text split)
    B->>M: post the teams, a Keep button under each
    Note over B,DB: a team nobody keeps ends after one day (confkit)
```

## Tournament and match flow

```mermaid
stateDiagram-v2
    [*] --> Signup: /tournament create
    Signup --> Running: organiser starts it<br/>(solo: draw temporary teams)
    Signup --> Cancelled
    Running --> Finished: final match decided
    Running --> Cancelled
    Finished --> [*]
    Cancelled --> [*]
```

A match copies its lineups from the entries when it becomes ready. A member who is in both lineups blocks the match until someone drops them from one side.

```mermaid
stateDiagram-v2
    [*] --> Waiting
    Waiting --> Ready: both entries known,<br/>lineups copied from ENTRY_PLAYER
    Ready --> Clash: a member is in both lineups
    Clash --> Ready: organiser or a captain<br/>drops them from one side
    Ready --> Ban
    Ban --> Pick
    Pick --> Live
    Live --> Finished: winner reported
    Ready --> Forfeit
    Ban --> Forfeit
    Pick --> Forfeit
    Live --> Forfeit
    Finished --> [*]
    Forfeit --> [*]
```

## Lineup changes carry forward

```mermaid
flowchart TD
    change["lineup change for an entry<br/>(stand-in, illness)"] --> current["update ENTRY_PLAYER"]
    current --> undecided{"entry's next match<br/>not live yet?"}
    undecided -->|yes| copy["replace that match's MATCH_LINEUP"]
    undecided -->|no, it is live| wait["applies from the match after"]
    change --> audit["LINEUP_CHANGE row:<br/>who, by whom, when, why"]
    copy --> later["later matches copy ENTRY_PLAYER<br/>when they become ready"]
    wait --> later
```

Decided matches keep their `MATCH_LINEUP` as it was, so match history shows who played.

## Migration

No tournaments run in production, so the migration can reshape the tables freely.

```mermaid
flowchart LR
    T[Tournament] -->|drop channel_id| T2[TOURNAMENT]
    TT[TournamentTeam] -->|one TEAM each:<br/>captains mode = lasting,<br/>solo mode = temporary, ended| TEAM
    TT -->|keep the id| E[TOURNAMENT_ENTRY]
    TP[TournamentPlayer] -->|no team yet| S[TOURNAMENT_SIGNUP]
    TP -->|in a team| EP[ENTRY_PLAYER]
    TP -->|in a team, per match the entry played| ML[MATCH_LINEUP]
    TP -->|in a team| TM[TEAM_MEMBER]
    M[TournamentMatch] -->|team ids are entry ids| M2[MATCH]
```

The **Auto-migrate** workflow generates the Alembic revision; the data moves are written by hand in it.

## Branches

```mermaid
flowchart BT
    main --> a["353-team-model<br/>TEAM, TEAM_MEMBER, /team commands"]
    a --> b["353-team-splits<br/>/voice split, /team split, Keep button,<br/>temporary team ending"]
    b --> c["353-tournament-entries<br/>standalone tournaments, entries,<br/>lineups, audit, migration"]
```

## Parked

```mermaid
flowchart LR
    i353["#353 this plan"]
    i415["#415 /voice lobby"]
    i416["#416 tournaments across guilds"]
    i417["#417 dashboard management pages"]
    i418["#418 /team channel with spectators"]
    i353 -.-> i415
    i353 -.-> i416
    i353 -.-> i417
    i353 -.-> i418
```

## Match audit

- Every match keeps its frozen `MATCH_LINEUP`, every `LINEUP_CHANGE`, and a `MATCH_EVENT` row for each phase change, draft choice, vote opened or closed, reported winner and forfeit, with who and when.
- The audit points at entries and match lineups, never at a team's current roster. An ended or kept temporary team still shows who played.
- Anyone who can see the tournament sees who played each match and the result. Only the organiser and the entries' captains see the change log.
- When a member's data is deleted, their user id in these rows becomes a deleted-player marker. The rows stay, so brackets and other players' history stay correct.

## Finding and showing a tournament

- Each `/tournament` subcommand takes a `tournament` option. Autocomplete lists the tournaments the member organises or signed up for, and open ones posted in the current channel.
- `/tournament post` puts the tournament's embed in a channel of the tournament's guild and records a `TOURNAMENT_POST`. The bot updates every post. A member needs Manage Messages in that channel.
- The organiser and the guild admins of the tournament's guild run it; a guild admin can do anything the organiser can.
- A lineup only holds members of the tournament's guild. The bot checks at signup and on every lineup change. Mixed-guild lineups wait for #416.
- Buttons on a post carry the tournament id. Anyone who can press signup on any post, or use `/tournament join`, can sign up. The organiser can close signups or remove an entry.
