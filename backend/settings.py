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
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or "dev-secret-change-me"
JWT_SECRET_FROM_ENV = bool(os.getenv("JWT_SECRET_KEY"))
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

raw_cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
CORS_ALLOW_ORIGINS = [origin.strip() for origin in raw_cors_origins.split(",") if origin.strip()]
