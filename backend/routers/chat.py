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


# =========================
# Request Schema
# =========================
class ChatRequest(BaseModel):
    user_id: int
    message: str


# =========================
# Basic Utility
# =========================
def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_text(text: str) -> str:
    return (
        str(text or "")
        .replace(" ", "")
        .replace("\n", "")
        .replace("\t", "")
        .lower()
    )


def contains_any(text: str, keywords: List[str]) -> bool:
    normalized = normalize_text(text)
    return any(keyword in normalized for keyword in keywords)


# =========================
# DB Utility
# =========================
def ensure_chat_history_table():
    """
    db.py의 init_db에 chat_history 테이블이 있어도,
    배포 환경에서 누락될 가능성을 방지하기 위해 여기서도 한 번 더 보장합니다.
    """
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


# =========================
# Fixed Project Knowledge
# =========================
def owner_reply() -> str:
    return "이 사이트를 만든 개발자는 전다훈 개발자님입니다."


def is_owner_question(message: str) -> bool:
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

    return contains_any(message, owner_keywords)


def project_intro_reply() -> str:
    return (
        "AI Developer Assistant는 전다훈 개발자님이 만든 AI 기반 개발 학습 지원 시스템입니다.\n\n"
        "이 프로젝트는 개발자가 학습하거나 코딩하는 과정에서 발생하는 에러 분석, 코드 리뷰, "
        "학습 기록 관리, 출석 체크, 포인트 보상, 시험/오답노트, 상점, 프로필 커스터마이징, "
        "플로팅 AI 챗봇 기능을 하나의 서비스 흐름으로 연결한 풀스택 프로젝트입니다.\n\n"
        "프론트엔드는 GitHub Pages로 배포되어 있고, 백엔드는 AWS EC2에서 Docker 컨테이너 기반 "
        "FastAPI 서버로 운영됩니다. API 도메인은 https://dahun-ai.duckdns.org 를 사용합니다."
    )


def tech_stack_reply() -> str:
    return (
        "이 프로젝트의 주요 기술 스택은 다음과 같습니다.\n\n"
        "Frontend\n"
        "- HTML\n"
        "- CSS\n"
        "- JavaScript\n"
        "- Chart.js\n\n"
        "Backend\n"
        "- Python\n"
        "- FastAPI\n"
        "- SQLite\n"
        "- Pydantic\n"
        "- JWT / python-jose\n"
        "- bcrypt\n\n"
        "AI\n"
        "- Hugging Face Inference API\n"
        "- 프로젝트 전용 system prompt\n"
        "- fallback 응답 처리\n"
        "- 에러 분석 / 코드 리뷰용 프롬프트 설계\n\n"
        "Deployment\n"
        "- GitHub Pages\n"
        "- AWS EC2\n"
        "- Docker 컨테이너 기반 백엔드 실행\n"
        "- DuckDNS 도메인 연결\n"
        "- deploy.sh 기반 재배포 자동화\n"
        "- docker-compose.yml은 향후 Docker Compose 사용을 위해 준비한 설정 파일입니다.\n\n"
        "주의: 현재 확인된 운영 방식은 Docker 컨테이너 + deploy.sh 기반입니다. "
        "Nginx, Traefik, Docker Compose로 현재 운영 중이라고 설명하지 않습니다."
    )


def ec2_deploy_reply() -> str:
    return (
        "이 프로젝트의 EC2 배포 구조는 다음과 같습니다.\n\n"
        "1. 사용자는 GitHub Pages로 배포된 프론트엔드에 접속합니다.\n"
        "2. 프론트엔드는 API 요청을 https://dahun-ai.duckdns.org 로 보냅니다.\n"
        "3. DuckDNS 도메인은 AWS EC2 서버의 백엔드 API 주소로 연결됩니다.\n"
        "4. EC2 서버에서는 Docker 컨테이너가 FastAPI 백엔드를 실행합니다.\n"
        "5. FastAPI는 SQLite DB, AI API, 인증, 포인트, 학습 기능을 처리합니다.\n\n"
        "현재 백엔드는 ai-backend 컨테이너로 실행되며, 8000번 포트를 사용합니다. "
        "SQLite DB는 EC2의 backend/history.db 파일을 컨테이너의 /app/history.db로 마운트하여 "
        "컨테이너를 재생성해도 데이터가 유지되도록 구성했습니다.\n\n"
        "재배포는 bash deploy.sh로 수행합니다. docker-compose.yml은 준비 파일이지만, "
        "현재 운영 환경에서 docker compose 명령어 기반으로 운영한다고 말하면 안 됩니다."
    )


