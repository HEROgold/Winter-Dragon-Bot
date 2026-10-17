# wd-config

Every operator-configurable value: confkit `Config[T]` descriptors bound to `config.ini` (and `DiscordConfig[T]` to `discord.ini`), grouped in one settings class per concern.

- **Depends on:** nothing internal (confkit only). Everything else may import it.
- **Start here:** `Settings` (bot), `DbUrl`, `SentrySettings`, `URLS` (Discord API base + version). Cog settings live with their cogs in `src/winter_dragon/cogs/`, on the app's `CogConfig` (`cogs.ini`).
- **Rules:** derived values use `Combined(...)`; secrets default to the `"!!"` sentinel; first launch writes defaults and raises `FirstTimeLaunchError`. See the `config-and-constants` skill.
- **API reference:** [wd_config](../docs/reference/wd-config.md)
