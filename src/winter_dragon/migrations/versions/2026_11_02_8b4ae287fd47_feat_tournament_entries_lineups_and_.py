"""feat: tournament entries, lineups and match audit (#429, #430, #431, #432).

Revision ID: 8b4ae287fd47
Revises: 3e73a57c5c77
Create Date: 2026-11-02 19:25:40.598505

Hand-edited: autogenerate dropped the old tables and columns and added new ones. This moves the data instead. Each
tournament team becomes a Team (lasting in a captains tournament, temporary and ended in a solo one) and a tournament
entry with the same ID. Its players become team members and entry players, and players without a team become solo
signups. Every match past WAITING gets a lineup from its entries' players, and the renamed columns keep their values.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "8b4ae287fd47"
down_revision: str | None = "3e73a57c5c77"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Apply this revision."""
    op.create_table(
        "entryplayer",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_entryplayer_alive_only",
        "entryplayer",
        ["id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(op.f("ix_entryplayer_entry_id"), "entryplayer", ["entry_id"], unique=False)
    op.create_index(op.f("ix_entryplayer_id"), "entryplayer", ["id"], unique=True)
    op.create_index("uq_entryplayer_natural_key", "entryplayer", ["entry_id", "user_id"], unique=True)
    op.create_table(
        "lineupchange",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("playing", sa.Boolean(), nullable=False),
        sa.Column("changed_by", sa.BigInteger(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_lineupchange_alive_only",
        "lineupchange",
        ["id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(op.f("ix_lineupchange_entry_id"), "lineupchange", ["entry_id"], unique=False)
    op.create_index(op.f("ix_lineupchange_id"), "lineupchange", ["id"], unique=True)
    op.create_table(
        "matchevent",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "PHASE",
                "DRAFT",
                "VOTE_OPENED",
                "VOTE_CLOSED",
                "WINNER",
                "FORFEIT",
                "CLASH_DROPPED",
                name="matcheventkind",
            ),
            nullable=False,
        ),
        sa.Column("actor_id", sa.BigInteger(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detail", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_matchevent_alive_only",
        "matchevent",
        ["id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(op.f("ix_matchevent_id"), "matchevent", ["id"], unique=True)
    op.create_index(op.f("ix_matchevent_match_id"), "matchevent", ["match_id"], unique=False)
    op.create_table(
        "matchlineup",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_matchlineup_alive_only",
        "matchlineup",
        ["id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(op.f("ix_matchlineup_entry_id"), "matchlineup", ["entry_id"], unique=False)
    op.create_index(op.f("ix_matchlineup_id"), "matchlineup", ["id"], unique=True)
    op.create_index(op.f("ix_matchlineup_match_id"), "matchlineup", ["match_id"], unique=False)
    op.create_table(
        "tournamententry",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_tournamententry_alive_only",
        "tournamententry",
        ["id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(op.f("ix_tournamententry_id"), "tournamententry", ["id"], unique=True)
    op.create_index(op.f("ix_tournamententry_team_id"), "tournamententry", ["team_id"], unique=False)
    op.create_index(op.f("ix_tournamententry_tournament_id"), "tournamententry", ["tournament_id"], unique=False)
    op.create_table(
        "tournamentsignup",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_tournamentsignup_alive_only",
        "tournamentsignup",
        ["id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(op.f("ix_tournamentsignup_id"), "tournamentsignup", ["id"], unique=True)
    op.create_index(op.f("ix_tournamentsignup_tournament_id"), "tournamentsignup", ["tournament_id"], unique=False)
    op.create_index("uq_tournamentsignup_natural_key", "tournamentsignup", ["tournament_id", "user_id"], unique=True)
    op.add_column("draftchoice", sa.Column("entry_id", sa.Integer(), nullable=True))
    op.add_column("tournament", sa.Column("winner_entry_id", sa.Integer(), nullable=True))
    op.add_column("tournamentmatch", sa.Column("entry_a_id", sa.Integer(), nullable=True))
    op.add_column("tournamentmatch", sa.Column("entry_b_id", sa.Integer(), nullable=True))
    op.add_column("tournamentmatch", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tournamentmatch", sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tournamentmatch", sa.Column("decided_by", sa.BigInteger(), nullable=True))
    # An entry keeps its tournament team's ID, so every column that pointed at a team now points at its entry.
    op.execute("UPDATE draftchoice SET entry_id = team_id")
    op.execute("UPDATE tournament SET winner_entry_id = winner_team_id")
    op.execute("UPDATE tournamentmatch SET entry_a_id = team_a_id, entry_b_id = team_b_id")
    _move_teams_and_players()
    op.alter_column("draftchoice", "entry_id", nullable=False)
    op.drop_column("draftchoice", "team_id")
    op.drop_column("tournament", "winner_team_id")
    op.drop_column("tournamentmatch", "team_a_id")
    op.drop_column("tournamentmatch", "team_b_id")
    op.drop_index(
        op.f("idx_tournamentplayer_alive_only"),
        table_name="tournamentplayer",
        postgresql_where="(deleted_at IS NULL)",
    )
    op.drop_index(op.f("ix_tournamentplayer_id"), table_name="tournamentplayer")
    op.drop_index(op.f("ix_tournamentplayer_tournament_id"), table_name="tournamentplayer")
    op.drop_index(op.f("uq_tournamentplayer_natural_key"), table_name="tournamentplayer")
    op.drop_table("tournamentplayer")
    op.drop_index(op.f("idx_tournamentteam_alive_only"), table_name="tournamentteam", postgresql_where="(deleted_at IS NULL)")
    op.drop_index(op.f("ix_tournamentteam_id"), table_name="tournamentteam")
    op.drop_index(op.f("ix_tournamentteam_tournament_id"), table_name="tournamentteam")
    op.drop_table("tournamentteam")


def _move_teams_and_players() -> None:
    """Turn each tournament team into a Team and an entry, its players into members and entry players; copy lineups."""
    bind = op.get_bind()
    teams = bind.execute(
        sa.text(
            "SELECT tt.id, tt.tournament_id, tt.name, tt.captain_id, tt.created_at, tt.updated_at, tt.deleted_at, t.mode "
            "FROM tournamentteam tt JOIN tournament t ON t.id = tt.tournament_id",
        ),
    ).all()
    for old in teams:
        lasting = old.mode == "CAPTAINS"
        team_id = bind.execute(
            sa.text(
                "INSERT INTO team (created_at, updated_at, deleted_at, name, kind, origin, captain_id, ended_at) "
                "VALUES (:created, :updated, :deleted, :name, :kind, :origin, :captain, :ended) RETURNING id",
            ),
            {
                "created": old.created_at,
                "updated": old.updated_at,
                "deleted": old.deleted_at,
                "name": old.name,
                "kind": "LASTING" if lasting else "TEMPORARY",
                "origin": "CREATED" if lasting else "SOLO_TOURNAMENT",
                "captain": old.captain_id,
                "ended": None if lasting else old.updated_at,
            },
        ).scalar_one()
        bind.execute(
            sa.text(
                "INSERT INTO tournamententry (id, created_at, updated_at, deleted_at, tournament_id, team_id, name) "
                "VALUES (:id, :created, :updated, :deleted, :tournament, :team, :name)",
            ),
            {
                "id": old.id,
                "created": old.created_at,
                "updated": old.updated_at,
                "deleted": old.deleted_at,
                "tournament": old.tournament_id,
                "team": team_id,
                "name": old.name,
            },
        )
        players = bind.execute(
            sa.text("SELECT user_id, created_at, updated_at, deleted_at FROM tournamentplayer WHERE team_id = :team"),
            {"team": old.id},
        ).all()
        for player in players:
            values = {
                "team": team_id,
                "entry": old.id,
                "user": player.user_id,
                "created": player.created_at,
                "updated": player.updated_at,
                "deleted": player.deleted_at,
            }
            bind.execute(
                sa.text(
                    "INSERT INTO teammember (created_at, updated_at, deleted_at, team_id, user_id, joined_at) "
                    "VALUES (:created, :updated, :deleted, :team, :user, :created)",
                ),
                values,
            )
            bind.execute(
                sa.text(
                    "INSERT INTO entryplayer (created_at, updated_at, deleted_at, entry_id, user_id) "
                    "VALUES (:created, :updated, :deleted, :entry, :user)",
                ),
                values,
            )
    op.execute(
        "INSERT INTO tournamentsignup (created_at, updated_at, deleted_at, tournament_id, user_id) "
        "SELECT created_at, updated_at, deleted_at, tournament_id, user_id FROM tournamentplayer WHERE team_id IS NULL",
    )
    op.execute(
        "INSERT INTO matchlineup (created_at, updated_at, deleted_at, match_id, entry_id, user_id) "
        "SELECT m.created_at, m.updated_at, NULL, m.id, ep.entry_id, ep.user_id FROM tournamentmatch m "
        "JOIN entryplayer ep ON ep.entry_id IN (m.entry_a_id, m.entry_b_id) AND ep.deleted_at IS NULL "
        "WHERE m.phase <> 'WAITING' AND m.deleted_at IS NULL",
    )
    _resume_sequence(bind, "tournamententry")


RESUME_SEQUENCE = {
    table: f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM {table}"  # noqa: S608 - table names are the constants below, not input
    for table in ("tournamententry", "tournamentteam")
}
"""Per table this revision inserts IDs into by hand, the statement moving its ID sequence past them."""


def _resume_sequence(bind: sa.engine.Connection, table: str) -> None:
    """Move ``table``'s ID sequence past the IDs inserted by hand, on PostgreSQL; sqlite needs nothing."""
    if bind.dialect.name == "postgresql":
        op.execute(RESUME_SEQUENCE[table])


def downgrade() -> None:
    """Undo this revision, moving entries back into tournament teams; the Teams made by the upgrade stay."""
    op.create_table(
        "tournamentteam",
        sa.Column("id", sa.BIGINT(), autoincrement=True, nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
        sa.Column("tournament_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("captain_id", sa.BIGINT(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("tournamentteam_pkey")),
    )
    op.create_index(op.f("ix_tournamentteam_tournament_id"), "tournamentteam", ["tournament_id"], unique=False)
    op.create_index(op.f("ix_tournamentteam_id"), "tournamentteam", ["id"], unique=True)
    op.create_index(
        op.f("idx_tournamentteam_alive_only"),
        "tournamentteam",
        ["id"],
        unique=False,
        postgresql_where="(deleted_at IS NULL)",
    )
    op.create_table(
        "tournamentplayer",
        sa.Column("id", sa.BIGINT(), autoincrement=True, nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
        sa.Column("tournament_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("user_id", sa.BIGINT(), autoincrement=False, nullable=False),
        sa.Column("team_id", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("tournamentplayer_pkey")),
    )
    op.create_index(op.f("uq_tournamentplayer_natural_key"), "tournamentplayer", ["tournament_id", "user_id"], unique=True)
    op.create_index(op.f("ix_tournamentplayer_tournament_id"), "tournamentplayer", ["tournament_id"], unique=False)
    op.create_index(op.f("ix_tournamentplayer_id"), "tournamentplayer", ["id"], unique=True)
    op.create_index(
        op.f("idx_tournamentplayer_alive_only"),
        "tournamentplayer",
        ["id"],
        unique=False,
        postgresql_where="(deleted_at IS NULL)",
    )
    op.add_column("draftchoice", sa.Column("team_id", sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column("tournament", sa.Column("winner_team_id", sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column("tournamentmatch", sa.Column("team_a_id", sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column("tournamentmatch", sa.Column("team_b_id", sa.INTEGER(), autoincrement=False, nullable=True))
    op.execute(
        "INSERT INTO tournamentteam (id, created_at, updated_at, deleted_at, tournament_id, name, captain_id) "
        "SELECT e.id, e.created_at, e.updated_at, e.deleted_at, e.tournament_id, e.name, COALESCE(t.captain_id, 0) "
        "FROM tournamententry e JOIN team t ON t.id = e.team_id",
    )
    # A member may play for several entries now, but was in one team per tournament before: keep the first entry.
    op.execute(
        "INSERT INTO tournamentplayer (created_at, updated_at, deleted_at, tournament_id, user_id, team_id) "
        "SELECT MIN(ep.created_at), MAX(ep.updated_at), NULL, e.tournament_id, ep.user_id, MIN(e.id) "
        "FROM entryplayer ep JOIN tournamententry e ON e.id = ep.entry_id WHERE ep.deleted_at IS NULL "
        "GROUP BY e.tournament_id, ep.user_id",
    )
    op.execute(
        "INSERT INTO tournamentplayer (created_at, updated_at, deleted_at, tournament_id, user_id, team_id) "
        "SELECT created_at, updated_at, deleted_at, tournament_id, user_id, NULL FROM tournamentsignup",
    )
    op.execute("UPDATE draftchoice SET team_id = entry_id")
    op.execute("UPDATE tournament SET winner_team_id = winner_entry_id")
    op.execute("UPDATE tournamentmatch SET team_a_id = entry_a_id, team_b_id = entry_b_id")
    _resume_sequence(op.get_bind(), "tournamentteam")
    op.alter_column("draftchoice", "team_id", nullable=False)
    op.drop_column("tournamentmatch", "decided_by")
    op.drop_column("tournamentmatch", "decided_at")
    op.drop_column("tournamentmatch", "started_at")
    op.drop_column("tournamentmatch", "entry_b_id")
    op.drop_column("tournamentmatch", "entry_a_id")
    op.drop_column("tournament", "winner_entry_id")
    op.drop_column("draftchoice", "entry_id")
    op.drop_index("uq_tournamentsignup_natural_key", table_name="tournamentsignup")
    op.drop_index(op.f("ix_tournamentsignup_tournament_id"), table_name="tournamentsignup")
    op.drop_index(op.f("ix_tournamentsignup_id"), table_name="tournamentsignup")
    op.drop_index(
        "idx_tournamentsignup_alive_only",
        table_name="tournamentsignup",
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_table("tournamentsignup")
    op.drop_index(op.f("ix_tournamententry_tournament_id"), table_name="tournamententry")
    op.drop_index(op.f("ix_tournamententry_team_id"), table_name="tournamententry")
    op.drop_index(op.f("ix_tournamententry_id"), table_name="tournamententry")
    op.drop_index(
        "idx_tournamententry_alive_only",
        table_name="tournamententry",
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_table("tournamententry")
    op.drop_index(op.f("ix_matchlineup_match_id"), table_name="matchlineup")
    op.drop_index(op.f("ix_matchlineup_id"), table_name="matchlineup")
    op.drop_index(op.f("ix_matchlineup_entry_id"), table_name="matchlineup")
    op.drop_index(
        "idx_matchlineup_alive_only",
        table_name="matchlineup",
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_table("matchlineup")
    op.drop_index(op.f("ix_matchevent_match_id"), table_name="matchevent")
    op.drop_index(op.f("ix_matchevent_id"), table_name="matchevent")
    op.drop_index(
        "idx_matchevent_alive_only",
        table_name="matchevent",
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_table("matchevent")
    op.drop_index(op.f("ix_lineupchange_id"), table_name="lineupchange")
    op.drop_index(op.f("ix_lineupchange_entry_id"), table_name="lineupchange")
    op.drop_index(
        "idx_lineupchange_alive_only",
        table_name="lineupchange",
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_table("lineupchange")
    op.drop_index("uq_entryplayer_natural_key", table_name="entryplayer")
    op.drop_index(op.f("ix_entryplayer_id"), table_name="entryplayer")
    op.drop_index(op.f("ix_entryplayer_entry_id"), table_name="entryplayer")
    op.drop_index(
        "idx_entryplayer_alive_only",
        table_name="entryplayer",
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_table("entryplayer")
    sa.Enum(name="matcheventkind").drop(op.get_bind(), checkfirst=True)
