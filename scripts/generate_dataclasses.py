#!/usr/bin/env python3
"""Generate Python dataclasses from an existing database schema.

This script connects to a PostgreSQL database and generates Python dataclasses
that represent only the columns of each table. The dataclasses use appropriate
type hints based on the column data types.

Usage:
    python generate_dataclasses.py [--output OUTPUT_DIR] [--package PACKAGE_NAME]

Environment Variables:
    DATABASE_URL: PostgreSQL connection string (postgres://user:pass@host:port/dbname)
                  Falls back to postgres://postgres@localhost/postgres
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2 import sql


# Type mapping from PostgreSQL types to Python types
PG_TO_PYTHON_TYPE_MAP = {
    # Numeric types
    "smallint": "int",
    "integer": "int",
    "bigint": "int",
    "decimal": "float",
    "numeric": "float",
    "real": "float",
    "double precision": "float",
    "smallserial": "int",
    "serial": "int",
    "bigserial": "int",
    # Boolean
    "boolean": "bool",
    # String types
    "character varying": "str",
    "varchar": "str",
    "character": "str",
    "char": "str",
    "text": "str",
    # Date/Time types
    "date": "datetime.date",
    "time without time zone": "datetime.time",
    "time with time zone": "datetime.time",
    "timestamp without time zone": "datetime.datetime",
    "timestamp with time zone": "datetime.datetime",
    "interval": "datetime.timedelta",
    # UUID
    "uuid": "str",
    # JSON
    "json": "dict[str, Any]",
    "jsonb": "dict[str, Any]",
    # Binary
    "bytea": "bytes",
}


@dataclass
class Column:
    """Represents a database column."""

    name: str
    pg_type: str
    python_type: str
    nullable: bool
    default: str | None = None

    @classmethod
    def from_row(cls, row: tuple) -> "Column":
        """Create a Column from a database query row."""
        column_name, data_type, is_nullable, column_default = row
        python_type = PG_TO_PYTHON_TYPE_MAP.get(data_type, "Any")

        if is_nullable == "YES":
            python_type = f"{python_type} | None"

        return cls(
            name=column_name,
            pg_type=data_type,
            python_type=python_type,
            nullable=is_nullable == "YES",
            default=column_default,
        )


class SchemaInspector:
    """Inspect PostgreSQL schema and extract table information."""

    def __init__(self, connection_string: str):
        """Initialize the inspector with a database connection string."""
        self.connection_string = connection_string
        self.conn = None
        self.cursor = None

    def connect(self) -> None:
        """Connect to the database."""
        try:
            self.conn = psycopg2.connect(self.connection_string)
            self.cursor = self.conn.cursor()
        except psycopg2.Error as e:
            print(f"Error connecting to database: {e}", file=sys.stderr)
            sys.exit(1)

    def disconnect(self) -> None:
        """Disconnect from the database."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def get_tables(self, schema: str = "public") -> list[str]:
        """Get all table names from the specified schema."""
        query = sql.SQL(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        )
        self.cursor.execute(query, (schema,))
        return [row[0] for row in self.cursor.fetchall()]

    def get_columns(self, table_name: str, schema: str = "public") -> list[Column]:
        """Get all columns from a table."""
        query = sql.SQL(
            """
            SELECT
                column_name,
                udt_name,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """
        )
        self.cursor.execute(query, (schema, table_name))
        return [Column.from_row(row) for row in self.cursor.fetchall()]


def generate_dataclass_code(table_name: str, columns: list[Column]) -> str:
    """Generate a dataclass definition for a table.

    Args:
        table_name: Name of the table
        columns: List of Column objects

    Returns:
        Generated Python dataclass code
    """
    # Convert table name to PascalCase
    class_name = "".join(word.capitalize() for word in table_name.split("_"))

    lines = ["@dataclass", f"class {class_name}:"]
    lines.append('    """Auto-generated dataclass from database schema."""')
    lines.append("")

    for column in columns:
        lines.append(f"    {column.name}: {column.python_type}")

    return "\n".join(lines)


def generate_all_dataclasses(
    inspector: SchemaInspector, schema: str = "public"
) -> str:
    """Generate dataclass definitions for all tables in the schema.

    Args:
        inspector: SchemaInspector instance
        schema: Schema name (default: public)

    Returns:
        Generated Python code with all dataclasses
    """
    tables = inspector.get_tables(schema)

    output_lines = [
        '"""Auto-generated dataclasses from database schema."""',
        "",
        "from dataclasses import dataclass",
        "from datetime import date, datetime, time, timedelta",
        "from typing import Any",
        "",
    ]

    for table_name in tables:
        columns = inspector.get_columns(table_name, schema)
        if columns:
            output_lines.append(generate_dataclass_code(table_name, columns))
            output_lines.append("")

    return "\n".join(output_lines)


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate Python dataclasses from PostgreSQL schema"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("generated_dataclasses.py"),
        help="Output file path (default: generated_dataclasses.py)",
    )
    parser.add_argument(
        "--schema",
        "-s",
        default="public",
        help="Database schema name (default: public)",
    )
    parser.add_argument(
        "--connection",
        "-c",
        help="PostgreSQL connection string",
    )

    args = parser.parse_args()

    # Get connection string from arg or environment
    import os

    connection_string = args.connection or os.getenv(
        "DATABASE_URL", "postgres://postgres@localhost/postgres"
    )

    print(f"Connecting to database: {connection_string.split('@')[-1]}")
    inspector = SchemaInspector(connection_string)

    try:
        inspector.connect()
        print(f"Generating dataclasses for schema: {args.schema}")
        code = generate_all_dataclasses(inspector, args.schema)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(code)
        print(f"Successfully generated dataclasses to: {args.output}")

    finally:
        inspector.disconnect()


if __name__ == "__main__":
    main()
