from datetime import datetime
from typing import TypedDict


class AccessToken(TypedDict):
    user_id: int
    access_token: str
    refresh_token: str
    created_at: datetime
    expires_in: int
    expires_at: datetime
    token_type: str
    scope: str
