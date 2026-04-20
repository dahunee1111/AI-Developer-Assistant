from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import requests
import sqlite3
import json
import hashlib
from datetime import datetime, date

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "history.db"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"


def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column_exists(cursor, table_name: str, column_name: str, alter_sql: str):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    if column_name not in columns:
        cursor.execute(alter_sql)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def user_exists(cursor, user_id: int) -> bool:
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone() is not None


def get_user_or_none(cursor, user_id: int):
    cursor.execute("""
        SELECT id, username, email, created_at
        FROM users
        WHERE id = ?
    """, (user_id,))
    return cursor.fetchone()


def add_points(user_id: int, amount: int, reason: str):
    conn = get_conn()
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO point_logs (user_id, amount, reason, created_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, amount, reason, created_at))

    conn.commit()
    conn.close()


def spend_points(user_id: int, amount: int, reason: str) -> bool:
    total = get_total_points(user_id)
    if total < amount:
        return False

    add_points(user_id, -amount, reason)
    return True


def get_total_points(user_id: int) -> int:
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) as total_points
        FROM point_logs
        WHERE user_id = ?
    """, (user_id,))
    total = cursor.fetchone()["total_points"]

    conn.close()
    return total


def init_db():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            error_text TEXT NOT NULL,
            result_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS learning_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS code_review_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            code_text TEXT NOT NULL,
            result_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exam_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            difficulty TEXT DEFAULT 'medium',
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_set_id INTEGER NOT NULL,
            question_type TEXT NOT NULL,
            question_text TEXT NOT NULL,
            options TEXT,
            correct_answer TEXT,
            starter_code TEXT,
            test_cases TEXT,
            score INTEGER DEFAULT 10,
            created_at TEXT NOT NULL,
            FOREIGN KEY (exam_set_id) REFERENCES exam_sets(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exam_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            exam_set_id INTEGER NOT NULL,
            total_score INTEGER NOT NULL,
            detail_result TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (exam_set_id) REFERENCES exam_sets(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wrong_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            exam_result_id INTEGER NOT NULL,
            exam_set_id INTEGER,
            exam_title TEXT,
            question_id INTEGER,
            question_type TEXT,
            question_text TEXT NOT NULL,
            user_answer TEXT,
            user_code TEXT,
            correct_answer TEXT,
            reference_answer TEXT,
            review_note TEXT,
            ai_explanation TEXT,
            status TEXT NOT NULL,
            is_reviewed INTEGER NOT NULL DEFAULT 0,
            reviewed_at TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS point_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shop_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_key TEXT NOT NULL UNIQUE,
            item_name TEXT NOT NULL,
            item_type TEXT NOT NULL,
            price INTEGER NOT NULL,
            description TEXT,
            style_value TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            purchased_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profile_custom (
            user_id INTEGER PRIMARY KEY,
            active_theme_item_id INTEGER,
            active_badge_item_id INTEGER,
            active_background_item_id INTEGER,
            active_name_color_item_id INTEGER,
            active_card_skin_item_id INTEGER,
            updated_at TEXT NOT NULL
        )
    """)

    ensure_column_exists(
        cursor,
        "analysis_history",
        "user_id",
        "ALTER TABLE analysis_history ADD COLUMN user_id INTEGER"
    )
    ensure_column_exists(
        cursor,
        "learning_journal",
        "user_id",
        "ALTER TABLE learning_journal ADD COLUMN user_id INTEGER"
    )
    ensure_column_exists(
        cursor,
        "code_review_history",
        "user_id",
        "ALTER TABLE code_review_history ADD COLUMN user_id INTEGER"
    )
    ensure_column_exists(
        cursor,
        "exam_results",
        "user_id",
        "ALTER TABLE exam_results ADD COLUMN user_id INTEGER"
    )
    ensure_column_exists(
        cursor,
        "wrong_notes",
        "user_id",
        "ALTER TABLE wrong_notes ADD COLUMN user_id INTEGER"
    )
    ensure_column_exists(
        cursor,
        "wrong_notes",
        "exam_set_id",
        "ALTER TABLE wrong_notes ADD COLUMN exam_set_id INTEGER"
    )
    ensure_column_exists(
        cursor,
        "wrong_notes",
        "is_reviewed",
        "ALTER TABLE wrong_notes ADD COLUMN is_reviewed INTEGER NOT NULL DEFAULT 0"
    )
    ensure_column_exists(
        cursor,
        "wrong_notes",
        "reviewed_at",
        "ALTER TABLE wrong_notes ADD COLUMN reviewed_at TEXT"
    )
    ensure_column_exists(
        cursor,
        "wrong_notes",
        "ai_explanation",
        "ALTER TABLE wrong_notes ADD COLUMN ai_explanation TEXT"
    )
    ensure_column_exists(
        cursor,
        "user_profile_custom",
        "active_name_color_item_id",
        "ALTER TABLE user_profile_custom ADD COLUMN active_name_color_item_id INTEGER"
    )
    ensure_column_exists(
        cursor,
        "user_profile_custom",
        "active_card_skin_item_id",
        "ALTER TABLE user_profile_custom ADD COLUMN active_card_skin_item_id INTEGER"
    )

    conn.commit()
    conn.close()


