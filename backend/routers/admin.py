from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json

try:
    from backend.db import get_conn
except ImportError:
    from db import get_conn

router = APIRouter()


class ExamCreateRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    difficulty: str


class QuestionCreateRequest(BaseModel):
    exam_set_id: int
    question_type: str
    question_text: str
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    starter_code: Optional[str] = None
    test_cases: Optional[List[dict]] = None
    score: int = 10


@router.post("/exams")
def create_exam(data: ExamCreateRequest):
    title = data.title.strip()
    difficulty = data.difficulty.strip().lower()

    if not title:
        return {"message": "시험 제목을 입력해주세요."}

    if difficulty not in ["easy", "medium", "hard"]:
        return {"message": "난이도는 easy, medium, hard 중 하나여야 합니다."}

    conn = get_conn()
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO exam_sets (title, description, difficulty, created_at)
        VALUES (?, ?, ?, ?)
    """, (title, data.description or "", difficulty, created_at))

    exam_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "message": "시험이 생성되었습니다.",
        "exam_id": exam_id
    }


@router.put("/exams/{exam_id}")
def update_exam(exam_id: int, data: ExamCreateRequest):
    title = data.title.strip()
    difficulty = data.difficulty.strip().lower()

    if not title:
        return {"message": "시험 제목을 입력해주세요."}

    if difficulty not in ["easy", "medium", "hard"]:
        return {"message": "난이도는 easy, medium, hard 중 하나여야 합니다."}

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM exam_sets WHERE id = ?", (exam_id,))
    exam = cursor.fetchone()
    if not exam:
        conn.close()
        return {"message": "수정할 시험을 찾을 수 없습니다."}

    cursor.execute("""
        UPDATE exam_sets
        SET title = ?, description = ?, difficulty = ?
        WHERE id = ?
    """, (title, data.description or "", difficulty, exam_id))

    conn.commit()
    conn.close()

    return {"message": "시험이 수정되었습니다."}


@router.delete("/exams/{exam_id}")
def delete_exam(exam_id: int):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM exam_sets WHERE id = ?", (exam_id,))
    exam = cursor.fetchone()
    if not exam:
        conn.close()
        return {"message": "삭제할 시험을 찾을 수 없습니다."}

    cursor.execute("DELETE FROM questions WHERE exam_set_id = ?", (exam_id,))
    cursor.execute("DELETE FROM exam_results WHERE exam_set_id = ?", (exam_id,))
    cursor.execute("DELETE FROM wrong_notes WHERE exam_set_id = ?", (exam_id,))
    cursor.execute("DELETE FROM exam_sets WHERE id = ?", (exam_id,))

    conn.commit()
    conn.close()

    return {"message": "시험이 삭제되었습니다."}


@router.post("/questions")
def create_question(data: QuestionCreateRequest):
    question_type = data.question_type.strip().lower()

    if question_type not in ["multiple", "code"]:
        return {"message": "문제 유형은 multiple 또는 code 여야 합니다."}

    if not data.question_text.strip():
        return {"message": "문제 내용을 입력해주세요."}

    if data.score <= 0:
        return {"message": "배점은 1점 이상이어야 합니다."}

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM exam_sets WHERE id = ?", (data.exam_set_id,))
    exam = cursor.fetchone()
    if not exam:
        conn.close()
        return {"message": "대상 시험을 찾을 수 없습니다."}

    if question_type == "multiple":
        if not data.options or len(data.options) < 2:
            conn.close()
            return {"message": "객관식 문제는 최소 2개 이상의 보기가 필요합니다."}
        if not data.correct_answer:
            conn.close()
            return {"message": "객관식 문제는 정답이 필요합니다."}
        if data.correct_answer not in data.options:
            conn.close()
            return {"message": "객관식 정답은 보기 목록 중 하나여야 합니다."}

    if question_type == "code":
        if not data.test_cases or len(data.test_cases) == 0:
            conn.close()
            return {"message": "코드 문제는 테스트케이스가 필요합니다."}

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO questions (
            exam_set_id, question_type, question_text, options, correct_answer,
            starter_code, test_cases, score, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.exam_set_id,
        question_type,
        data.question_text.strip(),
        json.dumps(data.options, ensure_ascii=False) if data.options else None,
        data.correct_answer,
        data.starter_code,
        json.dumps(data.test_cases, ensure_ascii=False) if data.test_cases else None,
        data.score,
        created_at
    ))

    question_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "message": "문제가 생성되었습니다.",
        "question_id": question_id
    }


@router.put("/questions/{question_id}")
def update_question(question_id: int, data: QuestionCreateRequest):
    question_type = data.question_type.strip().lower()

    if question_type not in ["multiple", "code"]:
        return {"message": "문제 유형은 multiple 또는 code 여야 합니다."}

    if not data.question_text.strip():
        return {"message": "문제 내용을 입력해주세요."}

    if data.score <= 0:
        return {"message": "배점은 1점 이상이어야 합니다."}

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM questions WHERE id = ?", (question_id,))
    question = cursor.fetchone()
    if not question:
        conn.close()
        return {"message": "수정할 문제를 찾을 수 없습니다."}

    cursor.execute("SELECT id FROM exam_sets WHERE id = ?", (data.exam_set_id,))
    exam = cursor.fetchone()
    if not exam:
        conn.close()
        return {"message": "대상 시험을 찾을 수 없습니다."}

    if question_type == "multiple":
        if not data.options or len(data.options) < 2:
            conn.close()
            return {"message": "객관식 문제는 최소 2개 이상의 보기가 필요합니다."}
        if not data.correct_answer:
            conn.close()
            return {"message": "객관식 문제는 정답이 필요합니다."}
        if data.correct_answer not in data.options:
            conn.close()
            return {"message": "객관식 정답은 보기 목록 중 하나여야 합니다."}

    if question_type == "code":
        if not data.test_cases or len(data.test_cases) == 0:
            conn.close()
            return {"message": "코드 문제는 테스트케이스가 필요합니다."}

    cursor.execute("""
        UPDATE questions
        SET exam_set_id = ?, question_type = ?, question_text = ?, options = ?, correct_answer = ?,
            starter_code = ?, test_cases = ?, score = ?
        WHERE id = ?
    """, (
        data.exam_set_id,
        question_type,
        data.question_text.strip(),
        json.dumps(data.options, ensure_ascii=False) if data.options else None,
        data.correct_answer,
        data.starter_code,
        json.dumps(data.test_cases, ensure_ascii=False) if data.test_cases else None,
        data.score,
        question_id
    ))

    conn.commit()
    conn.close()

    return {"message": "문제가 수정되었습니다."}


@router.delete("/questions/{question_id}")
def delete_question(question_id: int):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM questions WHERE id = ?", (question_id,))
    question = cursor.fetchone()
    if not question:
        conn.close()
        return {"message": "삭제할 문제를 찾을 수 없습니다."}

    cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()

    return {"message": "문제가 삭제되었습니다."}
