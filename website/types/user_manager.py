
from fastapi import Request
from fastapi_users import BaseUserManager

from database.tables.users import FastApiUser


SECRET = "SECRET"  # noqa: S105


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
