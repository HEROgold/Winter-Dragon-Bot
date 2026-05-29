# Database Schema

## Overview

Winter Dragon uses **PostgreSQL** with **SQLModel** ORM for type-safe database access. The schema is designed to support user data management, GDPR compliance, and game statistics.

## Core Tables

### user_data_deletion

**Purpose**: Audit trail for GDPR-compliant data deletion requests.

```sql
CREATE TABLE user_data_deletion (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL,
    requested_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    reason TEXT,
    FOREIGN KEY (user_id) REFERENCES user(id)
);
```

**Columns**:
- `id` - Unique deletion request identifier
- `user_id` - Discord user ID requesting deletion
- `requested_at` - When deletion was requested
- `completed_at` - When deletion was completed
- `status` - Current status: pending, completed, failed
- `reason` - Optional reason for deletion

### user

**Purpose**: Core user profile and authentication data.

```sql
CREATE TABLE user (
    id BIGINT PRIMARY KEY,
    username VARCHAR(32) NOT NULL,
    discriminator VARCHAR(4),
    avatar_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Columns**:
- `id` - Discord user ID
- `username` - Discord username
- `discriminator` - Discord discriminator (legacy)
- `avatar_url` - User avatar URL
- `created_at` - Account creation time
- `updated_at` - Last update time

### game

**Purpose**: Game session records.

```sql
CREATE TABLE game (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL,
    game_type VARCHAR(50) NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    result VARCHAR(20),
    score INT,
    FOREIGN KEY (user_id) REFERENCES user(id)
);
```

**Columns**:
- `id` - Unique game session identifier
- `user_id` - Player's user ID
- `game_type` - Type of game (chess, trivia, etc.)
- `started_at` - Game start time
- `ended_at` - Game end time
- `result` - Win/Loss/Draw
- `score` - Final score

### incremental.player

**Purpose**: Player statistics and rankings.

```sql
CREATE TABLE incremental.player (
    user_id BIGINT PRIMARY KEY,
    total_games INT DEFAULT 0,
    total_wins INT DEFAULT 0,
    win_rate DECIMAL(5,2),
    highest_score INT,
    last_played TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id)
);
```

**Columns**:
- `user_id` - Player's user ID
- `total_games` - Total games played
- `total_wins` - Total games won
- `win_rate` - Percentage of games won
- `highest_score` - Best score achieved
- `last_played` - Last game timestamp

## Indexes

For optimal query performance:

```sql
-- User queries
CREATE INDEX idx_user_username ON user(username);
CREATE INDEX idx_user_created_at ON user(created_at);

-- Deletion audit trail
CREATE INDEX idx_deletion_user_id ON user_data_deletion(user_id);
CREATE INDEX idx_deletion_requested_at ON user_data_deletion(requested_at);

-- Game history
CREATE INDEX idx_game_user_id ON game(user_id);
CREATE INDEX idx_game_started_at ON game(started_at);

-- Player stats
CREATE INDEX idx_player_win_rate ON incremental.player(win_rate DESC);
```

## Relationships

```
user
├── user_data_deletion (1:N)
│   └── Deletion requests for user
├── game (1:N)
│   └── Games played by user
└── incremental.player (1:1)
    └── Player statistics
```

## Data Integrity Constraints

### Foreign Keys

- `game.user_id` → `user.id`
- `user_data_deletion.user_id` → `user.id`
- `incremental.player.user_id` → `user.id`

### Unique Constraints

- `user.id` - Discord IDs are globally unique
- `incremental.player.user_id` - One stats record per player

## Views for Analytics

### leaderboard

```sql
CREATE VIEW leaderboard AS
SELECT 
    u.id,
    u.username,
    p.total_games,
    p.total_wins,
    p.win_rate,
    p.highest_score,
    ROW_NUMBER() OVER (ORDER BY p.win_rate DESC) as rank
FROM incremental.player p
JOIN user u ON p.user_id = u.id
ORDER BY p.win_rate DESC;
```

### recent_games

```sql
CREATE VIEW recent_games AS
SELECT 
    g.id,
    u.username,
    g.game_type,
    g.started_at,
    g.result,
    g.score
FROM game g
JOIN user u ON g.user_id = u.id
ORDER BY g.started_at DESC
LIMIT 100;
```

## Access Patterns

### Get User Profile

```python
from sqlmodel import Session, select
from src.winter_dragon.database.tables import User

def get_user(session: Session, user_id: int):
    return session.exec(select(User).where(User.id == user_id)).first()
```

### Get Player Statistics

```python
def get_player_stats(session: Session, user_id: int):
    # Returns combined user + player data
    user = session.exec(
        select(User).where(User.id == user_id)
    ).first()
    stats = session.exec(
        select(PlayerStats).where(PlayerStats.user_id == user_id)
    ).first()
    return {**user.dict(), **stats.dict()}
```

### Get Deletion Audit Trail

```python
def get_deletion_audit(session: Session, user_id: int):
    return session.exec(
        select(UserDataDeletion)
        .where(UserDataDeletion.user_id == user_id)
        .order_by(UserDataDeletion.requested_at.desc())
    ).all()
```

### Get Leaderboard

```python
def get_leaderboard(session: Session, limit: int = 10):
    # Query via leaderboard view
    return session.exec(
        "SELECT * FROM leaderboard LIMIT ?",
        [limit]
    ).all()
```

## Backups

### Automated Backups

PostgreSQL container data is persisted in Docker volume `postgres_data`.

### Manual Backup

```bash
# Dump database to file
docker compose exec postgres pg_dump -U postgres winter_dragon > backup.sql

# Restore from dump
cat backup.sql | docker compose exec -T postgres psql -U postgres
```

### Point-in-Time Recovery

Enable WAL (Write-Ahead Logging) for PITR:

```sql
ALTER SYSTEM SET wal_level = replica;
SELECT pg_reload_conf();
```

## Monitoring

### Database Queries

Access via Grafana at http://localhost:3002:
- Query execution time
- Slow query log
- Index usage statistics
- Table size analysis

### Connection Pooling

Monitor via PgAdmin:
1. Navigate to http://localhost:5050
2. Connect to server
3. View active connections and queries

## Optimization Tips

### Query Optimization

1. Use indexes on filtered columns
2. Avoid SELECT * - fetch specific columns
3. Use EXPLAIN to analyze query plans
4. Join strategically to minimize data transfer

### Index Optimization

```bash
# Identify missing indexes
EXPLAIN SELECT * FROM game WHERE user_id = 123;

# Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

### Maintenance

```bash
# Vacuum to reclaim space
VACUUM ANALYZE;

# Reindex tables
REINDEX DATABASE winter_dragon;

# Check for table bloat
SELECT * FROM pg_stat_user_tables
WHERE n_live_tup > 100000;
```

## Related Documentation

- [Architecture](architecture.md) - System design overview
- [Development Setup](setup.md) - Local development guide
- [API Usage](../guide/api-usage.md) - REST API documentation
