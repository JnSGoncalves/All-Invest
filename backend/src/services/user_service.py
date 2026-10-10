"""Implementação do componente de usuários sobre a camada de persistência."""

from sqlalchemy.orm import Session

from .. import models
from ..db import crud, schemas


class UserService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: int) -> models.User | None:
        return crud.get_user_by_id(self._db, user_id)

    def get_by_email(self, email: str) -> models.User | None:
        return crud.get_user_by_email(self._db, email)

    def create(self, user_in: schemas.UserCreate) -> models.User:
        return crud.create_user(self._db, user_in)

    def create_from_google(self, name: str, email: str) -> models.User:
        return crud.create_google_user(self._db, name=name, email=email)
