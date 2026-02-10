# Tournament Extension Logging Summary

## Overview

Comprehensive logging has been added throughout the tournament extension to enable debugging and monitoring of:
- Extension loading/unloading
- Command execution
- User interactions
- Matchmaking operations
- Database operations
- Error conditions

## Logging Levels

### INFO
- Extension initialization and loading
- Command execution starts
- Major operations (team generation, match recording)
- Successful completions
- State changes (voting concluded, tournament started)

### DEBUG
- Detailed operation parameters
- Vote counts and updates
- Player profiles loaded
- Database queries
- Team compositions
- Vote display updates

### WARNING
- Configuration issues (missing API keys)
- Missing guilds during auto-sync
- Non-critical failures

### EXCEPTION (with traceback)
- Extension loading failures
- Command execution errors
- Database operation failures
- Unexpected errors

---

## File-by-File Logging Details

### 1. matchmaking.py

**Class: MatchmakingSystem (now inherits LoggerMixin)**

#### Initialization
```python
self.logger.info("MatchmakingSystem initialized")
```

#### create_balanced_teams()
- **Start**: Logs game, player count, format, synergy setting
- **During**: Game fetch, player profile count
- **End**: Success with team count and composition details

```python
self.logger.info(
    f"Creating balanced teams for {game_name}: {len(player_ids)} players, "
    f"format={bracket_format}, avoid_synergy={avoid_synergy}"
)
self.logger.debug(f"Game fetched: {game.name} (ID: {game.id})")
self.logger.debug(f"Loaded {len(profiles)} player profiles")
self.logger.info(f"Successfully created {len(result)} balanced teams")
self.logger.debug(f"Team composition: {result}")
```

#### record_match_result()
- **Start**: Logs game, team count, winner, format
- **During**: Match record creation
- **End**: Match recorded with statistics updated

```python
self.logger.info(
    f"Recording match result for {game_name}: {len(teams)} teams, "
    f"winner=team_{winning_team_idx}, format={bracket_format}"
)
self.logger.debug(f"Match record created (ID: {match.id})")
self.logger.info(f"Match recorded and statistics updated (Match ID: {match.id})")
```

---

### 2. event.py

**Class: TournamentEventManager (already had LoggerMixin)**

#### Initialization
```python
# Success path
self.logger.info("TournamentEventManager initialized with Riot API")

# Warning path
self.logger.warning(
    "RIOT_API_KEY not configured. Tournament event features will be unavailable."
)
```

#### Cog Lifecycle
```python
async def cog_load(self):
    self.logger.info("TournamentEventManager cog loading...")
    # ... load operations ...
    self.logger.info("Auto-sync task started successfully")
    self.logger.info("TournamentEventManager cog loaded")

async def cog_unload(self):
    self.logger.info("TournamentEventManager cog unloading...")
    self.logger.info("Auto-sync task stopped")
    self.logger.info("Clash client closed")
    self.logger.info("TournamentEventManager cog unloaded")
```

#### Commands

**sync_clash_events**
```python
self.logger.info(
    f"User {interaction.user.id} ({interaction.user.name}) executing /sync-clash-events "
    f"in guild {interaction.guild.name if interaction.guild else 'DM'} (region={region})"
)
# ... operation ...
self.logger.info(
    f"Clash sync completed for {interaction.guild.name}: "
    f"{len(created)} created, {len(failed)} failed"
)
```

**enable_auto_sync**
```python
self.logger.info(
    f"User {interaction.user.id} ({interaction.user.name}) executing /enable-auto-sync "
    f"in guild {interaction.guild.name if interaction.guild else 'DM'} (region={region})"
)
self.logger.info(
    f"Auto-sync enabled for guild {interaction.guild.name} (region: {platform})"
)
```

**disable_auto_sync**
```python
self.logger.info(
    f"User {interaction.user.id} ({interaction.user.name}) executing /disable-auto-sync "
    f"in guild {interaction.guild.name if interaction.guild else 'DM'}"
)
self.logger.info(f"Auto-sync disabled for guild {interaction.guild.name}")
```

**list_clash_events**
```python
self.logger.info(
    f"User {interaction.user.id} ({interaction.user.name}) executing /list-clash-events "
    f"in guild {interaction.guild.name if interaction.guild else 'DM'}"
)
```

