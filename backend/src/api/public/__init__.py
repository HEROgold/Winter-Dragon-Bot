from fastapi import APIRouter

from database import NhieQuestion, Session, WyrQuestion, engine


router = APIRouter(tags=["public"])

session = Session(engine)


@router.get("/wyr_questions")
def wyr_questions() -> list[str]:
    with session:
        questions: list[WyrQuestion] = session.query(WyrQuestion).all()
        return [question.value for question in questions]


@router.get("/nhie_questions")
def nhie_questions() -> list[str]:
    with session:
        questions: list[NhieQuestion] = session.query(NhieQuestion).all()
        return [question.value for question in questions]
