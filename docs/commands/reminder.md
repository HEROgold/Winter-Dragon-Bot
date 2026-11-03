<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_command_docs.py -->

# /reminder

Set reminders for yourself.

Set a reminder for yourself. The bot sends it to you as a direct message when it is due, so you need to allow direct messages from server members.

## Commands

- [`/reminder add`](#add): Get reminded of something once, after the given time
- [`/reminder remove`](#remove): Cancel one of your reminders
- [`/reminder repeat`](#repeat): Get reminded of something over and over, every given time

## /reminder add {#add}

Get reminded of something once, after the given time.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `reminder` | text | yes | The text to remind you of (up to 1000 characters) |
| `minutes` | whole number | no | The number of minutes to wait before reminding you |
| `hours` | whole number | no | The number of hours to wait before reminding you |
| `days` | whole number | no | The number of days to wait before reminding you |

**Who can run it:** Anyone, in a server or in DMs.

!!! example "Example"
    You type `/reminder add reminder:Call mum hours:2`.

    The bot answers with an embed; only you see it:

    > On Wednesday 4 November 2026 14:00 (in 2 hours) I will remind you of
    > `Call mum`
    > Use /reminder remove to cancel it.

## /reminder remove {#remove}

Cancel one of your reminders.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `reminder` | text | yes | The reminder to remove |

**Who can run it:** Anyone, in a server or in DMs.

!!! example "Example"
    You type `/reminder remove reminder:Call mum`.

    The bot answers with an embed; only you see it:

    > Removed your reminder of
    > `Call mum`

## /reminder repeat {#repeat}

Get reminded of something over and over, every given time.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `reminder` | text | yes | The text to remind you of (up to 1000 characters) |
| `minutes` | whole number | no | The number of minutes before reminding you again |
| `hours` | whole number | no | The number of hours before reminding you again |
| `days` | whole number | no | The number of days before reminding you again |
| `weeks` | whole number | no | The number of weeks before reminding you again |

**Who can run it:** Anyone, in a server or in DMs.

!!! example "Example"
    You type `/reminder repeat reminder:Stand up and stretch hours:1`.

    The bot answers with an embed; only you see it:

    > On Wednesday 4 November 2026 13:00 (in 1 hour) and then every so often I will remind you of
    > `Stand up and stretch`
    > Use /reminder remove to cancel it.
