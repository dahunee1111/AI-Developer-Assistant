# 🔒 보안 가이드

AI Developer Assistant 프로젝트의 보안 개선사항과 설정 방법을 설명합니다.

---

## 📋 보안 개선사항 (2026-05-03)

### 1. ✅ JWT_SECRET_KEY 환경변수 강제화
**파일**: `backend/settings.py`

- **문제**: 기본값이 노출될 수 있음
- **해결**: 프로덕션 배포 시 환경변수 필수 설정

**설정 방법**:
```bash
# 환경변수 설정 (프로덕션)
export JWT_SECRET_KEY="your-super-secret-key-here-min-32-chars"
export ENV="production"

# 또는 .env 파일에 추가
echo "JWT_SECRET_KEY=your-super-secret-key-here-min-32-chars" >> .env
```

---

### 2. ✅ 비밀번호 해싱 개선 (SHA256 → bcrypt)
**파일**: `backend/db.py`

**변경사항**:
- ❌ **이전**: `hashlib.sha256()` - 레인보우 테이블 공격에 취약
- ✅ **현재**: `bcrypt` - 안전한 비밀번호 저장 (rounds=12)

**함수**:
```python
def hash_password(password: str) -> str:
    """bcrypt를 사용하여 비밀번호를 안전하게 해시합니다."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """bcrypt를 사용하여 비밀번호를 검증합니다."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
```

---

### 3. ✅ JWT 토큰 검증 강화
**파일**: `backend/auth_security.py`

**추가된 함수**:
```python
def get_current_user_id_from_header_required(authorization):
    """토큰 검증 필수 버전 (HTTP 401 반환)"""
    # 토큰 없으면 401 Unauthorized 발생
    ...
```

**사용 예**:
```python
@router.get("/protected")
def protected_endpoint(user_id: int = Depends(get_current_user_id_from_header_required)):
    return {"user_id": user_id}
```

---

### 4. ✅ 에러 처리 추가
**파일**: `backend/db.py`

모든 DB 함수에 `try-except` 추가:
- 데이터베이스 오류 로깅
- Graceful 한 오류 처리
- 예외 상황 대응

**예**:
```python
def add_points(user_id: int, amount: int, reason: str) -> bool:
    """성공/실패 여부를 boolean으로 반환"""
    try:
        # ...
        return True
    except sqlite3.Error as e:
        logger.error(f"포인트 추가 실패: {e}")
        return False
    finally:
        if conn:
            conn.close()
```

---

### 5. ✅ requirements.txt 정리
**파일**: `backend/requirements.txt`

**개선사항**:
- 불필요한 라이브러리 제거 (Selenium, BeautifulSoup 등)
- 버전 명시
- 카테고리별 주석 추가

**주요 보안 라이브러리**:
- `bcrypt` - 비밀번호 해싱
- `python-jose` - JWT 토큰 생성/검증
- `cryptography` - 암호화

---

## 🔐 환경변수 설정 체크리스트

| 변수 | 필수 | 설명 | 예시 |
|------|------|------|------|
| `JWT_SECRET_KEY` | ✅ (프로덕션) | JWT 비밀키 (최소 32자) | `super-secret-key...` |
| `ENV` | ✅ (프로덕션) | 환경 구분 | `production` |
| `ADA_DB_PATH` | ❌ | DB 경로 | `/path/to/history.db` |
| `CORS_ALLOW_ORIGINS` | ❌ | CORS 허용 도메인 | `https://example.com` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ❌ | 토큰 만료 시간 | `1440` (기본값) |

---

## 🚀 배포 전 체크리스트

### Render (백엔드)
```bash
# 1. 환경변수 설정
JWT_SECRET_KEY = "your-secret-key"
ENV = "production"
CORS_ALLOW_ORIGINS = "https://dahunee1111.github.io"

# 2. 배포 확인
curl https://your-backend.onrender.com/health
```

### GitHub Pages (프론트엔드)
```bash
# 1. API 엔드포인트 확인 (index.html)
# ✅ 프로덕션 API URL로 설정

# 2. HTTPS 사용 확인
# ✅ GitHub Pages는 자동 HTTPS 제공
```

---

## 🛡️ 추가 보안 권장사항

### 단기 (1-2주)
- [ ] Rate Limiting 추가 (API 악용 방지)
- [ ] HTTPS 확인 (배포 시)
- [ ] 비밀번호 최소 길이 설정 (8자 이상)

### 중기 (1-2개월)
- [ ] PostgreSQL 마이그레이션 (SQLite → PostgreSQL)
- [ ] 단위 테스트 추가
- [ ] API 인증 강화 (Refresh Token)

### 장기 (3개월+)
- [ ] 입력값 검증 강화 (SQL Injection 방지)
- [ ] 감사 로그 추가
- [ ] 보안 감사 (Penetration Testing)

---

## 📚 참고 자료

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [bcrypt 문서](https://github.com/pyca/bcrypt)
- [FastAPI 보안](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT 소개](https://jwt.io/)

---

## ❓ 문제 해결

### "JWT_SECRET_KEY 환경변수가 설정되지 않았습니다" 에러
```bash
# 해결: 환경변수 설정
export JWT_SECRET_KEY="your-secret-key"
python -m uvicorn backend.main:app
```

### bcrypt 설치 실패
```bash
# 해결: 개발 도구 설치 후 재설치
pip install --upgrade pip
pip install bcrypt==5.0.0
```

---

**작성일**: 2026-05-03
**유지보수**: 전다훈