#### Background Task
```python
async def auto_sync_task(self):
    self.logger.debug(f"Running auto-sync for {len(self.auto_sync_guilds)} guild(s)")
    # ... for each guild ...
    self.logger.warning(f"Guild {guild_id} not found, removing from auto-sync")
    self.logger.debug(f"No tournaments found for guild {guild.name} (region: {platform})")
    self.logger.info(
        f"Auto-sync for guild {guild.name}: "
        f"{len(created)} created, {len(failed)} failed, "
        f"{len(tournaments)} total tournaments"
    )
    # Errors
    self.logger.exception("Auto-sync failed for guild {guild_id}")
    self.logger.exception(f"Unexpected error in auto-sync for guild {guild_id}")
```

#### Setup Function
```python
async def setup(bot):
    logger.info("Loading TournamentEventManager extension...")
    await bot.add_cog(TournamentEventManager(bot=bot))
    logger.info("TournamentEventManager extension loaded successfully")
    # On error
    logger.exception(f"Failed to load TournamentEventManager: {e}")
```

---

### 3. voting.py

**Class: TournamentVoting (already had LoggerMixin)**

#### Initialization & Lifecycle
```python
def __init__(self):
    self.logger.info("TournamentVoting cog initialized")
    self.logger.debug(f"Active votes tracker initialized: {len(self.active_votes)} votes")

async def cog_load(self):
    self.logger.info("TournamentVoting cog loaded and ready")

async def cog_unload(self):
    self.logger.info(
        f"TournamentVoting cog unloading... {len(self.active_votes)} active votes will be cleared"
    )
    self.active_votes.clear()
    self.logger.info("TournamentVoting cog unloaded")
```

#### Commands

**start_tournament**
```python
self.logger.info(f"User {interaction.user.id} starting tournament vote")
self.logger.debug(f"Starting vote with games: {game_list}, formats: {format_list}")
self.logger.info(f"Tournament vote started (message ID: {message.id})")
```

**generate_teams (internal)**
```python
self.logger.info(f"Generating teams for {len(vote_tracker.participants)} participants")
self.logger.debug(f"Using bracket format: {bracket_format}")
self.logger.info(f"Teams generated successfully: {len(teams)} teams")
self.logger.info("Team assignments sent")
# Errors
self.logger.exception(f"Failed to generate teams: {e}")
self.logger.exception(f"Unexpected error generating teams: {e}")
```

**record_match**
```python
self.logger.info(f"User {interaction.user.id} recording match for {game}")
self.logger.debug(f"Teams parsed: {teams}")
self.logger.info(f"Match recorded successfully (ID: {match.id})")
# Errors
self.logger.exception(f"Invalid input: {e}")
self.logger.exception(f"Failed to record match: {e}")
```

**player_stats**
```python
self.logger.info(f"Fetching stats for user {target_user.id} in {game}")
self.logger.info(f"Stats displayed for user {target_user.id}")
# Errors
self.logger.exception(f"Failed to fetch stats: {e}")
```

**leaderboard**
```python
self.logger.info(f"Fetching leaderboard for {game}")
self.logger.info(f"Leaderboard displayed for {game}")
# Errors
self.logger.exception(f"Failed to fetch leaderboard: {e}")
```

#### Setup Function
```python
async def setup(bot):
    logger.info("Loading TournamentVoting extension...")
    await bot.add_cog(TournamentVoting(bot))
    logger.info("TournamentVoting extension loaded successfully")
    # On error
    logger.exception(f"Failed to load TournamentVoting: {e}")
```

---

### 4. views.py

**All UI components inherit LoggerMixin**

#### GameVoteSelect
```python
async def _handle_vote(self, interaction):
    self.logger.info(f"User {interaction.user.id} voting for: {self.values[0]}")
    self.logger.debug(f"Vote recorded: {game_name} now has {vote_count} votes")
```

#### BracketFormatSelect
```python
async def _handle_format_vote(self, interaction):
    self.logger.info(f"User {interaction.user.id} voting for format: {self.values[0]}")
    self.logger.debug(f"Format vote recorded: {format_choice} now has {vote_count} votes")
```

#### JoinTournamentButton
```python
async def _handle_join(self, interaction):
    self.logger.info(f"User {interaction.user.id} joining tournament")
    self.logger.debug(f"Participant added: {interaction.user.id}. Total: {len(participants)}")
```

#### ConcludeVotingButton
```python
async def _handle_conclude(self, interaction):
    self.logger.info(f"User {interaction.user.id} attempting to conclude voting")
    self.logger.info(f"Voting concluded: {winning_game} won with {winning_votes} votes")
```

#### StartTournamentButton
```python
async def _handle_start(self, interaction):
    self.logger.info(f"User {interaction.user.id} attempting to start tournament")
    self.logger.info(f"Tournament starting with {len(participants)} participants")
```

