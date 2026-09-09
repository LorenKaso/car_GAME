from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.models.entities import Car, LevelThreshold, PlayerState, Profile, User, UserCar
from app.schemas.responses import CurrentUserOutput, OwnedCarOutput, ProfileOutput


def lock_user(db: Session, user_id: UUID):
    return db.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def profile_view(db: Session, user: User):
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    state = db.get(PlayerState, user.id)
    level = db.scalar(
        select(func.max(LevelThreshold.level)).where(
            LevelThreshold.curve_version == state.curve_version,
            LevelThreshold.minimum_xp <= state.xp,
        )
    )
    if level is None:
        raise DomainError(503, "level_configuration_unavailable")
    values = {
        name: getattr(profile, name)
        for name in (
            "id",
            "username",
            "display_name",
            "avatar_reference",
            "country",
            "created_at",
            "updated_at",
        )
    }
    values["updated_at"] = max(profile.updated_at, state.updated_at)
    return ProfileOutput(**values, coins=state.coins, xp=state.xp, level=level)


def current_user_view(db: Session, user: User):
    return CurrentUserOutput(
        id=user.id,
        email=user.email,
        email_verified=user.email_verified_at is not None,
        profile=profile_view(db, user),
    )


def garage_view(db: Session, user_id: UUID, selected_only=False):
    query = (
        select(UserCar, Car).join(Car, Car.id == UserCar.car_id).where(UserCar.user_id == user_id)
    )
    if selected_only:
        query = query.where(UserCar.is_selected.is_(True))
    rows = db.execute(query.order_by(UserCar.created_at, UserCar.id)).all()
    return [
        OwnedCarOutput(
            id=owned.id, is_selected=owned.is_selected, created_at=owned.created_at, car=car
        )
        for owned, car in rows
    ]
