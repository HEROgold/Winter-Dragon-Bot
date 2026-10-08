<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_cogs.games` (wd-cogs)
Package for games cogs.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_cogs.games` — `wd-cogs/src/wd_cogs/games/__init__.py`

- exports: Games, Hangman, LeagueOfLegends, Love

## `wd_cogs.games.clash_settings` — `wd-cogs/src/wd_cogs/games/clash_settings.py`
Configuration settings for the Clash cog.

### `class ClashSettings`
Settings for the Clash cog.

- fields: riot_api_key: Config[str | None]

## `wd_cogs.games.games` — `wd-cogs/src/wd_cogs/games/games.py`
Module for tracking games.

### `class Games(GroupCog, auto_load=True)`
Cog that tracks known games and allows users to suggest new ones.

- fields: games: Sequence[GamesDB]
- `@app_commands.command async slash_list(interaction: discord.Interaction) -> None` — Get a list of known games.
- `@app_commands.command async slash_suggest(interaction: discord.Interaction, name: str) -> None` — Suggest a new game to be added.

## `wd_cogs.games.hangman` — `wd-cogs/src/wd_cogs/games/hangman.py`
Module to contain the Hangman game.

- module names: HANGMAN, HANGMEN
- `get_hangman(guess_amount: int) -> str` — Get a hangman text-image based on the amount of guesses.

### `class HangmanButton(Button)`
A button to start a hangman game.

- `async callback(interaction: discord.Interaction) -> None` — Start a hangman game.

### `class SubmitLetter(Modal, SessionMixin, title='Submit Letter')`
A modal to submit a letter for the hangman game.

- attributes: letter
- `async on_submit(interaction: discord.Interaction) -> None` — Submit a letter for the hangman game.
- `get_hidden_word() -> str` — Get the hidden word.
- `track_wrong_guesses() -> None` — Track wrong guesses. Return the wrong guesses and if the guess was wrong.
- `add_chosen_letter() -> None` — Add the chosen letter to the hangman game.
- `async notify_chosen_letter() -> None` — Notify the user about the chosen letter.
- `async notify_already_chosen() -> None` — Notify the user that the letter was already chosen.
- `async get_hangman_game() -> None` — Get the hangman game. Creates a new one if it doesn't exist.
- `calculate_placement(hangman_players: list[AUH], player: AUH) -> int` — Calculate the placement of the player.
- `rank_hangman_players(hangman_players: list[AUH]) -> None` — Rank the hangman players.
- `fetch_hangman_players() -> list[AUH]` — Fetch all players that played.
- `add_player_score(player: AUH, score: int) -> None` — Add score to player.
- `validate_guessed_letters() -> list[bool]` — Validate guessed letters.
- `get_player_record() -> AUH` — Get the player record. Create if it doesn't exist.
- `create_player_record() -> AUH` — Create a new player record.
- `async new_hangman_game() -> HangmanDb` — Create a new hangman game.

### `class Hangman(GroupCog, auto_load=True)`
A cog that plays the hangman game in a discord chat message.

- `@app_commands.command async slash_hangman(interaction: discord.Interaction) -> None` — Start a hangman game.

## `wd_cogs.games.incremental` — `wd-cogs/src/wd_cogs/games/incremental.py`
Incremental game cog for the Winter Dragon bot.

### `class PlayerManager`
Manages player-related database operations.

- `ensure_player_exists(user_id: int) -> Players` — Ensure a player exists in the database, creating if necessary.

### `class GeneratorManager`
Manages generator-related database operations.

- `get_by_name(name: str) -> Generators | None` — Get a generator by name.
- `create(name: str, description: str, cost_currency: str, cost_amount: int, base_per_second: float) -> Generators` — Create and save a new generator.
- `update(generator: Generators, cost_currency: str | None=None, cost_amount: int | None=None, base_per_second: float | None=None, description: str | None=None) -> None` — Update generator properties.
- `get_all() -> list[Generators]` — Get all generators.

### `class CurrencyManager`
Manages currency-related database operations.

