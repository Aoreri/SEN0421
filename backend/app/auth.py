"""JWT kimlik doğrulama ve rol denetimi (PLN-05). API sözleşmesi: docs/api-auth.md"""
import os
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select

from .db import DB
from .models import User

ADMIN, TEST_LEAD, TESTER, DEVELOPER = "Admin", "Test Lead", "Tester", "Developer"

# Sabit bir varsayılan, herkesin Admin token'ı üretebilmesi demek olurdu. Ortam değişkeni yoksa
# rastgele üretilir: token'lar yeniden başlatmada geçersizleşir; birden çok worker için JWT_SECRET şart.
JWT_SECRET = os.getenv("JWT_SECRET") or secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"
TOKEN_LIFETIME = timedelta(hours=8)

# Bilinmeyen kullanıcıda da hash doğrulanır; yanıt süresi kullanıcı adının varlığını sızdırmaz.
DUMMY_HASH = bcrypt.hashpw(b"unused", bcrypt.gensalt())

bearer = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/api/auth", tags=["auth"])


def unauthorized() -> HTTPException:
    return HTTPException(401, "Kimlik doğrulama gerekli", headers={"WWW-Authenticate": "Bearer"})


def optional_user(
    db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> User | None:
    """Token yoksa None; token verilmiş ama geçersizse 401."""
    if creds is None:
        return None
    try:
        claims = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM],
                            options={"require": ["exp", "sub"]})
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, ValueError):
        raise unauthorized() from None
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized()
    return user


OptionalUser = Annotated[User | None, Depends(optional_user)]


def current_user(user: OptionalUser) -> User:
    if user is None:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_roles(*roles: str) -> Callable[[User], User]:
    """Kullanım: `dependencies=[Depends(require_roles(ADMIN, TEST_LEAD))]`"""

    def check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Bu işlem için yetkiniz yok")
        return user

    return check


class Login(BaseModel):
    username: str
    password: str


def user_out(u: User) -> dict:
    return {"id": u.id, "username": u.username, "role": u.role}


@router.post("/login")
def login(body: Login, db: DB):
    user = db.scalar(select(User).where(User.username == body.username))
    stored = user.password_hash.encode() if user else DUMMY_HASH
    password = body.password.encode()
    # bcrypt 72 bayttan sonrasını yok sayar; uzun parola kesilip eşleşmiş sayılmasın diye reddedilir.
    if len(password) > 72 or not bcrypt.checkpw(password, stored) or user is None:
        raise HTTPException(401, "Geçersiz kullanıcı adı veya şifre")
    token = jwt.encode({"sub": str(user.id), "exp": datetime.now(UTC) + TOKEN_LIFETIME},
                       JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "user": user_out(user)}


@router.get("/me")
def me(user: CurrentUser):
    return user_out(user)
