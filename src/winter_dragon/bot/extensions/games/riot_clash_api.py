"""Riot Games Clash API client for retrieving tournament schedule and information.

This module provides a Pythonic OOP interface to Riot's public CLASH-V1 API
for fetching Clash tournament schedules, team information, and player details.
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Self

import aiohttp
import discord
from discord.ext import tasks


if TYPE_CHECKING:
    from discord.ext.commands.bot import BotBase


class Region(StrEnum):
    """Riot API regional routing values for platform independence."""

    AMERICAS = "americas"
    ASIA = "asia"
    EUROPE = "europe"
    SEA = "sea"


class Platform(StrEnum):
    """Riot API platform routing values for region-specific endpoints."""

    BR1 = "br1"
    EUN1 = "eun1"
    EUW1 = "euw1"
    JP1 = "jp1"
    KR = "kr"
    LA1 = "la1"
    LA2 = "la2"
    NA1 = "na1"
    OC1 = "oc1"
    PH2 = "ph2"
    RU = "ru"
    SG2 = "sg2"
    TH2 = "th2"
    TR1 = "tr1"
    TW2 = "tw2"
    VN2 = "vn2"


class ClashPhase(StrEnum):
    """Tournament phase stages in Clash."""

    REGISTRATION = "REGISTRATION"
    BANS_PHASE = "BANS_PHASE"
    LOCKED_IN = "LOCKED_IN"


@dataclass
class ClashPhaseTiming:
    """Timing information for a Clash tournament phase."""

    phase: ClashPhase
    started_at: datetime
    cancelled: bool = False

    def __str__(self) -> str:
        """Return human-readable phase timing."""
        status = "Cancelled" if self.cancelled else "Active"
        return f"{self.phase.value}: {self.started_at.strftime('%Y-%m-%d %H:%M:%S')} ({status})"


@dataclass
class ClashTournament:
    """Represents a Clash tournament with schedule and metadata."""

    tournament_id: int
    name: str
    schedule: list[ClashPhaseTiming] = field(default_factory=list)
    icon_url: str = ""
    tier: int = 0

    def __post_init__(self) -> None:
        """Sort schedule by start time."""
        self.schedule.sort(key=lambda p: p.started_at)

    @property
    def next_phase(self) -> ClashPhaseTiming | None:
        """Get the next active phase."""
        for phase in self.schedule:
            if not phase.cancelled:
                return phase
        return None

    @property
    def start_time(self) -> datetime | None:
        """Get the tournament start time (first registration phase)."""
        for phase in self.schedule:
            if phase.phase == ClashPhase.REGISTRATION:
                return phase.started_at
        return None

    def to_embed(self) -> discord.Embed:
        """Convert tournament to a Discord embed."""
        embed = discord.Embed(
            title=f"🏆 {self.name}",
            description=f"Tournament ID: {self.tournament_id}",
            color=discord.Color.gold(),
            timestamp=self.start_time,
        )

        if self.next_phase:
            embed.add_field(
                name="Next Phase",
                value=str(self.next_phase),
                inline=False,
            )

        if self.schedule:
            schedule_text = "\n".join(str(phase) for phase in self.schedule[:3])
            embed.add_field(
                name="Schedule",
                value=schedule_text,
                inline=False,
            )

        embed.set_footer(text=f"Tier {self.tier}")
        return embed


class RiotClashAPIError(Exception):
    """Base exception for Riot Clash API errors."""


class RiotClashAPIAuthError(RiotClashAPIError):
    """Raised when API authentication fails."""


class RiotClashAPIRateLimitError(RiotClashAPIError):
    """Raised when rate limit is exceeded."""


class RiotClashClient:
    """Pythonic async client for Riot Games Clash API.

    Provides methods to fetch upcoming Clash tournaments, team information,
    and player Clash details from the public CLASH-V1 API.
    """

    BASE_URL = "https://{platform}.api.riotgames.com/lol/clash/v1"
    API_VERSION = "v1"

    def __init__(self, api_key: str) -> None:
        """Initialize the Riot Clash API client."""
        self.api_key = api_key
        self._session: aiohttp.ClientSession | None = None
        self._cache: dict[str, Any] = {}
        self._cache_expires: dict[str, float] = {}

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._session:
            await self._session.close()

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get or create the HTTP session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    def _build_url(
        self,
        platform: Platform | str,
        endpoint: str,
    ) -> str:
        """Build a Riot API URL."""
        base = self.BASE_URL.format(platform=platform)
        return f"{base}{endpoint}"

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an authenticated HTTP request to Riot API.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to request
            **kwargs: Additional arguments to pass to aiohttp

        Returns:
            JSON response data

        Raises:
            RiotClashAPIAuthError: If authentication fails
            RiotClashAPIRateLimitError: If rate limited
            RiotClashAPIError: For other API errors

        """
        headers = {
            "X-Riot-Token": self.api_key,
            "User-Agent": "WinterDragonBot/1.0",
        }

        try:
            async with self.session.request(
                method,
                url,
                headers=headers,
                **kwargs,
            ) as response:
                if response.status == HTTPStatus.UNAUTHORIZED:
                    msg = f"Authentication failed: {response.status} {response.reason}"
                    raise RiotClashAPIAuthError(
                        msg,
                    )
                if response.status == HTTPStatus.TOO_MANY_REQUESTS:
                    msg = f"Rate limited: {response.headers.get('Retry-After', 'unknown')}s"
                    raise RiotClashAPIRateLimitError(
                        msg,
                    )
                if response.status == HTTPStatus.NOT_FOUND:
                    return {}
                if response.status >= HTTPStatus.BAD_REQUEST:
                    text = await response.text()
                    msg = f"API error {response.status}: {text}"
                    raise RiotClashAPIError(
                        msg,
                    )

                return await response.json()
        except aiohttp.ClientError as e:
            msg = f"Network error: {e!s}"
            raise RiotClashAPIError(msg) from e

    def _parse_tournament(self, data: dict[str, Any]) -> ClashTournament:
        """Parse tournament data from API response."""
        schedule = [
            ClashPhaseTiming(
                phase=ClashPhase(phase_data["type"]),
                started_at=datetime.fromtimestamp(phase_data["startTime"] / 1000, tz=UTC),
                cancelled=phase_data.get("cancelled", False),
            )
            for phase_data in data.get("schedule", [])
        ]

        return ClashTournament(
            tournament_id=data["id"],
            name=data["name"],
            schedule=schedule,
            icon_url=data.get("iconUrl", ""),
            tier=data.get("tier", 0),
        )

    async def get_tournaments(
        self,
        platform: Platform | str,
    ) -> list[ClashTournament]:
        """Fetch all available Clash tournaments for a platform.

        Args:
            platform: Platform routing value (e.g., 'na1', 'euw1')

        Returns:
            List of ClashTournament objects

        Raises:
            RiotClashAPIError: If the API request fails

        """
        url = self._build_url(platform, "/tournaments")
        data = await self._request("GET", url)

        if not isinstance(data, list):
            return []

        return [self._parse_tournament(tournament) for tournament in data if isinstance(tournament, dict)]

    async def get_tournament_by_id(
        self,
        platform: Platform | str,
        tournament_id: int,
    ) -> ClashTournament | None:
        """Fetch a specific Clash tournament by ID."""
        url = self._build_url(platform, f"/tournaments/{tournament_id}")
        data = await self._request("GET", url)

        return self._parse_tournament(data) if data else None

    async def get_tournaments_by_summoner(
        self,
        platform: Platform | str,
        summoner_id: str,
    ) -> list[ClashTournament]:
        """Fetch all Clash tournaments a summoner is registered in.

        Args:
            platform: Platform routing value
            summoner_id: Summoner ID

        Returns:
            List of ClashTournament objects

        Raises:
            RiotClashAPIError: If the API request fails

        """
        url = self._build_url(platform, f"/tournaments/by-summoner/{summoner_id}")
        data = await self._request("GET", url)

        if not isinstance(data, list):
            return []

        return [self._parse_tournament(tournament) for tournament in data if isinstance(tournament, dict)]

    async def get_teams(
        self,
        platform: Platform | str,
        tournament_id: int,
    ) -> list[dict[str, Any]]:
        """Fetch all teams registered in a Clash tournament.

        Args:
            platform: Platform routing value
            tournament_id: Tournament ID

        Returns:
            List of team data dictionaries

        Raises:
            RiotClashAPIError: If the API request fails

        """
        url = self._build_url(platform, f"/tournaments/{tournament_id}/teams")
        data = await self._request("GET", url)
        return data if isinstance(data, list) else []


