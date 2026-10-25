# Commands

A slash command is a cog method decorated with `@Cog.command`. Its parameters after `self` and `interaction`
become the command's options. wd-bot reads each parameter's annotation to decide what Discord asks the user
for, and uses the same annotation to build the argument it passes to the method.

```python
lazy from typing import Annotated

lazy from wd_bot.cogs import Cog
lazy from wd_bot.commands import ChannelTypes, Describe
lazy from wd_discord import Channel, CommandInteraction, User
lazy from wd_discord.permissions import ChannelType

MAX_REASON = 512


class Moderation(Cog):
    @Cog.command(name="ban", description="Ban a member")
    async def ban(
        self,
        interaction: CommandInteraction,
        member: Annotated[User, Describe("Who to ban")],
        reason: Annotated[str | None, Describe(t"Shown in the audit log, up to {MAX_REASON} characters")] = None,
        log: Annotated[Channel, ChannelTypes(ChannelType.GUILD_TEXT), Describe("Where to post the ban")] | None = None,
    ) -> None:
        """Ban ``member``."""
```

## Option types

| Annotation | Discord option |
| --- | --- |
| `str` | STRING |
| `int` | INTEGER |
| `float` | NUMBER |
| `bool` | BOOLEAN |
| `wd_discord.User` or the `User` model | USER |
| `wd_discord.Channel` or the `Channel` model | CHANNEL |
| `wd_discord.Role` or the `Role` model | ROLE |
| `User \| Role` | MENTIONABLE |

A parameter annotated with a bound entity (`wd_discord.User`) gets an entity bound to the client. One annotated
with the data model gets the model. Any other type raises `TypeError` when the command is defined.

An option is optional when its parameter has a default or its annotation includes `| None`.

## Annotated metadata

`Annotated[T, ...]` adds settings to an option without changing its type. wd-bot reads the metadata whether
it is inside the `| None` (`Annotated[str | None, ...]`) or outside it (`Annotated[str, ...] | None`), and one
`Annotated` can hold several items.

| Metadata | Effect |
| --- | --- |
| `ChannelTypes(*types)` | A channel option only lists channels of these kinds. It raises `TypeError` on any other option type. |
| `Describe(text)` | The text Discord shows under the option. Without it, Discord shows the parameter name. |

Other metadata is ignored, so pydantic constraints or comments in `Annotated` don't break a command.

## Descriptions

`Describe` takes a plain string or a t-string:

```python
member: Annotated[User, Describe("Who to ban")]
count: Annotated[int, Describe(t"How many, at most {MAX_ITEMS}")]
```

- The rendered text must be 1 to 100 characters (`wd_discord.interactions.MAX_DESCRIPTION_LENGTH`), Discord's
  limit. A longer or empty one raises `ValueError` when the command is defined, not when it syncs.
- A parameter takes one `Describe`. Two raise `TypeError`.
- For a description that several commands repeat, name it once with a type alias:
  `type Reason = Annotated[str, Describe("Shown in the audit log")]`.

### Template strings

A t-string lets a description name a constant instead of repeating its value, so the text and the limit it
describes can't drift apart. wd-bot renders it like an f-string: `{MAX_ITEMS:03d}` and `{name!r}` work.

Annotations are evaluated lazily (PEP 649), so an interpolation takes its value when `@Cog.command` reads the
handler's annotations. That happens while the cog class body runs, so a module constant defined above the cog
works. A name that doesn't exist raises `NameError` when the command is defined.

`Describe.template` keeps the t-string next to the rendered `Describe.text`. The literal parts and the values
stay separate, which `description_localizations` can build on later: translate `"How many, at most {}"` and
fill in the value after.

An f-string works too, but only as a plain string: it renders right away and keeps no template.

## Syncing

The bot re-registers a command with Discord when its signature changes. The signature holds the source text
of each annotation and the rendered description of each option. Changing a constant that a `Describe` names
therefore updates the command on Discord at the next sync, even though the source text stays the same.
