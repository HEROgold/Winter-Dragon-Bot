"""Text the bot's messages share."""

lazy from typing import TYPE_CHECKING

lazy from wd_discord.limits import MAX_EMBED_FIELD_VALUE_LENGTH, truncate


if TYPE_CHECKING:
    lazy from collections.abc import Sequence


def mentions(user_ids: Sequence[int]) -> str:
    """Return the users as mentions, or a dash for nobody; cut to fit an embed field."""
    text = ", ".join(f"<@{user_id}>" for user_id in user_ids) or "—"
    return truncate(text, MAX_EMBED_FIELD_VALUE_LENGTH)
