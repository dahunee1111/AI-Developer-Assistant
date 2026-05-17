from fastapi import APIRouter, Query, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict
import os
import requests

try:
    from backend.db import get_conn, user_exists
    from backend.auth_security import get_current_user_id_from_header, is_same_user
except ImportError:
    from db import get_conn, user_exists
    from auth_security import get_current_user_id_from_header, is_same_user


router = APIRouter()


class ChatRequest(BaseModel):
    user_id: int
    message: str


class ChatClearRequest(BaseModel):
    user_id: int


MAX_USER_MESSAGE_LENGTH = 4000
MAX_CONTEXT_MESSAGES = 8


PROJECT_CONTEXT = """
프로젝트명: AI Developer Assistant
목적: 개발 학습자를 위한 AI 기반 학습 대시보드
주요 기능: 에러 분석, 코드 리뷰, 학습 기록일기 CRUD, 출석 체크, 포인트 시스템, 상점/인벤토리, 프로필 꾸미기, 시험 시스템, 오답노트, 난이도 추천
백엔드: Python, FastAPI, SQLite, JWT 인증, bcrypt 비밀번호 해싱, Rate Limiting
프론트엔드: HTML, CSS, JavaScript, GitHub Pages
배포/연결: 프론트엔드는 GitHub Pages, 백엔드는 EC2 + DuckDNS HTTPS 도메인 API와 연결
AI 연결: Hugging Face Inference Providers 기반 응답을 우선 사용하고, 실패 시 기본 답변을 제공
""".strip()


SYSTEM_PROMPT = f"""
너는 'AI Developer Assistant' 프로젝트 안에 들어가는 한국어 AI 챗봇이다.
사용자는 개발을 배우는 학습자이며, Python/FastAPI/HTML/CSS/JS/SQL/배포 오류를 자주 질문한다.

규칙:
- 반드시 한국어로 답변한다.
- 내부 추론 과정은 절대 출력하지 않는다.
- 너무 장황하게 늘이지 말고, 바로 실행 가능한 설명을 준다.
- 코드가 필요하면 핵심 코드만 보여준다.
- 사용자가 프로젝트 기능을 물어보면 아래 프로젝트 정보를 기준으로 설명한다.
- 확실하지 않은 내용은 추측하지 말고 확인해야 할 파일/위치를 말한다.

프로젝트 정보:
{PROJECT_CONTEXT}
""".strip()


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _validate_user(cursor, request_user_id: int, token_user_id: Optional[int]):
    if not is_same_user(request_user_id, token_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="다른 사용자의 챗봇 기록에는 접근할 수 없습니다.",
        )

    if not user_exists(cursor, request_user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )


def save_chat_message(user_id: int, role: str, message: str):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_history (user_id, role, message, created_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, role, message, now_str()))
    conn.commit()
    conn.close()


def load_recent_messages(user_id: int) -> List[Dict[str, str]]:
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, message
        FROM chat_history
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (user_id, MAX_CONTEXT_MESSAGES))
    rows = cursor.fetchall()
    conn.close()

    # DB에서는 최신순으로 가져오고, AI에게는 오래된 순서로 전달
    rows = list(reversed(rows))
    return [
        {
            "role": row["role"],
            "content": row["message"],
        }
        for row in rows
        if row["role"] in ["user", "assistant"]
    ]