- `get_balance(user_id: int, currency: str) -> int` — Get a user's currency balance.
- `add_currency(user_id: int, currency: str, amount: int) -> UserMoney` — Add currency to a user.

### `class RateManager`
Manages generator rate-related database operations.

- `get_or_create_rate(generator_id: int, currency: str, per_second: float) -> GeneratorRates` — Get or create a rate for a generator.

### `class IncrementalGame(Cog, auto_load=True)`
Cog for managing the incremental game system.

- attributes: admin, currency, rate
- `@app_commands.command @app_commands.guild_only async buy(interaction: Interaction) -> None` — Open the generator shop menu.
- `@app_commands.command @app_commands.guild_only async progress(interaction: Interaction) -> None` — View player's game progress.
- `@admin.command async admin_generator_add(interaction: Interaction, name: str, cost_currency: str, cost_amount: int, base_per_second: float, description: str='A new generator') -> None` — Add a new generator to the game.
- `@admin.command async admin_generator_update(interaction: Interaction, name: str, cost_currency: str | None=None, cost_amount: int | None=None, base_per_second: float | None=None, description: str | None=None) -> None` — Update an existing generator.
- `@admin.command async admin_generator_list(interaction: Interaction) -> None` — List all generators in the game.
- `@currency.command async admin_currency_add(interaction: Interaction, user: discord.User, currency: str, amount: int) -> None` — Add currency to a user.
- `@rate.command async admin_rate_add(interaction: Interaction, generator_name: str, currency: str, per_second: float) -> None` — Add or update a generation rate for a generator and currency combination.

## `wd_cogs.games.incremental_ui` — `wd-cogs/src/wd_cogs/games/incremental_ui.py`
UI components for the incremental game.

### `class GeneratorShopMenu(Menu, SessionMixin)`
Menu for buying generators in the incremental game.

### `class ProgressMenu(Menu, SessionMixin)`
Menu for viewing player progress in the incremental game.

- `embed() -> discord.Embed` — Build the progress settings embed.

## `wd_cogs.games.league_of_legends` — `wd-cogs/src/wd_cogs/games/league_of_legends.py`
Module for League of Legends related Cogs.

### `class CassiopeiaEnumLike(Protocol)`
Minimal enum-like object from Cassiopeia with a .value property.

- fields: value: str

### `class CassiopeiaProfileIcon(Protocol)`
Minimal profile icon shape returned by Cassiopeia objects.

- fields: id: int

### `class CassiopeiaLeagueEntry(Protocol)`
Minimal ranked league entry shape.

- fields: queue: CassiopeiaEnumLike, tier: CassiopeiaEnumLike, division: CassiopeiaEnumLike, league_points: int, wins:
  int, losses: int

### `class CassiopeiaChampion(Protocol)`
Minimal champion shape returned by Cassiopeia.

- fields: name: str

### `class CassiopeiaChampionMastery(Protocol)`
Minimal champion mastery shape from Cassiopeia.

- fields: champion: CassiopeiaChampion, level: int, points: int

### `class CassiopeiaSummoner(Protocol)`
Minimal League of Legends summoner shape used by the bot.

- fields: league_entries: Sequence[CassiopeiaLeagueEntry], match_history: Sequence[Any], champion_masteries:
  Sequence[CassiopeiaChampionMastery], level: int
- `id() -> int | str` — Return the summoner identifier.
- `account_id() -> int | str` — Return the account identifier.
- `profile_icon() -> CassiopeiaProfileIcon` — Return the summoner's profile icon.

### `class CassiopeiaAccount(Protocol)`
Minimal League of Legends account shape used by the bot.

- fields: summoner: CassiopeiaSummoner
- `puuid() -> str` — Return the account's PUUID.

### `class CassiopeiaAccountFactory(Protocol)`
Callable Cassiopeia account constructor interface.

- `__call__(*args: object, **kwargs: object) -> CassiopeiaAccount` — Construct and return a Cassiopeia account object.

### `class CassiopeiaSummonerFactory(Protocol)`
Callable Cassiopeia summoner constructor interface.

