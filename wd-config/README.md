# wd-config

The configuration base: the unbound confkit `Config[T]` every scope subclasses and binds to its own ini file (`Config.bind`), the first-launch check (`OperatorFiles`), and the scopes of the libraries that can't own them (`DiscordConfig[T]` in `discord.ini`, `SentryConfig[T]` in `sentry.ini`). The app's `config.ini` and `cogs.ini` scopes live in `src/winter_dragon/config.py`.

- **Depends on:** nothing internal (confkit only). Everything else may import it.
- **Start here:** `Config.bind`, `OperatorFiles`, `SentrySettings`, `URLS` (Discord API base + version). App settings (`Settings`, in `config.ini`) and cog settings (`CogConfig`, in `cogs.ini`) live in `src/winter_dragon/`.
- **Rules:** every setting belongs to a bound scope; secrets default to the `"!!"` sentinel; first launch writes defaults and raises `FirstTimeLaunchError`. See the `config-and-constants` skill.
- **API reference:** [wd_config](../docs/reference/wd-config.md)
