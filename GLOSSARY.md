# Winter Dragon

A Discord bot whose features are organised as cogs. This glossary holds the domain language of those features.

## Guilds and people

**Guild**:
A Discord server the bot has been added to. Developers say guild; everything a user reads says server.
_Avoid_: Server (outside user-facing text), community

**Member**:
A Discord user in a guild the bot is in.
_Avoid_: User (when the guild matters), player

**Guild admin**:
A member with Discord's Manage Server permission in that guild, who configures the bot's features there, in commands and on the dashboard.
_Avoid_: Moderator, server owner, manager

**Bot owner**:
Whoever runs this instance of the bot, and alone may use its operator commands.
_Avoid_: Admin, developer, operator

**Tournament organiser**:
The member who created a tournament, or a guild admin of its guild; they run its bracket.
_Avoid_: Host, tournament admin

**Departed guild**:
A guild that has removed the bot. Its data is kept for a grace period so re-adding the bot restores its setup, then removed.
_Avoid_: Left guild, inactive guild

## Moderation

**Ban network**:
A private group of guilds that share their bans. A guild admin creates it and invites other guilds, whose guild admins accept; each guild applies the network's bans automatically or reviews them first.
_Avoid_: Synced bans, ban list, federation

## Ranked tracking

Holding a player accountable for their ranked progress in a competitive game, by flagging their unusual games and posting them where their server can see.

**Linked account**:
A member's account in a game, such as their Riot account, tied to their Discord identity once and used in every guild.
_Avoid_: Summoner, profile, connection

**Tracked Player**:
A member who has opted in, in one guild, to having their ranked games tracked and posted there; opting in is per guild.
_Avoid_: Summoner, subscriber

**Climb**:
A Tracked Player's ranked progress in one queue of one game during one season. It begins when they opt in and ends when the season ends.
_Avoid_: Run, session, journey

**Ranked Queue**:
A ranked game mode that has its own rank, such as League of Legends' Solo/Duo or Flex.
_Avoid_: Mode, ladder

**Attention Point**:
A statistic from one game that stands out from what is expected, marked so the player has to look at it.
_Avoid_: Flag, outlier, warning, highlight

**Baseline**:
What a Tracked Player's own statistics usually look like, used to judge whether a game is unusual for them.
_Avoid_: Average, norm

**Benchmark**:
What a statistic usually looks like for other players at the same rank and role, used to judge whether a game is unusual compared to peers.
_Avoid_: Peer average, standard

**Note**:
A written comment attached to one tracked game.
_Avoid_: Comment, reflection, annotation
