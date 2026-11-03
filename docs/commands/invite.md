<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_command_docs.py -->

# /invite

Invite the bot to your guild, or join its support guild.

Gives out the invite links for the bot and for its support server.

## Commands

- [`/invite bot`](#bot): Invite this bot to your own guild!
- [`/invite guild`](#guild): Get invited to the official support guild

## /invite bot {#bot}

Invite this bot to your own guild!.

It takes no options.

**Who can run it:** Anyone, in a server or in DMs.

!!! example "Example"
    You type `/invite bot`.

    The bot answers with a message; only you see it:

    > https://discord.com/oauth2/authorize?client_id=…&scope=bot+applications.commands

## /invite guild {#guild}

Get invited to the official support guild.

It takes no options.

**Who can run it:** Anyone, in a server or in DMs.

!!! example "Example"
    You type `/invite guild`.

    The bot answers with a message; only you see it:

    > https://discord.gg/… (a single-use invite that expires after a minute)
