
from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from fastapi_users import BaseUserManager

from database.tables.users import FastApiUser, get_user_db
from website.settings import Settings


settings = Settings()
SECRET = settings.SECRET_KEY


class UserManager(BaseUserManager[FastApiUser, int]):
    # reset_password_token_secret
    # reset_password_token_lifetime_seconds
    # reset_password_token_audience
    # verification_token_secret
    # verification_token_lifetime_seconds
    # verification_token_audience
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: FastApiUser, request: Request | None = None) -> None:  # noqa: ARG002
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(self, user: FastApiUser, token: str, request: Request | None = None) -> None:  # noqa: ARG002
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(self, user: FastApiUser, token: str, request: Request | None = None) -> None:  # noqa: ARG002
        print(f"Verification requested for user {user.id}. Verification token: {token}")


async def get_user_manager(user_db=Depends(get_user_db)) -> AsyncGenerator[UserManager, None]:  # noqa: ANN001, B008
    yield UserManager(user_db)
