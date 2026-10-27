"""The Profile's Steam page: the sales Steam DMs told the member about, newest first, with a total."""

lazy from sqlmodel import Session, col
lazy from wd_db.extension.lifecycle import owned_by

lazy from winter_dragon.cogs.steam.models import SaleNotification
lazy from winter_dragon.web.profile import ProfileContext, profile_page


@profile_page(slug="steam", title="Steam", template="profile/steam.html")
def steam(context: ProfileContext) -> dict[str, object]:
    """Return the Steam page's context: the member's sale notifications, newest first."""
    with Session(context.bind) as session:
        notifications = list(
            session.exec(owned_by(SaleNotification, member=context.member_id).order_by(col(SaleNotification.sent_at).desc())),
        )
    return {"notifications": [(entry, entry.sent_at.astimezone(context.zone)) for entry in notifications]}