- `__call__(*args: object, **kwargs: object) -> CassiopeiaSummoner` — Construct and return a Cassiopeia summoner object.

### `class Region(StrEnum)`
Riot API regions for League of Legends.

- attributes: BR, EUNE, EUW, JP, KR, LAN, LAS, NA, OCE, TR, RU, PH, SG, TH, TW, VN

### `class LeagueOfLegends(GroupCog, auto_load=True)`
League of Legends game.

- `@app_commands.command @app_commands.describe async link_account(interaction: discord.Interaction, summoner_name: str, tag_line: str, region: Region) -> None` — Link a League of Legends account to the user's Discord account.
- `@app_commands.command async unlink_account(interaction: discord.Interaction) -> None` — Unlink a League of Legends account from the user's Discord account.
- `@app_commands.command @app_commands.describe async profile(interaction: discord.Interaction, user: discord.User | None=None) -> None` — Display a user's League of Legends profile.
- `@app_commands.command @app_commands.describe async match_history(interaction: discord.Interaction, user: discord.User | None=None, count: int=5) -> None` — Display a user's recent match history.
- `@app_commands.command @app_commands.describe async champion_mastery(interaction: discord.Interaction, user: discord.User | None=None, count: int=5) -> None` — Display a user's champion mastery.

## `wd_cogs.games.lol_clash` — `wd-cogs/src/wd_cogs/games/lol_clash.py`
Contains the Clash cog for the bot.

- module names: FULL_TEAM_SIZE, TEAM_DATA_WITH_CHAMPS_LEN

### `class CassiopeiaEnumLike(Protocol)`
Minimal enum-like object from Cassiopeia with a .value property.

- fields: value: str

### `class CassiopeiaChampion(Protocol)`
Minimal champion shape returned by Cassiopeia.

- fields: name: str

### `class CassiopeiaLeagueEntry(Protocol)`
Minimal ranked league entry shape.

- fields: queue: CassiopeiaEnumLike, tier: CassiopeiaEnumLike, division: CassiopeiaEnumLike, wins: int, losses: int

### `class CassiopeiaChampionMastery(Protocol)`
Minimal champion mastery shape from Cassiopeia.

- fields: champion: CassiopeiaChampion, points: int

### `class CassiopeiaSummoner(Protocol)`
Minimal League of Legends summoner shape used by the bot.

- fields: league_entries: Sequence[CassiopeiaLeagueEntry], champion_masteries: Sequence[CassiopeiaChampionMastery]

### `class CassiopeiaAccount(Protocol)`
Minimal League of Legends account shape used by the bot.

- `puuid() -> str`

### `class CassiopeiaSummonerFactory(Protocol)`
Callable Cassiopeia summoner constructor interface.

- `__call__(*args: object, **kwargs: object) -> CassiopeiaSummoner`

### `class Clash(GroupCog, auto_load=True)`
Clash cog for League of Legends.

- `@app_commands.command @app_commands.describe async clash_schedule(interaction: discord.Interaction, region: str | None=None) -> None` — Display upcoming Clash schedule for a region.
- `@app_commands.command @app_commands.describe @app_commands.default_permissions async sync_clash_events(interaction: discord.Interaction, region: str | None=None) -> None` — Sync Clash tournaments to Discord scheduled events in this guild.
- `@app_commands.command @app_commands.describe async team_analysis(interaction: discord.Interaction, player1: discord.User, player2: discord.User | None=None, player3: discord.User | None=None, player4: discord.User | None=None, player5: discord.User | None=None) -> None` — Analyze a Clash team composition and provide suggestions.
- `@app_commands.command @app_commands.describe async clash_stats(interaction: discord.Interaction, user: discord.User | None=None) -> None` — Display a user's Clash statistics.
- `@app_commands.command @app_commands.describe async champion_suggestions(interaction: discord.Interaction, role: str, enemy_picks: str | None=None) -> None` — Get champion suggestions based on role and enemy picks.
- `async cog_unload() -> None` — Clean up resources when the cog is unloaded.

