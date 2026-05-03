# auth_security.py
"""
JWT 토큰 기반 인증 보안 모듈

Features:
- HS256 알고리즘 기반 JWT 토큰 생성/검증
- 토큰 만료 시간 설정
- Bearer 토큰 파싱 및 검증
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Header, HTTPException, status
from jose import JWTError, jwt

try:
    from backend.settings import (
        ACCESS_TOKEN_EXPIRE_MINUTES,
        JWT_SECRET_KEY,
    )
except ImportError:
    from settings import (
        ACCESS_TOKEN_EXPIRE_MINUTES,
        JWT_SECRET_KEY,
    )

SECRET_KEY = JWT_SECRET_KEY
ALGORITHM = "HS256"

# JWT 토큰 만료 시간 (분 단위)
TOKEN_EXPIRE_MINUTES = ACCESS_TOKEN_EXPIRE_MINUTES


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    JWT 액세스 토큰을 생성합니다.
    
    Args:
        data: 토큰에 포함할 페이로드 (user_id, email 등)
        expires_delta: 토큰 만료 시간 (기본: ACCESS_TOKEN_EXPIRE_MINUTES)
        
    Returns:
        인코딩된 JWT 토큰 문자열
        
    Example:
        >>> token = create_access_token({"user_id": 1, "email": "user@example.com"})
    """
    to_encode = data.copy()

    # 만료 시간 설정
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    )

    to_encode.update({"exp": expire})
    
    # JWT 토큰 인코딩
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    JWT 액세스 토큰을 검증하고 페이로드를 반환합니다.
    
    Args:
        token: JWT 토큰 문자열
        
    Returns:
        토큰이 유효하면 페이로드 딕셔너리, 아니면 None
        
    Raises:
        JWTError: 토큰이 유효하지 않거나 만료된 경우
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        # 토큰 검증 실패 (만료, 서명 오류 등)
        return None


def get_current_user_id_from_header(authorization: Optional[str] = Header(default=None)) -> Optional[int]:
    """
    Authorization 헤더에서 Bearer 토큰을 파싱하여 user_id를 추출합니다.
    
    헤더 형식: Authorization: Bearer <token>
    
    토큰이 없거나 유효하지 않으면 None을 반환하며, 
    기존 기능 호환성을 유지합니다.
    
    Args:
        authorization: Authorization 헤더 값
        
    Returns:
        유효한 토큰에서 추출한 user_id (int), 토큰이 없거나 유효하지 않으면 None
        
    Example:
        >>> user_id = get_current_user_id_from_header("Bearer eyJhbGc...")
        >>> # user_id = 123 (또는 None)
    """
    # 1. Authorization 헤더 확인
    if not authorization:
        return None

    # 2. "Bearer <token>" 형식 파싱
    parts = authorization.split()
    
    if len(parts) != 2:
        # 형식이 잘못됨 (예: "Bearer" 또는 "Bearer token extra")
        return None

    scheme, token = parts

    # 3. Bearer 스킴 확인 (case-insensitive)
    if scheme.lower() != "bearer":
        return None

    # 4. 토큰 검증
    payload = decode_access_token(token)
    
    if not payload:
        # 토큰이 유효하지 않거나 만료됨
        return None

    # 5. user_id 추출
    user_id = payload.get("user_id")

    try:
        return int(user_id)
    except (TypeError, ValueError):
        # user_id를 정수로 변환할 수 없음
        return None


def get_current_user_id_from_header_required(authorization: Optional[str] = Header(default=None)) -> int:
    """
    Authorization 헤더에서 user_id를 추출합니다. (필수)
    
    토큰이 없거나 유효하지 않으면 HTTP 401 Unauthorized 예외를 발생시킵니다.
    
    Args:
        authorization: Authorization 헤더 값
        
    Returns:
        유효한 토큰에서 추출한 user_id (int)
        
    Raises:
        HTTPException: 토큰이 없거나 유효하지 않은 경우 (401 Unauthorized)
        
    Example:
        @router.get("/protected")
        def protected_endpoint(user_id: int = Depends(get_current_user_id_from_header_required)):
            return {"user_id": user_id}
    """
    user_id = get_current_user_id_from_header(authorization)
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효한 토큰이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


def is_same_user(request_user_id: int, token_user_id: Optional[int]) -> bool:
    """
    요청 user_id와 토큰의 user_id가 일치하는지 확인합니다.
    
    기존 user_id 기반 API를 유지하면서 JWT 검증을 추가할 때 사용합니다.
    - token_user_id가 None이면 기존 동작 유지 (호환성)
    - token_user_id가 있으면 요청 user_id와 비교
    
    Args:
        request_user_id: 요청에서 제공한 user_id
        token_user_id: 토큰에서 추출한 user_id
        
    Returns:
        user_id가 일치하거나 토큰이 없으면 True, 불일치하면 False
        
    Example:
        >>> is_same_user(123, 123)
        True
        >>> is_same_user(123, 456)
        False
        >>> is_same_user(123, None)  # 토큰 없음 (호환성)
        True
    """
    if token_user_id is None:
        # 토큰이 없으면 기존 동작 유지
        return True

    return int(request_user_id) == int(token_user_id)
