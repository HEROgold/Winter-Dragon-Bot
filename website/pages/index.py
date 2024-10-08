from fastapi import APIRouter

from website.pages.base import TEMPLATES


router = APIRouter(tags=["website", "home"])

@router.get("/")
def read_root():
    return TEMPLATES.TemplateResponse("index.html")
