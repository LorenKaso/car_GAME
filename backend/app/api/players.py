from fastapi import APIRouter

from app.api.dependencies import DB, Actor
from app.core.errors import DomainError
from app.repositories.players import current_user_view, garage_view, profile_view
from app.schemas.requests import SelectCarRequest
from app.schemas.responses import CurrentUserOutput, OwnedCarOutput, ProfileOutput
from app.services.garage import select_owned_car

router = APIRouter(prefix="/v1/me", tags=["Player"])


@router.get("", response_model=CurrentUserOutput)
def me(actor: Actor, db: DB):
    return current_user_view(db, actor.user)


@router.get("/profile", response_model=ProfileOutput)
def profile(actor: Actor, db: DB):
    return profile_view(db, actor.user)


@router.get("/garage", response_model=list[OwnedCarOutput])
def garage(actor: Actor, db: DB):
    return garage_view(db, actor.user.id)


@router.get("/garage/selected", response_model=OwnedCarOutput)
def selected(actor: Actor, db: DB):
    cars = garage_view(db, actor.user.id, selected_only=True)
    if not cars:
        raise DomainError(404, "selected_car_not_found")
    return cars[0]


@router.post("/garage/select", response_model=OwnedCarOutput)
def select_car(data: SelectCarRequest, actor: Actor, db: DB):
    return select_owned_car(db, actor.user.id, data.user_car_id)
