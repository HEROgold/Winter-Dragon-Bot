from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar, Self

from discord.abc import GuildChannel, Messageable
from discord.embeds import Embed
from herogold.log import LoggerMixin
from herogold.orm.model import BaseModel
from wd_types.protocol import Mentionable


if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

    from discord import AuditLogEntry
    from discord.enums import AuditLogAction
    from discord.ext.commands.bot import BotBase
    from sqlalchemy.orm import Session

class AuditLog(BaseModel):
    """Database model for audit logs."""

    action: int
    """AuditLogAction"""
    reason: str | None
    target_id: str
    category: int

    @classmethod
    def from_audit_log(cls, entry: AuditLogEntry) -> Self:
        """Create an AuditLog instance from a Discord AuditLogEntry."""
        if entry.target is None:
            msg = f"Target should be AuditLogEntry.target type, but is {type(entry.target)}"
            raise ValueError(msg)
        if entry.category is None:
            msg = f"Category should be AuditLogEntry.category type, but is {type(entry.category)}"
            raise ValueError(msg)
        audit = cls(
            id=entry.id,
            action=entry.action.value,
            reason=entry.reason,
            created_at=entry.created_at,
            target_id=str(entry.target.id),
            category=entry.category.value,
        )
        cls.session.add(audit)
        cls.session.commit()
        return audit


class AuditEvent(ABC):
    """Base class for audit events."""

    def __init__(self, entry: AuditLogEntry) -> None:
        """Initialize the audit event."""
        super().__init__()
        self.entry = entry

    @property
    def category(self) -> AuditLogAction:
        """Get the log category. lazily evaluated."""
        if not self._category:
            self._category = self.entry.action
        return self._category

    @property
    def db_entry(self) -> AuditLog:
        """Get the database entry. lazily evaluated."""
        if not self._db_entry:
            self._db_entry = AuditLog.from_audit_log(self.entry)  # creates the entry in the database, and returns the entry.
        return self._db_entry

    @abstractmethod
    async def handle(self) -> None:
        """Handle the audit event."""

    @abstractmethod
    async def get_log_channels(self) -> Generator[LogChannel]:
        """Get the log channels for the guild."""

    async def create_embed(self) -> Embed:
        """Create an embed for the audit event."""
        target = self.entry.target.mention if isinstance(self.entry.target, Mentionable) else self.entry.target

        return Embed(
            colour=None,
            color=None,
            title=f"{self.entry.action}",
            type="rich",
            url=None,
            description=f"Performed by {self.entry.user} with target {target}. with extra {self.entry.extra}",
            timestamp=datetime.now(UTC),
        )

    def __init_subclass__(cls: type[Self], action: AuditLogAction) -> None:
        """Register the subclass with the factory."""
        AuditEventFactory.register(action, cls)

class LogChannel(GuildChannel, Messageable, ABC):
    """A wrapper around GuildChannel to allow for easier logging."""

    @abstractmethod
    async def filter(self, action: AuditLogAction) -> bool:
        """Determine if a log should be sent to this channel based on the category."""


class AuditEventHandler(LoggerMixin):
    """Class for handling audit events."""

    def __init__(self, event: AuditEvent, session: Session, bot: BotBase) -> None:
        """Initialize the audit event handler."""
        self.event = event
        self.session = session
        self.bot = bot
        self.log_channels: list[LogChannel] = []

    async def handle(self) -> None:
        """Handle the audit event."""
        await self.event.handle()
        await self.log(
            audit_action=self.event.entry.action,
            embed=await self.event.create_embed(),
            channels=await self.event.get_log_channels(),
        )

    async def log(
        self,
        audit_action: AuditLogAction,
        embed: Embed,
        channels: Iterable[LogChannel],
    ) -> None:
        """Dispatch a log to the appropriate channels/aggregators.

        This method now routes all logs to the aggregated log system.
        """
        for channel in channels:
            if await channel.filter(audit_action):
                await channel.send(embed=embed)

class AuditEventFactory:
    """Factory for creating audit events."""

    events: ClassVar[dict[AuditLogAction, list[type[AuditEvent]]]] = {}

    @classmethod
    def register(cls, action: AuditLogAction, event_type: type[AuditEvent]) -> None:
        """Register an audit event class for a category."""
        if action not in cls.events:
            cls.events[action] = [event_type]
            return
        cls.events[action] += [event_type]

    @classmethod
    def get_events(cls, entry: AuditLogEntry) -> Generator[AuditEvent]:
        """Get the audit event class for a category."""
        if entry.action not in cls.events:
            msg = f"Audit event for {entry.action} not implemented"
            raise NotImplementedError(msg)

        for event in cls.events[entry.action]:
            yield event(entry)
