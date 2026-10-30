"""Hooks a feature registers to clean up after a member whose data is hidden, so privacy needn't know the feature.

Hiding a member's data soft-deletes every row they own by :class:`~wd_db.extension.lifecycle.Ownership`. A hook does
what that rule can't, such as taking the member out of a tournament that hasn't started, which disbands the team they
captain. The data page lists the owned rows and the rows each hook says it removes.
"""

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, Any, ClassVar, override


if TYPE_CHECKING:
    lazy from collections.abc import Collection, Generator

    lazy from sqlmodel import Session
    lazy from sqlmodel.sql.expression import SelectOfScalar
    lazy from wd_db.extension.lifecycle import LifecycleModel
    lazy from wd_discord.snowflake import Snowflake


@dataclass(frozen=True)
class RemovedRows:
    """Rows of ``model`` a hook removes that the member doesn't own; ``ids`` selects their ``id``."""

    model: type[LifecycleModel]
    ids: SelectOfScalar[int | None]


class MemberHiddenHook:
    """A feature's own cleanup when a member's data is hidden; defining a subclass registers it.

    :meth:`run_all` calls every registered hook. A subclass defined again under the same module and name (a reloaded
    extension) replaces the old one.
    """

    tables: ClassVar[tuple[type[LifecycleModel], ...]] = ()
    """The tables the hook reads or writes; it runs only when they all exist."""
    _registered: ClassVar[dict[str, type[MemberHiddenHook]]] = {}

    @override
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        MemberHiddenHook._registered[f"{cls.__module__}.{cls.__qualname__}"] = cls

    @classmethod
    def on_member_hidden(cls, session: Session, member_id: Snowflake) -> None:
        """Clean up the member ``member_id``'s data in ``session``, before their owned rows are hidden; don't commit."""
        raise NotImplementedError

    @classmethod
    def removes(cls, member_id: Snowflake) -> Generator[RemovedRows]:  # noqa: ARG003 - subclasses use the member
        """Yield the rows :meth:`on_member_hidden` removes that the member ``member_id`` doesn't own; none by default."""
        yield from ()

    @staticmethod
    def _ready(stored: Collection[type[LifecycleModel]]) -> Generator[type[MemberHiddenHook]]:
        """Yield every registered hook whose :attr:`tables` are all in ``stored``."""
        for hook in MemberHiddenHook._registered.values():
            if all(table in stored for table in hook.tables):
                yield hook

    @staticmethod
    def run_all(session: Session, member_id: Snowflake, stored: Collection[type[LifecycleModel]]) -> None:
        """Call every registered hook whose :attr:`tables` are all in ``stored``, for the member ``member_id``."""
        for hook in MemberHiddenHook._ready(stored):
            hook.on_member_hidden(session, member_id)

    @staticmethod
    def removed_by_all(member_id: Snowflake, stored: Collection[type[LifecycleModel]]) -> Generator[RemovedRows]:
        """Yield the rows the hooks :meth:`run_all` calls remove for the member ``member_id``, beyond what they own."""
        for hook in MemberHiddenHook._ready(stored):
            yield from hook.removes(member_id)
