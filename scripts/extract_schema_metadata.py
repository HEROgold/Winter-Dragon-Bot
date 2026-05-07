#!/usr/bin/env python3
"""Extract database schema metadata and output as JSON.

This script connects to a PostgreSQL database and extracts metadata about tables,
including indices, relationships (foreign keys), primary keys, and constraints.
The metadata is output as structured JSON.

Usage:
    python extract_schema_metadata.py [--output OUTPUT_FILE] [--schema SCHEMA_NAME]

Environment Variables:
    DATABASE_URL: PostgreSQL connection string (postgres://user:pass@host:port/dbname)
                  Falls back to postgres://postgres@localhost/postgres
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import psycopg2
from psycopg2 import sql


@dataclass
class PrimaryKey:
    """Represents a primary key constraint."""

    constraint_name: str
    columns: list[str] = field(default_factory=list)


@dataclass
class ForeignKey:
    """Represents a foreign key relationship."""

    constraint_name: str
    columns: list[str] = field(default_factory=list)
    referenced_table: str = ""
    referenced_columns: list[str] = field(default_factory=list)


@dataclass
class Index:
    """Represents a database index."""

    name: str
    columns: list[str] = field(default_factory=list)
    is_unique: bool = False
    is_primary_key: bool = False


@dataclass
class UniqueConstraint:
    """Represents a unique constraint."""

    constraint_name: str
    columns: list[str] = field(default_factory=list)


@dataclass
class CheckConstraint:
    """Represents a check constraint."""

    constraint_name: str
    definition: str = ""


@dataclass
class TableMetadata:
    """Represents metadata for a single table."""

    name: str
    primary_keys: list[PrimaryKey] = field(default_factory=list)
    foreign_keys: list[ForeignKey] = field(default_factory=list)
    indices: list[Index] = field(default_factory=list)
    unique_constraints: list[UniqueConstraint] = field(default_factory=list)
    check_constraints: list[CheckConstraint] = field(default_factory=list)
    column_count: int = 0
    row_count: int = 0


class SchemaMetadataExtractor:
    """Extract metadata from PostgreSQL schema."""

    def __init__(self, connection_string: str):
        """Initialize the extractor with a database connection string."""
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

    def get_primary_keys(
        self, table_name: str, schema: str = "public"
    ) -> list[PrimaryKey]:
        """Get primary key constraints for a table."""
        query = sql.SQL(
            """
            SELECT
                constraint_name,
                array_agg(column_name ORDER BY ordinal_position)
            FROM information_schema.key_column_usage
            WHERE table_schema = %s
                AND table_name = %s
                AND constraint_name IN (
                    SELECT constraint_name
                    FROM information_schema.table_constraints
                    WHERE constraint_type = 'PRIMARY KEY'
                        AND table_schema = %s
                        AND table_name = %s
                )
            GROUP BY constraint_name
        """
        )
        self.cursor.execute(query, (schema, table_name, schema, table_name))
        return [
            PrimaryKey(constraint_name=row[0], columns=row[1])
            for row in self.cursor.fetchall()
        ]

    def get_foreign_keys(
        self, table_name: str, schema: str = "public"
    ) -> list[ForeignKey]:
        """Get foreign key relationships for a table."""
        query = sql.SQL(
            """
            SELECT
                kcu.constraint_name,
                array_agg(kcu.column_name ORDER BY kcu.ordinal_position),
                ccu.table_name,
                array_agg(ccu.column_name ORDER BY kcu.ordinal_position)
            FROM information_schema.key_column_usage AS kcu
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = kcu.constraint_name
                AND ccu.table_schema = kcu.table_schema
            WHERE kcu.table_schema = %s
                AND kcu.table_name = %s
                AND kcu.constraint_name IN (
                    SELECT constraint_name
                    FROM information_schema.table_constraints
                    WHERE constraint_type = 'FOREIGN KEY'
                        AND table_schema = %s
                        AND table_name = %s
                )
            GROUP BY kcu.constraint_name, ccu.table_name
        """
        )
        self.cursor.execute(query, (schema, table_name, schema, table_name))
        return [
            ForeignKey(
                constraint_name=row[0],
                columns=row[1],
                referenced_table=row[2],
                referenced_columns=row[3],
            )
            for row in self.cursor.fetchall()
        ]

    def get_indices(self, table_name: str, schema: str = "public") -> list[Index]:
        """Get indices for a table."""
        query = sql.SQL(
            """
            SELECT
                i.relname,
                array_agg(a.attname ORDER BY array_position(ix.indkey, a.attnum)),
                ix.indisunique,
                ix.indisprimary
            FROM pg_index ix
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_class t ON t.oid = ix.indrelid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE t.relname = %s AND n.nspname = %s
            GROUP BY i.relname, ix.indisunique, ix.indisprimary
        """
        )
        self.cursor.execute(query, (table_name, schema))
        return [
            Index(name=row[0], columns=row[1], is_unique=row[2], is_primary_key=row[3])
            for row in self.cursor.fetchall()
        ]

    def get_unique_constraints(
        self, table_name: str, schema: str = "public"
    ) -> list[UniqueConstraint]:
        """Get unique constraints for a table."""
        query = sql.SQL(
            """
            SELECT
                constraint_name,
                array_agg(column_name ORDER BY ordinal_position)
            FROM information_schema.key_column_usage
            WHERE table_schema = %s
                AND table_name = %s
                AND constraint_name IN (
                    SELECT constraint_name
                    FROM information_schema.table_constraints
                    WHERE constraint_type = 'UNIQUE'
                        AND table_schema = %s
                        AND table_name = %s
                )
            GROUP BY constraint_name
        """
        )
        self.cursor.execute(query, (schema, table_name, schema, table_name))
        return [
            UniqueConstraint(constraint_name=row[0], columns=row[1])
            for row in self.cursor.fetchall()
        ]

    def get_check_constraints(
        self, table_name: str, schema: str = "public"
    ) -> list[CheckConstraint]:
        """Get check constraints for a table."""
        query = sql.SQL(
            """
            SELECT constraint_name, check_clause
            FROM information_schema.check_constraints
            WHERE table_schema = %s AND table_name = %s
        """
        )
        self.cursor.execute(query, (schema, table_name))
        return [
            CheckConstraint(constraint_name=row[0], definition=row[1])
            for row in self.cursor.fetchall()
        ]

    def get_column_count(self, table_name: str, schema: str = "public") -> int:
        """Get the number of columns in a table."""
        query = sql.SQL(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
        """
        )
        self.cursor.execute(query, (schema, table_name))
        return self.cursor.fetchone()[0]

    def get_row_count(self, table_name: str, schema: str = "public") -> int:
        """Get the number of rows in a table."""
        query = sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
            sql.Identifier(schema), sql.Identifier(table_name)
        )
        try:
            self.cursor.execute(query)
            return self.cursor.fetchone()[0]
        except psycopg2.Error:
            return 0

    def extract_metadata(self, schema: str = "public") -> dict[str, TableMetadata]:
        """Extract metadata for all tables in the schema.

        Args:
            schema: Schema name (default: public)

        Returns:
            Dictionary mapping table names to their metadata
        """
        tables = self.get_tables(schema)
        metadata = {}

        for table_name in tables:
            table_meta = TableMetadata(
                name=table_name,
                primary_keys=self.get_primary_keys(table_name, schema),
                foreign_keys=self.get_foreign_keys(table_name, schema),
                indices=self.get_indices(table_name, schema),
                unique_constraints=self.get_unique_constraints(table_name, schema),
                check_constraints=self.get_check_constraints(table_name, schema),
                column_count=self.get_column_count(table_name, schema),
                row_count=self.get_row_count(table_name, schema),
            )
            metadata[table_name] = table_meta

        return metadata


