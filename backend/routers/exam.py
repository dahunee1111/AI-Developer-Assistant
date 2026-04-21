from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional
import json
import requests
from datetime import datetime

from db import (
    get_conn,
    user_exists,
    add_points,
    get_total_points,
)

router = APIRouter()

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"


class UserAnswer(BaseModel):
    question_id: int
    answer: Optional[str] = None
    code: Optional[str] = None


class SubmitExamRequest(BaseModel):
    user_id: int
    answers: List[UserAnswer]


class WrongNoteReviewRequest(BaseModel):
    user_id: int
    is_reviewed: bool


def call_ollama(prompt: str, timeout: int = 45) -> Optional[str]:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
    except Exception:
        return None


def grade_code_question(user_code: str, test_cases: List[dict]) -> dict:
    local_env = {}

    try:
        exec(user_code, {}, local_env)
    except Exception as e:
        return {
            "passed": False,
            "error": f"코드 실행 오류: {str(e)}",
            "passed_count": 0,
            "total_count": len(test_cases),
            "failed_cases": []
        }

    if "solution" not in local_env:
        return {
            "passed": False,
            "error": "solution 함수가 정의되어 있지 않습니다.",
            "passed_count": 0,
            "total_count": len(test_cases),
            "failed_cases": []
        }

    solution = local_env["solution"]
    passed_count = 0
    failed_cases = []

    for tc in test_cases:
        try:
            result = solution(tc["input"])
            if result == tc["output"]:
                passed_count += 1
            else:
                failed_cases.append({
                    "input": tc["input"],
                    "expected": tc["output"],
                    "got": result
                })
        except Exception as e:
            failed_cases.append({
                "input": tc["input"],
                "expected": tc["output"],
                "error": str(e)
            })

    return {
        "passed": passed_count == len(test_cases),
        "passed_count": passed_count,
        "total_count": len(test_cases),
        "failed_cases": failed_cases
    }


def analyze_code_mistake(user_code: str, judge_result: dict) -> str:
    reasons = []
    error_text = str(judge_result.get("error", ""))

    if "cannot access local variable" in error_text:
        reasons.append("변수를 초기화하지 않고 사용하고 있습니다. 예를 들어 total = 0 같은 초기값이 필요합니다.")

    if "= +" in user_code:
        reasons.append("누적 연산이 아니라 값이 계속 덮어써지고 있습니다. total += i 형태가 필요합니다.")

    if judge_result.get("error"):
        reasons.append("입력 데이터가 비어있을 때 처리 로직이 없을 가능성이 큽니다.")

    passed = judge_result.get("passed_count", 0)
    total = judge_result.get("total_count", 0)

    if passed > 0 and passed < total:
        reasons.append("일부 케이스만 통과했습니다. 특정 조건이나 예외 케이스에서 로직이 틀립니다.")

    if passed == 0 and total > 0:
        reasons.append("모든 테스트 케이스에서 실패했습니다. 기본 로직을 다시 확인해야 합니다.")

    failed_cases = judge_result.get("failed_cases", [])
    if failed_cases:
        first_case = failed_cases[0]
        if "expected" in first_case and "got" in first_case:
            reasons.append(
                f"실패 예시: 입력 {first_case['input']} 에서 기대값은 {first_case['expected']} 이지만 실제 결과는 {first_case['got']} 입니다."
            )
        elif "expected" in first_case and "error" in first_case:
            reasons.append(
                f"실패 예시: 입력 {first_case['input']} 에서 기대값은 {first_case['expected']} 이고, 실행 중 오류는 {first_case['error']} 입니다."
            )

    if not reasons:
        return "코드가 일부 동작하지만 특정 케이스에서 문제가 발생합니다. 로직을 다시 점검하세요."

    return "\n".join([f"- {r}" for r in reasons])


