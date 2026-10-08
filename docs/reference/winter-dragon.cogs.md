<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `winter_dragon.cogs` (winter-dragon)
Cogs for the winter_dragon example bot (see run_test_bot.py).

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `winter_dragon.cogs.bot_commands` — `src/winter_dragon/cogs/bot_commands.py`
Admin command group for inspecting and forcing the application-command sync state.

- `describe_sync_status(session: Session, commands: Sequence[tuple[str, str]]) -> Generator[str]` — Yield one "name: synced|pending" line per (name, signature) pair in ``commands``.

### `class BotCommands(GroupCog, name='bot-commands', description="Inspect and push the bot's application commands", default_member_permissions=Permissions.MANAGE_GUILD, contexts=[InteractionContextType.GUILD])`
Admin ``/bot-commands`` group for inspecting/forcing application-command sync.

- `@Cog.command async list_commands(interaction: CommandInteraction) -> None` — Show every registered command's synced/pending state.
- `@Cog.command async resync(interaction: CommandInteraction) -> None` — Acknowledge within Discord's 3s window, then force the diff-and-push sync.

## `winter_dragon.cogs.fuel` — `src/winter_dragon/cogs/fuel.py`
The /fuel command group: log refuels, and graph fuel efficiency over time.

- module names: GRAPH_SIZE_INCHES, GRAPH_FILENAME
- `render_efficiency_graph(refuels: Sequence[CarFuels]) -> bytes` — Return a PNG line graph of the efficiency of ``refuels`` over time, oldest first; refuels without fuel are left out.

### `class CarFuels(SQLModel, table=True)`
One refuel a user logged; ``user_id`` is their Discord user ID.

- fields: user_id: int, amount: float, distance: float, price: float, timestamp: datetime
- `@property efficiency -> float` — Distance driven per unit of fuel.

### `class Fuel(GroupCog, name='fuel', description="Track your car's refuels and fuel efficiency")`
Logs a user's refuels and graphs their fuel efficiency.

- `async load() -> None` — Create the refuel table if missing.
- `@Cog.command async add(interaction: CommandInteraction, price: float, distance: float, amount: float) -> None` — Store a refuel for the invoking user.
- `@Cog.command async efficiency(interaction: CommandInteraction) -> None` — Reply with a graph of the invoking user's fuel efficiency.

## `winter_dragon.cogs.heartbeat` — `src/winter_dragon/cogs/heartbeat.py`
A cog demonstrating independent background work, not just reacting to dispatch events.

- module names: HEARTBEAT_INTERVAL_SECONDS

### `class Heartbeat(Cog)`
Logs "still alive" roughly once a minute for as long as the bot keeps running.

- `async load() -> None` — Start the heartbeat background task once registered with the bot.

## `winter_dragon.cogs.invite` — `src/winter_dragon/cogs/invite.py`
The /invite command group: invite the bot to a guild, or join the support guild.

- module names: SUPPORT_INVITE_MAX_AGE
- `async invite_channel(client: Client, guild_id: int) -> BaseChannel | NetworkError | None` — Return the channel to invite people to in the guild ``guild_id``: its system channel, else its first text channel.

### `class Invite(GroupCog, name='invite', description='Invite the bot to your guild, or join its support guild')`
Cog for inviting the bot to a guild or getting support.

- `@Cog.command async bot_invite(interaction: CommandInteraction) -> None` — Reply with the link that adds the bot to a guild.
- `@Cog.command async support_invite(interaction: CommandInteraction) -> None` — Reply with a single-use, short-lived invite to the support guild.

## `winter_dragon.cogs.message_logger` — `src/winter_dragon/cogs/message_logger.py`
A cog that logs real gateway dispatch events at DEBUG level.

### `class MessageLogger(Cog)`
Logs every READY/MESSAGE_CREATE/GUILD_CREATE it's dispatched, at DEBUG level.

- `@Cog.listener async on_ready(ready: Ready) -> None` — Log a shard's READY.
- `@Cog.listener async on_message_create(message: Message) -> None` — Log a dispatched MESSAGE_CREATE event.
- `@Cog.listener async on_guild_create(guild: Guild) -> None` — Log a dispatched GUILD_CREATE event.

