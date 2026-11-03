<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_command_docs.py -->

# /team

Teams of members that outlast any one tournament.

Teams are saved groups of members with a captain. The captain invites and removes members; other members can leave. `/team split` draws temporary teams from a list of members, and each can be kept with a button.

## Commands

- [`/team captain`](#captain): Hand a team's captaincy to a member
- [`/team create`](#create): Create a team, with you as its captain
- [`/team disband`](#disband): Disband a team you captain
- [`/team invite`](#invite): Invite a member to a team you captain
- [`/team kick`](#kick): Take a member out of a team you captain
- [`/team leave`](#leave): Leave a team
- [`/team show`](#show): Show a team's captain and members
- [`/team split`](#split): Split members into random temporary teams

## /team captain {#captain}

Hand a team's captaincy to a member.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `team` | text | yes | The team to hand over |
| `member` | member | yes | The member to make captain |

**Who can run it:** The captain of the team, in a server.

!!! example "Example"
    You type `/team captain team:Red member:@Sam`.

    The bot answers with an embed; only you see it:

    > @Sam is now captain of **Red**.

## /team create {#create}

Create a team, with you as its captain.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `name` | text | yes | The team's name (1 to 100 characters) |

**Who can run it:** Anyone in a server.

!!! example "Example"
    You type `/team create name:Red`.

    The bot answers with an embed; only you see it:

    > Created **Red**; you're its captain.

## /team disband {#disband}

Disband a team you captain.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `team` | text | yes | The team to disband |

**Who can run it:** The captain of the team, in a server.

!!! example "Example"
    You type `/team disband team:Red`.

    The bot answers with an embed; only you see it:

    > Disbanded **Red**.

## /team invite {#invite}

Invite a member to a team you captain.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `team` | text | yes | The team to invite to |
| `member` | member | yes | The member to invite |

**Who can run it:** The captain of the team, in a server.

!!! example "Example"
    You type `/team invite team:Red member:@Sam`.

    The bot answers with an embed; everyone in the channel sees it:

    > @Sam, @You invites you to **Red**. (with a button only @Sam can use to join)

## /team kick {#kick}

Take a member out of a team you captain.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `team` | text | yes | The team to remove the member from |
| `member` | member | yes | The member to remove |

**Who can run it:** The captain of the team, in a server.

!!! example "Example"
    You type `/team kick team:Red member:@Sam`.

    The bot answers with an embed; only you see it:

    > Removed @Sam from **Red**.

## /team leave {#leave}

Leave a team.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `team` | text | yes | The team to leave |

**Who can run it:** Anyone in a server.

!!! example "Example"
    You type `/team leave team:Red`.

    The bot answers with an embed; only you see it:

    > You left **Red**.

## /team show {#show}

Show a team's captain and members.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `team` | text | yes | The team to show |

**Who can run it:** Anyone in a server.

!!! example "Example"
    You type `/team show team:Red`.

    The bot answers with an embed; everyone in the channel sees it:

    > **Red**
    > Captain: @You
    > Members (3): @You @Sam @Alex

## /team split {#split}

Split members into random temporary teams.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `teams` | whole number | no | How many teams to split into (2 to 10) |

**Who can run it:** Anyone in a server.

!!! example "Example"
    You type `/team split teams:2`.

    The bot answers with a message; only you see it:

    > Pick the members to split into 2 teams.
    > (With a member picker. After you pick, the bot posts the teams for everyone, each with a Keep button.)
