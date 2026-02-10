# Matchmaking System Quick Reference

## Quick Start

```python
from winter_dragon.bot.extensions.tournament.matchmaking import MatchmakingSystem

mm = MatchmakingSystem()
```

## Common Operations

### 1. Create Balanced Teams

```python
teams = mm.create_balanced_teams(
    game_name="League of Legends",
    player_ids=[100001, 100002, 100003, 100004],
    bracket_format="2v2",
    avoid_synergy=True,
)
# Returns: [[100001, 100003], [100002, 100004]]
```

### 2. Record Match Results

```python
match = mm.record_match_result(
    game_name="League of Legends",
    teams=[[100001, 100003], [100002, 100004]],
    winning_team_idx=0,  # First team won
    bracket_format="2v2",
    individual_scores={
        100001: 300,
        100002: 250,
        100003: 280,
        100004: 240,
    },
    team_scores=[580, 490],
    duration_seconds=1800,
)
```

### 3. View Player Stats

```python
mm.print_player_stats("League of Legends", limit=10)
```

### 4. View Synergy Data

```python
mm.print_synergy_data("League of Legends", limit=15)
```

### 5. Generate Test Data

```python
mm.generate_example_data(num_players=12, num_matches=100)
```

## Bracket Formats

| Format | Description | Example |
|--------|-------------|---------|
| `"1v1"` | One vs One | 2 players total |
| `"2v2"` | Two vs Two | 4 players total |
| `"3v3"` | Three vs Three | 6 players total |
| `"4v4"` | Four vs Four | 8 players total |
| `"ffa"` | Free For All | Any number (each player solo) |

## Database Tables

| Table | Purpose |
|-------|---------|
| `game_match` | Core match information |
| `match_player` | Player participation records |
| `match_team` | Team-level statistics |
| `player_game_stats` | Aggregated player stats |
| `player_synergy` | Player interaction history |
| `team_composition` | Historical team compositions |

## Direct Database Queries

### Get Player Stats

```python
from winter_dragon.database.tables.matchmaking.player_game_stats import PlayerGameStats
from sqlmodel import select

stats = mm.session.exec(
    select(PlayerGameStats)
    .where(PlayerGameStats.user_id == 100001)
    .where(PlayerGameStats.game_id == game_id)
).first()

print(f"Skill Rating: {stats.skill_rating}")
print(f"Win Rate: {stats.win_rate * 100}%")
```

### Get Synergy Between Two Players

```python
from winter_dragon.database.tables.matchmaking.player_synergy import PlayerSynergy

p1, p2 = sorted([100001, 100002])
synergy = mm.session.exec(
    select(PlayerSynergy)
    .where(PlayerSynergy.player1_id == p1)
    .where(PlayerSynergy.player2_id == p2)
    .where(PlayerSynergy.game_id == game_id)
).first()

print(f"Teammate Synergy: {synergy.teammate_synergy * 100}%")
```

### Get Recent Matches

```python
from winter_dragon.database.tables.matchmaking.game_match import GameMatch

matches = mm.session.exec(
    select(GameMatch)
    .where(GameMatch.game_id == game_id)
    .order_by(GameMatch.match_date.desc())
    .limit(10)
).all()
```

## Integration with Discord Bot

### Example Command: Create Tournament

```python
@bot.slash_command(name="create_tournament")
async def create_tournament(
    ctx: discord.ApplicationContext,
    game: str,
    format: str,
    players: str,  # Comma-separated user IDs or mentions
):
    """Create balanced teams for a tournament."""
    mm = MatchmakingSystem()
    
    # Parse player IDs
    player_ids = [int(p.strip()) for p in players.split(",")]
    
    try:
        teams = mm.create_balanced_teams(
            game_name=game,
            player_ids=player_ids,
            bracket_format=format,
            avoid_synergy=True,
        )
        
        # Format response
        response = f"**Tournament Teams for {game} ({format})**\n\n"
        for i, team in enumerate(teams, 1):
            team_mentions = [f"<@{uid}>" for uid in team]
            response += f"**Team {i}:** {', '.join(team_mentions)}\n"
        
        await ctx.respond(response)
        
    except ValueError as e:
        await ctx.respond(f"Error: {e}", ephemeral=True)
```

### Example Command: Record Result

