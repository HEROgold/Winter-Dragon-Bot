<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_command_docs.py -->

# /bot-commands

Inspect and manage the bot's application commands.

Shows which of the bot's commands Discord knows about, and pushes the bot's current commands to Discord when they differ.

## Commands

- [`/bot-commands list`](#list): List registered commands and their sync status
- [`/bot-commands resync`](#resync): Re-read the commands from Discord and push any differences

## /bot-commands list {#list}

List registered commands and their sync status.

It takes no options.

**Who can run it:** Members with Manage Server, in a server.

!!! example "Example"
    You type `/bot-commands list`.

    The bot answers with an embed; everyone in the channel sees it:

    > **Registered commands**
    > One line per command, saying whether it is synced with Discord or still pending.

## /bot-commands resync {#resync}

Re-read the commands from Discord and push any differences.

It takes no options.

**Who can run it:** The bot's owners, in a server.

!!! example "Example"
    You type `/bot-commands resync`.

    The bot answers with a message; everyone in the channel sees it:

    > Resyncing commands…
    > Resync finished.
