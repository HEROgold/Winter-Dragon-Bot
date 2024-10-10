from fastapi import APIRouter

from website.pages.base import TEMPLATES


router = APIRouter(tags=["website", "home"])


@router.get("/index")
@router.get("/")
def index(request: Request) -> TemplateResponse:
    return templates.TemplateResponse(
        request,
        "index.j2",
        {
            "request": request,
            "head": head,
            "header": header,
            "nav": nav,
            "content": """content""",
            "footer": footer,
            "script": """script""",
        },
    )
