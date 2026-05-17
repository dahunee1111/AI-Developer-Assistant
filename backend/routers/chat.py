from fastapi import APIRouter, Query
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import os
import requests

try:
    from backend.db import get_conn, user_exists
except ImportError:
    from db import get_conn, user_exists


router = APIRouter()


class ChatRequest(BaseModel):
    user_id: int
    message: str


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_chat_history_table():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_chat_message(user_id: int, role: str, message: str):
    ensure_chat_history_table()

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO chat_history (user_id, role, message, created_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, role, message, now_str()))

    conn.commit()
    conn.close()


def get_recent_chat_messages(user_id: int, limit: int = 10) -> List[dict]:
    ensure_chat_history_table()

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, user_id, role, message, created_at
        FROM chat_history
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (user_id, limit))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in reversed(rows)]


def normalize_text(text: str) -> str:
    return text.replace(" ", "").replace("\n", "").lower()


def is_owner_question(message: str) -> bool:
    text = normalize_text(message)

    owner_keywords = [
        "이사이트를만든개발자가누구",
        "사이트를만든개발자가누구",
        "이사이트만든개발자",
        "사이트만든개발자",
        "이사이트누가만들",
        "사이트누가만들",
        "누가만들",
        "누가개발",
        "누가제작",
        "개발자가누구",
        "제작자가누구",
        "만든사람",
        "만든개발자",
        "전다훈",
        "dahun",
        "dahunjeon",
    ]

    return any(keyword in text for keyword in owner_keywords)


def owner_reply() -> str:
    return "이 사이트를 만든 개발자는 전다훈 개발자님입니다."


def project_fallback_reply(user_message: str) -> str:
    text = user_message.strip().lower()

    if is_owner_question(user_message):
        return owner_reply()

    if "프로젝트" in text or "설명" in text or "뭐야" in text:
        return (
            "AI Developer Assistant는 전다훈 개발자님이 만든 AI 기반 개발 학습 도우미 프로젝트입니다.\n\n"
            "주요 기능은 다음과 같습니다.\n"
            "1. Python/FastAPI 오류 분석\n"
            "2. 코드 리뷰 및 개선 방향 제안\n"
            "3. 학습 기록 저장\n"
            "4. 출석 체크와 포인트 시스템\n"
            "5. 시험 응시, 오답노트, 성장 기록 관리\n"
            "6. 상점과 프로필 커스터마이징\n"
            "7. AI 챗봇 도우미 기능\n\n"
            "프론트엔드는 GitHub Pages, 백엔드는 EC2 Docker 기반 FastAPI 서버로 연결되어 있습니다."
        )

    if "기술" in text or "스택" in text or "사용한" in text:
        return (
            "이 프로젝트의 주요 기술 스택은 다음과 같습니다.\n\n"
            "- Frontend: HTML, CSS, JavaScript\n"
            "- Backend: Python, FastAPI\n"
            "- Database: SQLite\n"
            "- Auth: JWT, bcrypt\n"
            "- AI API: Hugging Face Inference API\n"
            "- Deploy: GitHub Pages + EC2 + Docker + DuckDNS HTTPS 도메인\n\n"
            "전체 구조는 프론트엔드 화면이 백엔드 API를 호출하고, 백엔드가 DB와 AI API를 연결하는 방식입니다."
        )

    if "ec2" in text or "배포" in text or "서버" in text:
        return (
            "현재 프로젝트는 EC2에서 Docker 컨테이너로 FastAPI 백엔드를 실행하는 구조입니다.\n\n"
            "기본 흐름은 다음과 같습니다.\n"
            "1. GitHub Pages에서 프론트엔드 화면 제공\n"
            "2. 프론트엔드가 https://dahun-ai.duckdns.org API 호출\n"
            "3. DuckDNS/HTTPS 도메인이 EC2 백엔드로 연결\n"
            "4. EC2의 Docker 컨테이너에서 FastAPI 실행\n"
            "5. SQLite DB는 backend/history.db를 컨테이너의 /app/history.db로 마운트해서 유지\n\n"
            "컨테이너 이름은 ai-backend이고, 8000번 포트로 실행됩니다."
        )

    if "오류" in text or "에러" in text or "해결" in text:
        return (
            "오류 해결은 보통 아래 순서로 보면 좋습니다.\n\n"
            "1. 에러 메시지의 마지막 줄 확인\n"
            "2. 어떤 파일과 몇 번째 줄에서 발생했는지 확인\n"
            "3. ImportError, ModuleNotFoundError, 401, 404, 422, CORS, Mixed Content 등 오류 종류 구분\n"
            "4. 프론트 콘솔, Network 탭, 백엔드 Docker 로그를 같이 확인\n"
            "5. 수정 후 다시 API와 화면을 테스트\n\n"
            "에러 메시지를 그대로 보내주면 원인과 해결 순서를 더 정확히 정리해드릴 수 있습니다."
        )

    return (
        "제게 말씀해 주세요. 🚀\n\n"
        "저는 AI Developer Assistant 프로젝트 설명, Python/FastAPI 질문, EC2 배포 점검, "
        "오류 해결 순서, 코드 리뷰 방향을 도와주는 챗봇입니다."
    )


