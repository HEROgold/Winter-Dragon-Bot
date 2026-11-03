<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_command_docs.py -->

# /autoreassign

Give members who leave and rejoin the roles they had.

When a member leaves the server and comes back, the bot gives them the roles they had when they left. A role the bot can't give, because it sits above the bot's highest role, is skipped.

## Setup

The bot needs the Manage Roles permission, and its own role must sit above the roles it should give back.

## Commands

- [`/autoreassign disable`](#disable): Stop giving rejoining members their roles back
- [`/autoreassign enable`](#enable): Give members who leave and rejoin the roles they had

## /autoreassign disable {#disable}

Stop giving rejoining members their roles back.

It takes no options.

**Who can run it:** Members with Manage Roles, in a server.

!!! example "Example"
    You type `/autoreassign disable`.

    The bot answers with an embed; only you see it:

    > Rejoining members no longer get their roles back.

## /autoreassign enable {#enable}

Give members who leave and rejoin the roles they had.

It takes no options.

**Who can run it:** Members with Manage Roles, in a server.

!!! example "Example"
    You type `/autoreassign enable`.

    The bot answers with an embed; only you see it:

    > Members who leave and rejoin now get their roles back; my role must be above the roles to give.
    > These roles are above my highest role, so I can't give them back: @Admin. Move my role above them.
    > (The second sentence appears only when some roles are out of reach.)
