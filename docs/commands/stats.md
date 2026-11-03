<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_command_docs.py -->

# /stats

Show this server's member counts.

Shows member counts for the server, and keeps a category of voice channels whose names show them (users, bots, online and the peak), so everyone can see the numbers at a glance.

## Setup

`/stats add` creates the category and its channels. The bot needs the Manage Channels permission.

## Commands

- [`/stats add`](#add): Add a category of channels showing this server's member counts
- [`/stats remove`](#remove): Remove the stats category and its channels
- [`/stats reset`](#reset): Recreate the stats channels of every server (bot owners only)
- [`/stats show`](#show): Show this server's member counts

## /stats add {#add}

Add a category of channels showing this server's member counts.

It takes no options.

**Who can run it:** Members with Manage Channels, in a server.

!!! example "Example"
    You type `/stats add`.

    The bot answers with an embed; only you see it:

    > Stats channels are set up.

## /stats remove {#remove}

Remove the stats category and its channels.

It takes no options.

**Who can run it:** Members with Manage Channels, in a server.

!!! example "Example"
    You type `/stats remove`.

    The bot answers with an embed; only you see it:

    > Removed the stats channels.

## /stats reset {#reset}

Recreate the stats channels of every server (bot owners only).

It takes no options.

**Who can run it:** The bot's owners, in a server.

!!! example "Example"
    You type `/stats reset`.

    The bot answers with an embed; only you see it:

    > Reset the stats channels of 12 servers.

## /stats show {#show}

Show this server's member counts.

It takes no options.

**Who can run it:** Anyone in a server.

!!! example "Example"
    You type `/stats show`.

    The bot answers with an embed; everyone in the channel sees it:

    > **My Server Stats**
    > Information about My Server
    > Users: 128 · Bots: 6 · Online: 41
    > Created on: Monday 1 January 2024 (2 years ago)
    > AFK channel: #AFK