def docker_reason_reply() -> str:
    return (
        "이 프로젝트에서 Docker를 사용한 이유는 배포 환경을 안정적으로 고정하기 위해서입니다.\n\n"
        "특히 EC2 호스트의 기본 Python 버전과 프로젝트가 요구하는 Python 버전이 다를 수 있습니다. "
        "실제로 EC2 호스트는 Python 3.14 환경이었지만, 백엔드는 Docker 컨테이너 내부에서 "
        "Python 3.11 기반으로 실행되도록 구성했습니다.\n\n"
        "Docker를 사용하면 다음 장점이 있습니다.\n\n"
        "1. 서버 환경 차이로 인한 실행 오류를 줄일 수 있습니다.\n"
        "2. Python, FastAPI, 의존성 버전을 컨테이너 안에서 고정할 수 있습니다.\n"
        "3. 재배포 시 같은 환경으로 반복 실행할 수 있습니다.\n"
        "4. DB 마운트, 환경변수, 포트 설정을 명확하게 관리할 수 있습니다.\n"
        "5. 포트폴리오에서 실제 서비스 운영 경험을 보여줄 수 있습니다.\n\n"
        "현재 실제 재배포는 deploy.sh를 통해 Docker 이미지 빌드, 기존 컨테이너 교체, "
        "DB 마운트, 환경변수 적용, health check까지 자동화하는 방식입니다."
    )


def point_system_reply() -> str:
    return (
        "포인트 시스템은 사용자의 활동 이력을 로그로 저장하고, 그 합계를 계산하는 구조입니다.\n\n"
        "핵심 방식은 point_logs 테이블입니다.\n\n"
        "예를 들어 사용자가 출석 체크, 에러 분석, 코드 리뷰, 학습 기록 작성, 시험 제출 같은 활동을 하면 "
        "각 활동마다 point_logs에 포인트 로그가 저장됩니다.\n\n"
        "총 포인트는 별도의 숫자 컬럼 하나만 수정하는 방식이 아니라, "
        "point_logs 테이블에서 해당 사용자의 amount 값을 SUM(amount)로 합산해서 계산합니다.\n\n"
        "이 방식의 장점은 다음과 같습니다.\n\n"
        "1. 포인트가 왜 늘었는지 이력 추적이 가능합니다.\n"
        "2. 상점 구매처럼 포인트가 차감되는 내역도 음수 로그로 관리할 수 있습니다.\n"
        "3. 총 포인트 계산의 신뢰성이 높아집니다.\n"
        "4. 관리자나 사용자에게 포인트 활동 내역을 보여주기 좋습니다."
    )


def attendance_reply() -> str:
    return (
        "출석 기능은 사용자가 하루에 한 번 출석 체크를 할 수 있도록 만든 학습 루틴 관리 기능입니다.\n\n"
        "동작 흐름은 다음과 같습니다.\n\n"
        "1. 사용자가 출석 체크 버튼을 누릅니다.\n"
        "2. 백엔드는 오늘 날짜에 이미 출석 기록이 있는지 확인합니다.\n"
        "3. 오늘 기록이 없으면 attendance_records 테이블에 출석 날짜를 저장합니다.\n"
        "4. 출석 성공 시 포인트 로그에 출석 보상 포인트를 추가합니다.\n"
        "5. 프론트엔드는 오늘 출석 여부, 누적 학습일, 총 포인트를 화면에 반영합니다.\n\n"
        "또한 학습일 계산은 단순 출석뿐 아니라 학습 기록 날짜와 출석 날짜를 함께 고려해서 "
        "사용자의 실제 학습 흐름을 보여주는 구조로 설계했습니다."
    )


def differentiation_reply() -> str:
    return (
        "이 프로젝트의 핵심 차별점은 단순한 기능 모음이 아니라, 개발 학습 과정을 하나의 흐름으로 연결했다는 점입니다.\n\n"
        "차별점은 다음과 같습니다.\n\n"
        "1. 에러 분석과 코드 리뷰를 통해 개발 중 문제 해결을 지원합니다.\n"
        "2. 학습 기록과 출석 체크로 사용자의 학습 루틴을 관리합니다.\n"
        "3. 포인트 시스템과 상점 기능으로 학습 활동에 보상 구조를 연결했습니다.\n"
        "4. 시험과 오답노트를 통해 학습 결과를 점검할 수 있습니다.\n"
        "5. 플로팅 AI 챗봇을 통해 프로젝트 설명, 기술 스택, 배포 구조, 오류 해결 방법을 바로 질문할 수 있습니다.\n"
        "6. GitHub Pages, EC2, Docker, DuckDNS를 연결해 실제 외부 접속 가능한 서비스 형태로 운영했습니다.\n\n"
        "즉, 단순히 화면만 만든 프로젝트가 아니라 프론트엔드, 백엔드, AI API, DB, 인증, 배포, 운영까지 "
        "경험한 서비스형 AI 학습 플랫폼이라는 점이 강점입니다."
    )


