<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_command_docs.py -->

# /autochannel

Voice channels of your own, made by joining the hub channel.

Members join one hub voice channel and the bot makes a voice channel for them, which they then own. They can rename it and set its user limit. The bot removes the channel when it is empty.

## Setup

Run `/autochannel setup` to create a category with a hub channel, or `/autochannel mark` to use a voice channel you already have. The bot needs the Manage Channels and Move Members permissions.

## Commands

- [`/autochannel guild-limit`](#guild-limit): Set how many automatic channels this server allows at once
- [`/autochannel limit`](#limit): Set how many users fit in your channel
- [`/autochannel mark`](#mark): Make a voice channel the hub members join to get their own
- [`/autochannel name`](#name): Set the name of your channel
- [`/autochannel setup`](#setup): Create a category with a hub channel members join to get their own

## /autochannel guild-limit {#guild-limit}

Set how many automatic channels this server allows at once.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `limit` | whole number | yes | The maximum number of automatic channels this server allows at once, 0 for no limit (at least 0) |

**Who can run it:** Members with Manage Server, in a server.

!!! example "Example"
    You type `/autochannel guild-limit limit:10`.

    The bot answers with an embed; only you see it:

    > This server now allows 10 automatic channels.

## /autochannel limit {#limit}

Set how many users fit in your channel.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `limit` | whole number | yes | The maximum number of users that can be in your channel, 0 for no limit (0 to 99) |

**Who can run it:** Anyone in a server.

!!! example "Example"
    You type `/autochannel limit limit:4`.

    The bot answers with an embed; only you see it:

    > Saved and applied to #Your channel.
    > (Before you have a channel: Saved; your next channel gets it.)

## /autochannel mark {#mark}

Make a voice channel the hub members join to get their own.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `channel` | channel | yes | channel |

**Who can run it:** Members with Manage Server, in a server.

!!! example "Example"
    You type `/autochannel mark channel:#Join to create`.

    The bot answers with an embed; only you see it:

    > Joining #Join to create now gives members their own channel.

## /autochannel name {#name}

Set the name of your channel.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `name` | text | yes | The new name for your channel (1 to 100 characters) |

**Who can run it:** Anyone in a server.

!!! example "Example"
    You type `/autochannel name name:Movie night`.

    The bot answers with an embed; only you see it:

    > Saved and applied to #Movie night.
    > (Before you have a channel: Saved; your next channel gets it.)

## /autochannel setup {#setup}

Create a category with a hub channel members join to get their own.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `category_name` | text | yes | The name of the category to create (1 to 100 characters) |
| `hub_name` | text | yes | The name of the hub channel to create (1 to 100 characters) |

**Who can run it:** Members with Manage Server, in a server.

!!! example "Example"
    You type `/autochannel setup category_name:Hangout hub_name:Join to create`.

    The bot answers with an embed; only you see it:

    > All set: joining #Join to create gives members their own channel.
