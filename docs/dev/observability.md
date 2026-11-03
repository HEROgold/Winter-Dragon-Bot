# Observability

How to see what the bot does on the VPS (`ubuntu-4gb-hel1-1`, over Tailscale): its logs, its stats, its traces in
Sentry, and profiles when something is slow.

## Logs

The deploy runs the stack from `~/Winter-Dragon-Bot`, and compose needs both env files:

```sh
cd ~/Winter-Dragon-Bot
alias dc='docker compose -f compose.yml --env-file .env --env-file .env.deploy'
dc logs -f --tail 200 bot            # everything the bot logs, live
dc exec bot ls /app/logs             # one file per logger: Bot.log, Client.log, ...
dc exec bot tail -f /app/logs/Client.log
```

The host's `logs/` folder belongs to the container's user, so read the files through `exec`.

## Bot stats

`/botstats` answers the bot's owners, privately, with guilds, channels and threads, approximate members, unique cached
users, each shard's state and heartbeat latency, uptime and version. The dashboard's `/bot` page shows the same
numbers to the owners, from a snapshot the bot stores every `snapshot_interval` seconds (`cogs.ini`, default 30). The
page warns when the snapshot is older than three intervals, which means the bot stopped storing them.

"Members (approx.)" adds up each guild's member count, so someone in two guilds counts twice. "Unique cached users"
counts distinct cached members; a large guild only sends them all with the members intent.

## Traces in Sentry

The bot reports to the Sentry environment set in `sentry.ini` (`production` on the VPS). Under **Performance**, each
transaction is one of these:

| Operation | Name | What it covers |
|---|---|---|
| `discord.interaction` | `/stats reset`, `/pet (autocomplete)`, `component tourney-leave` | One command, autocomplete, button or modal, from dispatch to reply. |
| `discord.listener` | the listener, like `AutoChannels.on_voice_state_update` | One listener's call for one gateway event, tagged `discord.event`. |
| `task.periodic` | `Cog.task`, like `Reminders.deliver_due` | One tick of a periodic task. |

Inside a transaction, each REST call is an `http.client` span named by its route (`GET /channels/{channel_id}`) and
each database query is a `db` span. To find what makes a command slow, open its transaction and look for the longest
span.

`sentry.ini` sets how many transactions are sent:

| Setting | Default | Meaning |
|---|---|---|
| `traces_sample_rate` | 1.0 | The share of interactions and periodic ticks traced. |
| `listener_traces_sample_rate` | 0.05 | The share of listener calls traced; some events arrive many times a second. |

The dashboard sends one `http.server` transaction per request, at `traces_sample_rate`.

## Profiling

Sentry can profile the traced transactions, which shows the functions the time went to. Sentry bills profiling
separately, so it's off by default.

1. On the VPS, set `profile_session_sample_rate = 1.0` under `[SentrySettings]` in `~/Winter-Dragon-Bot/sentry.ini`.
2. Restart the bot: `dc restart bot`. The setting is read once at startup.
3. Use the slow command, or wait for the slow task to run.
4. In Sentry, open the transaction and its **Profile** tab, or **Profiling** for the flame graph over all of them.
5. Set the rate back to `0.0` and restart again.

`profile_lifecycle` is `trace`, so the profiler only runs while a sampled transaction is open. A rate between 0 and 1
profiles that share of processes, not of transactions.