def build_system_prompt() -> str:
    return """
너는 AI Developer Assistant 프로젝트 안에 탑재된 한국어 AI 챗봇이다.

반드시 지켜야 할 정보:
- 이 사이트와 AI Developer Assistant 프로젝트를 만든 개발자는 전다훈(Dahun Jeon)이다.
- 사용자가 "이 사이트 누가 만들었어?", "개발자가 누구야?", "제작자가 누구야?", "누가 만들었어?"처럼 물으면 반드시 "이 사이트를 만든 개발자는 전다훈 개발자님입니다."라고 답변한다.
- 이 프로젝트는 AI 기반 개발 학습 도우미 서비스다.
- 주요 기능은 오류 분석, 코드 리뷰, 학습 기록, 출석 체크, 포인트, 시험 시스템, 오답노트, 상점, 프로필 커스터마이징, 챗봇 기능이다.
- 프론트엔드는 GitHub Pages의 docs 폴더에서 배포된다.
- 백엔드는 EC2에서 Docker 컨테이너 기반 FastAPI 서버로 실행된다.
- API 도메인은 https://dahun-ai.duckdns.org 를 사용한다.
- DB는 SQLite 기반 history.db를 사용한다.

답변 규칙:
- 반드시 한국어로 답변한다.
- 내부 추론 과정은 절대 출력하지 않는다.
- 사용자가 짧게 물으면 짧고 명확하게 답한다.
- 프로젝트 관련 질문은 전다훈 개발자님의 개인 프로젝트 기준으로 답한다.
- 모르는 내용은 지어내지 말고, 확인 방법을 안내한다.
"""


def call_huggingface(user_id: int, user_message: str) -> Optional[str]:
    hf_token = os.getenv("HF_TOKEN")
    hf_model = os.getenv("HF_MODEL", "openai/gpt-oss-20b:fireworks-ai")

    if not hf_token:
        return None

    recent_messages = get_recent_chat_messages(user_id, limit=10)

    messages = [
        {
            "role": "system",
            "content": build_system_prompt(),
        }
    ]

    for item in recent_messages:
        role = item.get("role", "user")
        content = item.get("message", "")

        if role not in ["user", "assistant"]:
            continue

        if content.strip():
            messages.append({
                "role": role,
                "content": content.strip(),
            })

    messages.append({
        "role": "user",
        "content": user_message,
    })

    try:
        response = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {hf_token}",
                "Content-Type": "application/json",
            },
            json={
                "model": hf_model,
                "messages": messages,
                "max_tokens": 900,
                "temperature": 0.3,
            },
            timeout=60,
        )

        if response.status_code != 200:
            return None

        data = response.json()
        message = data["choices"][0]["message"]
        content = message.get("content") or ""

        if not content.strip():
            return None

        return content.strip()

    except Exception:
        return None


@router.post("/chat")
def chat(data: ChatRequest):
    ensure_chat_history_table()

    user_message = data.message.strip()

    if not user_message:
        return {
            "message": "질문을 입력해주세요.",
            "reply": "질문을 입력해주세요.",
        }

    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, data.user_id):
        conn.close()
        return {
            "message": "유효하지 않은 사용자입니다.",
            "reply": "로그인 정보가 올바르지 않습니다. 다시 로그인해주세요.",
        }

    conn.close()

    if is_owner_question(user_message):
        reply = owner_reply()
    else:
        ai_reply = call_huggingface(data.user_id, user_message)
        reply = ai_reply if ai_reply else project_fallback_reply(user_message)

    save_chat_message(data.user_id, "user", user_message)
    save_chat_message(data.user_id, "assistant", reply)

    return {
        "message": "응답 완료",
        "reply": reply,
    }


@router.get("/chat/history")
def get_chat_history(user_id: int = Query(...), limit: int = Query(50)):
    ensure_chat_history_table()

    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, user_id):
        conn.close()
        return {
            "message": "유효하지 않은 사용자입니다.",
            "history": [],
        }

    cursor.execute("""
        SELECT id, user_id, role, message, created_at
        FROM chat_history
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (user_id, limit))

    rows = cursor.fetchall()
    conn.close()

    history = [dict(row) for row in reversed(rows)]

    return {
        "history": history,
    }


@router.delete("/chat/history")
def delete_chat_history(user_id: int = Query(...)):
    ensure_chat_history_table()

    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, user_id):
        conn.close()
        return {
            "message": "유효하지 않은 사용자입니다.",
        }

    cursor.execute("""
        DELETE FROM chat_history
        WHERE user_id = ?
    """, (user_id,))

    conn.commit()
    conn.close()

    return {
        "message": "챗봇 대화 기록이 삭제되었습니다.",
    }