def interview_reply() -> str:
    return (
        "면접에서는 아래처럼 설명하면 좋습니다.\n\n"
        "\"AI Developer Assistant는 개발자가 학습과 코딩 과정에서 겪는 에러 분석, 코드 리뷰, "
        "학습 기록 관리, 출석 체크, 포인트 보상, 시험/오답노트 기능을 하나의 흐름으로 연결한 "
        "AI 기반 개발 학습 지원 시스템입니다.\"\n\n"
        "\"저는 이 프로젝트에서 FastAPI 기반 백엔드 API를 구성하고, SQLite 데이터 저장 구조, "
        "JWT 인증 흐름, 포인트 로그 시스템, 프론트엔드 연동, GitHub Pages와 AWS EC2 기반 배포를 구현했습니다. "
        "또한 Docker를 사용해 서버 실행 환경을 고정하고, DuckDNS 도메인을 연결해 실제 외부 접속 가능한 API 서버로 운영했습니다.\"\n\n"
        "\"최근에는 사이트 전역에서 사용할 수 있는 플로팅 AI 챗봇 기능을 추가했습니다. "
        "이 챗봇은 프로젝트 설명, 기술 스택, EC2 배포 구조, 오류 해결 순서 등을 안내하며, "
        "Hugging Face API 응답 실패 시에도 fallback 답변이 동작하도록 안정성을 고려했습니다.\"\n\n"
        "기술 스택은 이렇게 설명하면 정확합니다.\n"
        "- 프론트엔드: GitHub Pages 기반 HTML/CSS/JavaScript\n"
        "- 백엔드: Python FastAPI\n"
        "- 데이터베이스: SQLite\n"
        "- 배포: AWS EC2 + Docker 컨테이너\n"
        "- 도메인: DuckDNS 기반 API 주소\n"
        "- 자동화: deploy.sh 기반 Docker 재빌드 및 재실행\n\n"
        "주의: 현재 확인된 운영 방식은 AWS EC2 + Docker + deploy.sh입니다. "
        "Nginx, Traefik, Docker Compose로 현재 운영 중이라고 설명하지 않습니다."
    )


def chatbot_feature_reply() -> str:
    return (
        "플로팅 AI 챗봇 기능은 사이트 오른쪽 아래에 고정되는 원형 버튼 형태로 구현했습니다.\n\n"
        "사용자가 버튼을 누르면 작은 채팅창이 열리고, 현재 페이지를 벗어나지 않고 바로 질문할 수 있습니다.\n\n"
        "주요 기능은 다음과 같습니다.\n\n"
        "1. 사이트 전역에서 사용 가능한 플로팅 챗봇 UI\n"
        "2. FastAPI /chat API와 연동\n"
        "3. 사용자별 대화 기록을 chat_history 테이블에 저장\n"
        "4. 프로젝트 설명, 기술 스택, EC2 배포 구조, 오류 해결 순서 안내\n"
        "5. Hugging Face API 기반 AI 답변 처리\n"
        "6. AI 응답 실패 시 fallback 답변 제공\n"
        "7. 제작자 정보처럼 중요한 질문은 고정 답변으로 처리\n\n"
        "이 기능을 통해 프로젝트가 단순한 학습 관리 서비스에서, 사용자가 즉시 질문하고 안내받을 수 있는 "
        "AI 기반 포트폴리오 서비스로 확장되었습니다."
    )


def auth_security_reply() -> str:
    return (
        "인증 시스템은 JWT 기반 로그인 구조로 구현했습니다.\n\n"
        "동작 흐름은 다음과 같습니다.\n\n"
        "1. 사용자가 이메일과 비밀번호로 로그인합니다.\n"
        "2. 백엔드는 bcrypt로 저장된 해시 비밀번호와 입력 비밀번호를 검증합니다.\n"
        "3. 로그인 성공 시 JWT access token을 발급합니다.\n"
        "4. 프론트엔드는 사용자 정보와 accessToken을 localStorage에 저장합니다.\n"
        "5. 인증이 필요한 API 요청 시 Authorization 헤더에 토큰을 포함할 수 있습니다.\n\n"
        "보안 개선 방향으로는 JWT_SECRET_KEY를 환경변수로 관리하고, CORS 허용 도메인을 제한하며, "
        "관리자 페이지 접근 권한을 더 엄격하게 분리하는 것이 좋습니다."
    )


