"""The Profile's love page: everyone the member has checked their compatibility with, highest percentage first."""

lazy from sqlmodel import Session
lazy from wd_db.extension.lifecycle import owned_by
lazy from wd_discord.snowflake import Snowflake

lazy from winter_dragon.cogs.percentage import CompatibilityCheck, calculate_percentage
lazy from winter_dragon.web.profile import ProfileContext, profile_page


@profile_page(slug="love", title="Love", template="profile/love.html")
def love(context: ProfileContext) -> dict[str, object]:
    """Return the love page's context: the member's checks with their percentage, highest first, then newest."""
    with Session(context.bind) as session:
        checks = list(session.exec(owned_by(CompatibilityCheck, member=context.member_id)))
    rows = [
        (check, calculate_percentage(context.member_id, Snowflake(check.target_id)), check.checked_at.astimezone(context.zone))
        for check in checks
    ]
    rows.sort(key=lambda row: (row[1], row[0].checked_at), reverse=True)
    return {"checks": rows}
