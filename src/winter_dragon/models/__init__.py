from herogold.orm.model import BaseModel
from sqlmodel import Field


class TournamentVote(BaseModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    votes: dict[int, str] = Field(default_factory=dict)
    vote_counts: dict[str, int] = Field(default_factory=dict)
    format_votes: dict[int, str] = Field(default_factory=dict)
    format_counts: dict[str, int] = Field(default_factory=dict)
    participants: list[int] = Field(default_factory=list)
    voting_concluded: bool = False
    tournament_started: bool = False
    winning_game: str | None = None
    winning_format: str | None = None


class NhieQuestion(BaseModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    question: str
    used_count: int = 0


class WyrQuestion(BaseModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    option_a: str
    option_b: str
    used_count: int = 0


class Player(BaseModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int
    guild_id: int | None = None
    score: int = 0


class HangmanGame(BaseModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    word: str
    guessed_letters: list[str] = Field(default_factory=list)
    incorrect_guesses: int = 0
    user_id: int
    guild_id: int | None = None


class LoveMeterResult(BaseModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id_a: int
    user_id_b: int
    score: int
    timestamp: str


class UserModel(BaseModel, table=True):
    name: str
    discriminator: str | None = None
    avatar_url: str | None = None


class GuildModel(BaseModel, table=True):
    name: str
    owner_id: int


class RoleModel(BaseModel, table=True):
    name: str
    permissions: int | None = None


class ChannelModel(BaseModel, table=True):
    name: str
    type: str
    guild_id: int | None = None
