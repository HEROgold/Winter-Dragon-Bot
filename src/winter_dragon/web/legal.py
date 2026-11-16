"""The privacy policy and terms of service: public pages that cover the whole bot, linked from every page's footer."""

from fastapi import APIRouter
lazy from fastapi import Request
lazy from starlette.responses import Response

lazy from winter_dragon.cogs.privacy.domain import RETENTION, USAGE_RETENTION
lazy from winter_dragon.web.responses import render
lazy from winter_dragon.web.settings import DashboardSettings


ISSUES_URL = "https://github.com/HEROgold/Winter-Dragon-Bot/issues"
"""Where anyone can report a problem in public."""
BACKUPS_KEPT = 14
"""How many database backups the server keeps (``KEEP`` of compose's backup services); the privacy policy quotes it."""
UPDATED = "16 November 2026"
"""When the privacy policy and terms of service last changed; update it with every change to either page."""

router = APIRouter()


def _legal_page(request: Request, template: str) -> Response:
    """Render one of the legal pages, with the contact details and retention periods both of them quote."""
    return render(
        request,
        template,
        email=DashboardSettings.privacy_email,
        issues_url=ISSUES_URL,
        updated=UPDATED,
        retention_days=RETENTION.days,
        usage_months=USAGE_RETENTION.days // 30,
        backups_kept=BACKUPS_KEPT,
    )


@router.get("/privacy")
def privacy(request: Request) -> Response:
    """Show the privacy policy: what the bot stores, why, who else sees it, and how to have it deleted."""
    return _legal_page(request, "legal/privacy.html")


@router.get("/tos")
def terms(request: Request) -> Response:
    """Show the terms of service: the rules for using the bot and the dashboard."""
    return _legal_page(request, "legal/terms.html")
