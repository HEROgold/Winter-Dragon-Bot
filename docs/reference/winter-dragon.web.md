<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `winter_dragon.web` (winter-dragon)
The web dashboard: htmx and Jinja pages served by FastAPI, run with ``python -m winter_dragon.web``.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `winter_dragon.web.accounts` — `src/winter_dragon/web/accounts.py`
Who is signed in to the dashboard, kept in the signed session cookie, and the CSRF token their forms carry.

- module names: ACCOUNT_KEY, CSRF_KEY, STATE_KEY, CSRF_FIELD, ZONE_COOKIE
- `current_account(request: Request) -> Account | None` — Return the account signed in on ``request``, if any.
- `signed_in(request: Request) -> Account` — Return the signed-in account; the FastAPI dependency of every page that needs one.
- `sign_in(request: Request, account: Account) -> None` — Start a fresh session for ``account``, dropping whatever the old one held.
- `sign_out(request: Request) -> None` — End the session on ``request``.
- `csrf_token(request: Request) -> str` — Return the session's CSRF token, creating it on first use.
- `async checked_csrf(request: Request) -> None` — Refuse a state-changing request whose form doesn't carry the session's CSRF token; a FastAPI dependency.
- `visitor_zone(request: Request) -> ZoneInfo` — Return the time zone the visitor's browser reported, or UTC until it has.

### `class Account(BaseModel)`
The Discord user signed in to the dashboard: only what its pages show of them.

- fields: id: int, username: str, display_name: str, avatar_url: str | None
- attributes: model_config
- `@classmethod from_user(user: User) -> Self` — Return the account of the Discord ``user``.
- `@property initials -> str` — The first two letters of the display name, shown when there is no avatar.

### `class SignInRequired(Exception)`
A page that needs a signed-in account was opened without one.

## `winter_dragon.web.app` — `src/winter_dragon/web/app.py`
The dashboard's FastAPI app: its pages, the session cookie they share, and where a page that needs sign-in sends you.

- module names: SESSION_COOKIE
- `create_app(*, bind: Engine, session_secret: str, session_lifetime: timedelta=timedelta(days=14), https_only: bool=False) -> FastAPI` — Return the dashboard on the database ``bind``, its session cookie signed with ``session_secret``.

## `winter_dragon.web.auth` — `src/winter_dragon/web/auth.py`
Signing in with Discord and out again; the callback sets the HttpOnly session cookie, never a token.

- module names: router, LOGIN_PATH
- `@router.get login(request: Request) -> Response` — Send the visitor to Discord to sign in, remembering the ``state`` the callback must bring back.
- `@router.get async callback(request: Request, code: str | None=None, state: str | None=None, error: str | None=None) -> Response` — Finish signing in with the ``code`` Discord sent back, if its ``state`` is the one this session asked for.
- `@router.post logout(request: Request) -> Response` — Sign out, and go back to the landing page.

## `winter_dragon.web.discord_oauth` — `src/winter_dragon/web/discord_oauth.py`
Signing in with Discord: the OAuth2 authorization code grant, used only to learn who is signing in.

- module names: CALLBACK_PATH, REQUEST_TIMEOUT, logger
- `redirect_uri() -> str` — Return the callback URL Discord redirects to, under :attr:`DashboardSettings.public_url`.
- `authorization_url(state: str) -> str` — Return the Discord page asking the user to sign in, which sends ``state`` back to the callback.
- `async signed_in_user(code: str) -> User | None` — Return the Discord user who authorized the dashboard with ``code``; ``None`` when Discord refused it.

