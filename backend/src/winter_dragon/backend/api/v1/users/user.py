"""Api endpoints for user data."""
from collections.abc import Sequence

from fastapi import APIRouter, status
from sqlmodel import select
from winter_dragon.database import session
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.associations.user_roles import UserRoles
from winter_dragon.database.tables.car_fuel import CarFuels
from winter_dragon.database.tables.infractions import Infractions
from winter_dragon.database.tables.message import Messages
from winter_dragon.database.tables.presence import Presence
from winter_dragon.database.tables.reminder import Reminder
from winter_dragon.database.tables.role import Roles
from winter_dragon.database.tables.steamuser import SteamUsers
from winter_dragon.database.tables.user import Users


model = APIModel(Users)
router = model.router

sub_router = APIRouter(prefix="/{id_:int}")
router.include_router(sub_router)

@sub_router.get("/messages")
async def get_messages(id_: int) -> Sequence[Messages]:
    """Get messages send by a user."""
    return session.exec(
        select(Messages).where(Messages.user_id == id_),
    ).all()

@sub_router.get("/presences")
async def get_presences(id_: int) -> Sequence[Presence]:
    """Get presences for a user."""
    return session.exec(
        select(Presence).where(Presence.user_id == id_),
    ).all()

@sub_router.get("/car_fuels")
async def get_car_fuels(id_: int) -> Sequence[CarFuels]:
    """Get car fuel data for a user."""
    return session.exec(
        select(CarFuels).where(CarFuels.user_id == id_),
    ).all()

@sub_router.get("/steam")
async def get_steam_user(id_: int) -> SteamUsers | 404:
    """Check if this user wants to be notified about steam sales."""
    return (
        session.exec(select(SteamUsers).where(SteamUsers.user_id == id_)).first()
        or status.HTTP_404_NOT_FOUND
    )

@sub_router.get("/reminders")
async def get_reminders(id_: int) -> Sequence[Reminder]:
    """Get all reminders for a user."""
    return session.exec(
        select(Reminder).where(Reminder.user_id == id_),
    ).all()

@sub_router.get("/infractions")
async def get_infractions(id_: int) -> Infractions | 404:
    """Get infractions for a user."""
    return (session.exec(
        select(Infractions).where(Infractions.user_id == id_),
    ).first() or status.HTTP_404_NOT_FOUND)

@sub_router.get("/roles")
async def get_roles(id_: int) -> Sequence[Roles]:
    """Get all roles the user has."""
    return session.exec(
        select(Roles).join(UserRoles).where(UserRoles.user_id == id_),
    ).all()
