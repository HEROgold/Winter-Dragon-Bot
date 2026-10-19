# Server management

Features a guild admin sets up for their guild. Their data belongs to the guild: when the guild becomes a **departed guild** it is hidden, restored if the bot is re-added within the grace period, and purged after it (see [Data and privacy](data-and-privacy.md)).

## Automatic voice channels

Joining a guild's hub voice channel gives a member a voice channel of their own, deleted once everyone has left.

- **Who:** guild admins set up the hub; members use it and choose their channel's name and user limit.
- **Commands:** `/autochannel setup` (create a category with a hub), `/autochannel mark` (make an existing voice channel the hub), `/autochannel guild-limit` (how many automatic channels at once; 0 is no limit); `/autochannel name` and `/autochannel limit` for the member's own channel.
- **Stores:** each guild's hub and channel limit; each automatic channel; each member's preferred name and user limit, which apply in every guild.
- **Rules:** the owner of a channel may run it but not change who may see it; at the guild limit, joining the hub creates nothing.
- **Dashboard:** server settings: the hub and the limit. Your data: the member's own name and limit.
- **Status:** Live, [autochannel.py](../../src/winter_dragon/cogs/autochannel.py).

## Roles back on rejoin

A member who leaves and rejoins a guild gets back the roles they had, including after a kick or ban.

- **Who:** guild admins turn it on.
- **Commands:** `/autoreassign enable`, `/autoreassign disable`.
- **Stores:** which guilds have it on; the roles each member had when they left.
- **Rules:** only roles the bot may still give are restored: roles that still exist, aren't managed by an integration, and are below the bot's highest role.
- **Dashboard:** a switch in server settings; Your data lists the roles kept for the member.
- **Status:** Live, [auto_reassign.py](../../src/winter_dragon/cogs/auto_reassign.py).

## Roles on join

Every new member gets one or more roles automatically.

- **Who:** guild admins.
- **Commands:** `/autoassign` to show, add and remove the roles.
- **Stores:** each guild's roles to give.
- **Rules:** the same restrictions as roles back on rejoin; a member who rejoins with roles to restore gets both.
- **Dashboard:** a role picker in server settings.
- **Status:** Port.

## Welcome messages

A greeting posted when a member joins.

- **Who:** guild admins.
- **Commands:** `/welcome` (an interactive menu: channel, message, on or off).
- **Stores:** each guild's welcome channel, message and whether it is on.
- **Dashboard:** server settings: channel, message with a preview, on or off.
- **Status:** Port.

## Stats channels

A guild's member counts, on demand and as the names of locked voice channels that update themselves.

- **Who:** members read them; guild admins add and remove the channels; the bot owner can recreate them everywhere.
- **Commands:** `/stats show`, `/stats add`, `/stats remove`, `/stats reset` (bot owner: recreate every guild's stats channels).
- **Stores:** each guild's stats channels and their category; each guild's peak online count.
- **Rules:** counts update every `update_interval`; Discord lets a channel be renamed only twice per 10 minutes, so it stays long.
- **Settings:** `StatsSettings`: `update_interval` (3600 s), `category_name`.
- **Dashboard:** a switch in server settings.
- **Status:** Live, [stats.py](../../src/winter_dragon/cogs/stats.py).

## Server announcements

A member who may mention everyone posts an announcement as a clean embed that pings the server.

- **Who:** members with the Mention Everyone permission.
- **Commands:** `/announcement`.
- **Status:** Port. (The bot owner's announcements to every guild are in [Bot core](bot-core.md#announcements-to-guilds).)

## Dropped

- **Guild scaffolding** (`/generate` on `main`): Discord's own server templates do this.