## `winter_dragon.cogs.percentage` — `src/winter_dragon/cogs/percentage.py`
A cog with a single command: a random compatibility percentage between two users.

- `calculate_percentage(user_id_a: int, user_id_b: int) -> int` — Compute a random 0-100 percentage, seeded by both user IDs (order-independent).
- `build_love_embed(target: User, percent: int) -> Embed` — Build the "Love Meter" embed for ``target`` with the given compatibility ``percent``.

### `class Love(Cog)`
Cog for the /love command.

- `@Cog.command async love(interaction: CommandInteraction, user: User) -> None` — Reply with a random compatibility love between the invoking user and ``user``.

## `winter_dragon.cogs.reminder` — `src/winter_dragon/cogs/reminder.py`
The /reminder command group: one-off and repeating reminders, sent as DMs by a background task.

- module names: MAX_DELAY, MAX_CONTENT_LENGTH, MAX_CHOICE_NAME_LENGTH, SECONDS_PER_UNIT, REMINDER_TABLES,
  CHOICE_PREFIXES: dict[type[AnyReminder], str]
- `type AnyReminder = Reminder | TimedReminder`
- `utc_now() -> datetime` — Return the current time in UTC.
- `delay_from(**amounts: int) -> timedelta | None` — Return the delay made of ``amounts`` per unit (``minutes=5, hours=1``), or ``None`` if it's not in (0, MAX_DELAY].
- `next_occurrence(due: datetime, repeat_every: timedelta, now: datetime) -> datetime` — Return the first time after ``now`` that a reminder due at ``due`` and repeating every ``repeat_every`` is due.
- `reminder_message(content: str) -> str` — Return the DM reminding someone of ``content``.
- `choice_value(reminder: AnyReminder) -> str` — Return the autocomplete value naming ``reminder``: its table and ID, like ``repeat:12``.
- `owned_reminders(session: Session, user_id: int) -> Generator[AnyReminder]` — Yield every reminder of the user ``user_id``: repeating ones first, then one-off ones by when they're due.
- `find_reminder(session: Session, user_id: int, reminder: str) -> AnyReminder | None` — Return the reminder of the user ``user_id`` that ``reminder`` names.
- `reminder_choices(reminders: Generator[AnyReminder], current: str) -> Generator[ApplicationCommandOptionChoice]` — Yield a choice for each of ``reminders`` whose content contains ``current``, ignoring case.
- `async send_reminder(client: Client, reminder: AnyReminder) -> bool` — DM ``reminder`` to its user; ``False`` when Discord refused it (e.g. their DMs are closed).

### `class ReminderBase(SQLModel)`
What one-off and repeating reminders share; ``user_id`` is the Discord user to remind.

- fields: content: str, user_id: int, timestamp: datetime

### `class Reminder(ReminderBase, table=True)`
A reminder sent once, then removed.

### `class TimedReminder(ReminderBase, table=True)`
A reminder sent again every :attr:`repeat_every`, until removed.

- fields: repeat_every: timedelta

### `class Reminders(GroupCog, name='reminder', description='Set reminders for yourself')`
Stores reminders and DMs them to their users when due, from a background task.

- `async load() -> None` — Create the reminder tables if missing, then start the background task sending due reminders.
- `async unload() -> None` — Stop the background task.
- `async send_due(now: datetime) -> int` — DM every reminder due at ``now``; remove one-off ones and move repeating ones on. Return how many were due.
- `@Cog.command async add(interaction: CommandInteraction, reminder: str, minutes: int=0, hours: int=0, days: int=0) -> None` — Remind the invoking user of ``reminder`` once, after the given time.
- `@Cog.command async repeat(interaction: CommandInteraction, reminder: str, minutes: int=0, hours: int=0, days: int=0, weeks: int=0) -> None` — Remind the invoking user of ``reminder`` every given time, starting one interval from now.
- `@Cog.command async remove(interaction: CommandInteraction, reminder: str) -> None` — Remove the invoking user's reminder named by ``reminder``.
- `@remove.autocomplete async remove_choices(interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]` — Suggest the invoking user's reminders whose content contains what they typed.