class DiscordClashEventManager:
    """Manages Discord scheduled events for Clash tournaments.

    Syncs Clash tournament data with Discord guild scheduled events,
    creating and updating events as needed.
    """

    def __init__(self, bot: BotBase) -> None:
        """Initialize the event manager."""
        self.bot = bot
        self._event_task: asyncio.Task[None] | None = None

    async def create_event(
        self,
        guild: discord.Guild,
        tournament: ClashTournament,
    ) -> discord.ScheduledEvent | None:
        """Create a Discord scheduled event for a Clash tournament.

        Args:
            guild: Discord guild to create event in
            tournament: Clash tournament data

        Returns:
            Created ScheduledEvent or None if creation failed

        """
        try:
            if not tournament.start_time:
                return None

            return await guild.create_scheduled_event(
                name=f"🏆 {tournament.name}",
                description=(f"Upcoming Clash Tournament\nID: {tournament.tournament_id}\nTier: {tournament.tier}"),
                start_time=tournament.start_time,
                end_time=tournament.start_time,
                location="League of Legends",
                privacy_level=discord.PrivacyLevel.guild_only,
            )
        except discord.DiscordException as e:
            msg = f"Failed to create Discord event: {e!s}"
            raise RiotClashAPIError(msg) from e

    async def sync_tournaments_to_events(
        self,
        guild: discord.Guild,
        tournaments: list[ClashTournament],
        remove_old: bool = True,
    ) -> tuple[list[discord.ScheduledEvent], list[ClashTournament]]:
        """Sync Clash tournaments to Discord scheduled events.

        Args:
            guild: Discord guild to sync to
            tournaments: List of ClashTournament objects
            remove_old: Whether to remove old Clash-related events

        Returns:
            Tuple of (created_events, failed_tournaments)

        """
        created = []
        failed = []

        # Clean up old Clash events if requested
        if remove_old:
            try:
                existing_events = guild.scheduled_events
                for event in existing_events:
                    if event.name.startswith("🏆"):
                        with contextlib.suppress(discord.DiscordException):
                            await event.delete()
            except discord.DiscordException:
                pass

        # Create new events
        for tournament in tournaments:
            try:
                event = await self.create_event(guild, tournament)
                if event:
                    created.append(event)
            except RiotClashAPIError:
                failed.append(tournament)

        return created, failed

    def start_sync_task(
        self,
        clash_client: RiotClashClient,
        guild: discord.Guild,
        platform: Platform | str,
        interval_seconds: int = 3600,
    ) -> None:
        """Start a background task to periodically sync tournaments to events.

        Args:
            clash_client: Initialized RiotClashClient instance
            guild: Discord guild to sync to
            platform: Platform routing value
            interval_seconds: Sync interval in seconds (default: 1 hour)

        """

        @tasks.loop(seconds=interval_seconds)
        async def sync_loop() -> None:
            try:
                tournaments = await clash_client.get_tournaments(platform)
                await self.sync_tournaments_to_events(guild, tournaments)
            except RiotClashAPIError:
                pass

        self._event_task = asyncio.create_task(sync_loop())

    async def stop_sync_task(self) -> None:
        """Stop the background sync task."""
        if self._event_task:
            self._event_task.cancel()
            self._event_task = None
