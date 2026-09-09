from fastapi import APIRouter
from sqlalchemy import text

from app.api.dependencies import DB
from app.core.errors import DomainError

router = APIRouter(tags=["Health"])


@router.get("/health/live")
def live():
    return {"status": "ok"}


@router.get("/health/ready")
def ready(db: DB):
    # Check schema and required seeds as well as extension availability.
    version = db.execute(text("SELECT version_num FROM game.alembic_version")).scalar_one()
    db.execute(text("SELECT public.PostGIS_Version()")).scalar_one()
    starter = db.execute(
        text("SELECT count(*) FROM game.cars WHERE is_starter AND enabled")
    ).scalar_one()
    if version != "0002" or starter != 1:
        raise DomainError(503, "database_not_ready")
    return {"status": "ready"}
