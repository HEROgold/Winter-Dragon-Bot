"""Audit-log reasons (https://docs.discord.com/developers/resources/audit-log#audit-log-entry-object).

Endpoints that change a guild accept an ``X-Audit-Log-Reason`` header; Discord shows its text in the guild's
audit log next to the action.
"""

from __future__ import annotations

from dataclasses import dataclass
lazy from urllib.parse import quote


MAX_REASON_LENGTH = 512
"""The longest reason Discord keeps; a longer one is cut short."""
REASON_HEADER = "X-Audit-Log-Reason"


@dataclass(frozen=True, slots=True)
class AuditLogReason:
    """Why the bot made a change, as shown in the guild's audit log."""

    text: str

    def headers(self) -> dict[str, str]:
        """Return the request header carrying this reason, cut to :data:`MAX_REASON_LENGTH` and URL-encoded."""
        return {REASON_HEADER: quote(self.text[:MAX_REASON_LENGTH], safe=" ")}


def reason_headers(reason: AuditLogReason | str | None) -> dict[str, str]:
    """Return the headers for ``reason``: none without one, else the audit-log reason header."""
    if reason is None:
        return {}
    return (reason if isinstance(reason, AuditLogReason) else AuditLogReason(reason)).headers()
