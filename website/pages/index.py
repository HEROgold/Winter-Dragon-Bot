from fastapi import APIRouter, Request

from website._types.responses import TemplateResponse
from website.templates import footer, head, header, nav, templates


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
