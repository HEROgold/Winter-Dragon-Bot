"""What wd-discord doesn't model yet, from the raw events: events without a model, and fields models don't know.

Every modelled event is parsed again; the keys a model kept as ``model_extra`` (fields it has no attribute for)
are counted per model. An event that no longer parses is counted too.
"""

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError
from wd_discord.gateway.dispatch import parse_dispatch
from wd_discord.gateway.events import EventName
from wd_discord.models import DiscordModel


if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping


@dataclass
class Unmodelled:
    """What the raw events carried that wd-discord doesn't model."""

    events: Counter[str] = field(default_factory=Counter)
    """Events without a model, by name."""
    fields: Counter[tuple[str, str]] = field(default_factory=Counter)
    """Fields a model doesn't know, by (model, field)."""
    unparsable: Counter[str] = field(default_factory=Counter)
    """Modelled events whose payload no longer parses, by name."""


def find_unmodelled(events: Iterable[tuple[str, Mapping[str, Any]]]) -> Unmodelled:
    """Sort ``events``, as (name, payload), into what wd-discord doesn't model."""
    result = Unmodelled()
    previous = logging.root.manager.disable
    logging.disable(logging.WARNING)  # parsing again would log every unknown field a second time
    try:
        for name, payload in events:
            if name not in EventName.__members__ or EventName(name).model is None:
                result.events[name] += 1
                continue
            try:
                model = parse_dispatch(name, payload)
            except ValidationError:
                result.unparsable[name] += 1
                continue
            for model_name, key in unknown_fields(model):
                result.fields[model_name, key] += 1
    finally:
        logging.disable(previous)
    return result


def unknown_fields(model: DiscordModel) -> Iterator[tuple[str, str]]:
    """Yield (model, field) for every field ``model`` and the models inside it keep as extra."""
    for key in model.model_extra or {}:
        yield type(model).__name__, key
    for name in type(model).model_fields:
        value = getattr(model, name)
        for item in value if isinstance(value, list) else [value]:
            if isinstance(item, DiscordModel):
                yield from unknown_fields(item)


def render(result: Unmodelled) -> str:
    """Return the report as text."""
    lines = ["Events without a model:"]
    lines += [f"  {name:40} {count:8}" for name, count in result.events.most_common()] or ["  (none)"]
    lines += ["", "Fields models don't know:"]
    lines += [f"  {model:28} {key:36} {count:8}" for (model, key), count in result.fields.most_common()] or ["  (none)"]
    if result.unparsable:
        lines += ["", "Modelled events that no longer parse:"]
        lines += [f"  {name:40} {count:8}" for name, count in result.unparsable.most_common()]
    return "\n".join(lines)