def dataclass_to_dict(obj: object) -> object:
    """Convert dataclasses to dictionaries recursively."""
    if hasattr(obj, "__dataclass_fields__"):
        return {
            k: dataclass_to_dict(v) for k, v in asdict(obj).items()
        }
    if isinstance(obj, (list, tuple)):
        return [dataclass_to_dict(item) for item in obj]
    return obj


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Extract PostgreSQL schema metadata to JSON"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("schema_metadata.json"),
        help="Output JSON file path (default: schema_metadata.json)",
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
    parser.add_argument(
        "--indent",
        "-i",
        type=int,
        default=2,
        help="JSON indentation level (default: 2)",
    )

    args = parser.parse_args()

    # Get connection string from arg or environment
    import os

    connection_string = args.connection or os.getenv(
        "DATABASE_URL", "postgres://postgres@localhost/postgres"
    )

    print(f"Connecting to database: {connection_string.split('@')[-1]}")
    extractor = SchemaMetadataExtractor(connection_string)

    try:
        extractor.connect()
        print(f"Extracting metadata from schema: {args.schema}")
        metadata = extractor.extract_metadata(args.schema)

        # Convert to dictionaries for JSON serialization
        metadata_dicts = {
            table_name: dataclass_to_dict(meta) for table_name, meta in metadata.items()
        }

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(metadata_dicts, f, indent=args.indent)

        print(f"Successfully extracted metadata to: {args.output}")
        print(f"Total tables processed: {len(metadata)}")

    finally:
        extractor.disconnect()


if __name__ == "__main__":
    main()
