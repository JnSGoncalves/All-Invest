import bcrypt


def hash_password(plain_password: str) -> str:
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """HU02 (login)"""
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
