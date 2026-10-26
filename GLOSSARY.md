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

## Archive

**Archive**:
A separate, read-only bot that records every gateway event into the database, to stress test wd-discord and the database on an existing server. Not part of Winter Dragon.
_Avoid_: Event logger (that only writes a log file), recorder, tracker

**Raw event**:
One gateway event exactly as Discord sent it, kept by the archive for 30 days.
_Avoid_: Frame (outside gateway code), payload, log entry

**Snapshot**:
The presences and voice states the archive appends when it connects, so its history has a starting point after downtime.
_Avoid_: Backfill, sync

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

## Tournaments

**Team**:
A group of members, which may span guilds, that exists apart from any tournament and can enter many. It may have a captain. Its roster can change and it stays the same team.
_Avoid_: Squad, roster, clan

**Tournament entry**:
A team's place in one tournament, with the players who play for it there.
_Avoid_: Tournament team, registration

## Member stats

**Profile**:
A member's own pages on the dashboard, showing what they have done with each feature across every guild. Only that member sees it.
_Avoid_: Stats, dashboard (for the member pages), your data (that is the GDPR view)

**Stats channel**:
A locked voice channel whose name shows one of a guild's member counts.
_Avoid_: Stat, counter

**Compatibility check**:
A member asking for their compatibility with another user. The percentage is fixed for each pair, so the check is the event worth keeping, and it belongs to the member who asked.
_Avoid_: Love score, match

**Sale threshold**:
The lowest Steam discount a member wants to be told about.
_Avoid_: Minimum, filter

**Sale notification**:
A Steam sale sent to a member because it met their sale threshold at the time it was sent.
_Avoid_: Alert, deal, ping

**Refuel**:
One fill-up a member logs: fuel added, distance driven since the last one, price, and the date it happened.
_Avoid_: Fuel entry, log, tank

**Lookup**:
An Urban Dictionary search by a member that returned a definition. Searches that found nothing are not lookups.
_Avoid_: Query, search

## Games

**Hangman game**:
One round of hangman, shown as a single message and started by one member, where anyone may guess. A channel can have several running at once.
_Avoid_: Match, session

**Participant**:
A member who guessed at least one correct letter in a hangman game. When the game is won, every participant is credited with the win.
_Avoid_: Player, guesser

**Incremental game**:
An idle game each member plays once, across every guild, in which generators produce currencies over time. A member can play it in Discord or on the dashboard, and both can do the same things.
_Avoid_: Clicker, idle game, economy

**Generator**:
Something a member buys in the incremental game that produces currencies at fixed rates. Only the bot's developers define which generators exist, as part of the game.
_Avoid_: Building, producer, upgrade

**Currency**:
A resource in the incremental game that generators produce and members spend. Only the bot's developers define which currencies exist, as part of the game.
_Avoid_: Money, coins, points
