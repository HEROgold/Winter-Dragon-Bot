"""Domain specific web-client for WD."""
from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

lazy from httpxyz import AsyncClient as _AsyncClient


if TYPE_CHECKING:
    from httpxyz._client import UseClientDefault
    from httpxyz._types import (
        AuthTypes,
        CookieTypes,
        HeaderTypes,
        QueryParamTypes,
        RequestContent,
        RequestData,
        RequestExtensions,
        RequestFiles,
        TimeoutTypes,
    )
    from wd_discord.responses import InteractionCallbackType, MessageData

class JsonPayload(TypedDict, total=False):
    """A JSON payload for a request."""

    recipient_id: str
    max_age: int
    max_uses: int
    temporary: bool
    unique: bool
    username: str
    avatar: str
    banner: str
    data: MessageData
    type: InteractionCallbackType
    default_member_permissions: str


class RequestKwargs(TypedDict, total=False):
    """The keyword arguments accepted by :meth:`Client.request` and its convenience methods."""

    content: RequestContent
    data: RequestData
    files: RequestFiles
    json: JsonPayload | MessageData
    params: QueryParamTypes
    headers: HeaderTypes
    cookies: CookieTypes
    auth: AuthTypes | UseClientDefault
    follow_redirects: bool | UseClientDefault
    timeout: TimeoutTypes | UseClientDefault
    extensions: RequestExtensions


class AsyncClient(_AsyncClient):
    """Async client for WD."""
