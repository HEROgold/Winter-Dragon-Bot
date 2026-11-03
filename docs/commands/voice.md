<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_command_docs.py -->

# /voice

Voice channel tools: split everyone in your channel into teams.

Tools for the voice channel you are in. `/voice split` draws random teams from everyone in your channel.

## Setup

With `move` on (the default), each team gets a Move button that moves its members to the team's voice channel. The bot needs the Move Members permission.

## Commands

- [`/voice split`](#split): Split everyone in your voice channel into random teams

## /voice split {#split}

Split everyone in your voice channel into random teams.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `teams` | whole number | no | How many teams to split into (2 to 10) |
| `move` | yes or no | no | Give each team a voice channel to move to |

**Who can run it:** Anyone in a server.

!!! example "Example"
    You type `/voice split teams:2`.

    The bot answers with a message; only you see it:

    > Posted the teams in #General.
    > (The teams are posted for everyone in the voice channel's chat, each with a Keep button and, if `move` is on, a Move button.)