## `winter_dragon.cogs.steam.cog` — `src/winter_dragon/cogs/steam/cog.py`
The /steam command group, its page buttons, and the background scrape of Steam's specials.

- module names: DEFAULT_THRESHOLD, MAX_PERCENT, MIN_SLEEP_SECONDS, SALE_END_HOUR_UTC, ROLLOVER_GRACE
- `next_scrape_time(now: datetime, interval: timedelta) -> datetime` — Return when to scrape next: after ``interval``, or just after Steam's daily rollover if that comes first.
- `sale_queries(percent: int, complete_percent: int, top_sellers: int) -> Generator[tuple[int, int | None]]` — Yield the ``(percent, limit)`` of each query a scrape makes.
- `utc_now() -> datetime` — Return the current time in UTC.

### `class SteamSales(GroupCog, name='steam', description='Get notified about free and discounted Steam games')`
Lists Steam sales on request and DMs subscribers new ones, re-checking sales right after they end.

- `@property throttle -> RequestThrottle` — The request throttle every scraper of this cog shares, so spacing and rate-limit pauses span them all.
- `async load() -> None` — Create the Steam tables if missing, then start the background scrape loop.
- `async unload() -> None` — Stop the background scrape loop.
- `async scrape(now: datetime) -> None` — Ask Steam for its sales, store them, and DM subscribers new ones.
- `async recheck_due(now: datetime) -> None` — Check the sales whose announced end has passed: update those still running, remove those that ended.
- `@Cog.command async add(interaction: CommandInteraction) -> None` — Subscribe the invoking user to Steam sale DMs.
- `@Cog.command async percentage(interaction: CommandInteraction, percent: int) -> None` — Set the minimum discount the invoking user is notified about.
- `@Cog.command async remove(interaction: CommandInteraction) -> None` — Unsubscribe the invoking user from Steam sale DMs.
- `@Cog.command async show(interaction: CommandInteraction, percent: int=DEFAULT_THRESHOLD) -> None` — Show the first page of current sales of at least ``percent``, with buttons to page through them.
- `@Cog.component async show_page(interaction: ComponentInteraction, owner_id: str, percent: str, page: str) -> None` — Turn a /steam show listing to ``page``; only the user who ran the command may.

## `winter_dragon.cogs.steam.models` — `src/winter_dragon/cogs/steam/models.py`
Database tables for Steam sales and the users subscribed to them.

- module names: STEAM_TABLES

### `class SaleTypes(StrEnum)`
What kind of store item a sale is for, beyond a plain game.

- attributes: DLC, BUNDLE

### `class SteamSale(SQLModel, table=True)`
A Steam store item on sale; ``id`` is its Steam app (or bundle/sub) ID.

- fields: title: str, url: str, sale_percent: int, final_price: float, update_datetime: datetime, discovered_at:
  datetime, sale_end: datetime | None
- `@property steam_url -> SteamURL` — The sale's store page.
- `is_outdated(after: timedelta, now: datetime) -> bool` — Whether the sale hasn't been seen on Steam for at least ``after``.

### `class SteamSaleProperties(SQLModel, table=True)`
One :class:`SaleTypes` a sale has.

- fields: steam_sale_id: int, property: SaleTypes

### `class SteamUsers(DiscordID, table=True)`
A Discord user subscribed to Steam sale DMs; ``id`` is their Discord user ID.

- fields: sale_threshold: int, last_notification: datetime

## `winter_dragon.cogs.steam.notifier` — `src/winter_dragon/cogs/steam/notifier.py`
DM subscribers the Steam sales they haven't been told about yet.

### `@dataclass class SteamSaleNotifier(LoggerMixin)`
Sends each subscriber one DM with the sales above their threshold discovered since their last notification.

- fields: client: Client, store: SteamSaleStore, color: int
- `async notify(*, now: datetime, content: str) -> int` — DM every subscriber with new sales, with ``content`` above the embed; return how many were notified.

