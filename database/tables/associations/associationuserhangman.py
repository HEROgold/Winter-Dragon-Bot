from sqlmodel import Field, SQLModel

from database.tables.definitions import AUTO_INCREMENT_ID, HANGMEN_ID, USERS_ID


class AssociationUserHangman(SQLModel, table=True):

    id = AUTO_INCREMENT_ID
    hangman_id: int = Field(foreign_key=HANGMEN_ID)
    user_id: int = Field(foreign_key=USERS_ID)
    score: int