def generate_ai_wrong_explanation(question_type: str, question_text: str, user_answer: str, correct_answer: str, review_note: str) -> str:
    prompt = f"""
너는 Python 학습 코치다.
아래 오답에 대해 한국어로 짧고 이해하기 쉽게 설명해줘.

반드시 아래 형식으로만 답변해:
1. 왜 틀렸는지
2. 어떻게 고쳐야 하는지
3. 다음에 체크할 포인트

문제 유형: {question_type}
문제: {question_text}
사용자 답변: {user_answer}
정답/기준: {correct_answer}
기본 분석: {review_note}
"""
    ai_result = call_ollama(prompt, timeout=35)
    if ai_result:
        return ai_result

    return (
        "1. 왜 틀렸는지\n"
        f"{review_note}\n\n"
        "2. 어떻게 고쳐야 하는지\n"
        "문제에서 요구한 출력 형태와 예외 케이스를 다시 확인하세요.\n\n"
        "3. 다음에 체크할 포인트\n"
        "내 답, 정답, 실패 케이스를 비교한 뒤 다시 풀어보세요."
    )


def save_wrong_notes(user_id: int, exam_result_id: int, exam_set_id: int, exam_title: str, detail_result: list):
    conn = get_conn()
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in detail_result:
        question_type = item.get("question_type")
        question_id = item.get("question_id")
        question_text = item.get("question_text", "")

        if question_type == "multiple":
            if item.get("is_correct"):
                continue

            user_answer_text = (item.get("user_answer") or "").strip()
            review_note = "답안을 입력하지 않았습니다." if user_answer_text == "" else "객관식 오답입니다. 내가 고른 답과 정답을 비교해서 개념 차이를 복습하세요."

            cursor.execute("""
                INSERT INTO wrong_notes (
                    user_id, exam_result_id, exam_set_id, exam_title, question_id, question_type,
                    question_text, user_answer, correct_answer, review_note,
                    ai_explanation, status, is_reviewed, reviewed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                exam_result_id,
                exam_set_id,
                exam_title,
                question_id,
                question_type,
                question_text,
                user_answer_text,
                item.get("correct_answer", ""),
                review_note,
                item.get("ai_explanation", ""),
                "wrong",
                0,
                None,
                created_at
            ))

        elif question_type == "code":
            judge_result = item.get("judge_result", {})
            passed_count = judge_result.get("passed_count", 0)
            total_count = judge_result.get("total_count", 0)
            user_code_text = (item.get("user_code") or "").strip()

            if total_count > 0 and passed_count == total_count:
                continue

            status = "partial" if passed_count > 0 else "wrong"
            review_note = "코드를 입력하지 않았습니다." if user_code_text == "" else (item.get("analysis") or "코드 문제 오답입니다. 실패한 테스트케이스와 오류 메시지를 중심으로 로직을 다시 확인하세요.")

            reference_answer = ""
            failed_cases = judge_result.get("failed_cases", [])
            if failed_cases:
                reference_answer = json.dumps(failed_cases, ensure_ascii=False)

            cursor.execute("""
                INSERT INTO wrong_notes (
                    user_id, exam_result_id, exam_set_id, exam_title, question_id, question_type,
                    question_text, user_code, reference_answer, review_note,
                    ai_explanation, status, is_reviewed, reviewed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                exam_result_id,
                exam_set_id,
                exam_title,
                question_id,
                question_type,
                question_text,
                user_code_text,
                reference_answer,
                review_note,
                item.get("ai_explanation", ""),
                status,
                0,
                None,
                created_at
            ))

    conn.commit()
    conn.close()


