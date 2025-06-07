"""Api endpoints for user data."""
from collections.abc import Sequence

from fastapi import APIRouter, status
from sqlmodel import select
from winter_dragon.bot.extensions.user.reminder import Reminder
from winter_dragon.database import session
from winter_dragon.database.tables.associations.user_roles import UserRoles
from winter_dragon.database.tables.car_fuel import CarFuels
from winter_dragon.database.tables.infractions import Infractions
from winter_dragon.database.tables.message import Messages
from winter_dragon.database.tables.presence import Presence
from winter_dragon.database.tables.role import Roles
from winter_dragon.database.tables.steamuser import SteamUsers
from winter_dragon.database.tables.user import Users


router = APIRouter(prefix="/users/{user_id}", tags=["users"])

@router.get("/")
async def get_user(user_id: int) -> Users:
    """Get user by ID."""
    return Users.fetch(user_id)

@router.get("/messages")
async def get_messages(user_id: int) -> Sequence[Messages]:
    """Get messages send by a user."""
    return session.exec(
        select(Messages).where(Messages.user_id == user_id),
    ).all()

@router.get("/presences")
async def get_presences(user_id: int) -> Sequence[Presence]:
    """Get presences for a user."""
    return session.exec(
        select(Presence).where(Presence.user_id == user_id),
    ).all()

@router.get("/car_fuels")
async def get_car_fuels(user_id: int) -> Sequence[CarFuels]:
    """Get car fuel data for a user."""
    return session.exec(
        select(CarFuels).where(CarFuels.user_id == user_id),
    ).all()

@router.get("/steam")
async def get_steam_user(user_id: int) -> SteamUsers | 404:
    """Check if this user wants to be notified about steam sales."""
    return (
        session.exec(select(SteamUsers).where(SteamUsers.id == user_id)).first()
        or status.HTTP_404_NOT_FOUND
    )

@router.get("/reminders")
async def get_reminders(user_id: int) -> Sequence[Reminder]:
    """Get all reminders for a user."""
    return session.exec(
        select(Reminder).where(Reminder.user_id == user_id),
    ).all()

@router.get("/infractions")
async def get_infractions(user_id: int) -> Infractions | 404:
    """Get infractions for a user."""
    return (session.exec(
        select(Infractions).where(Infractions.user_id == user_id),
    ).first() or status.HTTP_404_NOT_FOUND)

@router.get("/roles")
async def get_roles(user_id: int) -> Sequence[Roles]:
    """Get all roles the user has."""
    return session.exec(
        select(Roles).join(UserRoles).where(UserRoles.user_id == user_id),
    ).all()
