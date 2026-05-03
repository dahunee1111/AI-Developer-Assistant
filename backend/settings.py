import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _resolve_path(value: str | None, default: Path) -> Path:
    if not value:
        return default

    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = BASE_DIR / candidate

    return candidate.resolve()


DB_PATH = _resolve_path(os.getenv("ADA_DB_PATH"), BASE_DIR / "history.db")

# JWT 설정 - 환경변수 필수
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    # 개발 환경에서만 기본값 허용
    import sys
    if "pytest" not in sys.modules and os.getenv("ENV") == "production":
        raise ValueError(
            "❌ JWT_SECRET_KEY 환경변수가 설정되지 않았습니다!\n"
            "프로덕션 배포 전에 반드시 설정해주세요.\n"
            "export JWT_SECRET_KEY='your-secret-key-here'"
        )
    # 개발 환경: 기본값 사용 (경고 표시)
    JWT_SECRET_KEY = "dev-secret-change-me-in-production"
    print("⚠️  경고: 개발 환경 기본 JWT_SECRET_KEY 사용 중입니다. 프로덕션에서는 반드시 변경하세요!")

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

raw_cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
CORS_ALLOW_ORIGINS = [origin.strip() for origin in raw_cors_origins.split(",") if origin.strip()]
