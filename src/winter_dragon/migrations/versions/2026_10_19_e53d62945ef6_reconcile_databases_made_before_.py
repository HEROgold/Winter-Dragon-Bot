"""Reconcile databases made before migrations with the baseline.

The bot created its tables with ``create_all`` and later added the lifecycle columns with ``ALTER TABLE``, so such a
database differs from the baseline: nullable ``created_at``/``updated_at``, unique indexes on primary keys and a unique
constraint the lifecycle's natural-key index replaced, and the command-sync tables wd-bot stopped using in e2684f3e.
Every step checks first, so on a database the baseline created this revision changes nothing.

Revision ID: e53d62945ef6
Revises: 2a9de84f886e
Create Date: 2026-10-19 20:14:15.909046
"""

import sqlalchemy as sa
from alembic import op


revision: str = "e53d62945ef6"
down_revision: str | None = "2a9de84f886e"
branch_labels: str | None = None
depends_on: str | None = None


LIFECYCLE_TABLES = (
    "autochannel",
    "autochannelhub",
    "autochannelsettings",
    "autoreassignguild",
    "carfuels",
    "commandusage",
    "deletionrequest",
    "departedguild",
    "draftchoice",
    "matchballot",
    "matchvote",
    "peakonline",
    "rememberedrole",
    "reminder",
    "statchannel",
    "steamsale",
    "steamsaleproperties",
    "steamusers",
    "timedreminder",
    "tournament",
    "tournamentmatch",
    "tournamentplayer",
    "tournamentteam",
)
"""Every table of the baseline; each has the lifecycle columns."""

PRIMARY_KEY_INDEXES = (
    "ix_autochannel_id",
    "ix_autochannelhub_id",
    "ix_autochannelsettings_id",
    "ix_peakonline_id",
    "ix_statchannel_id",
    "ix_steamusers_id",
)
"""Unique indexes on the ``id`` of tables keyed by a Discord ID, which the primary key already covers."""

UNUSED_TABLES = ("globalsyncedcommand", "guildsyncedcommand", "commandrecord")
"""wd-bot's former command-sync tables, which the command registry replaced; the synced commands reference the record."""


def upgrade() -> None:
    """Make a pre-migration database match the baseline."""
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    for table in LIFECYCLE_TABLES:
        if table not in existing:
            continue
        for column in ("created_at", "updated_at"):
            op.execute(f"UPDATE {table} SET {column} = now() WHERE {column} IS NULL")  # noqa: S608 - names are constants
            op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} SET NOT NULL")
    for index in PRIMARY_KEY_INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {index}")
    op.execute(
        "ALTER TABLE steamsaleproperties DROP CONSTRAINT IF EXISTS steamsaleproperties_steam_sale_id_property_key",
    )
    for table in UNUSED_TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table}")


def downgrade() -> None:
    """Nothing to undo: the baseline is what this revision brings a database to."""