def compute_recommended_difficulty(user_id: int):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT status, is_reviewed, question_type
        FROM wrong_notes
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 20
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {
            "recommended_difficulty": "easy",
            "reason": "아직 시험 기록이 많지 않아 easy부터 추천합니다."
        }

    wrong_count = 0
    partial_count = 0
    reviewed_count = 0

    for row in rows:
        if row["status"] == "wrong":
            wrong_count += 1
        elif row["status"] == "partial":
            partial_count += 1
        if row["is_reviewed"]:
            reviewed_count += 1

    severity = wrong_count * 1.0 + partial_count * 0.6

    if severity >= 10:
        difficulty = "easy"
        reason = "최근 오답과 부분정답 비율이 높아 easy 난이도로 기초를 다지는 것이 좋습니다."
    elif severity >= 5:
        difficulty = "medium"
        reason = "기초는 어느 정도 잡혀 있지만 예외 케이스에서 흔들려 medium 난이도가 적절합니다."
    else:
        difficulty = "hard"
        reason = "최근 성적과 복습 흐름이 안정적이라 hard 난이도로 도전해볼 수 있습니다."

    if reviewed_count >= max(1, len(rows) // 2) and difficulty == "easy":
        difficulty = "medium"
        reason = "오답 복습이 꾸준해서 easy보다 한 단계 높은 medium 난이도를 추천합니다."

    return {
        "recommended_difficulty": difficulty,
        "reason": reason
    }


def build_exam_recommendations(user_id: int):
    conn = get_conn()
    cursor = conn.cursor()

    difficulty_info = compute_recommended_difficulty(user_id)
    target_difficulty = difficulty_info["recommended_difficulty"]

    cursor.execute("""
        SELECT id, title, description, difficulty, created_at
        FROM exam_sets
        ORDER BY id DESC
    """)
    exams = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT question_type, status
        FROM wrong_notes
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 20
    """, (user_id,))
    wrong_rows = cursor.fetchall()
    conn.close()

    weak_code = sum(1 for row in wrong_rows if row["question_type"] == "code")
    weak_multiple = sum(1 for row in wrong_rows if row["question_type"] == "multiple")

    recommendations = []
    for exam in exams:
        score = 0

        if exam["difficulty"] == target_difficulty:
            score += 5
        elif target_difficulty == "medium" and exam["difficulty"] in ["easy", "hard"]:
            score += 3

        text_blob = f"{exam['title']} {exam['description'] or ''}".lower()

        if weak_code >= weak_multiple and (
            "코드" in text_blob or "응용" in text_blob or "logic" in text_blob
        ):
            score += 2

        if weak_multiple > weak_code and (
            "기초" in text_blob or "자료구조" in text_blob
        ):
            score += 2

        exam["recommend_score"] = score
        recommendations.append(exam)

    recommendations.sort(key=lambda x: (-x["recommend_score"], x["id"]))

    return {
        "target_difficulty": target_difficulty,
        "reason": difficulty_info["reason"],
        "recommendations": recommendations[:3]
    }


@router.get("/exams")
def get_exams():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, description, difficulty, created_at
        FROM exam_sets
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    return {
        "exams": [
            {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "difficulty": row["difficulty"],
                "created_at": row["created_at"]
            }
            for row in rows
        ]
    }


@router.get("/exams/{exam_id}")
def get_exam_detail(exam_id: int):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, description, difficulty, created_at
        FROM exam_sets
        WHERE id = ?
    """, (exam_id,))
    exam = cursor.fetchone()

    if not exam:
        conn.close()
        return {"message": "시험을 찾을 수 없습니다."}

    cursor.execute("""
        SELECT id, question_type, question_text, options, starter_code, score
        FROM questions
        WHERE exam_set_id = ?
        ORDER BY id ASC
    """, (exam_id,))
    rows = cursor.fetchall()
    conn.close()

    return {
        "exam": {
            "id": exam["id"],
            "title": exam["title"],
            "description": exam["description"],
            "difficulty": exam["difficulty"],
            "created_at": exam["created_at"]
        },
        "questions": [
            {
                "id": row["id"],
                "question_type": row["question_type"],
                "question_text": row["question_text"],
                "options": json.loads(row["options"]) if row["options"] else [],
                "starter_code": row["starter_code"],
                "score": row["score"]
            }
            for row in rows
        ]
    }


