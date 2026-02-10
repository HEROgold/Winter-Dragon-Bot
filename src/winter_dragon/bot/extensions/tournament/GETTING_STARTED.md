# Getting Started with the Matchmaking System

## Quick Setup (5 minutes)

### Step 1: Run the Test Suite

This will verify everything works and generate example data:

```bash
cd c:\Users\marti\Documents\GitHub\Winter-Dragon-Bot
python src\winter_dragon\bot\extensions\tournament\test_matchmaking.py
```

Expected output:
- ✓ System initialized
- ✓ Example data generated
- Player statistics table
- Synergy data table
- Match history
- Data integrity check: OK
- Test matchmaking results

### Step 2: Understand the Core Concepts

#### 1. **Creating Balanced Teams**

```python
from winter_dragon.bot.extensions.tournament.matchmaking import MatchmakingSystem

mm = MatchmakingSystem()

# Create teams for 6 players in a 3v3 format
teams = mm.create_balanced_teams(
    game_name="League of Legends",
    player_ids=[100001, 100002, 100003, 100004, 100005, 100006],
    bracket_format="3v3",
    avoid_synergy=True,  # Separate players who usually win together
)
# Returns: [[id1, id3, id5], [id2, id4, id6]]
```

#### 2. **Recording Match Results**

```python
match = mm.record_match_result(
    game_name="League of Legends",
    teams=teams,
    winning_team_idx=0,  # Team at index 0 won
    bracket_format="3v3",
    individual_scores={
        100001: 300,  # Player scores
        100002: 250,
        # ... etc
    },
    team_scores=[850, 600],  # Total team scores
    duration_seconds=1800,   # 30 minutes
)
```

This automatically updates:
- Player skill ratings
- Win/loss records
- Synergy data between players
- Team composition history

#### 3. **Viewing Statistics**

```python
# View player rankings
mm.print_player_stats("League of Legends", limit=10)

# View player synergies (who works well together)
mm.print_synergy_data("League of Legends", limit=15)

# View recent matches
mm.print_match_history("League of Legends", limit=10)
```

### Step 3: Integrate with Your Discord Bot

Add these slash commands to your bot:

```python
@bot.slash_command(name="create_teams")
async def create_teams(
    ctx: discord.ApplicationContext,
    game: str,
    format: str,  # e.g., "2v2", "3v3"
    player1: discord.Member,
    player2: discord.Member,
    player3: discord.Member,
    player4: discord.Member,
    player5: discord.Member = None,
    player6: discord.Member = None,
):
    """Create balanced teams for a match."""
    mm = MatchmakingSystem()
    
    # Collect player IDs
    players = [player1, player2, player3, player4]
    if player5:
        players.append(player5)
    if player6:
        players.append(player6)
    
    player_ids = [p.id for p in players]
    
    try:
        teams = mm.create_balanced_teams(
            game_name=game,
            player_ids=player_ids,
            bracket_format=format,
            avoid_synergy=True,
        )
        
        # Format response
        embed = discord.Embed(
            title=f"{game} - {format} Teams",
            color=discord.Color.blue(),
        )
        
        for i, team in enumerate(teams, 1):
            team_members = [f"<@{uid}>" for uid in team]
            embed.add_field(
                name=f"Team {i}",
                value="\n".join(team_members),
                inline=True,
            )
        
        await ctx.respond(embed=embed)
        
    except ValueError as e:
        await ctx.respond(f"❌ Error: {e}", ephemeral=True)
```

## Key Features Explained

### 1. Skill Ratings (ELO System)

- All players start at 1000 rating
- Win = rating increases
- Lose = rating decreases
- Separate rating per game

### 2. Synergy Avoidance

The system tracks:
- **Teammate synergy**: Win rate when paired together
- **Rivalry**: Head-to-head win/loss records

When `avoid_synergy=True`, the algorithm actively avoids putting players with high synergy on the same team, creating more balanced matches.

### 3. Game-Specific Stats

Every statistic is tracked per game:
- A player skilled in "League of Legends" might be new to "Rocket League"
- Each game has independent ratings and statistics

### 4. Bracket Formats

Supported formats:
- `"1v1"` - One vs one (2 players)
- `"2v2"` - Two vs two (4 players)
- `"3v3"` - Three vs three (6 players)
- `"4v4"` - Four vs four (8 players)
- `"ffa"` - Free for all (any number, each player solo)

## Database Tables Overview

The system uses 6 tables in 6th Normal Form:

1. **`game_match`** - Stores match details (date, winner, format)
2. **`match_player`** - Records individual player participation
3. **`match_team`** - Stores team-level results
4. **`player_game_stats`** - Aggregated player statistics
5. **`player_synergy`** - Tracks player interactions
6. **`team_composition`** - Historical team performance

