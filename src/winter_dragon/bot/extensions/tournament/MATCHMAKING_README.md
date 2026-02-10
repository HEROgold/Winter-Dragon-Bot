# Matchmaking System Documentation

## Overview

This matchmaking system implements a sophisticated algorithm for creating balanced tournament brackets and teams. It uses a 6th Normal Form (6NF) database schema to track detailed player statistics, team compositions, and player interactions.

## Database Schema

The system uses 6 main tables in 6NF:

### 1. `game_match`
Stores core information about completed matches.
- `game_id`: Reference to the game being played
- `match_date`: When the match occurred
- `duration_seconds`: Match duration
- `winning_team_id`: Which team won
- `bracket_format`: Format (e.g., "2v2", "3v3", "ffa")

### 2. `match_player`
Records individual player participation in matches.
- `match_id`: Reference to the match
- `user_id`: Player who participated
- `team_number`: Which team (1, 2, etc.)
- `individual_score`: Player's score in this match
- `won`: Whether the player won

### 3. `match_team`
Stores team-level statistics for matches.
- `match_id`: Reference to the match
- `team_number`: Team identifier
- `team_score`: Total team score
- `won`: Whether the team won

### 4. `player_game_stats`
Aggregated player statistics per game (computed from match history).
- `user_id`: Player reference
- `game_id`: Game reference
- `total_matches`: Number of matches played
- `total_wins/losses`: Win/loss counts
- `win_rate`: Computed win percentage
- `avg_score`: Average individual score
- `skill_rating`: ELO-like rating (starts at 1000)

### 5. `player_synergy`
Tracks interactions between two players.
- `player1_id`, `player2_id`: Player pair (ordered)
- `game_id`: Game reference
- `matches_as_teammates`: Count of matches together
- `wins_as_teammates`: Wins when teamed together
- `teammate_synergy`: Win rate as teammates
- `matches_as_opponents`: Count of matches against each other
- `player1_wins_vs_player2`: Head-to-head record
- `rivalry_factor`: Win rate in head-to-head

### 6. `team_composition`
Historical record of specific team compositions.
- `player_ids`: Comma-separated sorted user IDs
- `game_id`: Game reference
- `times_played`: How many times this exact team played
- `wins/losses`: Record for this composition
- `win_rate`: Win percentage
- `avg_team_score`: Average score

## Matchmaking Algorithm

### Team Creation Process

The `create_balanced_teams()` method:

1. **Load Player Profiles**: Fetches skill ratings, win rates, and match history
2. **Load Synergy Data**: Retrieves teammate performance history
3. **Generate Candidates**: 
   - Small groups (≤8 players): Exhaustive search of all combinations
   - Large groups (>8 players): Iterative random sampling (1000 iterations)
4. **Evaluate Balance**: Scores each team split based on:
   - Skill variance between teams (lower is better)
   - Synergy penalty (avoids pairing players with high synergy)

### Balance Scoring Formula

```
balance_score = (skill_weight × skill_variance) + (synergy_weight × synergy_penalty)
```

Where:
- `skill_variance`: Sum of squared differences from mean team skill
- `synergy_penalty`: Sum of teammate synergy scores (we penalize high synergy)
- Default weights: `skill_weight=1.0`, `synergy_weight=0.5`

### Skill Rating System

Uses a simplified ELO system:
- Starting rating: 1000
- K-factor: 32
- Updates after each match based on win/loss
- Expected score is currently simplified to 0.5 (can be enhanced)

## Usage Examples

### Basic Setup

```python
from winter_dragon.bot.extensions.tournament.matchmaking import MatchmakingSystem

# Initialize the system
mm = MatchmakingSystem()
```

### Creating Balanced Teams

```python
# Create balanced teams for a 3v3 match
player_ids = [100001, 100002, 100003, 100004, 100005, 100006]
teams = mm.create_balanced_teams(
    game_name="League of Legends",
    player_ids=player_ids,
    bracket_format="3v3",
    avoid_synergy=True,
)

# Result: [[100001, 100003, 100005], [100002, 100004, 100006]]
print(f"Team 1: {teams[0]}")
print(f"Team 2: {teams[1]}")
```

### Recording Match Results

