from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import models
from config import get_settings
from database import get_db


settings = get_settings()
password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


try:
    from passlib.context import CryptContext
    _legacy_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception:  # passlib es solo compatibilidad con usuarios antiguos
    _legacy_pwd_context = None


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if hashed_password.startswith("$argon2"):
        try:
            return password_hasher.verify(hashed_password, plain_password)
        except (VerifyMismatchError, InvalidHashError):
            return False

    if hashed_password.startswith("$2") and _legacy_pwd_context:
        try:
            return _legacy_pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False

    return False


def password_needs_rehash(hashed_password: str) -> bool:
    if not hashed_password.startswith("$argon2"):
        return True
    try:
        return password_hasher.check_needs_rehash(hashed_password)
    except InvalidHashError:
        return True


def create_access_token(user: models.Usuario) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "rol": user.rol,
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret(), algorithm="HS256")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Usuario:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesión inválida o expirada",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret(), algorithms=["HS256"])
        if payload.get("type") != "access" or not payload.get("sub"):
            raise credentials_error
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError, TypeError):
        raise credentials_error

    user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not user:
        raise credentials_error
    return user


def require_roles(*roles: str):
    def dependency(current_user: models.Usuario = Depends(get_current_user)) -> models.Usuario:
        if current_user.rol not in roles:
            raise HTTPException(status_code=403, detail="No tiene permisos para realizar esta acción")
        return current_user
    return dependency