## `winter_dragon.cogs.steam.pages` — `src/winter_dragon/cogs/steam/pages.py`
Embeds and buttons that show Steam sales: the pages of /steam show and the sale DMs.

- module names: ITEMS_PER_PAGE, MAX_FIELD_NAME_LENGTH, HTTP_SCHEMES
- `format_sale(sale: SteamSale, properties: set[SaleTypes]) -> str` — Describe one sale: link, discount, price, kind, when it was last seen, and an install link for apps.
- `page_count(total: int) -> int` — Return how many /steam show pages ``total`` sales take; at least one.
- `build_page(sales: Sequence[SteamSale], properties: Mapping[int, set[SaleTypes]], *, page: int, color: int) -> Embed` — Build page ``page`` (0-based, clamped to the valid range) of the /steam show listing of ``sales``.
- `page_buttons(handler: ComponentHandler, *, owner_id: int, percent: int, page: int, pages: int) -> list[ActionRow]` — Build the previous / page counter / next buttons under page ``page`` of ``pages``.
- `build_notification(sales: Sequence[SteamSale], properties: Mapping[int, set[SaleTypes]], *, color: int) -> Embed` — Build the DM embed announcing ``sales``, dropping trailing sales that don't fit Discord's embed limits.

## `winter_dragon.cogs.steam.scrapers` — `src/winter_dragon/cogs/steam/scrapers.py`
Find Steam sales through Steam's store web APIs.

- module names: STORE_API_URL, QUERY_URL, GET_ITEMS_URL, QUERY_PAGE_SIZE, GET_ITEMS_BATCH_SIZE, TOP_SELLERS_SORT,
  MIN_DISCOUNT_FILTER, REQUEST_TIMEOUT_SECONDS, DEFAULT_REQUEST_INTERVAL, DEFAULT_COUNTRY_CODE, LANGUAGE, RATE_LIMITED

### `class ScrapeFailure(Enum)`
Why Steam gave no answer, as opposed to answering "not on sale".

- attributes: UNAVAILABLE

### `@dataclass class ScrapedSale`
One sale as found on Steam.

- fields: id: int, title: str, url: SteamURL, sale_percent: int, final_price: float, properties: frozenset[SaleTypes],
  sale_end: datetime | None
- `@classmethod from_store_item(item: StoreItem) -> Self | None` — Return the sale on ``item``, or ``None`` when it isn't discounted (or isn't a store item Steam knows).

### `class SteamScraper(LoggerMixin)`
Asks Steam's store APIs for sales; use as ``async with SteamScraper() as scraper``.

- `async query_sales(percent: int, limit: int | None=None) -> AsyncGenerator[ScrapedSale]` — Yield the sales of at least ``percent``, best-selling first: the first ``limit``, or every one without.
- `async get_sales(items: Iterable[StoreItemID]) -> AsyncGenerator[tuple[StoreItemID, ScrapedSale | ScrapeFailure | None]]` — Yield each item with its current sale, ``None`` when it isn't on sale, or why Steam gave no answer.

## `winter_dragon.cogs.steam.store` — `src/winter_dragon/cogs/steam/store.py`
Storing and querying Steam sales and their subscribers.

### `@dataclass class SteamSaleStore`
Reads and writes Steam sales through one database session.

