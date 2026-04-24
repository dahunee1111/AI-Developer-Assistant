from fastapi import APIRouter, Query
from pydantic import BaseModel
from datetime import datetime, date
import os
import requests

from db import (
    get_conn,
    user_exists,
    add_points,
    get_total_points,
)

router = APIRouter()


# ====== Request Schemas ======
class ErrorRequest(BaseModel):
    user_id: int
    error_text: str


class CodeRequest(BaseModel):
    user_id: int
    code_text: str


class JournalRequest(BaseModel):
    user_id: int
    content: str


class AttendanceRequest(BaseModel):
    user_id: int


# ====== 내부 유틸 ======
def call_huggingface(prompt: str) -> str:
    """
    Hugging Face Inference Providers 호출
    Render 환경변수 HF_TOKEN 필요
    선택 환경변수 HF_MODEL로 모델 변경 가능
    """
    hf_token = os.getenv("HF_TOKEN")
    hf_model = os.getenv("HF_MODEL", "openai/gpt-oss-20b:fireworks-ai")

    if not hf_token:
        return "Hugging Face API 토큰이 설정되지 않았습니다. Render 환경변수 HF_TOKEN을 확인해주세요."

    try:
        res = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {hf_token}",
                "Content-Type": "application/json",
            },
            json={
                "model": hf_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "너는 Python, FastAPI, AI 개발 학습을 돕는 한국어 튜터다. "
                            "초보자도 이해할 수 있게 원인, 해결 방법, 예시를 명확히 설명한다. "
                            "답변은 반드시 한국어로 한다."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "max_tokens": 1200,
                "temperature": 0.2,
            },
            timeout=40,
        )

        if res.status_code != 200:
            return f"Hugging Face API 오류: {res.status_code}\n{res.text}"

        data = res.json()

        try:
            message = data["choices"][0]["message"]

            content = (
                message.get("content")
                or message.get("reasoning_content")
                or ""
            )

            if content:
                return content.strip()

            return f"Hugging Face 응답 형식 오류:\n{data}"

        except (KeyError, IndexError, TypeError):
            return f"Hugging Face 응답 형식 오류:\n{data}"

    except requests.exceptions.Timeout:
        return "Hugging Face API 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."

    except Exception as e:
        return f"Hugging Face 연결 오류: {str(e)}"


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ====== 분석 ======
@router.post("/analyze")
def analyze_error(data: ErrorRequest):
    if not data.error_text.strip():
        return {"message": "에러 내용을 입력해주세요."}

    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, data.user_id):
        conn.close()
        return {"message": "유효하지 않은 사용자입니다."}

    prompt = f"""다음 Python 에러를 초보자도 이해할 수 있게 분석해줘.

아래 형식으로 답변해줘.

1. 에러 원인
2. 왜 발생했는지
3. 해결 방법
4. 수정 예시 또는 확인할 코드
5. 다시 안 나게 하는 팁

에러:
{data.error_text}
"""

    result = call_huggingface(prompt)

    cursor.execute("""
        INSERT INTO analysis_history (user_id, error_text, result_text, created_at)
        VALUES (?, ?, ?, ?)
    """, (data.user_id, data.error_text, result, now_str()))

    conn.commit()
    conn.close()

    add_points(data.user_id, 10, "에러 분석 수행")

    return {"result": result}


@router.post("/code-review")
def code_review(data: CodeRequest):
    if not data.code_text.strip():
        return {"message": "코드를 입력해주세요."}

    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, data.user_id):
        conn.close()
        return {"message": "유효하지 않은 사용자입니다."}

    prompt = f"""다음 Python 코드를 리뷰해줘.

아래 형식으로 답변해줘.

1. 코드의 목적 추정
2. 문제점
3. 개선 포인트
4. 더 나은 코드 예시
5. 학습 포인트

코드:
{data.code_text}
"""

    result = call_huggingface(prompt)

    cursor.execute("""
        INSERT INTO code_review_history (user_id, code_text, result_text, created_at)
        VALUES (?, ?, ?, ?)
    """, (data.user_id, data.code_text, result, now_str()))

    conn.commit()
    conn.close()

    add_points(data.user_id, 10, "코드 리뷰 수행")

    return {"result": result}


