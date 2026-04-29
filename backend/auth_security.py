# auth_security.py
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Header
from jose import JWTError, jwt

try:
    from backend.settings import (
        ACCESS_TOKEN_EXPIRE_MINUTES,
        JWT_SECRET_FROM_ENV,
        JWT_SECRET_KEY,
    )
except ImportError:
    from settings import (
        ACCESS_TOKEN_EXPIRE_MINUTES,
        JWT_SECRET_FROM_ENV,
        JWT_SECRET_KEY,
    )

if not JWT_SECRET_FROM_ENV:
    # 개발 환경에서는 기본 키로 동작하게 두고, 배포에서는 환경변수 설정을 권장합니다.
    pass

SECRET_KEY = JWT_SECRET_KEY
ALGORITHM = "HS256"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_user_id_from_header(authorization: Optional[str] = Header(default=None)) -> Optional[int]:
    """
    Authorization: Bearer <token>
    형태의 헤더에서 user_id를 추출합니다.

    기존 기능을 한 번에 깨지지 않게 하기 위해,
    이 함수는 토큰이 없거나 잘못되어도 None을 반환합니다.
    이후 API별로 점진적으로 강제 인증으로 전환하면 됩니다.
    """
    if not authorization:
        return None

    parts = authorization.split()

    if len(parts) != 2:
        return None

    scheme, token = parts

    if scheme.lower() != "bearer":
        return None

    payload = decode_access_token(token)

    if not payload:
        return None

    user_id = payload.get("user_id")

    try:
        return int(user_id)
    except (TypeError, ValueError):
        return None


def is_same_user(request_user_id: int, token_user_id: Optional[int]) -> bool:
    """
    기존 user_id 기반 API를 유지하면서 JWT 검증을 추가할 때 사용하는 함수입니다.
    token_user_id가 None이면 기존 동작을 유지합니다.
    토큰이 있으면 요청 user_id와 일치하는지 확인합니다.
    """
    if token_user_id is None:
        return True

    return int(request_user_id) == int(token_user_id)
