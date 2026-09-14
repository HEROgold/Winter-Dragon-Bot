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

lazy from functools import wraps
lazy from typing import TYPE_CHECKING, Any, Self

lazy from herogold.log import LoggerMixin
lazy from httpxyz import AsyncClient, RequestError
lazy from wd_config.bot import Settings
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
lazy from wd_discord.embed import Embed
lazy from wd_discord.errors.api import ApiResponseError
lazy from wd_discord.gateway import Message
lazy from wd_discord.gateway.sharding import GatewayBotInfo
lazy from wd_discord.interactions import CommandOption, RegisteredCommand
lazy from wd_discord.rate_limit import MAX_RATE_LIMIT_RETRIES, MaxRetriesExceededError, RateLimitHandler, route_key
lazy from wd_discord.resources.application import Application
lazy from wd_discord.resources.channel import Channel
lazy from wd_discord.resources.guild import Guild
lazy from wd_discord.resources.invite import Invite
lazy from wd_discord.resources.user import User


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable, Generator, Sequence

    lazy from httpxyz import Response
    lazy from wd_core.intents import Intents

    lazy from wd_discord.gateway.events import Interaction
    lazy from wd_discord.image import ImageHash

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


def _parse_error(response: Response) -> ApiResponseError:
    """Parse a failed Discord response body into a type-safe :class:`ApiResponseError`."""
    try:
        return ApiResponseError.model_validate(response.json())
    except Exception:  # noqa: BLE001 - non-JSON or unexpected shape (e.g. a Cloudflare HTML ban page)
        return ApiResponseError(code=response.status_code, message=response.text)


def _build_command_payload(name: str, description: str, options: Sequence[CommandOption]) -> dict[str, Any]:
    """Build the JSON body for creating/editing a chat-input application command."""
    return {
        "name": name,
        "description": description,
        "type": 1,
        "options": [option.model_dump(mode="json", exclude_none=True) for option in options],
    }


