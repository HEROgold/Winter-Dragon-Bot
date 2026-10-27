"""Audit-log reasons (https://docs.discord.com/developers/resources/audit-log#audit-log-entry-object).

Endpoints that change a guild accept an ``X-Audit-Log-Reason`` header; Discord shows its text in the guild's
audit log next to the action.
"""

from dataclasses import dataclass
lazy from urllib.parse import quote

lazy from wd_discord.limits import MAX_REASON_LENGTH, truncate


REASON_HEADER = "X-Audit-Log-Reason"
"""The header that carries an audit log reason (https://docs.discord.com/developers/resources/audit-log)."""


@dataclass(frozen=True, slots=True)
class AuditLogReason:
    """Why the bot made a change, as shown in the guild's audit log."""

    text: str

    def headers(self) -> dict[str, str]:
        """Return the request header carrying this reason, cut to :data:`~wd_discord.limits.MAX_REASON_LENGTH` with :func:`~wd_discord.limits.truncate` and URL-encoded."""
        return {REASON_HEADER: quote(truncate(self.text, MAX_REASON_LENGTH), safe=" ")}


type Reason = AuditLogReason | str | None
"""Why the bot makes a change, for the audit log: wrapped, as plain text, or not given."""


def reason_headers(reason: Reason) -> dict[str, str]:
    """Return the headers for ``reason``: none without one, else the audit-log reason header."""
    if reason is None:
        return {}
    return (reason if isinstance(reason, AuditLogReason) else AuditLogReason(reason)).headers()
