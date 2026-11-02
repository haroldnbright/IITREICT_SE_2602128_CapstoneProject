"""Password hashing, JWT tokens, and the dependencies that protect routes."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User


# ---------- Passwords (bcrypt) ----------
# bcrypt only uses the first 72 bytes of a password
BCRYPT_MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    """Hash a password with bcrypt and a fresh salt."""
    password_bytes = password.encode("utf-8")[:BCRYPT_MAX_PASSWORD_BYTES]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plain password against a stored bcrypt hash."""
    # Truncate the same way as hash_password so long passwords still match
    password_bytes = password.encode("utf-8")[:BCRYPT_MAX_PASSWORD_BYTES]
    return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))


# ---------- JWT ----------
def create_access_token(user: User) -> str:
    """Create a signed JWT holding the user id and role, valid for ACCESS_TOKEN_EXPIRE_MINUTES."""
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user.id), "role": user.role, "exp": expires}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# auto_error=False so we can return our own 401 message
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Read 'Authorization: Bearer <token>', check it and load the user. Raises 401 if anything is wrong."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not logged in or session expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = int(payload["sub"])  # decode() also rejects bad signatures and expired tokens
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized

    user = db.get(User, user_id)
    if user is None:  # token is valid but the account no longer exists
        raise unauthorized
    return user


def require_role(*roles: str):
    """Dependency factory: only lets users with one of the given roles through.

    Usage: current_user: User = Depends(require_role("owner"))
    """

    def checker(user: User = Depends(get_current_user)) -> User:
        """Return the logged-in user, or raise 403 if their role isn't allowed."""
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this")
        return user

    return checker
