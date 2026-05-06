"""
Rate Limiting 설정 및 유틸리티

API 악용 방지를 위한 요청 제한 기능을 제공합니다.
"""
import time
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    간단한 메모리 기반 Rate Limiter
    
    IP 주소 또는 사용자 ID 기반으로 요청을 제한합니다.
    
    Example:
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        @app.get("/api/data")
        def get_data(request: Request):
            if not limiter.allow_request(request.client.host):
                raise HTTPException(429, "Too many requests")
            return {"data": "..."}
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Rate Limiter 초기화
        
        Args:
            max_requests: 시간 윈도우 내 최대 요청 수
            window_seconds: 시간 윈도우 (초)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)  # {identifier: [timestamp1, timestamp2, ...]}
    
    def allow_request(self, identifier: str) -> bool:
        """
        요청이 허용되는지 확인합니다.
        
        Args:
            identifier: IP 주소 또는 사용자 ID
            
        Returns:
            요청이 허용되면 True, 초과하면 False
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        # 시간 윈도우 벗어난 요청 제거
        self.requests[identifier] = [
            timestamp for timestamp in self.requests[identifier]
            if timestamp > window_start
        ]
        
        # 요청 수 확인
        if len(self.requests[identifier]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return False
        
        # 현재 요청 기록
        self.requests[identifier].append(now)
        return True
    
    def get_remaining(self, identifier: str) -> int:
        """
        남은 요청 수를 반환합니다.
        
        Args:
            identifier: IP 주소 또는 사용자 ID
            
        Returns:
            남은 요청 수
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        valid_requests = [
            timestamp for timestamp in self.requests[identifier]
            if timestamp > window_start
        ]
        
        return max(0, self.max_requests - len(valid_requests))


# 기본 Rate Limiter 인스턴스들
# API 엔드포인트별로 다른 제한을 설정할 수 있습니다
limiter_login = RateLimiter(max_requests=5, window_seconds=300)  # 5분에 5회
limiter_signup = RateLimiter(max_requests=3, window_seconds=3600)  # 1시간에 3회
limiter_api = RateLimiter(max_requests=100, window_seconds=60)  # 1분에 100회
limiter_analysis = RateLimiter(max_requests=10, window_seconds=60)  # 1분에 10회 (AI API 호출)
