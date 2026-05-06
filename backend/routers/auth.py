from fastapi import APIRouter, Query, Request, HTTPException, status
from pydantic import BaseModel
from datetime import datetime

try:
    from backend.db import (
        get_conn,
        ensure_profile_custom_row,
        get_user_or_none,
        hash_password,
        verify_password,
    )
    from backend.auth_security import create_access_token
    from backend.rate_limiter import limiter_login, limiter_signup
except ImportError:
    from db import (
        get_conn,
        ensure_profile_custom_row,
        get_user_or_none,
        hash_password,
        verify_password,
    )
    from auth_security import create_access_token
    from rate_limiter import limiter_login, limiter_signup

router = APIRouter()


class SignupRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/signup")
def signup(data: SignupRequest, request: Request):
    """
    회원가입 엔드포인트
    
    Rate Limiting: 1시간에 3회 제한
    
    Args:
        data: SignupRequest (username, email, password)
        request: FastAPI Request 객체 (IP 주소 추출용)
        
    Returns:
        회원가입 성공 시 access_token 포함
    """
    # Rate Limiting 체크
    client_ip = request.client.host
    if not limiter_signup.allow_request(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="회원가입 요청이 너무 많습니다. 나중에 다시 시도해주세요.",
        )
    
    username = data.username.strip()
    email = data.email.strip().lower()
    password = data.password.strip()

    # 입력값 검증
    if not username or not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="아이디, 이메일, 비밀번호를 모두 입력해주세요.",
        )
    
    # 비밀번호 최소 길이 검증 (8자 이상)
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비밀번호는 최소 8자 이상이어야 합니다.",
        )
    
    # 사용자명 길이 검증 (3-20자)
    if len(username) < 3 or len(username) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="사용자명은 3자 이상 20자 이하여야 합니다.",
        )

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용 중인 아이디입니다.",
        )

    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용 중인 이메일입니다.",
        )

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hashed_password = hash_password(password)

    cursor.execute("""
        INSERT INTO users (username, email, password, created_at)
        VALUES (?, ?, ?, ?)
    """, (username, email, hashed_password, created_at))

    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    ensure_profile_custom_row(user_id)

    access_token = create_access_token({
        "user_id": user_id,
        "email": email,
        "username": username
    })

    return {
        "message": "회원가입이 완료되었습니다.",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "username": username,
            "email": email,
            "created_at": created_at
        }
    }


@router.post("/login")
def login(data: LoginRequest, request: Request):
    """
    로그인 엔드포인트
    
    Rate Limiting: 5분에 5회 제한 (브루트포스 공격 방지)
    
    Args:
        data: LoginRequest (email, password)
        request: FastAPI Request 객체 (IP 주소 추출용)
        
    Returns:
        로그인 성공 시 access_token 포함
    """
    # Rate Limiting 체크
    client_ip = request.client.host
    if not limiter_login.allow_request(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="로그인 시도가 너무 많습니다. 5분 후에 다시 시도해주세요.",
        )
    
    email = data.email.strip().lower()
    password = data.password.strip()

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이메일과 비밀번호를 입력해주세요.",
        )

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, email, password, created_at
        FROM users
        WHERE email = ?
    """, (email,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="존재하지 않는 이메일입니다.",
        )

    # ✅ bcrypt를 사용한 안전한 비밀번호 검증
    if not verify_password(password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비밀번호가 올바르지 않습니다.",
        )

    ensure_profile_custom_row(user["id"])

    access_token = create_access_token({
        "user_id": user["id"],
        "email": user["email"],
        "username": user["username"]
    })

    return {
        "message": "로그인 성공",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "created_at": user["created_at"]
        }
    }


@router.get("/me")
def get_me(user_id: int = Query(...)):
    """
    현재 사용자 정보 조회
    
    Args:
        user_id: 사용자 ID (쿼리 파라미터)
        
    Returns:
        사용자 정보
    """
    conn = get_conn()
    cursor = conn.cursor()
    user = get_user_or_none(cursor, user_id)
    conn.close()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )

    return {
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "created_at": user["created_at"]
        }
    }
