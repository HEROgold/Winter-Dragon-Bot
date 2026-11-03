<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_command_docs.py -->

# /channel-utils

Manage channels.

Small tools for managing channels without opening the channel settings.

## Setup

The bot needs the View Channels and Manage Channels permissions on the channels it changes.

## Commands

- [`/channel-utils delete-category`](#delete-category): Delete a category and every channel inside it
- [`/channel-utils lock`](#lock): Stop a role or member from sending messages in this channel
- [`/channel-utils unlock`](#unlock): Let a role or member send messages in this channel again

## /channel-utils delete-category {#delete-category}

Delete a category and every channel inside it.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `category` | channel | yes | category |

**Who can run it:** Members with Manage Channels, in a server.

!!! example "Example"
    You type `/channel-utils delete-category category:Old event`.

    The bot answers with an embed; only you see it:

    > Deleted the category Old event and its channels.

## /channel-utils lock {#lock}

Stop a role or member from sending messages in this channel.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `target` | member or role | yes | The role or member to lock |

**Who can run it:** Members with Manage Channels, in a server.

!!! example "Example"
    You type `/channel-utils lock target:@Newcomers`.

    The bot answers with an embed; only you see it:

    > Locked this channel for @Newcomers.

## /channel-utils unlock {#unlock}

Let a role or member send messages in this channel again.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `target` | member or role | yes | The role or member to unlock |

**Who can run it:** Members with Manage Channels, in a server.

!!! example "Example"
    You type `/channel-utils unlock target:@Newcomers`.

    The bot answers with an embed; only you see it:

    > Unlocked this channel for @Newcomers.
