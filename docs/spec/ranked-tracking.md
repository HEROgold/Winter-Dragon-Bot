# Ranked tracking

Holding a player accountable for their ranked progress: the bot follows a **Tracked Player**'s games in a **Ranked Queue** over their **Climb**, marks each game's **Attention Points**, and posts them where their guild can see. League of Legends comes first; the terms stay game-neutral so other games can follow.

- **Who:** members opt in; guild admins pick where it is posted; other members read and add **Notes**.
- **Rules:**
  - Tracking needs a **linked account** (see [Games](games.md#league-of-legends)), which is global.
  - Opting in is **per guild**: being a Tracked Player in one guild says nothing about another, because opting in is consent to being posted there.
  - A Climb belongs to the player, not a guild: one queue, one game, one season, from opting in to the season's end. The same Climb feeds every guild where the member opted in.
  - A game's statistics are judged against the player's own **Baseline** and against the **Benchmark** of peers at the same rank and role; a statistic that stands out from either is an Attention Point.
  - Attention Points are posted to the channel the guild admin picked; a guild without one has tracking off.
- **Stores:** linked accounts; per guild, who opted in and the tracking channel; Climbs, their games and statistics; Notes.
- **Dashboard:** a Climb page per player (games, Attention Points, Notes); server settings: the tracking channel.
- **Status:** New.

## Open decisions

To be settled before it is built:

1. Which statistics can become Attention Points, and how far from the Baseline or Benchmark one has to be.
2. How many games a Baseline needs before it is trusted, and what is judged until then.
3. Where Benchmarks come from: a Riot endpoint, a third-party source, or the bot's own Tracked Players.
