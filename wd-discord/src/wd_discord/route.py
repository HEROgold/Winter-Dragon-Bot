"""REST routes written as PEP 750 templates: ``t"/channels/{channel_id}/messages"``.

A template keeps the route's literal shape apart from its parameters, so the request path and the
rate-limit key both come from the same object without parsing a finished string back apart:

- :attr:`Route.path` percent-encodes every parameter, so a value can never add a path segment or query.
- :meth:`Route.key` keeps only the major parameter (https://docs.discord.com/developers/topics/rate-limits)
  and collapses every other parameter to ``{id}``.
"""

from __future__ import annotations

from dataclasses import dataclass
lazy from string.templatelib import Interpolation
lazy from typing import TYPE_CHECKING
lazy from urllib.parse import quote

lazy from wd_discord.rate_limit import MAJOR_PARAM_PREFIXES, RouteKey


if TYPE_CHECKING:
    from string.templatelib import Template


@dataclass(frozen=True, slots=True)
class Route:
    """One REST route: a template whose literal parts are the route and whose interpolations are its parameters."""

    template: Template

    @property
    def path(self) -> str:
        """The request path, with each parameter formatted and percent-encoded as one path segment."""
        parts: list[str] = []
        for item in self.template:
            if isinstance(item, Interpolation):
                value = format(item.value, item.format_spec) if item.format_spec else str(item.value)
                parts.append(quote(value, safe=""))
            else:
                parts.append(item)
        return "".join(parts)

    def key(self, method: str) -> RouteKey:
        """Collapse this route to Discord's rate-limit route shape for ``method``.

        A parameter right after a major prefix (``guilds``, ``channels``, ``webhooks``) stays in the key, since
        each guild, channel or webhook has its own bucket; every other parameter becomes ``{id}`` so unrelated
        IDs and tokens on one route share a single local key.
        """
        parts: list[str] = []
        previous = ""
        for item in self.template:
            if isinstance(item, Interpolation):
                major = previous.rstrip("/").rpartition("/")[2] in MAJOR_PARAM_PREFIXES
                parts.append(str(item.value) if major else "{id}")
            else:
                parts.append(item)
            previous = item if isinstance(item, str) else ""
        return RouteKey(f"{method} {''.join(parts).strip('/')}")