def seed_exam_data():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM exam_sets")
    count = cursor.fetchone()["count"]

    if count > 0:
        conn.close()
        return

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO exam_sets (title, description, difficulty, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        "Python 기초 시험 A",
        "자료형, 기본 문법, 간단한 리스트 연산 중심",
        "easy",
        created_at
    ))
    exam_easy_a = cursor.lastrowid

    easy_a_questions = [
        {
            "question_type": "multiple",
            "question_text": "파이썬에서 key-value 형태로 데이터를 저장하는 자료형은?",
            "options": ["list", "tuple", "dict", "set"],
            "correct_answer": "dict",
            "score": 10
        },
        {
            "question_type": "multiple",
            "question_text": "파이썬에서 함수를 정의할 때 사용하는 키워드는?",
            "options": ["def", "function", "func", "lambda"],
            "correct_answer": "def",
            "score": 10
        },
        {
            "question_type": "multiple",
            "question_text": "리스트의 마지막 원소를 가져오는 인덱스는?",
            "options": ["0", "1", "-1", "last"],
            "correct_answer": "-1",
            "score": 10
        },
        {
            "question_type": "code",
            "question_text": "nums 리스트의 모든 원소의 합을 반환하는 solution 함수를 완성하세요.",
            "starter_code": """def solution(nums):
    total = 0
    # nums의 합을 반환하세요
    return total
""",
            "test_cases": [
                {"input": [1, 2, 3], "output": 6},
                {"input": [10, 20], "output": 30},
                {"input": [], "output": 0}
            ],
            "score": 20
        },
        {
            "question_type": "code",
            "question_text": "nums 리스트에서 짝수의 개수를 반환하는 solution 함수를 작성하세요.",
            "starter_code": """def solution(nums):
    count = 0
    # 짝수의 개수를 세세요
    return count
""",
            "test_cases": [
                {"input": [1, 2, 3, 4], "output": 2},
                {"input": [2, 2, 2], "output": 3},
                {"input": [1, 3, 5], "output": 0}
            ],
            "score": 20
        }
    ]

    cursor.execute("""
        INSERT INTO exam_sets (title, description, difficulty, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        "Python 자료구조 시험 B",
        "문자열, 리스트 필터링, 딕셔너리 메서드 활용",
        "medium",
        created_at
    ))
    exam_medium_b = cursor.lastrowid

    medium_b_questions = [
        {
            "question_type": "multiple",
            "question_text": "딕셔너리에서 key가 없을 때 기본값과 함께 안전하게 값을 조회하기 좋은 메서드는?",
            "options": ["append()", "get()", "index()", "sort()"],
            "correct_answer": "get()",
            "score": 10
        },
        {
            "question_type": "multiple",
            "question_text": "문자열을 모두 소문자로 바꾸는 메서드는?",
            "options": ["lower()", "small()", "down()", "under()"],
            "correct_answer": "lower()",
            "score": 10
        },
        {
            "question_type": "multiple",
            "question_text": "리스트에 새 원소를 맨 뒤에 추가하는 메서드는?",
            "options": ["push()", "append()", "add()", "insert_last()"],
            "correct_answer": "append()",
            "score": 10
        },
        {
            "question_type": "code",
            "question_text": "문자열 리스트 words에서 길이가 3 이상인 단어만 반환하는 solution 함수를 작성하세요.",
            "starter_code": """def solution(words):
    result = []
    # 길이가 3 이상인 단어만 result에 넣으세요
    return result
""",
            "test_cases": [
                {"input": ["hi", "cat", "python"], "output": ["cat", "python"]},
                {"input": ["a", "be"], "output": []},
                {"input": ["sun", "sky"], "output": ["sun", "sky"]}
            ],
            "score": 20
        },
        {
            "question_type": "code",
            "question_text": "nums 리스트에서 10 이상인 숫자만 반환하는 solution 함수를 작성하세요.",
            "starter_code": """def solution(nums):
    result = []
    # 10 이상인 숫자만 result에 넣으세요
    return result
""",
            "test_cases": [
                {"input": [1, 10, 15, 3], "output": [10, 15]},
                {"input": [9, 8, 7], "output": []},
                {"input": [10, 10, 2], "output": [10, 10]}
            ],
            "score": 20
        }
    ]

    cursor.execute("""
        INSERT INTO exam_sets (title, description, difficulty, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        "Python 로직 응용 시험 C",
        "조건문, 누적, 예외 케이스와 로직 완성 문제 중심",
        "hard",
        created_at
    ))
    exam_hard_c = cursor.lastrowid

    hard_c_questions = [
        {
            "question_type": "multiple",
            "question_text": "for문에서 현재 반복을 건너뛰고 다음 반복으로 넘어가는 키워드는?",
            "options": ["pass", "stop", "continue", "break"],
            "correct_answer": "continue",
            "score": 10
        },
        {
            "question_type": "multiple",
            "question_text": "반복문을 즉시 종료하는 키워드는?",
            "options": ["end", "return", "stop", "break"],
            "correct_answer": "break",
            "score": 10
        },
        {
            "question_type": "multiple",
            "question_text": "len([1,2,3]) 의 결과는?",
            "options": ["2", "3", "4", "1"],
            "correct_answer": "3",
            "score": 10
        },
        {
            "question_type": "code",
            "question_text": "문자열 s에서 모음(a,e,i,o,u)의 개수를 반환하는 solution 함수를 작성하세요.",
            "starter_code": """def solution(s):
    count = 0
    # 모음 개수를 세세요
    return count
""",
            "test_cases": [
                {"input": "apple", "output": 2},
                {"input": "sky", "output": 0},
                {"input": "aeiou", "output": 5}
            ],
            "score": 20
        },
        {
            "question_type": "code",
            "question_text": "nums 리스트에서 가장 큰 값을 반환하는 solution 함수를 작성하세요. 빈 리스트면 0을 반환하세요.",
            "starter_code": """def solution(nums):
    # 가장 큰 값을 반환하세요
    return 0
""",
            "test_cases": [
                {"input": [1, 9, 3], "output": 9},
                {"input": [], "output": 0},
                {"input": [5], "output": 5}
            ],
            "score": 20
        }
    ]

    all_exam_map = {
        exam_easy_a: easy_a_questions,
        exam_medium_b: medium_b_questions,
        exam_hard_c: hard_c_questions
    }

    for exam_id, question_list in all_exam_map.items():
        for q in question_list:
            cursor.execute("""
                INSERT INTO questions (
                    exam_set_id, question_type, question_text, options,
                    correct_answer, starter_code, test_cases, score, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exam_id,
                q["question_type"],
                q["question_text"],
                json.dumps(q.get("options"), ensure_ascii=False) if q.get("options") else None,
                q.get("correct_answer"),
                q.get("starter_code"),
                json.dumps(q.get("test_cases"), ensure_ascii=False) if q.get("test_cases") else None,
                q["score"],
                created_at
            ))

    conn.commit()
    conn.close()


def seed_shop_items():
    conn = get_conn()
    cursor = conn.cursor()

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    items = [
        # theme
        {
            "item_key": "theme_blue_neon",
            "item_name": "블루 네온 테마",
            "item_type": "theme",
            "price": 100,
            "description": "푸른 계열의 강한 네온 느낌 테마",
            "style_value": "blue_neon"
        },
        {
            "item_key": "theme_purple_galaxy",
            "item_name": "퍼플 갤럭시 테마",
            "item_type": "theme",
            "price": 150,
            "description": "보라 계열의 우주 느낌 테마",
            "style_value": "purple_galaxy"
        },
        {
            "item_key": "theme_emerald_forest",
            "item_name": "에메랄드 포레스트 테마",
            "item_type": "theme",
            "price": 170,
            "description": "초록 계열의 차분하고 깊은 숲 느낌 테마",
            "style_value": "emerald_forest"
        },
        {
            "item_key": "theme_crimson_sunset",
            "item_name": "크림슨 선셋 테마",
            "item_type": "theme",
            "price": 180,
            "description": "붉은 노을 느낌의 강렬한 테마",
            "style_value": "crimson_sunset"
        },
        {
            "item_key": "theme_silver_minimal",
            "item_name": "실버 미니멀 테마",
            "item_type": "theme",
            "price": 140,
            "description": "깔끔하고 정돈된 미니멀 스타일 테마",
            "style_value": "silver_minimal"
        },

        # badge
        {
            "item_key": "badge_gold_dev",
            "item_name": "골드 개발자 배지",
            "item_type": "badge",
            "price": 120,
            "description": "프로필에 표시할 수 있는 골드 배지",
            "style_value": "gold_dev"
        },
        {
            "item_key": "badge_master_coder",
            "item_name": "마스터 코더 배지",
            "item_type": "badge",
            "price": 180,
            "description": "상위 학습자 느낌의 배지",
            "style_value": "master_coder"
        },
        {
            "item_key": "badge_bug_hunter",
            "item_name": "버그 헌터 배지",
            "item_type": "badge",
            "price": 160,
            "description": "디버깅 특화 느낌의 배지",
            "style_value": "bug_hunter"
        },
        {
            "item_key": "badge_exam_ace",
            "item_name": "시험 에이스 배지",
            "item_type": "badge",
            "price": 200,
            "description": "시험 고득점 느낌의 배지",
            "style_value": "exam_ace"
        },
        {
            "item_key": "badge_streak_master",
            "item_name": "스트릭 마스터 배지",
            "item_type": "badge",
            "price": 220,
            "description": "꾸준한 출석과 학습 흐름을 강조하는 배지",
            "style_value": "streak_master"
        },

        # background
        {
            "item_key": "background_space",
            "item_name": "우주 배경",
            "item_type": "background",
            "price": 200,
            "description": "메인 배경을 우주 느낌으로 꾸밈",
            "style_value": "space"
        },
        {
            "item_key": "background_sunset",
            "item_name": "선셋 배경",
            "item_type": "background",
            "price": 160,
            "description": "따뜻한 석양 느낌 배경",
            "style_value": "sunset"
        },
        {
            "item_key": "background_aurora",
            "item_name": "오로라 배경",
            "item_type": "background",
            "price": 210,
            "description": "북극광 느낌의 몽환적인 배경",
            "style_value": "aurora"
        },
        {
            "item_key": "background_matrix",
            "item_name": "매트릭스 배경",
            "item_type": "background",
            "price": 230,
            "description": "코드 비가 내리는 듯한 배경",
            "style_value": "matrix"
        },
        {
            "item_key": "background_midnight_city",
            "item_name": "미드나잇 시티 배경",
            "item_type": "background",
            "price": 240,
            "description": "도시 야경 느낌의 배경",
            "style_value": "midnight_city"
        },

        # name_color
        {
            "item_key": "name_color_sky",
            "item_name": "스카이 닉네임 컬러",
            "item_type": "name_color",
            "price": 90,
            "description": "밝은 하늘색 닉네임 컬러",
            "style_value": "sky"
        },
        {
            "item_key": "name_color_lime",
            "item_name": "라임 닉네임 컬러",
            "item_type": "name_color",
            "price": 90,
            "description": "산뜻한 라임색 닉네임 컬러",
            "style_value": "lime"
        },
        {
            "item_key": "name_color_pink",
            "item_name": "핑크 닉네임 컬러",
            "item_type": "name_color",
            "price": 100,
            "description": "포인트가 되는 핑크 닉네임 컬러",
            "style_value": "pink"
        },
        {
            "item_key": "name_color_gold",
            "item_name": "골드 닉네임 컬러",
            "item_type": "name_color",
            "price": 140,
            "description": "고급스러운 골드 닉네임 컬러",
            "style_value": "gold"
        },

        # card_skin
        {
            "item_key": "card_skin_glass_strong",
            "item_name": "글래스 스트롱 카드 스킨",
            "item_type": "card_skin",
            "price": 150,
            "description": "더 진한 유리 느낌 카드 스킨",
            "style_value": "glass_strong"
        },
        {
            "item_key": "card_skin_soft_light",
            "item_name": "소프트 라이트 카드 스킨",
            "item_type": "card_skin",
            "price": 150,
            "description": "조금 더 밝고 부드러운 카드 스킨",
            "style_value": "soft_light"
        },
        {
            "item_key": "card_skin_outline_neon",
            "item_name": "네온 아웃라인 카드 스킨",
            "item_type": "card_skin",
            "price": 180,
            "description": "외곽선이 강조되는 카드 스킨",
            "style_value": "outline_neon"
        }
    ]

    for item in items:
        cursor.execute("SELECT id FROM shop_items WHERE item_key = ?", (item["item_key"],))
        exists = cursor.fetchone()
        if exists:
            continue

        cursor.execute("""
            INSERT INTO shop_items (
                item_key, item_name, item_type, price, description, style_value, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["item_key"],
            item["item_name"],
            item["item_type"],
            item["price"],
            item["description"],
            item["style_value"],
            1,
            created_at
        ))

    conn.commit()
    conn.close()


