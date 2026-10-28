"""Implementação do Broker Component: catálogo global de corretoras."""

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models
from ..db import crud, schemas


class BrokerService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_brokers(self) -> list[models.Broker]:
        return crud.list_brokers(self._db)

    def get_broker(self, broker_id: int) -> models.Broker:
        broker = crud.get_broker_by_id(self._db, broker_id)
        if broker is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Corretora não encontrada.",
            )
        return broker

    def create_broker(self, broker_in: schemas.BrokerCreate) -> models.Broker:
        if crud.get_broker_by_name(self._db, broker_in.broker_name):
            raise self._duplicated_name()
        try:
            return crud.create_broker(self._db, broker_in.broker_name)
        except IntegrityError as exc:
            # Outra requisição cadastrou o mesmo nome entre a checagem e o commit.
            self._db.rollback()
            raise self._duplicated_name() from exc

    def delete_broker(self, broker_id: int) -> None:
        broker = self.get_broker(broker_id)
        if crud.broker_has_trades(self._db, broker_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A corretora possui operações registradas e não pode ser removida.",
            )
        crud.delete_broker(self._db, broker)

    @staticmethod
    def _duplicated_name() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma corretora com este nome.",
        )
