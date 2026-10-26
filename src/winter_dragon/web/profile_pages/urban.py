"""The Profile's Urban Dictionary page: the member's lookups, newest first, with a total."""

lazy from sqlmodel import Session, col
lazy from wd_db.extension.lifecycle import owned_by

lazy from winter_dragon.cogs.urban import Lookup
lazy from winter_dragon.web.profile import ProfileContext, profile_page


@profile_page(slug="urban", title="Urban Dictionary", template="profile/urban.html")
def urban(context: ProfileContext) -> dict[str, object]:
    """Return the Urban page's context: the member's lookups, newest first, in their time zone."""
    with Session(context.bind) as session:
        lookups = list(session.exec(owned_by(Lookup, member=context.member_id).order_by(col(Lookup.looked_up_at).desc())))
    return {
        "lookups": [(lookup, lookup.looked_up_at.astimezone(context.zone)) for lookup in lookups],
        "total": len(lookups),
    }
