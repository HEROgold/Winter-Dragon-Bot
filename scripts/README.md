# Database Schema Scripts

This directory contains utility scripts for working with PostgreSQL database schemas.

## Scripts

### 1. `generate_dataclasses.py`
Generates Python dataclasses from an existing PostgreSQL database schema. The dataclasses represent only the column definitions with appropriate type hints.

**Usage:**
```bash
python scripts/generate_dataclasses.py [OPTIONS]
```

**Options:**
- `--output, -o OUTPUT_FILE`: Output file path (default: `generated_dataclasses.py`)
- `--schema, -s SCHEMA_NAME`: Database schema name (default: `public`)
- `--connection, -c CONNECTION_STRING`: PostgreSQL connection string

**Environment Variables:**
- `DATABASE_URL`: PostgreSQL connection string (e.g., `postgres://user:pass@host:port/dbname`)
  - Falls back to `postgres://postgres@localhost/postgres` if not set

**Example:**
```bash
# Using environment variable
export DATABASE_URL="postgres://user:password@localhost/mydb"
python scripts/generate_dataclasses.py --output dataclasses.py --schema public

# Using connection argument
python scripts/generate_dataclasses.py \
  --connection "postgres://user:password@localhost/mydb" \
  --output generated/models.py \
  --schema public
```

**Output:**
Generates a Python file with dataclasses like:
```python
@dataclass
class Users:
    """Auto-generated dataclass from database schema."""
    id: int
    username: str
    email: str | None
    created_at: datetime.datetime
```

### 2. `extract_schema_metadata.py`
Extracts comprehensive database schema metadata including indices, relationships, constraints, and outputs it as JSON.

**Usage:**
```bash
python scripts/extract_schema_metadata.py [OPTIONS]
```

**Options:**
- `--output, -o OUTPUT_FILE`: Output JSON file path (default: `schema_metadata.json`)
- `--schema, -s SCHEMA_NAME`: Database schema name (default: `public`)
- `--connection, -c CONNECTION_STRING`: PostgreSQL connection string
- `--indent, -i INDENT_LEVEL`: JSON indentation level (default: 2)

**Environment Variables:**
- `DATABASE_URL`: PostgreSQL connection string

**Example:**
```bash
# Using environment variable
export DATABASE_URL="postgres://user:password@localhost/mydb"
python scripts/extract_schema_metadata.py --output metadata.json --schema public

# Using connection argument
python scripts/extract_schema_metadata.py \
  --connection "postgres://user:password@localhost/mydb" \
  --output generated/metadata.json \
  --schema public \
  --indent 4
```

**Output:**
Generates a JSON file with structure like:
```json
{
  "users": {
    "name": "users",
    "primary_keys": [
      {
        "constraint_name": "users_pkey",
        "columns": ["id"]
      }
    ],
    "foreign_keys": [
      {
        "constraint_name": "users_guild_fk",
        "columns": ["guild_id"],
        "referenced_table": "guilds",
        "referenced_columns": ["id"]
      }
    ],
    "indices": [
      {
        "name": "users_username_idx",
        "columns": ["username"],
        "is_unique": true,
        "is_primary_key": false
      }
    ],
    "unique_constraints": [
      {
        "constraint_name": "users_email_unique",
        "columns": ["email"]
      }
    ],
    "check_constraints": [],
    "column_count": 5,
    "row_count": 1250
  }
}
```

## Requirements

Both scripts require:
- Python 3.13+
- `psycopg2-binary` (already in project dependencies)

## Integration with Winter Dragon Bot

These scripts work with the Winter Dragon Bot's existing PostgreSQL setup. The `DATABASE_URL` environment variable can be set from your `.env` file or Docker environment configuration.

### Docker Usage
If running in Docker, ensure the PostgreSQL service is running and accessible:
```bash
docker-compose exec bot python scripts/generate_dataclasses.py
docker-compose exec bot python scripts/extract_schema_metadata.py --output=/data/metadata.json
```

## Type Mapping

The `generate_dataclasses.py` script maps PostgreSQL types to Python types as follows:

| PostgreSQL Type | Python Type |
|---|---|
| `smallint`, `integer`, `bigint` | `int` |
| `decimal`, `numeric`, `real`, `double precision` | `float` |
| `boolean` | `bool` |
| `character varying`, `varchar`, `text` | `str` |
| `date` | `datetime.date` |
| `time` | `datetime.time` |
| `timestamp` | `datetime.datetime` |
| `interval` | `datetime.timedelta` |
| `uuid` | `str` |
| `json`, `jsonb` | `dict[str, Any]` |
| `bytea` | `bytes` |

## Notes

- Both scripts work with any PostgreSQL database and are not limited to the Winter Dragon Bot
- The scripts respect the database schema and will only process tables in the specified schema (default: `public`)
- Foreign keys are resolved to their referenced tables and columns
- Row counts are estimated for large tables but accurate for smaller ones
- All constraint names and column names are preserved as-is from the database