init_db()
seed_exam_data()
seed_shop_items()


class SignupRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ErrorRequest(BaseModel):
    user_id: int
    error: str


class JournalRequest(BaseModel):
    user_id: int
    content: str


class CodeRequest(BaseModel):
    user_id: int
    code: str


class AttendanceRequest(BaseModel):
    user_id: int


class PurchaseItemRequest(BaseModel):
    user_id: int
    item_id: int


class ApplyItemRequest(BaseModel):
    user_id: int
    item_id: int


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
        reasons.append("누적 연산이 아니라 값이 계속 덮어써지고 있습니다. sum = + i 가 아니라 total += i 형태가 필요합니다.")

    if judge_result.get("error"):
        reasons.append("입력 데이터가 비어있을 때(예: []) 처리 로직이 없을 가능성이 큽니다.")

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


def ensure_profile_custom_row(user_id: int):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT user_id FROM user_profile_custom WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if not row:
        cursor.execute("""
            INSERT INTO user_profile_custom (
                user_id, active_theme_item_id, active_badge_item_id,
                active_background_item_id, active_name_color_item_id,
                active_card_skin_item_id, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            None,
            None,
            None,
            None,
            None,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()

    conn.close()


@app.get("/")
def root():
    return {"message": "AI Developer Assistant API is working"}


@app.post("/signup")
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

    return {
        "message": "회원가입이 완료되었습니다.",
        "user": {
            "id": user_id,
            "username": username,
            "email": email,
            "created_at": created_at
        }
    }


@app.post("/login")
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

    return {
        "message": "로그인 성공",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "created_at": user["created_at"]
        }
    }


@app.get("/me")
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


@app.post("/analyze")
def analyze_error(data: ErrorRequest):
    error_text = data.error.strip()

    if not error_text:
        return {"result": "에러를 입력해주세요."}

    conn = get_conn()
    cursor = conn.cursor()
    if not user_exists(cursor, data.user_id):
        conn.close()
        return {"result": "사용자를 찾을 수 없습니다."}
    conn.close()

    prompt = f"""
아래 Python 에러를 한국어로 분석해줘.

반드시 아래 형식으로 답변해:
1. 에러 원인
2. 해결 방법
3. 바로 실행할 코드

에러:
{error_text}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()

        result = response.json()["response"]

        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO analysis_history (user_id, error_text, result_text, created_at)
            VALUES (?, ?, ?, ?)
        """, (data.user_id, error_text, result, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

        return {"result": result}

    except Exception as e:
        return {"result": f"AI 호출 오류: {str(e)}"}


@app.post("/code-review")
def analyze_code(data: CodeRequest):
    code_text = data.code.strip()

    if not code_text:
        return {"result": "코드를 입력해주세요."}

    conn = get_conn()
    cursor = conn.cursor()
    if not user_exists(cursor, data.user_id):
        conn.close()
        return {"result": "사용자를 찾을 수 없습니다."}
    conn.close()

    prompt = f"""
아래 Python 코드를 한국어로 분석해줘.

반드시 아래 형식으로 답변해:
1. 문법 오류 또는 의심되는 부분
2. 오타나 빠진 부분 가능성
3. 들여쓰기/구조 문제
4. 개선 포인트
5. 수정 예시 코드

코드:
{code_text}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()

        result = response.json()["response"]

        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO code_review_history (user_id, code_text, result_text, created_at)
            VALUES (?, ?, ?, ?)
        """, (data.user_id, code_text, result, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

        return {"result": result}

    except Exception as e:
        return {"result": f"AI 호출 오류: {str(e)}"}


@app.get("/code-review-history")
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

    return {
        "history": [
            {
                "id": row["id"],
                "code_text": row["code_text"],
                "result_text": row["result_text"],
                "created_at": row["created_at"]
            }
            for row in rows
        ]
    }


@app.get("/history")
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

    return {
        "history": [
            {
                "id": row["id"],
                "error_text": row["error_text"],
                "result_text": row["result_text"],
                "created_at": row["created_at"]
            }
            for row in rows
        ]
    }


@app.post("/journal")
def save_journal(data: JournalRequest):
    content = data.content.strip()

    if not content:
        return {"message": "배운 점을 입력해주세요."}

    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, data.user_id):
        conn.close()
        return {"message": "사용자를 찾을 수 없습니다."}

    cursor.execute("""
        INSERT INTO learning_journal (user_id, content, created_at)
        VALUES (?, ?, ?)
    """, (data.user_id, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    return {"message": "기록이 저장되었습니다."}


@app.get("/journal")
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

    return {
        "journal": [
            {
                "id": row["id"],
                "content": row["content"],
                "created_at": row["created_at"]
            }
            for row in rows
        ]
    }


@app.put("/journal/{journal_id}")
def update_journal(journal_id: int, data: JournalRequest):
    content = data.content.strip()

    if not content:
        return {"message": "수정할 내용을 입력해주세요."}

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM learning_journal
        WHERE id = ? AND user_id = ?
    """, (journal_id, data.user_id))
    target = cursor.fetchone()

    if not target:
        conn.close()
        return {"message": "수정할 기록을 찾을 수 없습니다."}

    cursor.execute("""
        UPDATE learning_journal
        SET content = ?
        WHERE id = ? AND user_id = ?
    """, (content, journal_id, data.user_id))
    conn.commit()
    conn.close()

    return {"message": "기록이 수정되었습니다."}