def database_reply() -> str:
    return (
        "이 프로젝트는 SQLite 기반으로 사용자, 학습 기록, 분석 기록, 시험 결과, 오답노트, 포인트 로그, "
        "상점 아이템, 프로필 커스터마이징, 챗봇 대화 기록을 관리합니다.\n\n"
        "주요 테이블 예시는 다음과 같습니다.\n\n"
        "- users: 사용자 정보\n"
        "- analysis_history: 에러 분석 기록\n"
        "- code_review_history: 코드 리뷰 기록\n"
        "- learning_journal: 학습 기록\n"
        "- attendance_records: 출석 기록\n"
        "- point_logs: 포인트 이력\n"
        "- exam_sets / questions / exam_results / wrong_notes: 시험과 오답노트\n"
        "- shop_items / user_inventory / user_profile_custom: 상점과 프로필 꾸미기\n"
        "- chat_history: 챗봇 대화 기록\n\n"
        "현재 배포 구조에서는 backend/history.db 파일을 Docker 컨테이너의 /app/history.db로 마운트하여 "
        "컨테이너를 재생성해도 데이터가 유지되도록 구성했습니다."
    )


def error_analysis_reply() -> str:
    return (
        "에러 분석 기능은 사용자가 에러 메시지를 입력하면 백엔드가 AI API에 분석 요청을 보내고, "
        "원인과 해결 방향을 한국어로 정리해주는 기능입니다.\n\n"
        "기본 분석 흐름은 다음과 같습니다.\n\n"
        "1. 사용자가 에러 메시지를 입력합니다.\n"
        "2. FastAPI 백엔드가 입력값과 사용자 정보를 검증합니다.\n"
        "3. AI 분석 프롬프트를 구성합니다.\n"
        "4. Hugging Face API를 호출해 원인과 해결 방법을 생성합니다.\n"
        "5. 결과를 analysis_history 테이블에 저장합니다.\n"
        "6. 사용자는 프론트 화면에서 분석 결과를 확인합니다.\n\n"
        "오류를 볼 때는 마지막 줄, 파일 경로, 발생 위치, HTTP 상태 코드, 브라우저 콘솔, Docker 로그를 함께 확인하는 것이 중요합니다."
    )


def project_pages_reply() -> str:
    return (
        "이 프로젝트의 주요 페이지는 다음과 같습니다.\n\n"
        "- Login Page: 로그인\n"
        "- Signup Page: 회원가입\n"
        "- Main Dashboard: 전체 학습 현황과 주요 기능 진입\n"
        "- Study / Journal Page: 학습 기록과 에러 분석, 코드 리뷰\n"
        "- Exam / Quiz Page: 시험 응시, 결과 확인, 오답노트\n"
        "- Shop Page: 포인트 기반 아이템 구매와 프로필 커스터마이징\n"
        "- Admin Page: 관리자용 데이터 관리\n"
        "- Floating AI Chatbot: 사이트 전역에서 사용할 수 있는 AI 도우미\n\n"
        "프론트엔드는 docs 폴더를 기준으로 GitHub Pages에 배포됩니다."
    )


