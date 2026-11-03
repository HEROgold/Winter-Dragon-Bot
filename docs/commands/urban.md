<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_command_docs.py -->

# /urban

Look up words on Urban Dictionary.

Looks a word up on Urban Dictionary, or picks random entries. Entries are written by Urban Dictionary's users, so they can be rude.

## Commands

- [`/urban random`](#random): Get random definitions from Urban Dictionary
- [`/urban search`](#search): Look up the meaning of a word on Urban Dictionary

## /urban random {#random}

Get random definitions from Urban Dictionary.

It takes no options.

**Who can run it:** Anyone, in a server or in DMs.

!!! example "Example"
    You type `/urban random`.

    The bot answers with an embed; everyone in the channel sees it:

    > **Urban Dictionary: random**
    > 1. word
    > The definition, then the thumbs up and thumbs down counts and a link to the entry. Up to the configured number of entries.
    > Results are from api.urbandictionary.com

## /urban search {#search}

Look up the meaning of a word on Urban Dictionary.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `query` | text | yes | query |

**Who can run it:** Anyone, in a server or in DMs.

!!! example "Example"
    You type `/urban search query:touch grass`.

    The bot answers with an embed; everyone in the channel sees it:

    > **Urban Dictionary: touch grass**
    > 1. touch grass
    > The definition, then the thumbs up and thumbs down counts and a link to the entry.
    > Results are from api.urbandictionary.com
    > (With no results: No definitions found for `touch grass`.)