#### TournamentVotingView
```python
def __init__(self):
    self.logger.info(
        f"TournamentVotingView initialized: {len(available_games)} games, "
        f"{len(available_formats) if available_formats else 0} formats, admin={admin_id}"
    )

async def update_vote_display(self, interaction):
    self.logger.debug("Updating vote display")
    self.logger.debug("Vote display updated successfully")
    # On error
    self.logger.exception(f"Failed to update vote display: {e}")
```

---

## Usage Examples

### Debugging Extension Loading
```python
# Check logs for:
# INFO: "Loading TournamentVoting extension..."
# INFO: "TournamentVoting cog initialized"
# INFO: "TournamentVoting cog loaded and ready"
# INFO: "TournamentVoting extension loaded successfully"
```

### Debugging Command Execution
```python
# For /start_tournament command, look for:
# INFO: "User 123456789 starting tournament vote"
# DEBUG: "Starting vote with games: ['Game1', 'Game2'], formats: ['2v2', '3v3']"
# INFO: "Tournament vote started (message ID: 987654321)"
```

### Debugging Team Generation
```python
# Look for:
# INFO: "Generating teams for 8 participants"
# INFO: "Creating balanced teams for League of Legends: 8 players, format=2v2, avoid_synergy=True"
# DEBUG: "Game fetched: League of Legends (ID: 1)"
# DEBUG: "Loaded 8 player profiles"
# INFO: "Successfully created 4 balanced teams"
# DEBUG: "Team composition: [[1, 2], [3, 4], [5, 6], [7, 8]]"
# INFO: "Teams generated successfully: 4 teams"
```

### Debugging Match Recording
```python
# Look for:
# INFO: "User 123456789 recording match for League of Legends"
# DEBUG: "Teams parsed: [[1, 2], [3, 4]]"
# INFO: "Recording match result for League of Legends: 2 teams, winner=team_0, format=2v2"
# DEBUG: "Match record created (ID: 42)"
# INFO: "Match recorded and statistics updated (Match ID: 42)"
# INFO: "Match recorded successfully (ID: 42)"
```

### Debugging Auto-Sync
```python
# Every hour, look for:
# DEBUG: "Running auto-sync for 3 guild(s)"
# INFO: "Auto-sync for guild MyGuild: 2 created, 0 failed, 5 total tournaments"
```

### Debugging Errors
```python
# Any exception will include full traceback:
# EXCEPTION: "Failed to load TournamentVoting: <error details>"
# EXCEPTION: "Failed to generate teams: <error details>"
# EXCEPTION: "Unexpected error in auto-sync for guild 123: <error details>"
```

---

## Log Filtering

### By Component
- **Extension Loading**: Search for "extension" or "cog load"
- **Commands**: Search for "executing" or specific command names
- **Matchmaking**: Search for "Creating balanced teams" or "MatchmakingSystem"
- **Database**: Search for "Match record" or "statistics updated"
- **UI Interactions**: Search for "voting for" or "joining tournament"

### By User
- Search for user ID: `User 123456789`
- Filter by username: `(Username)`

### By Guild
- Search for guild name: `guild GuildName`
- Search for guild ID in auto-sync logs

### By Log Level
- **Production Monitoring**: INFO and above
- **Development Debugging**: DEBUG and above
- **Error Tracking**: WARNING and above only

---

## Best Practices

1. **Always check logs when troubleshooting** - The extension now provides comprehensive information at every step
2. **Enable DEBUG level during testing** - Provides detailed operation traces
3. **Monitor EXCEPTION logs** - All errors include full tracebacks
4. **Check extension loading first** - Ensures cogs are properly initialized
5. **Verify command execution** - Confirms users are executing commands correctly
6. **Track user IDs** - All user actions are logged with IDs for auditing

---

## Future Enhancements

Potential logging additions:
- Performance metrics (execution time for operations)
- Cache hit/miss rates
- Database query performance
- Rate limiting information
- API quota usage
- WebSocket event tracking

---

## Summary

Every major operation in the tournament extension now has comprehensive logging:

✅ **Extension lifecycle** - Load, unload, initialization  
✅ **Command execution** - All commands log start and completion  
✅ **User interactions** - Votes, joins, button clicks  
✅ **Matchmaking operations** - Team generation, profile loading  
✅ **Database operations** - Match recording, statistics updates  
✅ **Background tasks** - Auto-sync with detailed progress  
✅ **Error handling** - All exceptions with full tracebacks  
✅ **State changes** - Voting concluded, tournament started  
✅ **Configuration** - API keys, settings validation  

The logging system provides complete visibility into the tournament system's operation, making debugging and monitoring straightforward and efficient.
