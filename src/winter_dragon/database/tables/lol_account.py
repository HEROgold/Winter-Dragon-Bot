"""Database table for League of Legends account linking."""

from sqlmodel import Field

from winter_dragon.database.extension.model import DiscordID


class LoLAccount(DiscordID, table=True):
    """Table to store linked League of Legends accounts."""

    summoner_name: str = Field(index=True)
    tag_line: str
    region: str = Field(index=True)
    puuid: str | None = Field(default=None, unique=True, index=True)  # Riot's universal unique identifier
    summoner_id: str | None = Field(default=None)  # Summoner ID for API calls
    account_id: str | None = Field(default=None)  # Account ID for API calls
    profile_icon_id: int | None = Field(default=None)
    summoner_level: int | None = Field(default=None)
    last_updated: int | None = Field(default=None)  # Timestamp of last data update
