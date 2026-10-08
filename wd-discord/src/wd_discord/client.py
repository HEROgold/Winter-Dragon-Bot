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
        me = await client.users.me()
        if is_network_error(me):
            ...  # handle the failure
        else:
            await me.edit(username="Winter Dragon")

The client is the transport level of wd-discord. Resource operations live in the stores it carries
(``client.users``, ``client.channels``, ``client.guilds``, and ``client.application`` with its
``commands``) and on the entities they return; see :mod:`wd_discord.entities`.
"""

from __future__ import annotations

lazy from functools import wraps
lazy from typing import TYPE_CHECKING, Self, TypeIs, Unpack

lazy from herogold.log import LoggerMixin
lazy from httpxyz import AsyncClient, RequestError
lazy from wd_config.discord import URLS

lazy from wd_discord import ShardManager
lazy from wd_discord.authenticate import URL as UserAgentURL  # noqa: N811
lazy from wd_discord.authenticate import (
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
lazy from wd_discord.entities.application import CurrentApplication
lazy from wd_discord.entities.base import EntityStore
lazy from wd_discord.entities.channel import PartialChannel
lazy from wd_discord.entities.guild import PartialGuild
lazy from wd_discord.entities.user import PartialUser, UserStore
lazy from wd_discord.errors.api import ApiResponseError
lazy from wd_discord.gateway.sharding import GatewayBotInfo
lazy from wd_discord.rate_limit import MAX_RATE_LIMIT_RETRIES, MaxRetriesExceededError, RateLimitHandler, route_key


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable

    lazy from httpxyz import Response
    lazy from wd_core.client import RequestKwargs
    lazy from wd_core.intents import Intents

    lazy from wd_discord.snowflake import SnowflakeLike


# Discord requires a valid User-Agent or requests may be blocked with a Cloudflare error.
DEFAULT_USER_AGENT_URL = "https://github.com/HEROgold/WinterDragon"
DEFAULT_USER_AGENT_VERSION = "0.1.0"

type NetworkError = ApiResponseError | RequestError
type RequestResult = Response | NetworkError


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


def is_network_error(value: object) -> TypeIs[NetworkError]:
    """Whether ``value`` is a failed request: a Discord API error or a network error."""
    return isinstance(value, ApiResponseError | RequestError)


def _parse_error(response: Response) -> ApiResponseError:
    """Parse a failed Discord response body into a type-safe :class:`ApiResponseError`."""
    try:
        return ApiResponseError.model_validate(response.json())
    except Exception:  # noqa: BLE001 - non-JSON or unexpected shape (e.g. a Cloudflare HTML ban page)
        return ApiResponseError(code=response.status_code, message=response.text)


class Client(LoggerMixin):
    """An async Discord REST client pinned to the configured API version (v10 by default)."""

    def __init__(
        self,
        token: str,
        *,
        token_type: TokenType = TokenType.BOT,
        version: int | None = None,
        application_id: SnowflakeLike | None = None,
    ) -> None:
        """Build a client for ``token``.

        ``version`` overrides the API version from :class:`~wd_config.discord.URLS`. ``application_id`` skips
        looking up the application's ID; see :meth:`CurrentApplication.id`.
        """
        self.token = Token(token)
        self.token_type = token_type
        self.version = version if version is not None else URLS.version
        self.base_url = f"{URLS.base}/v{self.version}"
        self._client = AsyncClient(base_url=self.base_url, headers=self._default_headers())
        self.application = CurrentApplication(self, application_id)
        self.users = UserStore(self, PartialUser)
        self.channels = EntityStore(self, PartialChannel)
        self.guilds = EntityStore(self, PartialGuild)

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
    async def request(self, method: str, path: str, **kwargs: Unpack[RequestKwargs]) -> Response | ApiResponseError:
        """Send a request, returning the :class:`Response` or a parsed error value.

        Network errors are returned (not raised) as :class:`httpxyz.RequestError`, and 4xx/5xx
        responses are returned as :class:`ApiResponseError`. Before sending, waits on the global
        and per-route :mod:`wd_discord.rate_limit` limiters so normal operation shouldn't cause a
        429 in the first place; if one still happens, waits Discord's own ``retry_after`` plus an
        extra exponential backoff (``2 ** attempt`` seconds) and retries transparently (up to
        :data:`MAX_RATE_LIMIT_RETRIES` times) rather than surfacing the 429 to the caller.
        """
        key = route_key(method, path)
        handler = RateLimitHandler(key)

        async def send_once() -> Response:
            self.logger.debug(t"{method} {path}")
            try:
                return await self._client.request(method, path, **kwargs)
            except RequestError:
                # Re-raise so ``returns_known_exception`` converts it to a value; log it first.
                self.logger.exception(t"Request error for {method} {path}")
                raise

        try:
            response = await handler.send(send_once)
        except MaxRetriesExceededError:
            self.logger.exception(t"Giving up on {method} {path} after {MAX_RATE_LIMIT_RETRIES} rate-limit retries")
            return ApiResponseError(code=0, message="Exceeded rate-limit retries")

        if response.is_success:
            self.logger.debug(t"{response.status_code} {method} {path}")
            return response
        error = _parse_error(response)
        self.logger.warning(t"API error {error.code}: {error.message} for {method} {path}")
        return error

    async def get(self, path: str) -> RequestResult:
        """Send a GET request."""
        return await self.request("GET", path)

    async def post(self, path: str, **kwargs: Unpack[RequestKwargs]) -> RequestResult:
        """Send a POST request."""
        return await self.request("POST", path, **kwargs)

    async def patch(self, path: str, **kwargs: Unpack[RequestKwargs]) -> RequestResult:
        """Send a PATCH request."""
        return await self.request("PATCH", path, **kwargs)

    async def put(self, path: str, **kwargs: Unpack[RequestKwargs]) -> RequestResult:
        """Send a PUT request."""
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs: Unpack[RequestKwargs]) -> RequestResult:
        """Send a DELETE request."""
        if "json" not in kwargs:
            kwargs["json"] = {}
        return await self.request("DELETE", path, **kwargs)

    # --- Gateway bootstrap ----------------------------------------------------------

    async def get_gateway_bot(self) -> GatewayBotInfo | NetworkError:
        """GET /gateway/bot - the gateway WebSocket URL + recommended shard/session info."""
        result = await self.get("/gateway/bot")
        if is_network_error(result):
            return result
        return GatewayBotInfo.model_validate(result.json())

    async def get_shard_manager(self, info: GatewayBotInfo, *, intents: Intents | None = None) -> ShardManager:
        """Return an unstarted :class:`ShardManager` for the given :class:`GatewayBotInfo`."""
        return ShardManager(self.token, info, intents=intents)
