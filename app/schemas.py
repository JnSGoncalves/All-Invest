from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserCreate(BaseModel):
    """Payload do formulário de cadastro (CA01)."""
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, description="Mínimo de 8 caracteres")


class UserOut(BaseModel):
    """Retorno da API — nunca inclui password_hash."""
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    name: str
    email: EmailStr
    created_at: datetime