# ====== 히스토리 ======
@router.get("/history")
def get_history(user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, error_text, result_text, created_at
        FROM analysis_history
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    return {"history": [dict(r) for r in rows]}


@router.get("/code-review-history")
def get_code_review_history(user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, code_text, result_text, created_at
        FROM code_review_history
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    return {"history": [dict(r) for r in rows]}


# ====== 저널 ======
@router.get("/journal")
def get_journal(user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, content, created_at
        FROM learning_journal
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    return {"journal": [dict(r) for r in rows]}


@router.post("/journal")
def create_journal(data: JournalRequest):
    if not data.content.strip():
        return {"message": "내용을 입력해주세요."}

    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, data.user_id):
        conn.close()
        return {"message": "유효하지 않은 사용자입니다."}

    cursor.execute("""
        INSERT INTO learning_journal (user_id, content, created_at)
        VALUES (?, ?, ?)
    """, (data.user_id, data.content, now_str()))

    conn.commit()
    conn.close()

    add_points(data.user_id, 5, "학습 기록 작성")

    return {"message": "저장 완료"}


@router.put("/journal/{journal_id}")
def update_journal(journal_id: int, data: JournalRequest):
    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, data.user_id):
        conn.close()
        return {"message": "유효하지 않은 사용자입니다."}

    cursor.execute("""
        UPDATE learning_journal
        SET content = ?
        WHERE id = ? AND user_id = ?
    """, (data.content, journal_id, data.user_id))

    conn.commit()
    conn.close()

    return {"message": "수정 완료"}


@router.delete("/journal/{journal_id}")
def delete_journal(journal_id: int, user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, user_id):
        conn.close()
        return {"message": "유효하지 않은 사용자입니다."}

    cursor.execute("""
        DELETE FROM learning_journal
        WHERE id = ? AND user_id = ?
    """, (journal_id, user_id))

    conn.commit()
    conn.close()

    return {"message": "삭제 완료"}


# ====== 출석 ======
@router.get("/attendance")
def get_attendance(user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, user_id):
        conn.close()
        return {
            "message": "사용자를 찾을 수 없습니다.",
            "attendance_dates": [],
            "today_checked": False,
            "total_days": 0,
        }

    cursor.execute("""
        SELECT DISTINCT substr(created_at, 1, 10) as study_date
        FROM learning_journal
        WHERE user_id = ?
        ORDER BY study_date DESC
    """, (user_id,))
    journal_rows = cursor.fetchall()

    cursor.execute("""
        SELECT attendance_date
        FROM attendance_records
        WHERE user_id = ?
        ORDER BY attendance_date DESC
    """, (user_id,))
    attendance_rows = cursor.fetchall()

    conn.close()

    journal_dates = {row["study_date"] for row in journal_rows}
    attendance_dates = {row["attendance_date"] for row in attendance_rows}
    merged_dates = sorted(journal_dates.union(attendance_dates), reverse=True)

    today = date.today().strftime("%Y-%m-%d")

    return {
        "attendance_dates": merged_dates,
        "today_checked": today in attendance_dates,
        "total_days": len(merged_dates),
    }


@router.post("/attendance/check")
def check_attendance(data: AttendanceRequest):
    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, data.user_id):
        conn.close()
        return {"message": "사용자를 찾을 수 없습니다."}

    today = date.today().strftime("%Y-%m-%d")
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        SELECT id
        FROM attendance_records
        WHERE user_id = ? AND attendance_date = ?
    """, (data.user_id, today))

    existing = cursor.fetchone()

    if existing:
        conn.close()
        return {
            "message": "오늘은 이미 출석체크를 완료했습니다.",
            "awarded_points": 0,
            "today_checked": True,
            "total_points": get_total_points(data.user_id),
        }

    cursor.execute("""
        INSERT INTO attendance_records (user_id, attendance_date, created_at)
        VALUES (?, ?, ?)
    """, (data.user_id, today, created_at))

    conn.commit()
    conn.close()

    add_points(data.user_id, 10, "출석 체크")
    total_points = get_total_points(data.user_id)

    return {
        "message": "출석체크 완료! 10포인트를 획득했습니다.",
        "awarded_points": 10,
        "today_checked": True,
        "total_points": total_points,
    }


# ====== 포인트 ======
@router.get("/points")
def get_points(user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, user_id):
        conn.close()
        return {"message": "사용자를 찾을 수 없습니다.", "total_points": 0}

    conn.close()

    return {
        "user_id": user_id,
        "total_points": get_total_points(user_id),
    }


@router.get("/point-logs")
def get_point_logs(user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, user_id):
        conn.close()
        return {
            "message": "사용자를 찾을 수 없습니다.",
            "logs": [],
            "total_points": 0,
        }

    cursor.execute("""
        SELECT id, amount, reason, created_at
        FROM point_logs
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    return {
        "logs": [
            {
                "id": row["id"],
                "amount": row["amount"],
                "reason": row["reason"],
                "created_at": row["created_at"],
            }
            for row in rows
        ],
        "total_points": get_total_points(user_id),
    }


# ====== 통계 ======
@router.get("/stats")
def stats(user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, user_id):
        conn.close()
        return {
            "message": "사용자를 찾을 수 없습니다.",
            "analysis_count": 0,
            "code_review_count": 0,
            "journal_count": 0,
            "total_points": 0,
        }

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM analysis_history WHERE user_id = ?",
        (user_id,),
    )
    analysis_cnt = cursor.fetchone()["cnt"]

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM code_review_history WHERE user_id = ?",
        (user_id,),
    )
    review_cnt = cursor.fetchone()["cnt"]

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM learning_journal WHERE user_id = ?",
        (user_id,),
    )
    journal_cnt = cursor.fetchone()["cnt"]

    conn.close()

    total_points = get_total_points(user_id)

    return {
        "analysis_count": analysis_cnt,
        "code_review_count": review_cnt,
        "journal_count": journal_cnt,
        "total_points": total_points,
    }