@router.post("/exams/{exam_id}/submit")
def submit_exam(exam_id: int, data: SubmitExamRequest):
    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, data.user_id):
        conn.close()
        return {"message": "사용자를 찾을 수 없습니다."}

    cursor.execute("""
        SELECT title
        FROM exam_sets
        WHERE id = ?
    """, (exam_id,))
    exam_info = cursor.fetchone()

    if not exam_info:
        conn.close()
        return {"message": "시험을 찾을 수 없습니다."}

    exam_title = exam_info["title"]

    cursor.execute("""
        SELECT id, question_type, question_text, correct_answer, test_cases, score
        FROM questions
        WHERE exam_set_id = ?
        ORDER BY id ASC
    """, (exam_id,))
    rows = cursor.fetchall()

    if not rows:
        conn.close()
        return {"message": "시험 문제가 없습니다."}

    answer_map = {answer.question_id: answer for answer in data.answers}

    total_score = 0
    detail_result = []

    for question in rows:
        qid = question["id"]
        user_answer = answer_map.get(qid)

        result_item = {
            "question_id": question["id"],
            "question_text": question["question_text"],
            "question_type": question["question_type"],
            "score": 0,
            "max_score": question["score"]
        }

        if question["question_type"] == "multiple":
            user_answer_text = (user_answer.answer if user_answer else "") or ""
            user_answer_text = user_answer_text.strip()

            is_blank = user_answer_text == ""
            is_correct = user_answer_text == question["correct_answer"]

            review_note = (
                "답안을 입력하지 않았습니다."
                if is_blank
                else ("정답입니다." if is_correct else "객관식 오답입니다. 정답과 내가 선택한 답을 비교해서 개념 차이를 복습하세요.")
            )

            ai_explanation = ""
            if not is_correct:
                ai_explanation = generate_ai_wrong_explanation(
                    "multiple",
                    question["question_text"],
                    user_answer_text,
                    question["correct_answer"] or "",
                    review_note
                )

            result_item["user_answer"] = user_answer_text
            result_item["correct_answer"] = question["correct_answer"]
            result_item["is_correct"] = is_correct
            result_item["is_blank"] = is_blank
            result_item["analysis"] = review_note
            result_item["ai_explanation"] = ai_explanation

            if is_correct:
                result_item["score"] = question["score"]
                total_score += question["score"]

        elif question["question_type"] == "code":
            user_code_text = (user_answer.code if user_answer else "") or ""
            user_code_text = user_code_text.strip()

            if not user_code_text:
                judge_result = {
                    "passed": False,
                    "error": "코드를 입력하지 않았습니다.",
                    "passed_count": 0,
                    "total_count": 0,
                    "failed_cases": []
                }
                analysis_text = "코드를 입력하지 않았습니다."
                ai_explanation = generate_ai_wrong_explanation(
                    "code",
                    question["question_text"],
                    "",
                    "",
                    analysis_text
                )
                result_item["judge_result"] = judge_result
                result_item["user_code"] = ""
                result_item["analysis"] = analysis_text
                result_item["ai_explanation"] = ai_explanation
                result_item["is_blank"] = True
            else:
                test_cases = json.loads(question["test_cases"]) if question["test_cases"] else []
                judge_result = grade_code_question(user_code_text, test_cases)
                analysis_text = analyze_code_mistake(user_code_text, judge_result)

                reference_answer = ""
                if judge_result.get("failed_cases"):
                    reference_answer = json.dumps(judge_result["failed_cases"], ensure_ascii=False)

                ai_explanation = ""
                total_count = judge_result["total_count"]
                passed_count = judge_result["passed_count"]

                if not (total_count > 0 and passed_count == total_count):
                    ai_explanation = generate_ai_wrong_explanation(
                        "code",
                        question["question_text"],
                        user_code_text,
                        reference_answer,
                        analysis_text
                    )

                result_item["judge_result"] = judge_result
                result_item["user_code"] = user_code_text
                result_item["analysis"] = analysis_text
                result_item["ai_explanation"] = ai_explanation
                result_item["is_blank"] = False

                if judge_result["total_count"] > 0:
                    earned_score = int(
                        question["score"] *
                        (judge_result["passed_count"] / judge_result["total_count"])
                    )
                    result_item["score"] = earned_score
                    total_score += earned_score

        detail_result.append(result_item)

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO exam_results (user_id, exam_set_id, total_score, detail_result, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data.user_id,
        exam_id,
        total_score,
        json.dumps(detail_result, ensure_ascii=False),
        created_at
    ))

    exam_result_id = cursor.lastrowid
    conn.commit()
    conn.close()

    save_wrong_notes(data.user_id, exam_result_id, exam_id, exam_title, detail_result)

    awarded_points = []
    add_points(data.user_id, 10, f"시험 제출: {exam_title}")
    awarded_points.append({"amount": 10, "reason": f"시험 제출: {exam_title}"})

    if total_score >= 80:
        add_points(data.user_id, 15, f"고득점 보너스(80점 이상): {exam_title}")
        awarded_points.append({"amount": 15, "reason": f"고득점 보너스(80점 이상): {exam_title}"})

    if total_score == 100:
        add_points(data.user_id, 10, f"만점 보너스: {exam_title}")
        awarded_points.append({"amount": 10, "reason": f"만점 보너스: {exam_title}"})

    total_points = get_total_points(data.user_id)

    return {
        "message": "시험이 제출되었습니다.",
        "exam_set_id": exam_id,
        "exam_title": exam_title,
        "total_score": total_score,
        "detail_result": detail_result,
        "submitted_at": created_at,
        "awarded_points": awarded_points,
        "total_points": total_points
    }


