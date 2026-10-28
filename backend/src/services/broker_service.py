from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..db import crud, schemas


class BrokerService:
    def __init__(self, db: Session):
        self._db = db

    def create(self, user_id: int, payload: schemas.BrokerCreate) -> models.Broker:
        # Serializa cadastros do mesmo usuário, inclusive solicitações repetidas.
        self._db.query(models.User).filter_by(user_id=user_id).with_for_update().one()
        broker = self._db.query(models.Broker).filter(
            func.lower(models.Broker.broker_name) == payload.broker_name.lower()
        ).order_by(models.Broker.broker_id).first()
        if broker is None:
            broker = crud.get_or_create_broker(self._db, payload.broker_name)
        if self._db.get(models.UserBroker, (broker.broker_id, user_id)):
            raise HTTPException(409, "Esta corretora já está vinculada à sua conta.")
        crud.ensure_user_broker(self._db, user_id=user_id, broker_id=broker.broker_id)
        self._db.commit()
        self._db.refresh(broker)
        return broker
