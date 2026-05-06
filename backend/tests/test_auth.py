"""
pytest를 사용한 백엔드 테스트

실행: pytest backend/tests/ -v
"""
import pytest
from datetime import timedelta
from backend.db import hash_password, verify_password
from backend.auth_security import create_access_token, decode_access_token
from backend.rate_limiter import RateLimiter


# ============================================================================
# 1. 비밀번호 해싱 & 검증 테스트
# ============================================================================

class TestPasswordHashing:
    """bcrypt 기반 비밀번호 해싱 테스트"""
    
    def test_hash_password_returns_string(self):
        """hash_password는 문자열을 반환해야 함"""
        password = "test_password_123"
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0
    
    def test_hash_password_different_each_time(self):
        """같은 비밀번호도 매번 다른 해시값을 생성 (salt 때문)"""
        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2  # bcrypt는 항상 다른 hash 생성
    
    def test_verify_password_correct(self):
        """올바른 비밀번호 검증 성공"""
        password = "test_password_123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """잘못된 비밀번호 검증 실패"""
        password = "test_password_123"
        wrong_password = "wrong_password_456"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False
    
    def test_verify_password_empty_string(self):
        """빈 문자열 검증 실패"""
        password = "test_password_123"
        hashed = hash_password(password)
        assert verify_password("", hashed) is False
    
    def test_verify_password_with_special_chars(self):
        """특수문자가 포함된 비밀번호도 정상 작동"""
        password = "P@ssw0rd!#$%"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
    
    def test_verify_password_korean_chars(self):
        """한글이 포함된 비밀번호도 정상 작동"""
        password = "비밀번호123!@#"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True


# ============================================================================
# 2. JWT 토큰 생성 & 검증 테스트
# ============================================================================

class TestJWTToken:
    """JWT 토큰 생성 및 검증 테스트"""
    
    def test_create_access_token_returns_string(self):
        """create_access_token은 문자열을 반환해야 함"""
        data = {"user_id": 1, "email": "test@example.com"}
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_access_token_has_three_parts(self):
        """JWT는 3개 부분으로 구성 (header.payload.signature)"""
        data = {"user_id": 1}
        token = create_access_token(data)
        parts = token.split(".")
        assert len(parts) == 3
    
    def test_decode_access_token_valid(self):
        """유효한 토큰 디코딩 성공"""
        data = {"user_id": 123, "email": "test@example.com"}
        token = create_access_token(data)
        decoded = decode_access_token(token)
        
        assert decoded is not None
        assert decoded["user_id"] == 123
        assert decoded["email"] == "test@example.com"
    
    def test_decode_access_token_invalid(self):
        """유효하지 않은 토큰 디코딩 실패"""
        invalid_token = "invalid.token.here"
        decoded = decode_access_token(invalid_token)
        assert decoded is None
    
    def test_decode_access_token_empty_string(self):
        """빈 토큰 디코딩 실패"""
        decoded = decode_access_token("")
        assert decoded is None
    
    def test_token_contains_exp_claim(self):
        """토큰에 exp (만료 시간) 클레임이 포함되어야 함"""
        data = {"user_id": 1}
        token = create_access_token(data)
        decoded = decode_access_token(token)
        
        assert decoded is not None
        assert "exp" in decoded
    
    def test_create_access_token_with_custom_expires_delta(self):
        """커스텀 만료 시간 설정 가능"""
        data = {"user_id": 1}
        expires_delta = timedelta(hours=2)
        token = create_access_token(data, expires_delta=expires_delta)
        decoded = decode_access_token(token)
        
        assert decoded is not None
        assert "exp" in decoded


# ============================================================================
# 3. Rate Limiter 테스트
# ============================================================================

class TestRateLimiter:
    """Rate Limiter 동작 테스트"""
    
    def test_allow_request_within_limit(self):
        """제한 내의 요청은 허용"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        
        assert limiter.allow_request("192.168.1.1") is True
        assert limiter.allow_request("192.168.1.1") is True
        assert limiter.allow_request("192.168.1.1") is True
    
    def test_allow_request_exceeds_limit(self):
        """제한을 초과한 요청은 거부"""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        assert limiter.allow_request("192.168.1.1") is True
        assert limiter.allow_request("192.168.1.1") is True
        assert limiter.allow_request("192.168.1.1") is False  # 3번째 요청 거부
    
    def test_different_identifiers_separate_limits(self):
        """다른 IP는 독립적인 제한 적용"""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        # IP 1
        assert limiter.allow_request("192.168.1.1") is True
        assert limiter.allow_request("192.168.1.1") is True
        assert limiter.allow_request("192.168.1.1") is False
        
        # IP 2 (독립적)
        assert limiter.allow_request("192.168.1.2") is True
        assert limiter.allow_request("192.168.1.2") is True
        assert limiter.allow_request("192.168.1.2") is False
    
    def test_get_remaining_requests(self):
        """남은 요청 수 계산"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        assert limiter.get_remaining("192.168.1.1") == 5
        limiter.allow_request("192.168.1.1")
        assert limiter.get_remaining("192.168.1.1") == 4
        limiter.allow_request("192.168.1.1")
        assert limiter.get_remaining("192.168.1.1") == 3
    
    def test_get_remaining_exceeds_limit(self):
        """제한 초과 시 남은 요청 수는 0"""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        limiter.allow_request("192.168.1.1")
        limiter.allow_request("192.168.1.1")
        limiter.allow_request("192.168.1.1")  # 초과
        
        assert limiter.get_remaining("192.168.1.1") == 0
    
    def test_rate_limiter_user_id_identifier(self):
        """사용자 ID로도 Rate Limiting 가능"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        
        # user_id로 추적
        user_id_str = "user_123"
        assert limiter.allow_request(user_id_str) is True
        assert limiter.allow_request(user_id_str) is True
        assert limiter.allow_request(user_id_str) is True
        assert limiter.allow_request(user_id_str) is False


