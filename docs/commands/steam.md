<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_command_docs.py -->

# /steam

Get notified about free and discounted Steam games.

Get a direct message when a Steam game goes free or on sale, or look through the sales on right now. You choose the smallest discount that is worth a message.

## Setup

Allow direct messages from server members, or the bot can't reach you.

## Commands

- [`/steam add`](#add): Get notified automatically about free steam games
- [`/steam percentage`](#percentage): Get notified of steam games on sale for the given percentage or higher
- [`/steam remove`](#remove): No longer get notified of free steam games
- [`/steam show`](#show): Get a list of steam games that are on sale for the given percentage or higher

## /steam add {#add}

Get notified automatically about free steam games.

It takes no options.

**Who can run it:** Anyone, in a server or in DMs.

!!! example "Example"
    You type `/steam add`.

    The bot answers with an embed; only you see it:

    > I will notify you of new steam games!
    > Use /steam show to view current sales.

## /steam percentage {#percentage}

Get notified of steam games on sale for the given percentage or higher.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `percent` | whole number | yes | The minimum percentage the discount has to be before getting notified (0 to 100) |

**Who can run it:** Anyone, in a server or in DMs.

!!! example "Example"
    You type `/steam percentage percent:50`.

    The bot answers with an embed; only you see it:

    > Changed your sale notification threshold to 50%.

## /steam remove {#remove}

No longer get notified of free steam games.

It takes no options.

**Who can run it:** Anyone, in a server or in DMs.

!!! example "Example"
    You type `/steam remove`.

    The bot answers with an embed; only you see it:

    > I will no longer notify you of new steam games.

## /steam show {#show}

Get a list of steam games that are on sale for the given percentage or higher.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `percent` | whole number | no | Show discounts of at least this percentage |

**Who can run it:** Anyone, in a server or in DMs.

!!! example "Example"
    You type `/steam show percent:75`.

    The bot answers with a card with buttons; everyone in the channel sees it:

    > A page of games on sale by 75% or more, with a price, the discount and a link for each, and buttons to page through them. Only you can use the buttons.
    > If nothing is that cheap: No steam games found with sales 75% or higher.
