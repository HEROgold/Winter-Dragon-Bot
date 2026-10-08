"""Column types shared by the models of several features."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import override

from sqlalchemy import DateTime, Dialect, TypeDecorator


def as_utc(moment: datetime) -> datetime:
    """Return ``moment`` as an aware UTC datetime; naive values are taken as UTC."""
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)


class AwareDateTime(TypeDecorator[datetime]):
    """A timestamp column that always stores and reads back aware UTC datetimes, also on sqlite (which drops zones)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    @override
    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        """Store ``value`` as UTC."""
        return None if value is None else as_utc(value)

    @override
    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        """Read the stored value back as aware UTC."""
        return None if value is None else as_utc(value)