## `wd_cogs.games.looking_for_group` — `wd-cogs/src/wd_cogs/games/looking_for_group.py`
Module containing the looking for group cog.

### `@app_commands.guilds class Lfg(GroupCog, auto_load=True)`
LFG cog for finding people to play games with.

- attributes: slash_suggest
- `@app_commands.command async slash_lfg_join(interaction: discord.Interaction, game: str) -> None` — Join a search queue for finding people for the same game.
- `@app_commands.command async slash_lfg_leave(interaction: discord.Interaction) -> None` — Leave all joined search queues.
- `@slash_lfg_join.autocomplete async autocomplete_game(_interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]` — Autocomplete for the game name.
- `async search_match(interaction: discord.Interaction, _game: str) -> None` — Search for a match in the database.

## `wd_cogs.games.love_meter` — `wd-cogs/src/wd_cogs/games/love_meter.py`
Module containing the love meter command.

### `class Love(Cog, auto_load=True)`
Cog for the love meter command.

- `@app_commands.command async love(interaction: discord.Interaction, member: discord.Member) -> None` — Find out if another person is compatible with you.

## `wd_cogs.games.questions.base_question_game` — `wd-cogs/src/wd_cogs/games/questions/base_question_game.py`
Module for an Abstract class, for questionnaire like games.

- module names: T

### `class BaseQuestionGame[T](GroupCog, auto_load=False)`
Base class for question-based games like Never Have I Ever and Would You Rather.

- fields: GAME_NAME: str, GAME_DISPLAY_NAME: str, QUESTION_MODEL: type[T], BASE_QUESTIONS: list[str]
- `set_default_data() -> None` — Set default data to the database if it doesn't exist.
- `get_questions() -> tuple[int, Sequence[T]]` — Get all questions from the database.
- `get_random_question() -> T | None` — Get a random question from the database.
- `create_embed(question: T) -> discord.Embed` — Create a game-specific embed. To be overridden by subclasses.
- `async add_reactions(message: discord.Message) -> None` — Add game-specific reactions. To be overridden by subclasses.
- `async show(interaction: discord.Interaction) -> None` — Send a randomized question to the channel.
- `async add(interaction: discord.Interaction, question: str) -> None` — Add a new question to the game.
- `async add_verified(interaction: discord.Interaction) -> None` — Add all verified questions to the game.

## `wd_cogs.games.questions.never_have_i_ever` — `wd-cogs/src/wd_cogs/games/questions/never_have_i_ever.py`
Module to implement the Would You Rather game.

### `class NeverHaveIEver(BaseQuestionGame[NhieQuestion], auto_load=True)`
Never Have I Ever game implementation.

- attributes: GAME_NAME, GAME_DISPLAY_NAME, QUESTION_MODEL, BASE_QUESTIONS
- `create_embed(question: NhieQuestion) -> discord.Embed`
- `async add_reactions(message: discord.Message) -> None` — Add reactions to the message.
- `@app_commands.command @app_commands.checks.cooldown async slash_nhie_show(interaction: discord.Interaction) -> None` — Send a random Would You Rather question to the channel.
- `@app_commands.command async slash_nhie_add(interaction: discord.Interaction, nhie_question: str) -> None` — Add a Would You Rather question to the game. The question requires verification first.
- `@app_commands.command async slash_nhie_add_verified(interaction: discord.Interaction) -> None` — Add all verified questions to the game.

## `wd_cogs.games.questions.would_you_rather` — `wd-cogs/src/wd_cogs/games/questions/would_you_rather.py`
Module to implement the Would You Rather game.

### `class WouldYouRather(BaseQuestionGame[WyrQuestion], auto_load=True)`
Would You Rather game implementation.

- attributes: GAME_NAME, GAME_DISPLAY_NAME, QUESTION_MODEL, BASE_QUESTIONS
- `create_embed(question: WyrQuestion) -> discord.Embed`
- `async add_reactions(message: discord.Message) -> None` — Add reactions to the message.
- `@app_commands.command @app_commands.checks.cooldown async slash_wyr_show(interaction: discord.Interaction) -> None` — Send a random Would You Rather question to the channel.
- `@app_commands.command async slash_wyr_add(interaction: discord.Interaction, wyr_question: str) -> None` — Add a Would You Rather question to the game. The question requires verification first.
- `@app_commands.command async slash_wyr_add_verified(interaction: discord.Interaction) -> None` — Add all verified questions to the game.