### `class AccessToken(DiscordModel)`
The token response of the code grant (https://docs.discord.com/developers/topics/oauth2#authorization-code-grant-access-token-response).

- fields: access_token: str, token_type: str, expires_in: int, scope: str, refresh_token: str | None

## `winter_dragon.web.formatting` — `src/winter_dragon/web/formatting.py`
How the dashboard writes stored values for people: times in their zone, intervals and table names in words.

- `humanized_name(name: str) -> str` — Return a class or field name as words: ``TimedReminder`` is ``Timed reminder``, ``repeat_every`` ``Repeat every``.
- `plural(count: int, noun: str) -> str` — Return ``count`` with ``noun``, plural unless there's one: ``1 entry``, ``3 entries``, ``2 reminders``.
- `every(interval: timedelta) -> str` — Return how often something repeating every ``interval`` happens: ``Every day``, ``Every 3 days``.
- `day_label(day: date, today: date) -> str` — Return ``day`` as a heading on ``today``: ``Today``, ``Tomorrow``, or ``Tuesday 21 October`` (with any other year).
- `shown_value(value: object, zone: ZoneInfo) -> str` — Return a stored ``value`` as the data page shows it: times in ``zone``, intervals in words, nothing as a dash.

## `winter_dragon.web.pages` — `src/winter_dragon/web/pages.py`
The landing page, and the data page: everything the bot stores about the signed-in member, and deleting it.

- module names: router
- `signposts(bind: Engine, member_id: int) -> Signposts` — Return what the signpost arms say for the member ``member_id``.
- `@router.get landing(request: Request, bind: Engine) -> Response` — Show what the bot does, with the way in: signing in, or adding it to a server.
- `@router.get data_page(request: Request, account: Account, bind: Engine) -> Response` — Show everything the bot stores about the signed-in member, and the way to delete it.
- `@router.get record_rows(request: Request, key: str, account: Account, bind: Engine) -> Response` — Show the signed-in member's rows of the table ``key``, when its record is opened.
- `@router.get deletion_ask(request: Request, account: Account, bind: Engine) -> Response` — Show the deletion section as it first is: what deleting does, and the button to start.
- `@router.get deletion_confirm(request: Request, account: Account, bind: Engine) -> Response` — Ask the member to type their username, to confirm they mean to delete their data.
- `@router.post request_deletion(request: Request, account: Account, bind: Engine, confirm_name: str='') -> Response` — Hide all of the member's data for their deletion request, once they typed their username to confirm it.

### `@dataclass class DeletionProgress`
How far the member's latest deletion request got: each step done, with when.

- fields: steps: tuple[tuple[DeletionStep, datetime], ...]
- `@property pending -> bool` — Whether a request is in progress: their data is hidden, but not purged for good yet.
- `@property purge_due -> datetime | None` — When the data of a pending request is purged for good; ``None`` without one.

### `@dataclass class Signposts`
What the landing page's signpost arms say a signed-in member will find down each way.

- fields: reminders: str, records: str

## `winter_dragon.web.profile` — `src/winter_dragon/web/profile.py`
The Profile: a member's own pages, one per feature, across every guild.

- module names: router
- `type ContextBuilder = Callable[[ProfileContext], Mapping[str, object]]`
- `profile_page(*, slug: str, title: str, template: str) -> Callable[[ContextBuilder], ContextBuilder]` — Register the decorated function as the context builder of a Profile page; return it unchanged.
- `profile_pages() -> list[ProfilePage]` — Return every registered page, by title.
- `load_profile_pages() -> None` — Import every module in ``web/profile_pages/``, so each registers its page.
- `@router.get profile(request: Request) -> Response` — Show the signed-in member's Profile: a link to each feature's page.
- `@router.get profile_page_view(request: Request, slug: str, account: Account, bind: Engine) -> Response` — Show the signed-in member's page ``slug`` of the Profile.

### `@dataclass class ProfileContext`
What a Profile page reads to build itself: the database, the member whose Profile it is, and their time zone.

- fields: bind: Engine, member_id: int, zone: ZoneInfo

### `@dataclass class ProfilePage`
One feature's page in the Profile.

- fields: slug: str, title: str, template: str, context: ContextBuilder
- `@property path -> str` — The URL the page is served at.

## `winter_dragon.web.profile_pages.fuel` — `src/winter_dragon/web/profile_pages/fuel.py`
The Profile's fuel page: an efficiency graph over time and a table of the member's refuels, newest first.

- module names: GRAPH_WIDTH, GRAPH_HEIGHT, GRAPH_PADDING
- `efficiency_graph(refuels: Sequence[CarFuels], units: FuelUnits) -> EfficiencyGraph | None` — Return the graph of ``refuels`` in ``units``, or ``None`` when none of them added fuel.
- `@profile_page fuel(context: ProfileContext) -> dict[str, object]` — Return the fuel page's context: the member's refuels, newest first, and their efficiency graph.

### `@dataclass class GraphPoint`
One refuel on the graph, in SVG coordinates.

- fields: x: float, y: float, label: str

### `@dataclass class EfficiencyGraph`
The efficiency of a member's refuels over time, ready to draw as an SVG line.

- fields: points: tuple[GraphPoint, ...], lowest: float, highest: float, first_day: datetime, last_day: datetime
- `@property line -> str` — The ``points`` attribute of the SVG polyline.

## `winter_dragon.web.profile_pages.love` — `src/winter_dragon/web/profile_pages/love.py`
The Profile's love page: everyone the member has checked their compatibility with, highest percentage first.

- `@profile_page love(context: ProfileContext) -> dict[str, object]` — Return the love page's context: the member's checks with their percentage, highest first, then newest.

## `winter_dragon.web.profile_pages.steam` — `src/winter_dragon/web/profile_pages/steam.py`
The Profile's Steam page: the sales Steam DMs told the member about, newest first, with a total.

- `@profile_page steam(context: ProfileContext) -> dict[str, object]` — Return the Steam page's context: the member's sale notifications, newest first.

## `winter_dragon.web.profile_pages.urban` — `src/winter_dragon/web/profile_pages/urban.py`
The Profile's Urban Dictionary page: the member's lookups, newest first, with a total.

- `@profile_page urban(context: ProfileContext) -> dict[str, object]` — Return the Urban page's context: the member's lookups, newest first, in their time zone.

## `winter_dragon.web.records` — `src/winter_dragon/web/records.py`
What the dashboard shows of the bot: the features its cogs define, and every record it stores about a member.

- module names: HIDDEN_FIELDS
- `create_dashboard_tables(bind: Engine) -> None` — Make sure the tables the dashboard writes to exist (deletion requests and reminders), as the bot's cogs do.
- `features() -> Generator[Feature]` — Yield every command group the app's cogs define, by name; call :func:`~winter_dragon.cogs.import_cogs` first.
- `member_records(bind: Engine, member_id: int) -> Generator[DataRecord]` — Yield a record for every table holding rows the member ``member_id`` owns, by name.
- `record_table(bind: Engine, member_id: int, key: str, zone: ZoneInfo) -> RecordTable | None` — Return the rows the member ``member_id`` owns in the table ``key``, times in ``zone``; ``None`` for no such table.

### `@dataclass class Feature`
A command group the bot offers: ``/name``, and what it does.

- fields: name: str, description: str

### `@dataclass class DataRecord`
One table's worth of what the bot stores about a member: which table, and how many rows.

- fields: model: type[LifecycleModel], count: int
- `@property key -> str` — The table's name, which the page asks for the rows by.
- `@property name -> str` — The table's name in words.
- `@property summary -> str` — How many rows there are, in words.

### `@dataclass class RecordTable`
The rows of one :class:`DataRecord`, as the data page shows them.

- fields: columns: tuple[str, ...], rows: tuple[tuple[str, ...], ...]

## `winter_dragon.web.reminders` — `src/winter_dragon/web/reminders.py`
The reminders page: a member's reminders by day, and adding or removing one, as ``/reminder`` does in Discord.

- module names: router
- `blank_draft(zone: ZoneInfo, now: datetime) -> ReminderDraft` — Return an empty add form, due tomorrow morning in ``zone``.
- `reminder_days(bind: Engine, user_id: int, zone: ZoneInfo, now: datetime) -> Generator[ReminderDay]` — Yield the user ``user_id``'s reminders grouped by the day they're due in ``zone``, soonest first.
- `@router.get reminders_page(request: Request, account: Account, bind: Engine) -> Response` — Show the signed-in member's reminders and the form to add one.
- `@router.post add_reminder(request: Request, account: Account, bind: Engine, content: str='', day: str='', at: str='', repeat: str=Repeat.NEVER, every_days: str='3') -> Response` — Add the reminder the form describes, or show the form again with why it can't be set.
- `@router.post remove_reminder(request: Request, key: str, account: Account, bind: Engine) -> Response` — Remove the signed-in member's reminder ``key``; someone else's, or one already gone, is left be.

### `class Repeat(StrEnum)`
How often a reminder added on the page comes back.

- attributes: NEVER, DAILY, WEEKLY, EVERY_DAYS

### `class InvalidReminderError(ValueError)`
The add form describes a reminder that can't be set; the message says why, for the person who filled it in.

### `@dataclass class ReminderDraft`
What the add form holds, as typed, so a refused form comes back filled in.

- fields: content: str, day: str, at: str, repeat: Repeat, every_days: str
- `reminder(user_id: int, zone: ZoneInfo, now: datetime) -> AnyReminder` — Return the reminder this draft describes for the user ``user_id``, read in ``zone`` and checked against ``now``.

### `@dataclass class ReminderStop`
One reminder on the page, with its due time in the visitor's zone.

- fields: reminder: AnyReminder, zone: ZoneInfo
- `@property key -> str` — The reminder's table and ID, which its delete button posts to.
- `@property due -> datetime` — When it's due next, in the visitor's zone.
- `@property repeat -> str | None` — How often it comes back, in words; ``None`` for a one-off.

### `@dataclass class ReminderDay`
The reminders due on one day, under its heading.

- fields: label: str, stops: tuple[ReminderStop, ...]

## `winter_dragon.web.responses` — `src/winter_dragon/web/responses.py`
Rendering the dashboard's templates, as a whole page or as the fragment an htmx request swaps in.

- module names: TEMPLATES_DIR, STATIC_DIR, templates
- `is_htmx(request: Request) -> bool` — Whether ``request`` came from htmx, which swaps in a fragment instead of loading a page.
- `render(request: Request, name: str, *, status_code: int=status.HTTP_200_OK, **context: object) -> Response` — Render the template ``name`` with ``context``, plus the signed-in account and the CSRF token every form carries.
- `render_mapping(request: Request, name: str, context: Mapping[str, object], *, status_code: int=status.HTTP_200_OK) -> Response` — Like :func:`render`, for a ``context`` built elsewhere, whose keys can't be passed as keyword arguments.
- `see_other(url: str) -> RedirectResponse` — Redirect a submitted form to the page ``url``, which the browser then loads with a GET.
- `database(request: Request) -> Engine` — Return the database the app was created on; a FastAPI dependency.

## `winter_dragon.web.settings` — `src/winter_dragon/web/settings.py`
The dashboard's config scope, in ``dashboard.ini``; only the web process defines it, so the bot never asks for it.

- module names: DASHBOARD_CONFIG_FILE

### `class DashboardConfig[T](Config[T])`
Config descriptor scoped to the dashboard settings file.

### `class DashboardSettings`
Where the dashboard is served, and how it signs people in with Discord.

- attributes: host, port, public_url, client_secret, session_secret, session_days
- `@classmethod https_only() -> bool` — Whether the dashboard is served over HTTPS, so its session cookie is only ever sent over it.
