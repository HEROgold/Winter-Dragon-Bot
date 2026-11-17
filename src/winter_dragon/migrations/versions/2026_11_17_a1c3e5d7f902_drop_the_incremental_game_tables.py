"""Drop the Incremental game's tables.

Revision ID: a1c3e5d7f902
Revises: 3eee35c48567
Create Date: 2026-11-17 22:00:00.000000
"""

import sqlalchemy as sa
from alembic import op


revision: str = "a1c3e5d7f902"
down_revision: str | None = "3eee35c48567"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Apply this revision."""
    op.drop_index("uq_savegenerator_natural_key", table_name="savegenerator")
    op.drop_index(op.f("ix_savegenerator_id"), table_name="savegenerator")
    op.drop_index(
        "idx_savegenerator_alive_only",
        table_name="savegenerator",
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_table("savegenerator")
    op.drop_index("uq_savebalance_natural_key", table_name="savebalance")
    op.drop_index(op.f("ix_savebalance_id"), table_name="savebalance")
    op.drop_index(
        "idx_savebalance_alive_only",
        table_name="savebalance",
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_table("savebalance")
    op.drop_index(
        "idx_incrementalsave_alive_only",
        table_name="incrementalsave",
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_table("incrementalsave")


def downgrade() -> None:
    """Undo this revision."""
    op.create_table(
        "incrementalsave",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_incrementalsave_alive_only",
        "incrementalsave",
        ["id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "savebalance",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("save_id", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["save_id"], ["incrementalsave.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_savebalance_alive_only",
        "savebalance",
        ["id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(op.f("ix_savebalance_id"), "savebalance", ["id"], unique=True)
    op.create_index("uq_savebalance_natural_key", "savebalance", ["save_id", "currency"], unique=True)
    op.create_table(
        "savegenerator",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("save_id", sa.BigInteger(), nullable=False),
        sa.Column("generator", sa.String(), nullable=False),
        sa.Column("owned", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["save_id"], ["incrementalsave.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_savegenerator_alive_only",
        "savegenerator",
        ["id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(op.f("ix_savegenerator_id"), "savegenerator", ["id"], unique=True)
    op.create_index("uq_savegenerator_natural_key", "savegenerator", ["save_id", "generator"], unique=True)
