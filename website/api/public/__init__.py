from fastapi import APIRouter


router = APIRouter(tags=["public"])

@router.get("/")
def home():
    return {"message": "Hello, public!"}
