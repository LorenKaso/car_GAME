"""Internal-only ledger writer. No HTTP route exposes credits or debits."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.errors import DomainError
from app.core.security import utcnow
from app.models.entities import EconomyTransaction


def append_entry(
    db,
    *,
    user_id: UUID,
    kind: str,
    coins_delta: int,
    xp_delta: int,
    reference_type: str,
    reference_id: UUID,
):
    values = dict(
        id=uuid4(),
        user_id=user_id,
        kind=kind,
        coins_delta=coins_delta,
        xp_delta=xp_delta,
        reference_type=reference_type,
        reference_id=reference_id,
        created_at=utcnow(),
    )
    stmt = (
        insert(EconomyTransaction)
        .values(**values)
        .on_conflict_do_nothing(index_elements=["user_id", "reference_type", "reference_id"])
    )
    db.execute(stmt)
    row = db.scalar(
        select(EconomyTransaction).where(
            EconomyTransaction.user_id == user_id,
            EconomyTransaction.reference_type == reference_type,
            EconomyTransaction.reference_id == reference_id,
        )
    )
    if (row.kind, row.coins_delta, row.xp_delta) != (kind, coins_delta, xp_delta):
        raise DomainError(409, "conflicting_economy_reference")
    # PostgreSQL AFTER INSERT trigger updates the projection only for a newly inserted row.
    return row
