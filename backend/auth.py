from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

from backend.config import get_settings
from backend.database import db
from backend.models import Permission, PointOfInterest, User, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def token_scopes(user: User) -> str:
    if user.role == UserRole.ADMIN:
        return "admin,poi:read,poi:write"
    if user.permission == Permission.READ_WRITE:
        return "poi:read,poi:write"
    return "poi:read"


def create_access_token(
    *,
    user: User,
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {
        "sub": user.username,
        "role": user.role.value,
        "permission": user.permission.value if user.permission else None,
        "exp": expire,
        "scope": token_scopes(user),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def authenticate_user(session: Session, username: str, password: str) -> User | None:
    user = session.exec(select(User).where(User.username == username)).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def get_user_by_username(session: Session, username: str) -> User | None:
    return session.exec(select(User).where(User.username == username)).first()


def can_write_pois(user: User) -> bool:
    return user.role == UserRole.ADMIN or user.permission == Permission.READ_WRITE


def can_modify_poi(user: User, poi: PointOfInterest) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    return poi.created_by_user_id == user.id


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Session = Depends(db.get_session),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    try:
        payload = decode_token(credentials.credentials)
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        if not payload.get("scope"):
            raise HTTPException(status_code=403, detail="Missing required scope")
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Token expired or invalid") from exc

    user = get_user_by_username(session, username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


async def require_write_access(current_user: User = Depends(get_current_user)) -> User:
    if not can_write_pois(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read and write permission required",
        )
    return current_user


async def verify_service_key(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> None:
    settings = get_settings()
    if credentials is None or credentials.credentials != settings.service_api_key:
        raise HTTPException(status_code=401, detail="Invalid service credentials")
