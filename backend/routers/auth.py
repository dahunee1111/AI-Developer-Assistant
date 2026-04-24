from fastapi import APIRouter, Query
from pydantic import BaseModel
from datetime import datetime

from db import (
    get_conn,
    ensure_profile_custom_row,
    get_user_or_none,
    hash_password,
)

from auth_security import create_access_token

router = APIRouter()


class SignupRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/signup")
def signup(data: SignupRequest):
    username = data.username.strip()
    email = data.email.strip().lower()
    password = data.password.strip()

    if not username or not email or not password:
        return {"message": "아이디, 이메일, 비밀번호를 모두 입력해주세요."}

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return {"message": "이미 사용 중인 아이디입니다."}

    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        return {"message": "이미 사용 중인 이메일입니다."}

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
def login(data: LoginRequest):
    email = data.email.strip().lower()
    password = data.password.strip()

    if not email or not password:
        return {"message": "이메일과 비밀번호를 입력해주세요."}

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
        return {"message": "존재하지 않는 이메일입니다."}

    if user["password"] != hash_password(password):
        return {"message": "비밀번호가 올바르지 않습니다."}

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
    conn = get_conn()
    cursor = conn.cursor()
    user = get_user_or_none(cursor, user_id)
    conn.close()

    if not user:
        return {"message": "사용자를 찾을 수 없습니다."}

    return {
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "created_at": user["created_at"]
        }
    }
