import sqlite3
import json
import bcrypt
from datetime import datetime

try:
    from backend.settings import DB_PATH
except ImportError:
    from settings import DB_PATH

DB_NAME = str(DB_PATH)


def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_column_exists(cursor, table_name: str, column_name: str, alter_sql: str):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    if column_name not in columns:
        cursor.execute(alter_sql)


def hash_password(password: str) -> str:
    """
    bcrypt를 사용하여 비밀번호를 안전하게 해시합니다.
    
    Args:
        password: 평문 비밀번호
        
    Returns:
        해시된 비밀번호 (str)
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """
    bcrypt를 사용하여 비밀번호를 검증합니다.
    
    Args:
        password: 평문 비밀번호
        hashed_password: 저장된 해시 비밀번호
        
    Returns:
        일치하면 True, 아니면 False
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except (ValueError, TypeError):
        return False


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

    # 포인트 로그 기록
    cursor.execute("""
        INSERT INTO point_logs (user_id, amount, reason, created_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, amount, reason, created_at))

    conn.commit()
    conn.close()


def get_total_points(user_id: int):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) as total
        FROM point_logs
        WHERE user_id = ?
    """, (user_id,))

    result = cursor.fetchone()
    conn.close()

    return result["total"]


def spend_points(user_id: int, amount: int, reason: str) -> bool:
    total = get_total_points(user_id)
    if total < amount:
        return False

    add_points(user_id, -amount, reason)
    return True


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
        {"item_key": "theme_blue_neon", "item_name": "블루 네온 테마", "item_type": "theme", "price": 100, "description": "푸른 계열의 강한 네온 느낌 테마", "style_value": "blue_neon"},
        {"item_key": "theme_purple_galaxy", "item_name": "퍼플 갤럭시 테마", "item_type": "theme", "price": 150, "description": "보라 계열의 우주 느낌 테마", "style_value": "purple_galaxy"},
        {"item_key": "theme_emerald_forest", "item_name": "에메랄드 포레스트 테마", "item_type": "theme", "price": 170, "description": "초록 계열의 차분하고 깊은 숲 느낌 테마", "style_value": "emerald_forest"},
        {"item_key": "theme_crimson_sunset", "item_name": "크림슨 선셋 테마", "item_type": "theme", "price": 180, "description": "붉은 노을 느낌의 강렬한 테마", "style_value": "crimson_sunset"},
        {"item_key": "theme_silver_minimal", "item_name": "실버 미니멀 테마", "item_type": "theme", "price": 140, "description": "깔끔하고 정돈된 미니멀 스타일 테마", "style_value": "silver_minimal"},

        {"item_key": "badge_gold_dev", "item_name": "골드 개발자 배지", "item_type": "badge", "price": 120, "description": "프로필에 표시할 수 있는 골드 배지", "style_value": "gold_dev"},
        {"item_key": "badge_master_coder", "item_name": "마스터 코더 배지", "item_type": "badge", "price": 180, "description": "상위 학습자 느낌의 배지", "style_value": "master_coder"},
        {"item_key": "badge_bug_hunter", "item_name": "버그 헌터 배지", "item_type": "badge", "price": 160, "description": "디버깅 특화 느낌의 배지", "style_value": "bug_hunter"},
        {"item_key": "badge_exam_ace", "item_name": "시험 에이스 배지", "item_type": "badge", "price": 200, "description": "시험 고득점 느낌의 배지", "style_value": "exam_ace"},
        {"item_key": "badge_streak_master", "item_name": "스트릭 마스터 배지", "item_type": "badge", "price": 220, "description": "꾸준한 출석과 학습 흐름을 강조하는 배지", "style_value": "streak_master"},

        {"item_key": "background_space", "item_name": "우주 배경", "item_type": "background", "price": 200, "description": "메인 배경을 우주 느낌으로 꾸밈", "style_value": "space"},
        {"item_key": "background_sunset", "item_name": "선셋 배경", "item_type": "background", "price": 160, "description": "따뜻한 석양 느낌 배경", "style_value": "sunset"},
        {"item_key": "background_aurora", "item_name": "오로라 배경", "item_type": "background", "price": 210, "description": "북극광 느낌의 몽환적인 배경", "style_value": "aurora"},
        {"item_key": "background_matrix", "item_name": "매트릭스 배경", "item_type": "background", "price": 230, "description": "코드 비가 내리는 듯한 배경", "style_value": "matrix"},
        {"item_key": "background_midnight_city", "item_name": "미드나잇 시티 배경", "item_type": "background", "price": 240, "description": "도시 야경 느낌의 배경", "style_value": "midnight_city"},

        {"item_key": "name_color_sky", "item_name": "스카이 닉네임 컬러", "item_type": "name_color", "price": 90, "description": "밝은 하늘색 닉네임 컬러", "style_value": "sky"},
        {"item_key": "name_color_lime", "item_name": "라임 닉네임 컬러", "item_type": "name_color", "price": 90, "description": "산뜻한 라임색 닉네임 컬러", "style_value": "lime"},
        {"item_key": "name_color_pink", "item_name": "핑크 닉네임 컬러", "item_type": "name_color", "price": 100, "description": "포인트가 되는 핑크 닉네임 컬러", "style_value": "pink"},
        {"item_key": "name_color_gold", "item_name": "골드 닉네임 컬러", "item_type": "name_color", "price": 140, "description": "고급스러운 골드 닉네임 컬러", "style_value": "gold"},

        {"item_key": "card_skin_glass_strong", "item_name": "글래스 스트롱 카드 스킨", "item_type": "card_skin", "price": 150, "description": "더 진한 유리 느낌 카드 스킨", "style_value": "glass_strong"},
        {"item_key": "card_skin_soft_light", "item_name": "소프트 라이트 카드 스킨", "item_type": "card_skin", "price": 150, "description": "조금 더 밝고 부드러운 카드 스킨", "style_value": "soft_light"},
        {"item_key": "card_skin_outline_neon", "item_name": "네온 아웃라인 카드 스킨", "item_type": "card_skin", "price": 180, "description": "외곽선이 강조되는 카드 스킨", "style_value": "outline_neon"},
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
