"""The /urban command group: look up a term, or random terms, on Urban Dictionary."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, Field, ValidationError
lazy from herogold.errors import with_known_exception
lazy from herogold.log import LoggerMixin
lazy from httpxyz import AsyncClient, RequestError
lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_config.urban import UrbanSettings
lazy from wd_discord.embed import MAX_EMBED_CHARACTERS, MAX_EMBED_FIELDS, Embed, EmbedField, EmbedFooter
lazy from wd_errors import BaseError


if TYPE_CHECKING:
    lazy from collections.abc import Generator, Sequence

    lazy from wd_discord import CommandInteraction


DEFINE_URL = "https://api.urbandictionary.com/v0/define"
RANDOM_URL = "https://api.urbandictionary.com/v0/random"
REQUEST_TIMEOUT_SECONDS = 10.0
MAX_FIELD_VALUE = 1024
"""Discord's limit on the length of an embed field's value."""
ELLIPSIS = "…"


class Definition(BaseModel):
    """One definition of a term, as Urban Dictionary's API returns it."""

    word: str
    definition: str
    permalink: str
    thumbs_up: int
    thumbs_down: int


class DefinitionList(BaseModel):
    """The body of an Urban Dictionary API response."""

    definitions: list[Definition] = Field(alias="list")


class LookupFailed(BaseError):  # noqa: N818 - reads as the outcome callers branch on
    """Urban Dictionary couldn't be asked, or answered something unexpected; the message says which, for the user."""


def truncate(text: str, limit: int) -> str:
    """Return ``text``, cut to ``limit`` characters with an ellipsis when it's longer."""
    return text if len(text) <= limit else text[: limit - len(ELLIPSIS)] + ELLIPSIS


def definition_field(index: int, definition: Definition) -> EmbedField:
    """Return the embed field showing ``definition``, numbered ``index``, with its votes and link."""
    footer = f"\n:thumbsup: {definition.thumbs_up} :thumbsdown: {definition.thumbs_down}\n{definition.permalink}"
    return EmbedField(
        name=truncate(f"{index}. {definition.word}", 256),
        value=truncate(definition.definition, MAX_FIELD_VALUE - len(footer)) + footer,
    )


def definition_fields(definitions: Sequence[Definition], limit: int, budget: int) -> Generator[EmbedField]:
    """Yield a field for each of the first ``limit`` definitions, stopping before their text exceeds ``budget``."""
    for index, definition in enumerate(definitions[: min(limit, MAX_EMBED_FIELDS)], start=1):
        field = definition_field(index, definition)
        budget -= len(field.name) + len(field.value)
        if budget < 0:
            return
        yield field


def build_embed(title: str, definitions: Sequence[Definition], limit: int) -> Embed:
    """Return an embed titled ``title`` showing up to ``limit`` of ``definitions``, within Discord's embed limits."""
    footer = EmbedFooter(text="Results are from api.urbandictionary.com")
    budget = MAX_EMBED_CHARACTERS - len(title) - len(footer.text)
    return Embed(title=title, fields=list(definition_fields(definitions, limit, budget)), footer=footer)


class UrbanDictionary(LoggerMixin):
    """Asks Urban Dictionary's API for definitions; use as ``async with UrbanDictionary() as urban``."""

    def __init__(self, http: AsyncClient | None = None) -> None:
        """Ask through ``http``, or through a client of its own (closed on exit) when not given."""
        self._owns_http = http is None
        self.http = http or AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS)

    async def __aenter__(self) -> Self:
        """Enter the context, returning the client."""
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Close the HTTP client, if it's this object's own."""
        if self._owns_http:
            await self.http.aclose()

    async def define(self, term: str) -> list[Definition] | LookupFailed:
        """Return the definitions of ``term``, best first; empty when it has none."""
        return await self._definitions(DEFINE_URL, {"term": term})  # pyrefly: ignore[not-async] - herogold's with_known_exception lacks an async overload

    async def random(self) -> list[Definition] | LookupFailed:
        """Return a handful of definitions of random terms."""
        return await self._definitions(RANDOM_URL, {})  # pyrefly: ignore[not-async] - herogold's with_known_exception lacks an async overload

    @with_known_exception(LookupFailed)
    async def _definitions(self, url: str, params: dict[str, str]) -> list[Definition]:
        try:
            response = await self.http.get(url, params=params)
        except RequestError as error:
            self.logger.warning(t"Urban Dictionary request failed: {error!r}")
            msg = "Urban Dictionary can't be reached right now."
            raise LookupFailed(msg) from error
        if response.is_error:
            self.logger.warning(t"Urban Dictionary answered {response.status_code} for {url}")
            msg = "Urban Dictionary isn't answering right now."
            raise LookupFailed(msg)
        try:
            return DefinitionList.model_validate_json(response.content).definitions
        except ValidationError as error:
            self.logger.exception(t"Unexpected Urban Dictionary response for {url}")
            msg = "Urban Dictionary answered something I didn't understand."
            raise LookupFailed(msg) from error


class Urban(GroupCog, name="urban", description="Look up words on Urban Dictionary"):
    """Looks up terms on Urban Dictionary."""

    http: AsyncClient | None = None
    """The HTTP client lookups go through; ``None`` gives each lookup a client of its own."""

    @Cog.command(name="search", description="Look up the meaning of a word on Urban Dictionary")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def search(self, interaction: CommandInteraction, query: str) -> None:
        """Reply with the definitions of ``query``."""
        await interaction.defer()
        async with UrbanDictionary(self.http) as urban:
            definitions = await urban.define(query)
        if isinstance(definitions, LookupFailed):
            await interaction.respond(str(definitions))
            return
        if not definitions:
            await interaction.respond(f"No definitions found for `{truncate(query, 100)}`.")
            return
        title = truncate(f"Urban Dictionary: {query}", 256)
        await interaction.respond(embeds=[build_embed(title, definitions, UrbanSettings.max_definitions)])

    @Cog.command(name="random", description="Get random definitions from Urban Dictionary")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def random(self, interaction: CommandInteraction) -> None:
        """Reply with definitions of random terms, unless that's turned off."""
        if not UrbanSettings.allow_random:
            await interaction.respond("Random definitions are turned off.", ephemeral=True)
            return
        await interaction.defer()
        async with UrbanDictionary(self.http) as urban:
            definitions = await urban.random()
        if isinstance(definitions, LookupFailed):
            await interaction.respond(str(definitions))
            return
        await interaction.respond(embeds=[build_embed("Urban Dictionary: random", definitions, UrbanSettings.max_definitions)])
