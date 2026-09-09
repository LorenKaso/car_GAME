from sqlalchemy import select, update

from app.core.errors import DomainError
from app.models.entities import Car, UserCar
from app.repositories.players import garage_view, lock_user


def select_owned_car(db, user_id, user_car_id):
    lock_user(db, user_id)
    owned = db.scalar(
        select(UserCar)
        .join(Car, Car.id == UserCar.car_id)
        .where(UserCar.id == user_car_id, UserCar.user_id == user_id, Car.enabled.is_(True))
    )
    if owned is None:
        raise DomainError(404, "owned_car_not_found")
    # Two statements deliberately avoid transient unique-index conflicts when swapping.
    db.execute(
        update(UserCar)
        .where(UserCar.user_id == user_id, UserCar.is_selected.is_(True))
        .values(is_selected=False)
    )
    db.execute(
        update(UserCar)
        .where(UserCar.id == owned.id, UserCar.user_id == user_id)
        .values(is_selected=True)
    )
    db.commit()
    return garage_view(db, user_id, selected_only=True)[0]
