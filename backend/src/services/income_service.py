from datetime import timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..db import schemas


class IncomeService:
    """Rendimentos recebidos: lançamentos do usuário, sem estimar valorização."""
    def __init__(self, db: Session):
        self._db = db

    def list(self, user_id: int) -> list[models.Income]:
        return self._db.query(models.Income).filter_by(user_id=user_id).order_by(
            models.Income.received_at.desc(), models.Income.income_id.desc()).all()

    def get(self, user_id: int, income_id: int) -> models.Income:
        item = self._db.query(models.Income).filter_by(user_id=user_id, income_id=income_id).first()
        if item is None:
            raise HTTPException(404, "Rendimento não encontrado.")
        return item

    def save(self, user_id: int, payload: schemas.IncomeCreate, income_id: int | None = None) -> models.Income:
        item = self.get(user_id, income_id) if income_id is not None else models.Income(user_id=user_id)
        stock = self._db.query(models.UserStock).join(models.Stock).filter(
            models.UserStock.user_id == user_id, models.Stock.stock_name == payload.stock_name).first()
        if stock is None:
            raise HTTPException(404, "Ativo não encontrado no seu histórico de investimentos.")
        for field, value in payload.model_dump().items():
            if field == "received_at":
                value = value.astimezone(timezone.utc)
            setattr(item, field, value)
        self._db.add(item)
        self._db.commit()
        self._db.refresh(item)
        return item

    def delete(self, user_id: int, income_id: int) -> None:
        self._db.delete(self.get(user_id, income_id))
        self._db.commit()