All tables are automatically created via SQLModel migrations.

## Common Use Cases

### Tournament Bracket Creation

```python
# Generate teams for a tournament
all_players = [100001, 100002, 100003, 100004, 100005, 100006, 100007, 100008]

# Create 4 teams of 2
match1_players = all_players[:4]
match2_players = all_players[4:]

match1_teams = mm.create_balanced_teams(
    game_name="CS:GO",
    player_ids=match1_players,
    bracket_format="2v2",
)

match2_teams = mm.create_balanced_teams(
    game_name="CS:GO",
    player_ids=match2_players,
    bracket_format="2v2",
)
```

### Ranked Ladder System

```python
# Get top players by skill rating
from winter_dragon.database.tables.matchmaking.player_game_stats import PlayerGameStats
from sqlmodel import select

top_players = mm.session.exec(
    select(PlayerGameStats)
    .where(PlayerGameStats.game_id == game.id)
    .order_by(PlayerGameStats.skill_rating.desc())
    .limit(100)
).all()

# Display leaderboard
for rank, stats in enumerate(top_players, 1):
    print(f"{rank}. User {stats.user_id}: {stats.skill_rating:.0f} rating")
```

### Player vs Player History

```python
from winter_dragon.database.tables.matchmaking.player_synergy import PlayerSynergy

p1, p2 = sorted([100001, 100002])
synergy = mm.session.exec(
    select(PlayerSynergy)
    .where(PlayerSynergy.player1_id == p1)
    .where(PlayerSynergy.player2_id == p2)
    .where(PlayerSynergy.game_id == game.id)
).first()

if synergy:
    print(f"Matches as teammates: {synergy.matches_as_teammates}")
    print(f"Win rate together: {synergy.teammate_synergy * 100:.1f}%")
    print(f"Matches against each other: {synergy.matches_as_opponents}")
    print(f"Head-to-head: {synergy.player1_wins_vs_player2}-"
          f"{synergy.matches_as_opponents - synergy.player1_wins_vs_player2}")
```

## Troubleshooting

### Problem: "No module named 'winter_dragon'"

**Solution**: Ensure you're in the project root and Python can find the module:
```bash
cd c:\Users\marti\Documents\GitHub\Winter-Dragon-Bot
set PYTHONPATH=%cd%\src
python -m winter_dragon.bot.extensions.tournament.test_matchmaking
```

### Problem: Database tables don't exist

**Solution**: Create tables manually:
```python
from sqlmodel import SQLModel
from winter_dragon.database.constants import engine

SQLModel.metadata.create_all(engine)
```

### Problem: Teams are unbalanced

**Cause**: Not enough match history

**Solution**: 
- Record at least 10-20 matches per player
- Initial matches are random until system learns player skills
- Synergy data requires 5+ matches between player pairs

### Problem: "Game not found"

**Solution**: Create the game first:
```python
from winter_dragon.database.tables.game import Games
game = Games.fetch_game_by_name("Your Game Name")
# This creates the game if it doesn't exist
```

## Next Steps

1. **Read Full Documentation**: See `MATCHMAKING_README.md` for comprehensive details
2. **Check Quick Reference**: See `QUICK_REFERENCE.md` for code snippets
3. **Review Architecture**: See `ARCHITECTURE.md` for system design
4. **Run Tests**: Execute `test_matchmaking.py` regularly to verify system health

## Configuration Tips

### For More Competitive Balance

In `matchmaking.py`, line ~367:

```python
def _evaluate_team_balance(
    self,
    teams: list[TeamCandidate],
    synergy_map: dict[tuple[int, int], float],
    skill_weight: float = 2.0,     # Increase from 1.0
    synergy_weight: float = 0.8,   # Increase from 0.5
) -> float:
```

### For Faster Skill Rating Changes

In `matchmaking.py`, line ~530:

```python
# Update skill rating (simple ELO-like adjustment)
k_factor = 48  # Increase from 32 for faster changes
```

### For Better Large-Group Results

In `matchmaking.py`, line ~330:

```python
def _iterative_team_search(
    self,
    profiles: list[PlayerProfile],
    team_size: int,
    num_teams: int,
    synergy_map: dict[tuple[int, int], float],
    iterations: int = 2000,  # Increase from 1000
) -> list[TeamCandidate]:
```

## Support

For questions or issues:
1. Check the documentation files in this directory
2. Run `verify_data_integrity()` to check for database issues
3. Review the test output for errors
4. Check the Discord bot logs for integration issues

---

**You're ready to go! Start by running the test suite to verify everything works.**

```bash
python src\winter_dragon\bot\extensions\tournament\test_matchmaking.py
```

Good luck with your matchmaking system! 🎮