```python
# Record the match outcome
match = mm.record_match_result(
    game_name="League of Legends",
    teams=teams,
    winning_team_idx=0,  # Team 1 won
    bracket_format="3v3",
    individual_scores={
        100001: 250,
        100002: 180,
        100003: 310,
        100004: 220,
        100005: 290,
        100006: 200,
    },
    team_scores=[850, 600],
    duration_seconds=1800,
)
```

### Generating Example Data

```python
# Generate test data for development
mm.generate_example_data(num_players=12, num_matches=100)
```

### Debugging and Verification

```python
# Print player statistics
mm.print_player_stats("League of Legends", limit=10)

# Show synergy data
mm.print_synergy_data("League of Legends", limit=15)

# View match history
mm.print_match_history("League of Legends", limit=10)

# Verify data integrity
integrity = mm.verify_data_integrity()
print(integrity)
```

## Bracket Formats

Supported formats:
- `"1v1"`: One-on-one matches
- `"2v2"`: Two players per team
- `"3v3"`: Three players per team
- `"4v4"`: Four players per team
- `"ffa"`: Free-for-all (each player is their own team)

## Key Features

### 1. Skill-Based Balancing
Teams are balanced based on aggregated skill ratings to ensure competitive matches.

### 2. Synergy Avoidance
The algorithm actively avoids pairing players with high synergy (good win rate together) to increase competitive balance.

### 3. Game-Specific Stats
All statistics are tracked per-game, so players can have different skill levels in different games.

### 4. Historical Learning
The system improves over time as more match data is collected, leading to better balanced teams.

### 5. Scalability
- Exhaustive search for small player counts (perfect solutions)
- Iterative sampling for large player counts (good solutions quickly)

## Data Flow

1. **Match Creation** → `create_balanced_teams()`
   - Loads player profiles and synergy data
   - Generates optimal team splits
   - Returns team assignments

2. **Match Completion** → `record_match_result()`
   - Stores match details in `game_match`
   - Records player participation in `match_player`
   - Records team results in `match_team`
   - Updates aggregated statistics in `player_game_stats`
   - Updates synergy data in `player_synergy`
   - Updates team composition history in `team_composition`

## Performance Considerations

- **Small Groups** (≤8 players): O(n!) complexity but acceptable
- **Large Groups** (>8 players): O(iterations × team_size) = O(1000 × n)
- Database queries use proper indexing on foreign keys
- Synergy lookups use composite indexes on player pairs

## Future Enhancements

Possible improvements:
1. More sophisticated ELO calculation using opponent ratings
2. Role-based matchmaking (e.g., support/carry in MOBAs)
3. Time-based weighting (recent matches count more)
4. Machine learning for predicting match outcomes
5. Constraint-based matchmaking (avoid certain player pairs)
6. MMR (Matchmaking Rating) decay for inactive players
7. Placement matches for new players

## Testing

Run the built-in test suite:

```python
python -m winter_dragon.bot.extensions.tournament.matchmaking
```

This will:
1. Generate 100 example matches with 12 players
2. Display player statistics
3. Show synergy data
4. Print match history
5. Verify data integrity
6. Test the matchmaking algorithm

## Maintenance

### Regenerating Statistics

If statistics become inconsistent:

```python
# TODO: Implement statistics regeneration from match history
# This would recalculate all player_game_stats, player_synergy,
# and team_composition records from the raw match data
```

### Database Migration

All tables should be created automatically through SQLModel. Ensure migrations are run:

```python
from winter_dragon.database.extension.model import models
from sqlmodel import SQLModel
from winter_dragon.database.constants import engine

# Create all tables
SQLModel.metadata.create_all(engine)
```

## Troubleshooting

### Teams seem unbalanced
- Ensure enough match history exists (minimum 10-20 matches per player)
- Check if `avoid_synergy` is set correctly
- Verify skill ratings are being updated properly

### Synergy data not updating
- Confirm matches are being recorded with `record_match_result()`
- Check that player pairs exist in both `match_player` records
- Verify game_id matches in queries

### Performance issues
- Add database indexes on frequently queried columns
- Consider caching player profiles for repeated matchmaking
- Use batch inserts for large data imports

## License

This matchmaking system is part of the Winter Dragon Bot project.