# =========================
# Fallback Routing
# =========================
def project_fallback_reply(user_message: str) -> str:
    """
    Hugging Face API가 없거나 실패했을 때 사용할 프로젝트 전용 기본 답변.
    챗봇이 죽지 않고 항상 응답하도록 설계합니다.
    """
    if is_owner_question(user_message):
        return owner_reply()

    if contains_any(user_message, ["면접", "자기소개", "설명하면", "어떻게설명", "포트폴리오설명"]):
        return interview_reply()

    if contains_any(user_message, ["차별점", "핵심차별", "강점", "특징", "핵심기능", "장점"]):
        return differentiation_reply()

    if contains_any(user_message, ["기술스택", "기술", "스택", "사용한기술", "뭐썼어", "사용도구"]):
        return tech_stack_reply()

    if contains_any(user_message, ["ec2", "배포구조", "배포", "서버구조", "duckdns", "도메인"]):
        return ec2_deploy_reply()

    if contains_any(user_message, ["docker", "도커", "컨테이너", "이미지", "재배포"]):
        return docker_reason_reply()

    if contains_any(user_message, ["포인트", "point", "pointlogs", "포인트계산", "보상"]):
        return point_system_reply()

    if contains_any(user_message, ["출석", "attendance", "학습일", "연속학습", "출석체크"]):
        return attendance_reply()

    if contains_any(user_message, ["챗봇", "chatbot", "채팅", "대화기록", "chat_history"]):
        return chatbot_feature_reply()

    if contains_any(user_message, ["인증", "로그인", "jwt", "토큰", "보안", "bcrypt"]):
        return auth_security_reply()

    if contains_any(user_message, ["db", "데이터베이스", "sqlite", "테이블", "historydb", "저장구조"]):
        return database_reply()

    if contains_any(user_message, ["오류", "에러", "error", "해결", "분석", "코드리뷰", "리뷰"]):
        return error_analysis_reply()

    if contains_any(user_message, ["페이지", "화면", "구성", "메뉴"]):
        return project_pages_reply()

    if contains_any(user_message, ["프로젝트", "서비스", "뭐야", "소개", "개요"]):
        return project_intro_reply()

    return (
        "안녕하세요! 저는 AI Developer Assistant 챗봇입니다. 🚀\n\n"
        "프로젝트 설명, 기술 스택, EC2 배포 구조, Docker 사용 이유, 포인트 시스템, 출석 기능, "
        "오류 해결 순서, 면접용 프로젝트 설명을 도와드릴 수 있습니다.\n\n"
        "예를 들어 이렇게 질문해보세요.\n"
        "- 이 프로젝트 만든 사람 누구야?\n"
        "- 사용한 기술 스택 알려줘\n"
        "- EC2 배포 구조 설명해줘\n"
        "- Docker는 왜 썼어?\n"
        "- 포인트 시스템은 어떻게 계산돼?\n"
        "- 면접에서 이 프로젝트를 어떻게 설명하면 돼?"
    )


def is_fixed_project_question(user_message: str) -> bool:
    """
    프로젝트 핵심 정보는 AI가 추측하지 않도록 Hugging Face 호출 전에 고정 답변으로 처리합니다.
    """
    if is_owner_question(user_message):
        return True

    fixed_keywords = [
        "면접", "자기소개", "설명하면", "어떻게설명", "포트폴리오설명",
        "차별점", "핵심차별", "강점", "특징", "핵심기능", "장점",
        "기술스택", "기술", "스택", "사용한기술", "뭐썼어", "사용도구",
        "ec2", "배포구조", "배포", "서버구조", "duckdns", "도메인",
        "docker", "도커", "컨테이너", "이미지", "재배포",
        "포인트", "point", "pointlogs", "포인트계산", "보상",
        "출석", "attendance", "학습일", "연속학습", "출석체크",
        "챗봇", "chatbot", "채팅", "대화기록", "chat_history",
        "인증", "로그인", "jwt", "토큰", "보안", "bcrypt",
        "db", "데이터베이스", "sqlite", "테이블", "historydb", "저장구조",
        "오류", "에러", "error", "해결", "분석", "코드리뷰", "리뷰",
        "페이지", "화면", "구성", "메뉴",
        "프로젝트", "서비스", "뭐야", "소개", "개요",
    ]

    return contains_any(user_message, fixed_keywords)


