from sqlalchemy.orm import Session

from . import models, schemas, security


def get_user_by_email(db: Session, email: str) -> models.User | None:
    """Usada na Verificação de Conta Existente (CA02)."""
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    """Persistência do Usuário (CA01): cria o registro com a senha já hasheada."""
    db_user = models.User(
        name=user_in.name,
        email=user_in.email,
        password_hash=security.hash_password(user_in.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
