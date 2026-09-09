from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies import DB, Actor
from app.models.entities import Location
from app.schemas.responses import LocationOutput

router = APIRouter(prefix="/v1/locations", tags=["Locations"])


@router.get("", response_model=list[LocationOutput])
def locations(actor: Actor, db: DB):
    return db.scalars(select(Location).order_by(Location.name)).all()