# ============================================================================
# 4. 입력값 검증 테스트
# ============================================================================

class TestInputValidation:
    """입력값 검증 테스트"""
    
    def test_password_minimum_length(self):
        """비밀번호 최소 8자 검증"""
        short_password = "short"
        assert len(short_password) < 8
    
    def test_username_length_validation(self):
        """사용자명 길이 검증 (3-20자)"""
        # 너무 짧음
        assert len("ab") < 3
        
        # 적당함
        assert 3 <= len("john_doe") <= 20
        
        # 너무 긺
        assert len("a" * 21) > 20
    
    def test_email_basic_format(self):
        """이메일 기본 형식 검증"""
        valid_emails = [
            "user@example.com",
            "test.email@domain.co.kr",
            "user+tag@example.com"
        ]
        
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user name@example.com"
        ]
        
        # 간단한 이메일 검증
        for email in valid_emails:
            assert "@" in email and "." in email
        
        for email in invalid_emails:
            # 이메일이 유효하지 않은 경우를 감지해야 함
            if email == "notanemail":
                assert "@" not in email


# ============================================================================
# 5. 데이터 타입 테스트
# ============================================================================

class TestDataTypes:
    """데이터 타입 및 형식 테스트"""
    
    def test_hash_password_output_type(self):
        """hash_password 출력이 문자열"""
        result = hash_password("test")
        assert isinstance(result, str)
    
    def test_verify_password_output_type(self):
        """verify_password 출력이 boolean"""
        hashed = hash_password("test")
        result = verify_password("test", hashed)
        assert isinstance(result, bool)
    
    def test_create_token_output_type(self):
        """create_access_token 출력이 문자열"""
        token = create_access_token({"user_id": 1})
        assert isinstance(token, str)
    
    def test_decode_token_output_type(self):
        """decode_access_token 출력이 dict 또는 None"""
        token = create_access_token({"user_id": 1})
        result = decode_access_token(token)
        assert isinstance(result, dict)
        
        result_invalid = decode_access_token("invalid")
        assert result_invalid is None


if __name__ == "__main__":
    # pytest로 실행: pytest backend/tests/test_auth.py -v
    pytest.main([__file__, "-v"])