```python
@bot.slash_command(name="record_match")
async def record_match(
    ctx: discord.ApplicationContext,
    game: str,
    format: str,
    team1: str,  # Comma-separated user IDs
    team2: str,  # Comma-separated user IDs
    winner: int,  # 1 or 2
):
    """Record match results."""
    mm = MatchmakingSystem()
    
    team1_ids = [int(p.strip()) for p in team1.split(",")]
    team2_ids = [int(p.strip()) for p in team2.split(",")]
    teams = [team1_ids, team2_ids]
    
    match = mm.record_match_result(
        game_name=game,
        teams=teams,
        winning_team_idx=winner - 1,  # Convert to 0-based
        bracket_format=format,
    )
    
    await ctx.respond(f"✅ Match recorded (ID: {match.id})")
```

### Example Command: View Stats

```python
@bot.slash_command(name="player_stats")
async def player_stats(
    ctx: discord.ApplicationContext,
    game: str,
    player: discord.Member,
):
    """View player statistics."""
    mm = MatchmakingSystem()
    game_obj = Games.fetch_game_by_name(game)
    
    stats = mm.session.exec(
        select(PlayerGameStats)
        .where(PlayerGameStats.user_id == player.id)
        .where(PlayerGameStats.game_id == game_obj.id)
    ).first()
    
    if not stats:
        await ctx.respond(f"{player.mention} has no stats for {game}", ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"{player.display_name}'s {game} Stats",
        color=discord.Color.blue(),
    )
    embed.add_field(name="Matches", value=stats.total_matches, inline=True)
    embed.add_field(name="Record", value=f"{stats.total_wins}-{stats.total_losses}", inline=True)
    embed.add_field(name="Win Rate", value=f"{stats.win_rate * 100:.1f}%", inline=True)
    embed.add_field(name="Skill Rating", value=f"{stats.skill_rating:.0f}", inline=True)
    embed.add_field(name="Avg Score", value=f"{stats.avg_score:.1f}", inline=True)
    
    await ctx.respond(embed=embed)
```

## Testing

Run the test suite:

```bash
python src/winter_dragon/bot/extensions/tournament/test_matchmaking.py
```

Or in Python:

```python
from winter_dragon.bot.extensions.tournament.test_matchmaking import test_matchmaking_system
test_matchmaking_system()
```

## Troubleshooting

### Issue: "Record with Games.id=X not found"
**Solution:** Create the game first:
```python
from winter_dragon.database.tables.game import Games
game = Games.fetch_game_by_name("Your Game Name")
```

### Issue: "Record with Users.id=X not found"
**Solution:** Ensure users exist in the database or create them:
```python
from winter_dragon.database.tables.user import Users
user = Users(id=user_id)
user.add(mm.session)
mm.session.commit()
```

### Issue: Teams seem unbalanced
**Solution:** Need more match history. Run at least 20-30 matches before synergy data becomes useful.

### Issue: Database tables not created
**Solution:** Run migrations:
```python
from sqlmodel import SQLModel
from winter_dragon.database.constants import engine
SQLModel.metadata.create_all(engine)
```

## Performance Tips

1. **Batch Operations**: Record multiple matches at once
2. **Cache Player Profiles**: Store frequently accessed player data
3. **Index Optimization**: Ensure foreign keys are indexed
4. **Limit Queries**: Use `.limit()` on large result sets
5. **Transaction Batching**: Group related operations in single transactions

## Advanced Configuration

### Adjust Balance Weights

```python
# In matchmaking.py, modify _evaluate_team_balance method:
def _evaluate_team_balance(
    self,
    teams: list[TeamCandidate],
    synergy_map: dict[tuple[int, int], float],
    skill_weight: float = 1.5,  # Increase to prioritize skill balance
    synergy_weight: float = 0.3,  # Decrease to care less about synergy
) -> float:
    # ... rest of method
```

### Modify Skill Rating Updates

```python
# In _update_player_stats method:
k_factor = 32  # Lower = slower changes, Higher = faster changes
```

### Change Iteration Count for Large Groups

```python
# In _iterative_team_search method:
iterations: int = 2000  # Increase for better results (slower)
```

## Resources

- Full Documentation: `MATCHMAKING_README.md`
- Test Script: `test_matchmaking.py`
- Database Tables: `src/winter_dragon/database/tables/matchmaking/`