class Client(LoggerMixin):
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
        self._application_id: str | None = None

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

    async def get_current_user(self) -> User | NetworkError:
        """GET /users/@me - the bot user behind the token."""
        result = await self.get("/users/@me")
        if isinstance(result, ApiResponseError | RequestError):
            return result
        return User.model_validate(result.json())

    async def get_current_application(self) -> Application | NetworkError:
        """GET /applications/@me - the current application object."""
        result = await self.get("/applications/@me")
        if isinstance(result, (ApiResponseError, RequestError)):
            return result
        return Application.model_validate(result.json())

    async def _get_application_id(self) -> str | NetworkError:
        """Return this client's application ID, fetching-and-caching it via the API if unset.

        Prefers an already-configured ``Settings.application_id``; otherwise fetches it once via
        :meth:`get_current_application` and writes it back into ``Settings`` so future ``Client``
        instances don't need to fetch it again.
        """
        if self._application_id is not None:
            return self._application_id
        if Settings.application_id:
            self._application_id = str(Settings.application_id)
            return self._application_id
        app = await self.get_current_application()
        if isinstance(app, (ApiResponseError, RequestError)):
            return app
        application_id = app.model_dump(mode="json")["id"]
        self._application_id = application_id
        Settings.application_id = int(application_id)
        return application_id

    async def get_gateway_bot(self) -> GatewayBotInfo | NetworkError:
        """GET /gateway/bot - the gateway WebSocket URL + recommended shard/session info."""
        result = await self.get("/gateway/bot")
        if isinstance(result, (ApiResponseError, RequestError)):
            return result
        return GatewayBotInfo.model_validate(result.json())

    async def get_shard_manager(self, info: GatewayBotInfo, *, intents: Intents | None = None) -> ShardManager:
        """Return an unstarted :class:`ShardManager` for the given :class:`GatewayBotInfo`."""
        return ShardManager(self.token, info, intents=intents)

    async def get_user(self, user_id: int | str) -> User | NetworkError:
        """GET /users/{user_id}."""
        result = await self.get(f"/users/{user_id}")
        if isinstance(result, (ApiResponseError, RequestError)):
            return result
        return User.model_validate(result.json())

    async def get_guild(self, guild_id: int | str) -> Guild | NetworkError:
        """GET /guilds/{guild_id}."""
        result = await self.get(f"/guilds/{guild_id}")
        if isinstance(result, (ApiResponseError, RequestError)):
            return result
        return Guild.model_validate(result.json())

    async def get_channel(self, channel_id: int | str) -> Channel | NetworkError:
        """GET /channels/{channel_id}."""
        result = await self.get(f"/channels/{channel_id}")
        if isinstance(result, (ApiResponseError, RequestError)):
            return result
        return Channel.model_validate(result.json())

    async def get_guild_channels(self, guild_id: int | str) -> Generator[Channel] | NetworkError:
        """GET /guilds/{guild_id}/channels - the guild's channels."""
        result = await self.get(f"/guilds/{guild_id}/channels")
        if isinstance(result, (ApiResponseError, RequestError)):
            return result
        return (Channel.model_validate(channel) for channel in result.json())

    async def leave_guild(self, guild_id: int | str) -> NetworkError | None:
        """DELETE /users/@me/guilds/{guild_id} - remove the bot from a guild it doesn't own.

        Discord returns 204 No Content on success, so there's no body to parse - ``None`` is
        the real result here, not a raw-dict shortcut.
        """
        result = await self.delete(f"/users/@me/guilds/{guild_id}", json={})
        if isinstance(result, (ApiResponseError, RequestError)):
            return result
        return None

    async def create_dm(self, recipient_id: int | str) -> Channel | NetworkError:
        """POST /users/@me/channels - open (or fetch the existing) DM channel with a user."""
        result = await self.post("/users/@me/channels", json={"recipient_id": str(recipient_id)})
        if isinstance(result, (ApiResponseError, RequestError)):
            return result
        return Channel.model_validate(result.json())

    async def create_message(self, channel_id: int | str, content: str) -> Message | NetworkError:
        """POST /channels/{channel_id}/messages - send a message (works for DM channels too)."""
        result = await self.post(f"/channels/{channel_id}/messages", json={"content": content})
        if isinstance(result, (ApiResponseError, RequestError)):
            return result
        return Message.model_validate(result.json())

    async def create_channel_invite(
        self,
        channel_id: int | str,
        *,
        max_age: int = 86400,
        max_uses: int = 1,
        temporary: bool = False,
        unique: bool = True,
    ) -> Invite | NetworkError:
        """POST /channels/{channel_id}/invites - create an instant invite for a channel.

        Defaults to a single-use, 24h invite (``max_age``/``max_uses``) - unlike a permanent
        vanity invite, this is meant for handing to one specific person.
        """
        payload = {"max_age": max_age, "max_uses": max_uses, "temporary": temporary, "unique": unique}
        result = await self.post(f"/channels/{channel_id}/invites", json=payload)
        if isinstance(result, (ApiResponseError, RequestError)):
            return result
        return Invite.model_validate(result.json())

    async def modify_current_user(
        self,
        *,
        username: str | None = None,
        avatar: ImageHash | None = None,
        banner: ImageHash | None = None,
    ) -> RequestResult:
        """PATCH /users/@me - update the bot's profile (username and/or avatar)."""
        payload: dict[str, str] = {}
        if username is not None:
            payload["username"] = username
        if avatar is not None:
            payload["avatar"] = str(avatar)
        if banner is not None:
            payload["banner"] = str(banner)
        return await self.patch("/users/@me", json=payload)

    async def create_interaction_response(
        self,
        interaction: Interaction,
        *,
        content: str | None = None,
        embeds: list[Embed] | None = None,
    ) -> RequestResult:
        """POST /interactions/{id}/{token}/callback - respond to an interaction (type 4: message with source)."""
        data: dict[str, Any] = {}
        if content is not None:
            data["content"] = content
        if embeds is not None:
            data["embeds"] = [embed.model_dump(mode="json", exclude_none=True) for embed in embeds]
        payload = {"type": 4, "data": data}
        return await self.post(f"/interactions/{interaction.id}/{interaction.token}/callback", json=payload)

    async def create_global_command(
        self,
        name: str,
        description: str,
        options: list[CommandOption] | None = None,
    ) -> RegisteredCommand | NetworkError:
        """POST /applications/{application_id}/commands - register a new global chat-input command."""
        application_id = await self._get_application_id()
        if isinstance(application_id, (ApiResponseError, RequestError)):
            return application_id
        result = await self.post(
            f"/applications/{application_id}/commands",
            json=_build_command_payload(name, description, options or []),
        )
        if isinstance(result, (ApiResponseError, RequestError)):
            return result
        return RegisteredCommand.model_validate(result.json())

    async def edit_global_command(
        self,
        command_id: str,
        name: str,
        description: str,
        options: list[CommandOption] | None = None,
    ) -> RegisteredCommand | NetworkError:
        """PATCH /applications/{application_id}/commands/{command_id} - update an existing global command."""
        application_id = await self._get_application_id()
        if isinstance(application_id, (ApiResponseError, RequestError)):
            return application_id
        result = await self.patch(
            f"/applications/{application_id}/commands/{command_id}",
            json=_build_command_payload(name, description, options or []),
        )
        if isinstance(result, (ApiResponseError, RequestError)):
            return result
        return RegisteredCommand.model_validate(result.json())

    async def delete_global_command(self, command_id: str) -> NetworkError | None:
        """DELETE /applications/{application_id}/commands/{command_id} - remove a global command."""
        application_id = await self._get_application_id()
        if isinstance(application_id, (ApiResponseError, RequestError)):
            return application_id
        result = await self.delete(f"/applications/{application_id}/commands/{command_id}", json={})
        if isinstance(result, (ApiResponseError, RequestError)):
            return result
        return None

    async def get_global_commands(self) -> Generator[RegisteredCommand] | NetworkError:
        """GET /applications/{application_id}/commands - every currently-registered global command."""
        application_id = await self._get_application_id()
        if isinstance(application_id, (ApiResponseError, RequestError)):
            return application_id
        result = await self.get(f"/applications/{application_id}/commands")
        if isinstance(result, (ApiResponseError, RequestError)):
            return result
        return (RegisteredCommand.model_validate(item) for item in result.json())
