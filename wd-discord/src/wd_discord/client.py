"""The built-in Discord REST client for wd-discord.

A thin, async wrapper around :mod:`httpxyz` that targets the Discord API v10
(https://docs.discord.com/developers/reference). It reuses the package's existing
building blocks: :class:`~wd_config.discord.URLS` for the base URL + version,
the header builders in :mod:`wd_discord.authenticate`, and
:class:`~wd_discord.errors.ApiResponseError` for parsing failures.

Following herogold's ``with_known_exception`` style, request methods do **not** raise on
API/network failure; they return the error as a type-safe value so callers can handle it
with ``isinstance`` / ``match`` instead of ``try``/``except``::

    async with Client(token) as client:
        result = await client.get_current_user()
        match result:
            case ApiResponseError() as err:
                ...  # handle the failure
            case _:
                user = result.json()
"""
from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, Self

from httpxyz import AsyncClient, RequestError
from wd_config.discord import URLS

from wd_discord.application import Application
from wd_discord.authenticate import URL as UserAgentURL  # noqa: N811
from wd_discord.authenticate import (
    ContentType,
    MetaData,
    Token,
    TokenType,
    UserAgentVersion,
    content_type,
    get_auth_header,
    render_header,
    user_agent,
)
from wd_discord.channel import Channel
from wd_discord.errors.api import ApiResponseError
from wd_discord.gateway.sharding import GatewayBotInfo
from wd_discord.guild import Guild

from .user import User


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from httpxyz import Response

# Discord requires a valid User-Agent or requests may be blocked with a Cloudflare error.
DEFAULT_USER_AGENT_URL = "https://github.com/HEROgold/WinterDragon"
DEFAULT_USER_AGENT_VERSION = "0.1.0"

type RequestResult = Response | ApiResponseError | RequestError


def returns_known_exception[**P, T, E: Exception](
    *exceptions: type[E],
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T | E]]]:
    """Async analog of :func:`herogold.errors.with_known_exception`.

    Wraps a coroutine so that any of the named exception types are returned as a value
    instead of raised. Anything else propagates normally.
    """

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T | E]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | E:
            try:
                return await func(*args, **kwargs)
            except exceptions as error:
                return error

        return wrapper

    return decorator


def _parse_error(response: Response) -> ApiResponseError:
    """Parse a failed Discord response body into a type-safe :class:`ApiResponseError`."""
    try:
        return ApiResponseError.model_validate(response.json())
    except Exception:  # noqa: BLE001 - non-JSON or unexpected shape (e.g. a Cloudflare HTML ban page)
        return ApiResponseError(code=response.status_code, message=response.text)


class Client:
    """An async Discord REST client pinned to the configured API version (v10 by default)."""

    def __init__(
        self,
        token: str,
        *,
        token_type: TokenType = TokenType.BOT,
        version: int | None = None,
    ) -> None:
        """Build a client for ``token``.

        ``version`` overrides the API version from :class:`~wd_config.discord.URLS`.
        """
        self.token = Token(token)
        self.token_type = token_type
        self.version = version if version is not None else URLS.version
        self.base_url = f"{URLS.base}/v{self.version}"
        self._client = AsyncClient(base_url=self.base_url, headers=self._default_headers())

    def _default_headers(self) -> dict[str, str]:
        """Render the auth, user-agent and content-type headers into a plain dict.

        Values are stripped because an empty user-agent metadata segment would otherwise
        leave a trailing space, which HTTP rejects as an illegal header value.
        """
        headers = (
            render_header(get_auth_header(self.token_type, self.token)),
            render_header(
                user_agent(
                    UserAgentURL(DEFAULT_USER_AGENT_URL),
                    UserAgentVersion(DEFAULT_USER_AGENT_VERSION),
                    MetaData(""),
                ),
            ),
            render_header(content_type(ContentType.json)),
        )
        return {name: value.strip() for name, value in headers}

    async def __aenter__(self) -> Self:
        """Enter the async context, returning the client."""
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Close the underlying transport on context exit."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying httpxyz transport."""
        await self._client.aclose()

    @returns_known_exception(RequestError)
    async def request(self, method: str, path: str, **kwargs: Any) -> Response | ApiResponseError:  # noqa: ANN401
        """Send a request, returning the :class:`Response` or a parsed error value.

        Network errors are returned (not raised) as :class:`httpxyz.RequestError`, and
        4xx/5xx responses are returned as :class:`ApiResponseError`.
        """
        response = await self._client.request(method, path, **kwargs)
        if response.is_success:
            return response
        return _parse_error(response)

    async def get(self, path: str, **kwargs: Any) -> RequestResult:  # noqa: ANN401
        """Send a GET request."""
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> RequestResult:  # noqa: ANN401
        """Send a POST request."""
        return await self.request("POST", path, **kwargs)

    async def patch(self, path: str, **kwargs: Any) -> RequestResult:  # noqa: ANN401
        """Send a PATCH request."""
        return await self.request("PATCH", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> RequestResult:  # noqa: ANN401
        """Send a PUT request."""
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> RequestResult:  # noqa: ANN401
        """Send a DELETE request."""
        return await self.request("DELETE", path, **kwargs)

    # --- Resource helpers (read-only unless noted) -------------------------------------

    async def get_current_user(self) -> User | ApiResponseError | RequestError:
        """GET /users/@me - the bot user behind the token."""
        result = await self.get("/users/@me")
        if isinstance(result, ApiResponseError | RequestError):
            return result
        return User.model_validate(result.json())

    async def get_current_application(self) -> Application | ApiResponseError | RequestError:
        """GET /applications/@me - the current application object."""
        result = await self.get("/applications/@me")
        if isinstance(result, ApiResponseError | RequestError):
            return result
        return Application.model_validate(result.json())

    async def get_gateway_bot(self) -> GatewayBotInfo | ApiResponseError | RequestError:
        """GET /gateway/bot - the gateway WebSocket URL + recommended shard/session info."""
        result = await self.get("/gateway/bot")
        if isinstance(result, ApiResponseError | RequestError):
            return result
        # TODO: automatically shard out bot based on GatewayBotInfo.shards and SessionStartLimit
        # using a ShardManager helper class
        return GatewayBotInfo.model_validate(result.json())

    async def get_user(self, user_id: int | str) -> User | ApiResponseError | RequestError:
        """GET /users/{user_id}."""
        result = await self.get(f"/users/{user_id}")
        if isinstance(result, ApiResponseError | RequestError):
            return result
        return User.model_validate(result.json())

    async def get_guild(self, guild_id: int | str) -> Guild | ApiResponseError | RequestError:
        """GET /guilds/{guild_id}."""
        result = await self.get(f"/guilds/{guild_id}")
        if isinstance(result, ApiResponseError | RequestError):
            return result
        return Guild.model_validate(result.json())

    async def get_channel(self, channel_id: int | str) -> Channel | ApiResponseError | RequestError:
        """GET /channels/{channel_id}."""
        result = await self.get(f"/channels/{channel_id}")
        if isinstance(result, ApiResponseError | RequestError):
            return result
        return Channel.model_validate(result.json())

    async def modify_current_user(
        self,
        *,
        username: str | None = None,
        avatar: str | None = None,
    ) -> RequestResult:
        """PATCH /users/@me - update the bot's profile (username and/or avatar)."""
        payload: dict[str, str] = {}
        if username is not None:
            payload["username"] = username
        if avatar is not None:
            payload["avatar"] = avatar
        return await self.patch("/users/@me", json=payload)