- fields: session: Session
- `record(scraped: ScrapedSale, *, now: datetime, outdated_after: timedelta) -> tuple[SteamSale, bool]` — Store a scraped sale, returning the stored row and whether it counts as new.
- `refresh(sale: SteamSale, scraped: ScrapedSale, *, now: datetime) -> None` — Apply what Steam now says about ``sale``: its current discount, end and properties.
- `remove(sale: SteamSale) -> None` — Delete ``sale`` and its properties.
- `properties(sales: Iterable[SteamSale]) -> dict[int, set[SaleTypes]]` — Return the properties of each of ``sales``, by sale ID.
- `current_sales(percent: int, *, now: datetime, outdated_after: timedelta) -> list[SteamSale]` — Return the sales of at least ``percent`` still running: biggest discount first, then cheapest.
- `unseen_without_end(moment: datetime, percent: int, *, outdated_after: timedelta) -> list[SteamSale]` — Return the shown sales of at least ``percent`` last seen before ``moment``, longest unseen first.
- `due_rechecks(*, now: datetime, delay: timedelta) -> Sequence[SteamSale]` — Return the sales whose announced end was at least ``delay`` ago.
- `next_recheck(*, delay: timedelta) -> datetime | None` — Return when the next sale is due for a re-check, if any sale has a known end.
- `new_since(moment: datetime, percent: int) -> list[SteamSale]` — Return the sales of at least ``percent`` discovered after ``moment``, newest first.
- `subscriber(user_id: int) -> SteamUsers | None` — Return the subscription of ``user_id``, if subscribed.
- `subscribers() -> Sequence[SteamUsers]` — Return every subscribed user.
- `lowest_threshold() -> int | None` — Return the lowest ``sale_threshold`` among subscribers, or ``None`` without subscribers.

## `winter_dragon.cogs.steam.store_api` — `src/winter_dragon/cogs/steam/store_api.py`
The parts of Steam's store web APIs the sale finder reads.

- module names: ITEM_KINDS, DLC_APP_TYPE, FOUND

### `class SteamModel(BaseModel)`
A part of a Steam store API answer.

- attributes: model_config

### `class ActiveDiscount(SteamModel)`
One discount applied to a purchase option.

- fields: discount_end_date: datetime | None

### `class PurchaseOption(SteamModel)`
The cheapest way to buy a store item, and the discount it gets.

- fields: final_price_in_cents: int, discount_pct: int, active_discounts: list[ActiveDiscount], is_free_to_keep: bool,
  free_to_keep_ends: datetime | None
- `@property discount_end -> datetime | None` — When the discount ends: its first discount to run out, or the end of a free giveaway.

### `class StoreItem(SteamModel)`
An app, package or bundle on the Steam store.

- fields: item_type: int, id: int, success: int, name: str, store_url_path: str, type: int, best_purchase_option:
  PurchaseOption | None
- `@property item_id -> StoreItemID | None` — The item's ID, or ``None`` for an ``item_type`` the sale finder doesn't know.
- `@property url -> SteamURL | None` — The item's store page.

### `class QueryMetadata(SteamModel)`
How many items a store query matches in total.

- fields: total_matching_records: int

### `class QueryResult(SteamModel)`
One page of ``IStoreQueryService/Query`` results.

- fields: metadata: QueryMetadata, store_items: list[StoreItem]

### `class QueryResponse(SteamModel)`
The answer of ``IStoreQueryService/Query``.

- fields: response: QueryResult

### `class ItemsResult(SteamModel)`
The items ``IStoreBrowseService/GetItems`` looked up.

- fields: store_items: list[StoreItem]

### `class ItemsResponse(SteamModel)`
The answer of ``IStoreBrowseService/GetItems``.

- fields: response: ItemsResult

## `winter_dragon.cogs.steam.throttle` — `src/winter_dragon/cogs/steam/throttle.py`
Space out requests to Steam, and stop sending them for a while once Steam rate-limits us.

- module names: INITIAL_BACKOFF_SECONDS, MAX_BACKOFF_SECONDS

### `@dataclass class RequestThrottle`
Lets requests through at least ``interval`` seconds apart, and none at all while paused by a rate limit.

- fields: interval: float, clock: Callable[[], float], sleep: Callable[[float], Awaitable[None]], sent: int
- `@property paused -> bool` — Whether requests are paused after a rate-limit answer.
- `async acquire() -> bool` — Wait for the next request slot and claim it; ``False`` (without waiting) while paused.
- `rate_limited(retry_after: float | None) -> float` — Pause requests for ``retry_after`` seconds, or the current backoff when Steam didn't say; return the pause.
- `succeeded() -> None` — Reset the backoff after a request Steam answered normally.