## `wd_cogs.games.riot_clash_api` — `wd-cogs/src/wd_cogs/games/riot_clash_api.py`
Riot Games Clash API client for retrieving tournament schedule and information.

### `class Region(StrEnum)`
Riot API regional routing values for platform independence.

- attributes: AMERICAS, ASIA, EUROPE, SEA

### `class Platform(StrEnum)`
Riot API platform routing values for region-specific endpoints.

- attributes: BR1, EUN1, EUW1, JP1, KR, LA1, LA2, NA1, OC1, PH2, RU, SG2, TH2, TR1, TW2, VN2

### `class ClashPhase(StrEnum)`
Tournament phase stages in Clash.

- attributes: REGISTRATION, BANS_PHASE, LOCKED_IN

### `@dataclass class ClashPhaseTiming`
Timing information for a Clash tournament phase.

- fields: phase: ClashPhase, started_at: datetime, cancelled: bool

### `@dataclass class ClashTournament`
Represents a Clash tournament with schedule and metadata.

- fields: tournament_id: int, name: str, schedule: list[ClashPhaseTiming], icon_url: str, tier: int
- `@property next_phase -> ClashPhaseTiming | None` — Get the next active phase.
- `@property start_time -> datetime | None` — Get the tournament start time (first registration phase).
- `to_embed() -> discord.Embed` — Convert tournament to a Discord embed.

### `class RiotClashAPIError(Exception)`
Base exception for Riot Clash API errors.

### `class RiotClashAPIAuthError(RiotClashAPIError)`
Raised when API authentication fails.

### `class RiotClashAPIRateLimitError(RiotClashAPIError)`
Raised when rate limit is exceeded.

### `class RiotClashClient`
Pythonic async client for Riot Games Clash API.

- attributes: BASE_URL, API_VERSION
- `@property session -> aiohttp.ClientSession` — Get or create the HTTP session.
- `async close() -> None` — Close the HTTP session.
- `async get_tournaments(platform: Platform | str) -> list[ClashTournament]` — Fetch all available Clash tournaments for a platform.
- `async get_tournament_by_id(platform: Platform | str, tournament_id: int) -> ClashTournament | None` — Fetch a specific Clash tournament by ID.
- `async get_tournaments_by_summoner(platform: Platform | str, summoner_id: str) -> list[ClashTournament]` — Fetch all Clash tournaments a summoner is registered in.
- `async get_teams(platform: Platform | str, tournament_id: int) -> list[dict[str, Any]]` — Fetch all teams registered in a Clash tournament.
- `async get_team_by_id(platform: Platform | str, team_id: str) -> dict[str, Any]` — Fetch a specific Clash team by ID.
- `async get_tournaments_by_team(platform: Platform | str, team_id: str) -> list[ClashTournament]` — Fetch tournaments that a team is registered in.
- `async get_player(platform: Platform | str, summoner_id: str) -> list[dict[str, Any]]` — Fetch player Clash data by summoner ID.

### `class DiscordClashEventManager`
Manages Discord scheduled events for Clash tournaments.

- `async create_event(guild: discord.Guild, tournament: ClashTournament) -> discord.ScheduledEvent | None` — Create a Discord scheduled event for a Clash tournament.
- `async sync_tournaments_to_events(guild: discord.Guild, tournaments: list[ClashTournament], remove_old: bool=True) -> tuple[list[discord.ScheduledEvent], list[ClashTournament]]` — Sync Clash tournaments to Discord scheduled events.
- `start_sync_task(clash_client: RiotClashClient, guild: discord.Guild, platform: Platform | str, interval_seconds: int=3600) -> None` — Start a background task to periodically sync tournaments to events.
- `async stop_sync_task() -> None` — Stop the background sync task.
