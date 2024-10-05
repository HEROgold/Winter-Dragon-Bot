from fastapi import APIRouter


router = APIRouter(prefix="/user", tags=["user"])

@router.get("/")
def home():
    return {"message": "Hello, user!"}
