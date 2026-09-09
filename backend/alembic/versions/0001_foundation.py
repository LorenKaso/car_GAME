"""Immutable schema, constraints, and least-privilege grants."""

from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute(Path(__file__).with_suffix(".sql").read_text())


def downgrade():
    # This rollback deletes account/economy history. Only use on disposable databases.
    for table in (
        "track_versions",
        "race_zones",
        "locations",
        "rate_limits",
        "outbox_messages",
        "economy_transactions",
        "player_state",
        "level_thresholds",
        "level_curves",
        "user_cars",
        "cars",
        "account_tokens",
        "used_refresh_tokens",
        "sessions",
        "profiles",
        "users",
    ):
        op.execute(f"DROP TABLE game.{table} CASCADE")
    for name in ("apply_ledger_entry", "immutable_ledger", "zero_opening_state"):
        op.execute(f"DROP FUNCTION game.{name}()")