## `winter_dragon.cogs.steam.urls` — `src/winter_dragon/cogs/steam/urls.py`
Steam store URLs, and the IDs of the store items they point at.

- module names: STORE_URL, APP_URL_PATTERN, ITEM_URL_PATTERN, ITEM_PATHS

### `class StoreItemKind(StrEnum)`
What a Steam store ID numbers; the value is the key Steam's store APIs take such an ID under.

- attributes: APP, PACKAGE, BUNDLE
- `@property path -> str` — The store URL path segment of this kind's pages.

### `@dataclass class StoreItemID`
One store item: app, package and bundle IDs are separate number ranges, so the kind is part of the ID.

- fields: kind: StoreItemKind, id: int
- `as_request() -> dict[str, int]` — Return this ID the way Steam's store APIs take it, e.g. ``{"appid": 730}``.
- `@property url -> SteamURL` — The item's store page.

### `class SteamURL(str)`
A Steam store URL.

- `@property app_id -> int | None` — The app ID of an app page URL, or ``None`` for any other page (bundles, subs, search).
- `@property is_app -> bool` — Whether this URL points at a single app's store page.
- `@property is_bundle -> bool` — Whether this URL points at a bundle (``/bundle/``) or a package (``/sub/``).
- `@property store_item -> StoreItemID | None` — The store item this URL's page is for, or ``None`` for a page that isn't one item's.

## `winter_dragon.cogs.uptime` — `src/winter_dragon/cogs/uptime.py`
The /uptime command group: how long the bot has been running.

- `uptime_message(launch_time: datetime) -> str` — Return the reply to /uptime bot: when the bot started, as an absolute and a relative Discord timestamp.

### `class Uptime(GroupCog, name='uptime', description='Show how long the bot has been running')`
Cog for showing the bot's uptime.

- `@Cog.command async bot_uptime(interaction: CommandInteraction) -> None` — Reply with when the bot started.

## `winter_dragon.cogs.urban` — `src/winter_dragon/cogs/urban.py`
The /urban command group: look up a term, or random terms, on Urban Dictionary.

- module names: DEFINE_URL, RANDOM_URL, REQUEST_TIMEOUT_SECONDS, MAX_FIELD_VALUE, ELLIPSIS
- `truncate(text: str, limit: int) -> str` — Return ``text``, cut to ``limit`` characters with an ellipsis when it's longer.
- `definition_field(index: int, definition: Definition) -> EmbedField` — Return the embed field showing ``definition``, numbered ``index``, with its votes and link.
- `definition_fields(definitions: Sequence[Definition], limit: int, budget: int) -> Generator[EmbedField]` — Yield a field for each of the first ``limit`` definitions, stopping before their text exceeds ``budget``.
- `build_embed(title: str, definitions: Sequence[Definition], limit: int) -> Embed` — Return an embed titled ``title`` showing up to ``limit`` of ``definitions``, within Discord's embed limits.

### `class Definition(BaseModel)`
One definition of a term, as Urban Dictionary's API returns it.

- fields: word: str, definition: str, permalink: str, thumbs_up: int, thumbs_down: int

### `class DefinitionList(BaseModel)`
The body of an Urban Dictionary API response.

- fields: definitions: list[Definition]

### `class LookupFailed(BaseError)`
Urban Dictionary couldn't be asked, or answered something unexpected; the message says which, for the user.

### `class UrbanDictionary(LoggerMixin)`
Asks Urban Dictionary's API for definitions; use as ``async with UrbanDictionary() as urban``.

- `async define(term: str) -> list[Definition] | LookupFailed` — Return the definitions of ``term``, best first; empty when it has none.
- `async random() -> list[Definition] | LookupFailed` — Return a handful of definitions of random terms.

### `class Urban(GroupCog, name='urban', description='Look up words on Urban Dictionary')`
Looks up terms on Urban Dictionary.

- fields: http: AsyncClient | None
- `@Cog.command async search(interaction: CommandInteraction, query: str) -> None` — Reply with the definitions of ``query``.
- `@Cog.command async random(interaction: CommandInteraction) -> None` — Reply with definitions of random terms, unless that's turned off.
