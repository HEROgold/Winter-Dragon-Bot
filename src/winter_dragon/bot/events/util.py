"""Utility functions for audit log entries."""
from collections.abc import Generator, Iterable

from discord import AuditLogEntry, Embed, Member, Role


def get_differences(entry: AuditLogEntry, properties: Iterable[str]) -> Generator[str]:
    """Get the differences between before and after states of an audit log entry."""
    before = entry.before
    after = entry.after
    yield from [
        prop
        for prop in properties
        if hasattr(before, prop) and getattr(before, prop) != getattr(after, prop)
    ]

def get_member_role_differences(before: Member, after: Member) -> tuple[Generator[Role], Generator[Role]]:
    """Get the difference in roles between two member states."""
    role_diff_add = (role for role in after.roles if role not in before.roles)
    role_diff_rem = (role for role in after.roles if role in before.roles)
    return role_diff_add, role_diff_rem

def add_differences_to_embed(embed: Embed, entry: AuditLogEntry, properties: Iterable[str]) -> None:
    """Add differences to the embed."""
    differences = list(get_differences(entry, properties))
    before = entry.before
    after = entry.after

    for prop in properties:
        if prop not in differences:
            continue
        before_val = getattr(before, prop, None)
        after_val = getattr(after, prop, None)

        embed.add_field(
            name=f"{prop.replace('_', ' ').title()}",
            value=f"From: `{before_val}` → To: `{after_val}`",
            inline=False,
        )
