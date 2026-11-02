"""Implementação do Broker Component: catálogo global e vínculos de cada usuário."""

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

    def list_user_brokers(self, user_id: int) -> list[models.Broker]:
        return crud.list_user_brokers(self._db, user_id)

    def get_broker(self, broker_id: int) -> models.Broker:
        broker = crud.get_broker_by_id(self._db, broker_id)
        if broker is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Corretora não encontrada.",
            )
        return broker

    def create_broker(self, user_id: int, broker_in: schemas.BrokerCreate) -> models.Broker:
        # Serializa cadastros do mesmo usuário, inclusive solicitações repetidas.
        self._db.query(models.User).filter_by(user_id=user_id).with_for_update().one()
        name = broker_in.broker_name
        try:
            broker = crud.get_broker_by_name(self._db, name) or crud.create_broker(self._db, name)
        except IntegrityError:
            # Outro usuário cadastrou o mesmo nome entre a checagem e o commit.
            self._db.rollback()
            broker = crud.get_broker_by_name(self._db, name)
        if self._db.get(models.UserBroker, (broker.broker_id, user_id)):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Esta corretora já está vinculada à sua conta.",
            )
        crud.ensure_user_broker(self._db, user_id=user_id, broker_id=broker.broker_id)
        self._db.commit()
        self._db.refresh(broker)
        return broker

    def delete_broker(self, broker_id: int) -> None:
        broker = self.get_broker(broker_id)
        if crud.broker_has_trades(self._db, broker_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A corretora possui operações registradas e não pode ser removida.",
            )
        crud.delete_broker(self._db, broker)