@app.delete("/journal/{journal_id}")
def delete_journal(journal_id: int, user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM learning_journal
        WHERE id = ? AND user_id = ?
    """, (journal_id, user_id))
    target = cursor.fetchone()

    if not target:
        conn.close()
        return {"message": "삭제할 기록을 찾을 수 없습니다."}

    cursor.execute("""
        DELETE FROM learning_journal
        WHERE id = ? AND user_id = ?
    """, (journal_id, user_id))
    conn.commit()
    conn.close()

    return {"message": "기록이 삭제되었습니다."}


@app.get("/attendance")
def get_attendance(user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

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


@app.post("/attendance/check")
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


@app.get("/stats")
def get_stats(user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT substr(created_at, 1, 10) as date, COUNT(*) as count
        FROM learning_journal
        WHERE user_id = ?
        GROUP BY date
        ORDER BY date
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    return {
        "dates": [row["date"] for row in rows],
        "counts": [row["count"] for row in rows]
    }


@app.get("/points")
def get_points(user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, user_id):
        conn.close()
        return {"message": "사용자를 찾을 수 없습니다."}

    conn.close()

    return {
        "user_id": user_id,
        "total_points": get_total_points(user_id)
    }


@app.get("/point-logs")
def get_point_logs(user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, amount, reason, created_at
        FROM point_logs
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 30
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


@app.get("/shop/items")
def get_shop_items(user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, item_key, item_name, item_type, price, description, style_value, is_active
        FROM shop_items
        WHERE is_active = 1
        ORDER BY item_type, price ASC, id ASC
    """)
    items = cursor.fetchall()

    cursor.execute("""
        SELECT item_id
        FROM user_inventory
        WHERE user_id = ?
    """, (user_id,))
    owned_rows = cursor.fetchall()
    owned_ids = {row["item_id"] for row in owned_rows}

    conn.close()

    return {
        "items": [
            {
                "id": row["id"],
                "item_key": row["item_key"],
                "item_name": row["item_name"],
                "item_type": row["item_type"],
                "price": row["price"],
                "description": row["description"],
                "style_value": row["style_value"],
                "is_owned": row["id"] in owned_ids
            }
            for row in items
        ],
        "total_points": get_total_points(user_id)
    }