# =========================
# Hugging Face AI Call
# =========================
def build_system_prompt() -> str:
    return """
너는 AI Developer Assistant 프로젝트 안에 탑재된 한국어 AI 챗봇이다.

가장 중요한 원칙:
- 반드시 확인된 정보만 말한다.
- 확인되지 않은 기술, 도구, 서버 구성을 추측해서 말하지 않는다.
- 특히 Nginx, Traefik, Docker Compose를 실제 운영 중이라고 말하면 안 된다.
- docker-compose.yml은 준비 파일일 뿐, 현재 EC2에서 docker compose 명령어가 동작한다고 확인되지 않았다.
- 현재 실제 재배포는 deploy.sh 기반으로 수행한다.
- HTTPS 세부 구성 방식은 확인되지 않았으므로 Nginx 또는 Traefik을 사용한다고 말하지 않는다.
- 모르는 내용은 "확인된 정보로는 알 수 없습니다" 또는 "서버 설정 확인이 필요합니다"라고 답한다.

반드시 지켜야 할 고정 정보:
- 이 사이트와 AI Developer Assistant 프로젝트를 만든 개발자는 전다훈(Dahun Jeon)이다.
- 사용자가 "이 사이트 누가 만들었어?", "개발자가 누구야?", "제작자가 누구야?", "누가 만들었어?"처럼 물으면 반드시 "이 사이트를 만든 개발자는 전다훈 개발자님입니다."라고 답변한다.
- 이 프로젝트는 AI 기반 개발 학습 도우미 서비스다.
- 주요 기능은 오류 분석, 코드 리뷰, 학습 기록, 출석 체크, 포인트, 시험 시스템, 오답노트, 상점, 프로필 커스터마이징, 플로팅 AI 챗봇 기능이다.
- 프론트엔드는 GitHub Pages의 docs 폴더에서 배포된다.
- 백엔드는 AWS EC2에서 Docker 컨테이너 기반 FastAPI 서버로 실행된다.
- API 도메인은 https://dahun-ai.duckdns.org 를 사용한다.
- DB는 SQLite 기반 history.db를 사용한다.
- Docker 컨테이너 이름은 ai-backend다.
- SQLite DB는 EC2의 backend/history.db를 컨테이너 /app/history.db에 마운트한다.
- 배포 자동화를 위해 deploy.sh를 사용한다.
- docker-compose.yml은 향후 Docker Compose 사용을 위해 준비한 설정 파일이다.
- AI 답변은 Hugging Face Inference API를 사용하고, 실패 시 fallback 답변을 제공한다.

정확한 배포 설명:
- 프론트엔드: GitHub Pages
- 백엔드: AWS EC2
- 백엔드 실행 방식: Docker 컨테이너
- API 도메인: https://dahun-ai.duckdns.org
- DB 유지 방식: backend/history.db를 /app/history.db로 bind mount
- 재배포 방식: bash deploy.sh
- 준비 파일: docker-compose.yml, .env.example
- 실제 토큰 저장 파일: .env
- GitHub에 올리면 안 되는 파일: .env, backend/history.db, db_backups/

말하면 안 되는 표현:
- "Nginx를 사용했다"
- "Traefik을 사용했다"
- "Docker Compose로 현재 운영 중이다"
- "docker compose 명령어로 배포한다"
- "HTTPS는 Nginx/Traefik으로 구성했다"

면접 답변에서 사용할 정확한 표현:
"프론트엔드는 GitHub Pages 기반 HTML/CSS/JavaScript로 구성했고, 백엔드는 Python FastAPI와 SQLite를 사용했습니다. 배포는 AWS EC2에서 Docker 컨테이너로 운영했고, DuckDNS 도메인을 통해 API 주소를 연결했습니다. 또한 deploy.sh를 만들어 Docker 재빌드와 재실행 과정을 자동화했습니다."

프로젝트 기능 요약:
1. 에러 분석: 에러 메시지 기반 원인 분석과 해결 방법 제공
2. 코드 리뷰: 코드 개선 방향과 리팩토링 포인트 제공
3. 학습 기록: 사용자의 학습 내용을 저장하고 관리
4. 출석 시스템: 하루 1회 출석 체크와 학습일 계산
5. 포인트 시스템: point_logs 기반 활동 보상 기록과 SUM(amount) 총 포인트 계산
6. 시험 시스템: 객관식/코드 문제 응시, 채점, 결과 저장
7. 오답노트: 틀린 문제와 복습 상태 관리
8. 상점 시스템: 포인트 기반 아이템 구매
9. 프로필 커스터마이징: 테마, 배지, 배경, 닉네임 색상, 카드 스킨 적용
10. 플로팅 챗봇: 사이트 전역에서 사용하는 AI 도우미

답변 규칙:
- 반드시 한국어로 답변한다.
- 내부 추론 과정은 절대 출력하지 않는다.
- 사용자가 짧게 물으면 짧고 명확하게 답한다.
- 프로젝트 관련 질문은 전다훈 개발자님의 개인 프로젝트 기준으로 답한다.
- 모르는 내용은 지어내지 말고 확인 방법을 안내한다.
- 면접 질문에는 포트폴리오 설명에 적합한 문장으로 답한다.
- 너무 장황하게 쓰지 말고, 필요한 경우 번호 목록으로 정리한다.
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
                "max_tokens": 1000,
                "temperature": 0.25,
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


# =========================
# API
# =========================
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

    if is_fixed_project_question(user_message):
        reply = project_fallback_reply(user_message)
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