def fallback_reply(message: str) -> str:
    text = message.lower().strip()

    if any(keyword in text for keyword in ["프로젝트", "소개", "뭐야", "무슨 서비스", "개요"]):
        return (
            "AI Developer Assistant는 개발 학습을 돕는 개인 프로젝트입니다.\n\n"
            "핵심 흐름은 사용자가 에러나 코드를 입력하면 AI가 분석하고, "
            "학습 기록·시험·오답노트·출석·포인트·상점 시스템으로 학습 성장을 이어가게 만드는 구조입니다.\n\n"
            "즉, 단순 챗봇이 아니라 개발 학습 과정을 기록하고 보상하는 학습 대시보드입니다."
        )

    if any(keyword in text for keyword in ["기술", "스택", "fastapi", "sqlite", "배포"]):
        return (
            "이 프로젝트의 주요 기술 스택은 다음과 같습니다.\n\n"
            "- Backend: Python, FastAPI, SQLite\n"
            "- Auth: JWT, bcrypt 비밀번호 해싱\n"
            "- Frontend: HTML, CSS, JavaScript\n"
            "- AI: Hugging Face Inference Providers 연동\n"
            "- Deploy: GitHub Pages + EC2/DuckDNS API 서버 구조\n\n"
            "프론트엔드는 정적 페이지로 동작하고, 백엔드는 API 서버로 로그인·학습·시험·상점·챗봇 요청을 처리합니다."
        )

    if any(keyword in text for keyword in ["포인트", "상점", "아이템", "인벤토리"]):
        return (
            "포인트/상점 기능은 학습 행동을 보상으로 연결하는 기능입니다.\n\n"
            "출석, 에러 분석, 코드 리뷰, 기록 작성, 시험 제출 같은 활동으로 포인트를 얻고, "
            "그 포인트로 테마·배지·배경·닉네임 컬러·카드 스킨 같은 꾸미기 아이템을 구매하고 적용할 수 있습니다."
        )

    if any(keyword in text for keyword in ["출석", "학습일", "체크"]):
        return (
            "출석 기능은 하루에 한 번 출석 기록을 저장하고 포인트를 지급하는 기능입니다.\n\n"
            "백엔드는 attendance_records 테이블에 오늘 날짜를 저장하고, 이미 출석한 날이면 중복 지급을 막는 방식으로 동작합니다."
        )

    if any(keyword in text for keyword in ["시험", "오답", "난이도", "문제"]):
        return (
            "시험 시스템은 객관식 문제와 코드 문제를 풀고 결과를 저장하는 기능입니다.\n\n"
            "틀린 문제는 오답노트에 저장되고, 최근 오답 흐름을 기준으로 easy/medium/hard 난이도를 추천할 수 있습니다."
        )

    if any(keyword in text for keyword in ["에러", "오류", "코드리뷰", "코드 리뷰", "분석"]):
        return (
            "에러 분석과 코드 리뷰 기능은 사용자가 입력한 에러 메시지나 Python 코드를 AI에게 보내고, "
            "원인·해결 방법·개선 포인트를 한국어로 받아보는 기능입니다.\n\n"
            "챗봇에서는 더 자유롭게 질문할 수 있고, 학습 페이지에서는 정해진 형식으로 분석 결과를 받을 수 있습니다."
        )

    return (
        "현재 AI 응답 서버가 설정되지 않았거나 일시적으로 응답하지 않아 기본 챗봇 답변으로 안내할게요.\n\n"
        "이 챗봇은 AI Developer Assistant 프로젝트 설명, 기능 안내, Python/FastAPI 학습 질문, "
        "에러 해결 방향을 도와주는 용도로 설계되었습니다.\n\n"
        "더 자유로운 AI 답변을 원하면 EC2 환경변수에 HF_TOKEN이 설정되어 있는지 확인해주세요."
    )


def call_huggingface_chat(user_id: int, message: str) -> Optional[str]:
    hf_token = os.getenv("HF_TOKEN")
    hf_model = os.getenv("HF_MODEL", "openai/gpt-oss-20b:fireworks-ai")

    if not hf_token:
        return None

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(load_recent_messages(user_id))
    messages.append({"role": "user", "content": message})

    try:
        res = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {hf_token}",
                "Content-Type": "application/json",
            },
            json={
                "model": hf_model,
                "messages": messages,
                "max_tokens": 1200,
                "temperature": 0.25,
            },
            timeout=60,
        )

        if res.status_code != 200:
            return None

        data = res.json()
        content = data["choices"][0]["message"].get("content") or ""
        content = content.strip()
        return content if content else None

    except Exception:
        return None


@router.post("/chat")
def chat(data: ChatRequest, token_user_id: Optional[int] = Depends(get_current_user_id_from_header)):
    message = data.message.strip()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="메시지를 입력해주세요.",
        )

    if len(message) > MAX_USER_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"메시지는 {MAX_USER_MESSAGE_LENGTH}자 이하로 입력해주세요.",
        )

    conn = get_conn()
    cursor = conn.cursor()
    _validate_user(cursor, data.user_id, token_user_id)
    conn.close()

    save_chat_message(data.user_id, "user", message)

    ai_reply = call_huggingface_chat(data.user_id, message)
    reply = ai_reply or fallback_reply(message)

    save_chat_message(data.user_id, "assistant", reply)

    return {
        "reply": reply,
        "source": "huggingface" if ai_reply else "fallback",
    }


@router.get("/chat/history")
def get_chat_history(
    user_id: int = Query(...),
    token_user_id: Optional[int] = Depends(get_current_user_id_from_header),
):
    conn = get_conn()
    cursor = conn.cursor()
    _validate_user(cursor, user_id, token_user_id)

    cursor.execute("""
        SELECT id, role, message, created_at
        FROM chat_history
        WHERE user_id = ?
        ORDER BY id ASC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    return {
        "history": [
            {
                "id": row["id"],
                "role": row["role"],
                "message": row["message"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    }


@router.delete("/chat/history")
def clear_chat_history(
    user_id: int = Query(...),
    token_user_id: Optional[int] = Depends(get_current_user_id_from_header),
):
    conn = get_conn()
    cursor = conn.cursor()
    _validate_user(cursor, user_id, token_user_id)

    cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return {"message": "챗봇 대화 기록을 삭제했습니다."}
