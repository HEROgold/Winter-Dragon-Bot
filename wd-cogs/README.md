# wd-cogs

**Legacy.** A catalog of cogs from the discord.py era (`discord.Interaction`, `app_commands`, `commands`). discord.py is not installed and the app does not load this package.

- To bring a feature back, port it into `src/winter_dragon/cogs/` on the `wd_bot` API (`Cog`, `@Cog.command`) instead of editing it here.
- `wd_bot.bot.Bot` still defaults `extensions_package` to `wd_cogs` — always pass your own.
- **API reference:** [wd_cogs](../docs/reference/wd-cogs.md) — use it to see what a cog did before porting it.
