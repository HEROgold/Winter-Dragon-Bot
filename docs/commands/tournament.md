<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_command_docs.py -->

# /tournament

Run a team tournament: sign-up, a bracket, drafts and votes.

Run a tournament in a channel. The sign-up card shows who has signed up and how the tournament stands, and the bot keeps it up to date. Sign-up is either solo, where the bot draws teams of the chosen size, or by captains who enter whole teams. Starting it draws a bracket, and each match gets a card for its drafts (bans and picks), votes, lineups and result.

## Setup

Whoever runs `/tournament create` needs the Manage Server permission and organises the tournament. The bot needs permission to send messages and attach files in the channel where the card is posted.

## Commands

- [`/tournament ban`](#ban): Ban something from your match, as your team's captain
- [`/tournament bracket`](#bracket): Show a tournament's bracket
- [`/tournament cancel`](#cancel): Call off a tournament
- [`/tournament create`](#create): Open sign-up for a tournament, shown in this channel
- [`/tournament enter`](#enter): Enter one of your teams into a tournament, as its captain
- [`/tournament entry-add`](#entry-add): Add a server member to the entry you captain
- [`/tournament entry-remove`](#entry-remove): Remove a player from the entry you captain
- [`/tournament join`](#join): Sign up for a tournament
- [`/tournament leave`](#leave): Withdraw from a tournament before it starts
- [`/tournament lineup-in`](#lineup-in): Put a server member in your entry's lineup, from its next match not yet live
- [`/tournament lineup-out`](#lineup-out): Take a player out of your entry's lineup, from its next match not yet live
- [`/tournament log`](#log): Show what happened in a match: its phases, drafts, votes, lineups and result
- [`/tournament match`](#match): Show a match's card; its organiser manages the match from it
- [`/tournament pick`](#pick): Pick something for your match, as your team's captain
- [`/tournament post`](#post): Show a tournament in this channel, and keep the post up to date
- [`/tournament start`](#start): Close sign-up, form the teams and draw the bracket
- [`/tournament vote`](#vote): Let a match's players vote, e.g. on a map; answers separated by commas

## /tournament ban {#ban}

Ban something from your match, as your team's captain.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `match` | text | yes | The match to ban in |
| `choice` | text | yes | The item to ban |

**Who can run it:** The captain of a team in the match, in a server.

!!! example "Example"
    You type `/tournament ban match:#3 Red vs Blue choice:Mirage`.

    The bot answers with an embed; only you see it:

    > Your team banned **Mirage** in match #3.

## /tournament bracket {#bracket}

Show a tournament's bracket.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `tournament` | text | yes | The tournament |

**Who can run it:** Anyone in a server.

!!! example "Example"
    You type `/tournament bracket tournament:Spring cup`.

    The bot answers with a card with buttons; everyone in the channel sees it:

    > The tournament's card with the bracket drawn as an image: the matches and who won.

## /tournament cancel {#cancel}

Call off a tournament.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `tournament` | text | yes | The tournament |

**Who can run it:** The tournament's organiser, in a server.

!!! example "Example"
    You type `/tournament cancel tournament:Spring cup`.

    The bot answers with an embed; everyone in the channel sees it:

    > **Spring cup** is called off.

## /tournament create {#create}

Open sign-up for a tournament, shown in this channel.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `name` | text | yes | The name of the tournament (1 to 100 characters) |
| `team_size` | whole number | no | The size of each team (1 to 25) |
| `captains` | yes or no | no | Allow team captains to register entire teams |

**Who can run it:** Members with Manage Server, in a server.

!!! example "Example"
    You type `/tournament create name:Spring cup team_size:5`.

    The bot answers with an embed; only you see it:

    > **Spring cup** is open for sign-up.
    > (The sign-up card is posted in the channel for everyone.)

## /tournament enter {#enter}

Enter one of your teams into a tournament, as its captain.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `tournament` | text | yes | The tournament |
| `team` | text | yes | Your team to enter |

**Who can run it:** The captain of the team, in a server.

!!! example "Example"
    You type `/tournament enter tournament:Spring cup team:Red`.

    The bot answers with an embed; only you see it:

    > Your team **Red** is entered; add players with /tournament entry-add.

## /tournament entry-add {#entry-add}

Add a server member to the entry you captain.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `tournament` | text | yes | The tournament |
| `player` | member | yes | The player to add to your entry |

**Who can run it:** The captain of the entry, in a server.

!!! example "Example"
    You type `/tournament entry-add tournament:Spring cup player:@Sam`.

    The bot answers with an embed; only you see it:

    > Added @Sam to your entry.

## /tournament entry-remove {#entry-remove}

Remove a player from the entry you captain.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `tournament` | text | yes | The tournament |
| `player` | member | yes | The player to remove from your entry |

**Who can run it:** The captain of the entry, in a server.

!!! example "Example"
    You type `/tournament entry-remove tournament:Spring cup player:@Sam`.

    The bot answers with an embed; only you see it:

    > Removed @Sam from your entry.

## /tournament join {#join}

Sign up for a tournament.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `tournament` | text | yes | The tournament |

**Who can run it:** Anyone in a server.

!!! example "Example"
    You type `/tournament join tournament:Spring cup`.

    The bot answers with an embed; only you see it:

    > You're signed up!

## /tournament leave {#leave}

Withdraw from a tournament before it starts.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `tournament` | text | yes | The tournament |

**Who can run it:** Anyone in a server.

!!! example "Example"
    You type `/tournament leave tournament:Spring cup`.

    The bot answers with an embed; only you see it:

    > You've left the tournament.

## /tournament lineup-in {#lineup-in}

Put a server member in your entry's lineup, from its next match not yet live.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `tournament` | text | yes | The tournament |
| `player` | member | yes | The member to put in your lineup |
| `reason` | text | no | Why, e.g. stand-in or illness (1 to 100 characters) |

**Who can run it:** The captain of the entry, in a server.

!!! example "Example"
    You type `/tournament lineup-in tournament:Spring cup player:@Sam reason:Stand-in`.

    The bot answers with an embed; only you see it:

    > Put @Sam in your lineup.

## /tournament lineup-out {#lineup-out}

Take a player out of your entry's lineup, from its next match not yet live.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `tournament` | text | yes | The tournament |
| `player` | member | yes | The player to take out of your lineup |
| `reason` | text | no | Why, e.g. stand-in or illness (1 to 100 characters) |

**Who can run it:** The captain of the entry, in a server.

!!! example "Example"
    You type `/tournament lineup-out tournament:Spring cup player:@Sam reason:Illness`.

    The bot answers with an embed; only you see it:

    > Took @Sam out of your lineup.

## /tournament log {#log}

Show what happened in a match: its phases, drafts, votes, lineups and result.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `tournament` | text | yes | The tournament |
| `match` | text | yes | The match to show the log of |

**Who can run it:** The organiser, or a captain of the match's two entries, in a server.

!!! example "Example"
    You type `/tournament log tournament:Spring cup match:#3 Red vs Blue`.

    The bot answers with an embed; only you see it:

    > **Log: #3 Red vs Blue**
    > One line per phase, draft, vote, lineup change and the result. A match with no history says: Nothing has been logged yet.

## /tournament match {#match}

Show a match's card; its organiser manages the match from it.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `match` | text | yes | The match to show |

**Who can run it:** Anyone in a server.

!!! example "Example"
    You type `/tournament match match:#3 Red vs Blue`.

    The bot answers with a card with buttons; everyone in the channel sees it:

    > The match's card: its teams, phase and result. The organiser manages the match with the card's buttons.

## /tournament pick {#pick}

Pick something for your match, as your team's captain.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `match` | text | yes | The match to pick in |
| `choice` | text | yes | The item to pick |

**Who can run it:** The captain of a team in the match, in a server.

!!! example "Example"
    You type `/tournament pick match:#3 Red vs Blue choice:Inferno`.

    The bot answers with an embed; only you see it:

    > Your team picked **Inferno** in match #3.

## /tournament post {#post}

Show a tournament in this channel, and keep the post up to date.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `tournament` | text | yes | The tournament to show here |

**Who can run it:** Members with Manage Messages, in a server.

!!! example "Example"
    You type `/tournament post tournament:Spring cup`.

    The bot answers with an embed; only you see it:

    > Posted **Spring cup** here.
    > (The tournament's card is posted in the channel for everyone, and the bot edits it as the tournament goes on.)

## /tournament start {#start}

Close sign-up, form the teams and draw the bracket.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `tournament` | text | yes | The tournament |

**Who can run it:** The tournament's organiser, in a server.

!!! example "Example"
    You type `/tournament start tournament:Spring cup`.

    The bot answers with a card with buttons; everyone in the channel sees it:

    > Sign-up is closed, the teams are formed and the bracket is drawn. The bot posts the tournament's card with the bracket as an image.

## /tournament vote {#vote}

Let a match's players vote, e.g. on a map; answers separated by commas.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `match` | text | yes | The match to vote in |
| `question` | text | yes | The question to vote on (up to 200 characters) |
| `answers` | text | yes | The answers to the question, separated by commas |

**Who can run it:** The tournament's organiser, in a server.

!!! example "Example"
    You type `/tournament vote match:#3 Red vs Blue question:Which map? answers:Mirage, Inferno, Nuke`.

    The bot answers with a card with buttons; everyone in the channel sees it:

    > A vote card for the match's players, with one button per answer and a button for the organiser to close the vote.
