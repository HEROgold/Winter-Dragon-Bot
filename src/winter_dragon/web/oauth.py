"""Placeholder pages for ``/oauth/login`` and ``/oauth/logout``, which are still being built; both show a maintenance page."""

from fastapi import APIRouter
lazy from fastapi import Request, status
lazy from starlette.responses import Response  # noqa: TC002 - FastAPI resolves route annotations at runtime

lazy from winter_dragon.web.responses import render


router = APIRouter(prefix="/oauth")


def _work_in_progress(request: Request) -> Response:
    """Render the maintenance page with ``503 Service Unavailable``, so crawlers and monitors don't treat it as content."""
    return render(request, "maintenance.html", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


@router.get("/login")
def login(request: Request) -> Response:
    """Show the maintenance page until OAuth sign-in on this route is built."""
    return _work_in_progress(request)


@router.get("/logout")
def logout(request: Request) -> Response:
    """Show the maintenance page until OAuth sign-out on this route is built."""
    return _work_in_progress(request)