@app.post("/shop/purchase")
def purchase_shop_item(data: PurchaseItemRequest):
    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, data.user_id):
        conn.close()
        return {"message": "사용자를 찾을 수 없습니다."}

    cursor.execute("""
        SELECT id, item_name, item_type, price
        FROM shop_items
        WHERE id = ? AND is_active = 1
    """, (data.item_id,))
    item = cursor.fetchone()

    if not item:
        conn.close()
        return {"message": "구매할 아이템을 찾을 수 없습니다."}

    cursor.execute("""
        SELECT id
        FROM user_inventory
        WHERE user_id = ? AND item_id = ?
    """, (data.user_id, data.item_id))
    already_owned = cursor.fetchone()

    if already_owned:
        conn.close()
        return {
            "message": "이미 보유 중인 아이템입니다.",
            "total_points": get_total_points(data.user_id)
        }

    price = item["price"]
    if get_total_points(data.user_id) < price:
        conn.close()
        return {
            "message": "포인트가 부족합니다.",
            "total_points": get_total_points(data.user_id)
        }

    purchased_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO user_inventory (user_id, item_id, purchased_at)
        VALUES (?, ?, ?)
    """, (data.user_id, data.item_id, purchased_at))
    conn.commit()
    conn.close()

    spend_points(data.user_id, price, f"상점 구매: {item['item_name']}")

    return {
        "message": f"{item['item_name']} 구매 완료",
        "item_id": data.item_id,
        "item_name": item["item_name"],
        "item_type": item["item_type"],
        "spent_points": price,
        "total_points": get_total_points(data.user_id)
    }


@app.get("/shop/inventory")
def get_user_inventory(user_id: int = Query(...)):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ui.id as inventory_id, si.id as item_id, si.item_key, si.item_name, si.item_type,
               si.price, si.description, si.style_value, ui.purchased_at
        FROM user_inventory ui
        JOIN shop_items si ON ui.item_id = si.id
        WHERE ui.user_id = ?
        ORDER BY ui.id DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    return {
        "items": [
            {
                "inventory_id": row["inventory_id"],
                "item_id": row["item_id"],
                "item_key": row["item_key"],
                "item_name": row["item_name"],
                "item_type": row["item_type"],
                "price": row["price"],
                "description": row["description"],
                "style_value": row["style_value"],
                "purchased_at": row["purchased_at"]
            }
            for row in rows
        ],
        "total_points": get_total_points(user_id)
    }


@app.get("/profile/custom")
def get_profile_custom(user_id: int = Query(...)):
    ensure_profile_custom_row(user_id)

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT upc.user_id,
               theme.item_name as theme_name, theme.style_value as theme_style,
               badge.item_name as badge_name, badge.style_value as badge_style,
               bg.item_name as background_name, bg.style_value as background_style,
               nc.item_name as name_color_name, nc.style_value as name_color_style,
               cs.item_name as card_skin_name, cs.style_value as card_skin_style,
               upc.updated_at
        FROM user_profile_custom upc
        LEFT JOIN shop_items theme ON upc.active_theme_item_id = theme.id
        LEFT JOIN shop_items badge ON upc.active_badge_item_id = badge.id
        LEFT JOIN shop_items bg ON upc.active_background_item_id = bg.id
        LEFT JOIN shop_items nc ON upc.active_name_color_item_id = nc.id
        LEFT JOIN shop_items cs ON upc.active_card_skin_item_id = cs.id
        WHERE upc.user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()

    return {
        "custom": {
            "user_id": user_id,
            "theme_name": row["theme_name"] if row else None,
            "theme_style": row["theme_style"] if row else None,
            "badge_name": row["badge_name"] if row else None,
            "badge_style": row["badge_style"] if row else None,
            "background_name": row["background_name"] if row else None,
            "background_style": row["background_style"] if row else None,
            "name_color_name": row["name_color_name"] if row else None,
            "name_color_style": row["name_color_style"] if row else None,
            "card_skin_name": row["card_skin_name"] if row else None,
            "card_skin_style": row["card_skin_style"] if row else None,
            "updated_at": row["updated_at"] if row else None
        }
    }


@app.post("/profile/apply-item")
def apply_profile_item(data: ApplyItemRequest):
    ensure_profile_custom_row(data.user_id)

    conn = get_conn()
    cursor = conn.cursor()

    if not user_exists(cursor, data.user_id):
        conn.close()
        return {"message": "사용자를 찾을 수 없습니다."}

    cursor.execute("""
        SELECT si.id, si.item_name, si.item_type, si.style_value
        FROM user_inventory ui
        JOIN shop_items si ON ui.item_id = si.id
        WHERE ui.user_id = ? AND si.id = ?
    """, (data.user_id, data.item_id))
    item = cursor.fetchone()

    if not item:
        conn.close()
        return {"message": "보유 중인 아이템만 적용할 수 있습니다."}

    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if item["item_type"] == "theme":
        cursor.execute("""
            UPDATE user_profile_custom
            SET active_theme_item_id = ?, updated_at = ?
            WHERE user_id = ?
        """, (data.item_id, updated_at, data.user_id))
    elif item["item_type"] == "badge":
        cursor.execute("""
            UPDATE user_profile_custom
            SET active_badge_item_id = ?, updated_at = ?
            WHERE user_id = ?
        """, (data.item_id, updated_at, data.user_id))
    elif item["item_type"] == "background":
        cursor.execute("""
            UPDATE user_profile_custom
            SET active_background_item_id = ?, updated_at = ?
            WHERE user_id = ?
        """, (data.item_id, updated_at, data.user_id))
    elif item["item_type"] == "name_color":
        cursor.execute("""
            UPDATE user_profile_custom
            SET active_name_color_item_id = ?, updated_at = ?
            WHERE user_id = ?
        """, (data.item_id, updated_at, data.user_id))
    elif item["item_type"] == "card_skin":
        cursor.execute("""
            UPDATE user_profile_custom
            SET active_card_skin_item_id = ?, updated_at = ?
            WHERE user_id = ?
        """, (data.item_id, updated_at, data.user_id))
    else:
        conn.close()
        return {"message": "지원하지 않는 아이템 타입입니다."}

    conn.commit()
    conn.close()

    return {
        "message": f"{item['item_name']} 적용 완료",
        "item_id": data.item_id,
        "item_name": item["item_name"],
        "item_type": item["item_type"],
        "style_value": item["style_value"]
    }


@app.get("/exams")
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


@app.post("/exams")
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


@app.get("/exams/{exam_id}")
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


@app.post("/questions")
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


@app.post("/exams/{exam_id}/submit")
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


@app.get("/exam-results")
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


@app.get("/exam-stats")
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


@app.get("/wrong-notes")
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


@app.put("/wrong-notes/{note_id}/review")
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


@app.get("/exam-insights")
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
