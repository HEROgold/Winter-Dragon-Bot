from fastapi import APIRouter, Request
from aliases.responses import TemplateResponse
from templates import templates


router = APIRouter(tags=["website", "home"])


@router.get("/index")
@router.get("/")
def index(request: Request) -> TemplateResponse:
    return templates.TemplateResponse(
        request,
        "index.j2",
        {
            "request": request,
        },
    )