@router.get("/exam-results")
def get_exam_results(user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT er.id, er.user_id, er.exam_set_id, es.title, er.total_score, er.detail_result, er.created_at
        FROM exam_results er
        JOIN exam_sets es ON er.exam_set_id = es.id
        WHERE er.user_id = ?
        ORDER BY er.id DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    return {
        "results": [
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "exam_set_id": row["exam_set_id"],
                "exam_title": row["title"],
                "total_score": row["total_score"],
                "detail_result": json.loads(row["detail_result"]) if row["detail_result"] else [],
                "created_at": row["created_at"]
            }
            for row in rows
        ]
    }


@router.get("/exam-stats")
def get_exam_stats(user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT created_at, total_score
        FROM exam_results
        WHERE user_id = ?
        ORDER BY id ASC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    return {
        "dates": [row["created_at"][:10] for row in rows],
        "scores": [row["total_score"] for row in rows]
    }


@router.get("/wrong-notes")
def get_wrong_notes(user_id: int = Query(...), review_filter: Optional[str] = None):
    conn = get_conn()
    cursor = conn.cursor()

    query = """
        SELECT id, user_id, exam_result_id, exam_set_id, exam_title, question_id, question_type,
               question_text, user_answer, user_code, correct_answer,
               reference_answer, review_note, ai_explanation, status,
               is_reviewed, reviewed_at, created_at
        FROM wrong_notes
        WHERE user_id = ?
    """
    params = [user_id]

    if review_filter == "reviewed":
        query += " AND is_reviewed = 1"
    elif review_filter == "pending":
        query += " AND is_reviewed = 0"

    query += " ORDER BY id DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return {
        "wrong_notes": [
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "exam_result_id": row["exam_result_id"],
                "exam_set_id": row["exam_set_id"],
                "exam_title": row["exam_title"],
                "question_id": row["question_id"],
                "question_type": row["question_type"],
                "question_text": row["question_text"],
                "user_answer": row["user_answer"],
                "user_code": row["user_code"],
                "correct_answer": row["correct_answer"],
                "reference_answer": row["reference_answer"],
                "review_note": row["review_note"],
                "ai_explanation": row["ai_explanation"],
                "status": row["status"],
                "is_reviewed": bool(row["is_reviewed"]),
                "reviewed_at": row["reviewed_at"],
                "created_at": row["created_at"]
            }
            for row in rows
        ]
    }


@router.put("/wrong-notes/{note_id}/review")
def update_wrong_note_review(note_id: int, data: WrongNoteReviewRequest):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM wrong_notes
        WHERE id = ? AND user_id = ?
    """, (note_id, data.user_id))
    note = cursor.fetchone()

    if not note:
        conn.close()
        return {"message": "오답노트를 찾을 수 없습니다."}

    reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if data.is_reviewed else None

    cursor.execute("""
        UPDATE wrong_notes
        SET is_reviewed = ?, reviewed_at = ?
        WHERE id = ? AND user_id = ?
    """, (1 if data.is_reviewed else 0, reviewed_at, note_id, data.user_id))

    conn.commit()
    conn.close()

    return {
        "message": "오답노트 상태가 변경되었습니다.",
        "note_id": note_id,
        "is_reviewed": data.is_reviewed,
        "reviewed_at": reviewed_at
    }


@router.get("/exam-insights")
def get_exam_insights(user_id: int = Query(...)):
    difficulty_info = compute_recommended_difficulty(user_id)
    recommendation_info = build_exam_recommendations(user_id)

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM wrong_notes WHERE user_id = ? AND is_reviewed = 0", (user_id,))
    pending_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM wrong_notes WHERE user_id = ? AND is_reviewed = 1", (user_id,))
    reviewed_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM exam_results WHERE user_id = ?", (user_id,))
    exam_count = cursor.fetchone()["count"]

    conn.close()

    return {
        "recommended_difficulty": difficulty_info["recommended_difficulty"],
        "difficulty_reason": difficulty_info["reason"],
        "pending_wrong_notes": pending_count,
        "reviewed_wrong_notes": reviewed_count,
        "exam_count": exam_count,
        "recommendations": recommendation_info["recommendations"],
        "recommendation_reason": recommendation_info["reason"]
    }