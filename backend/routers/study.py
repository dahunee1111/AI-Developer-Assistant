from fastapi import APIRouter, Query
from pydantic import BaseModel
from datetime import datetime, date
import requests
import json

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
def call_ollama(prompt: str) -> str:
    """
    로컬 Ollama 서버 호출 (없으면 간단한 fallback 반환)
    """
    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False,
            },
            timeout=15,
        )
        if res.status_code == 200:
            data = res.json()
            return data.get("response", "").strip() or "AI 응답이 비어 있습니다."
        return f"Ollama 오류: {res.status_code}"
    except Exception:
        return "AI 서버에 연결할 수 없습니다. (Ollama 미실행 혹은 네트워크 문제)"


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

    prompt = f"""다음 Python 에러를 초보자도 이해할 수 있게 설명하고 해결 방법을 단계별로 알려줘:

에러:
{data.error_text}
"""
    result = call_ollama(prompt)

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
- 문제점
- 개선 포인트
- 더 나은 코드 예시

코드:
{data.code_text}
"""
    result = call_ollama(prompt)

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
            "total_days": 0
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
        "total_days": len(merged_dates)
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
            "total_points": get_total_points(data.user_id)
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
        "total_points": total_points
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
        "total_points": get_total_points(user_id)
    }


@router.get("/point-logs")
def get_point_logs(user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, user_id):
        conn.close()
        return {"message": "사용자를 찾을 수 없습니다.", "logs": [], "total_points": 0}

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
                "created_at": row["created_at"]
            }
            for row in rows
        ],
        "total_points": get_total_points(user_id)
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

    cursor.execute("SELECT COUNT(*) as cnt FROM analysis_history WHERE user_id = ?", (user_id,))
    analysis_cnt = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM code_review_history WHERE user_id = ?", (user_id,))
    review_cnt = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM learning_journal WHERE user_id = ?", (user_id,))
    journal_cnt = cursor.fetchone()["cnt"]

    conn.close()

    total_points = get_total_points(user_id)

    return {
        "analysis_count": analysis_cnt,
        "code_review_count": review_cnt,
        "journal_count": journal_cnt,
        "total_points": total_points,
    }