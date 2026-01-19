"""
에러 핸들러

중앙 집중식 에러 처리 및 복구 로직
"""

import functools
import logging
import traceback
import time
from typing import Callable, Optional, Type, Tuple, Any, Dict, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .exceptions import (
    SmartStoreError,
    ValidationError,
    APIError,
    GeminiAPIError,
    RateLimitError,
    NetworkError,
    TimeoutError,
)


class RecoveryAction(Enum):
    """복구 액션"""
    RETRY = "retry"
    SKIP = "skip"
    FALLBACK = "fallback"
    ABORT = "abort"
    LOG_AND_CONTINUE = "log_and_continue"


@dataclass
class ErrorRecord:
    """에러 기록"""
    error_code: str
    message: str
    timestamp: str
    traceback: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    recovery_action: Optional[RecoveryAction] = None
    recovered: bool = False


class ErrorHandler:
    """에러 핸들러"""

    def __init__(self, logger: logging.Logger = None, max_retries: int = 3):
        self.logger = logger or logging.getLogger(__name__)
        self.max_retries = max_retries
        self.error_history: List[ErrorRecord] = []

        # 에러별 복구 전략 매핑
        self._recovery_strategies = {
            RateLimitError: self._handle_rate_limit,
            NetworkError: self._handle_network_error,
            TimeoutError: self._handle_timeout,
            GeminiAPIError: self._handle_gemini_error,
            ValidationError: self._handle_validation_error,
        }

    def handle(
        self,
        error: Exception,
        context: Dict[str, Any] = None
    ) -> RecoveryAction:
        """
        에러 처리

        Args:
            error: 발생한 예외
            context: 에러 컨텍스트

        Returns:
            복구 액션
        """
        context = context or {}

        # 에러 기록
        record = self._create_record(error, context)
        self.error_history.append(record)

        # 로깅
        self._log_error(error, context)

        # 복구 전략 결정
        recovery = self._determine_recovery(error, context)
        record.recovery_action = recovery

        return recovery

    def _create_record(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> ErrorRecord:
        """에러 기록 생성"""
        error_code = "UNKNOWN"
        details = {}

        if isinstance(error, SmartStoreError):
            error_code = error.error_code
            details = error.details

        return ErrorRecord(
            error_code=error_code,
            message=str(error),
            timestamp=datetime.now().isoformat(),
            traceback=traceback.format_exc(),
            details={**details, **context}
        )

    def _log_error(self, error: Exception, context: Dict[str, Any]):
        """에러 로깅"""
        if isinstance(error, SmartStoreError):
            self.logger.error(
                f"[{error.error_code}] {error.message}",
                extra={"context": {**error.details, **context}},
                exc_info=True
            )
        else:
            self.logger.error(
                f"Unhandled error: {str(error)}",
                extra={"context": context},
                exc_info=True
            )

    def _determine_recovery(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> RecoveryAction:
        """복구 전략 결정"""
        # 등록된 복구 전략 찾기
        for error_type, handler in self._recovery_strategies.items():
            if isinstance(error, error_type):
                return handler(error, context)

        # 기본 전략
        if isinstance(error, SmartStoreError):
            return RecoveryAction.LOG_AND_CONTINUE
        else:
            return RecoveryAction.ABORT

    def _handle_rate_limit(
        self,
        error: RateLimitError,
        context: Dict[str, Any]
    ) -> RecoveryAction:
        """속도 제한 에러 처리"""
        retry_after = error.retry_after or 60
        self.logger.warning(f"Rate limited. Waiting {retry_after}s before retry...")
        time.sleep(retry_after)
        return RecoveryAction.RETRY

    def _handle_network_error(
        self,
        error: NetworkError,
        context: Dict[str, Any]
    ) -> RecoveryAction:
        """네트워크 에러 처리"""
        retry_count = context.get("retry_count", 0)
        if retry_count < self.max_retries:
            wait_time = 2 ** retry_count  # 지수 백오프
            self.logger.warning(f"Network error. Retrying in {wait_time}s...")
            time.sleep(wait_time)
            return RecoveryAction.RETRY
        return RecoveryAction.ABORT

    def _handle_timeout(
        self,
        error: TimeoutError,
        context: Dict[str, Any]
    ) -> RecoveryAction:
        """타임아웃 처리"""
        retry_count = context.get("retry_count", 0)
        if retry_count < self.max_retries:
            return RecoveryAction.RETRY
        return RecoveryAction.ABORT

    def _handle_gemini_error(
        self,
        error: GeminiAPIError,
        context: Dict[str, Any]
    ) -> RecoveryAction:
        """Gemini API 에러 처리"""
        if error.status_code == 429:  # Rate limit
            return RecoveryAction.RETRY
        elif error.status_code == 503:  # Service unavailable
            return RecoveryAction.RETRY
        elif error.status_code == 401:  # Unauthorized
            self.logger.error("Gemini API key invalid")
            return RecoveryAction.ABORT
        return RecoveryAction.FALLBACK

    def _handle_validation_error(
        self,
        error: ValidationError,
        context: Dict[str, Any]
    ) -> RecoveryAction:
        """검증 에러 처리"""
        return RecoveryAction.SKIP

    def get_error_summary(self) -> Dict[str, Any]:
        """에러 요약 반환"""
        if not self.error_history:
            return {"total_errors": 0, "by_code": {}}

        by_code = {}
        for record in self.error_history:
            code = record.error_code
            by_code[code] = by_code.get(code, 0) + 1

        return {
            "total_errors": len(self.error_history),
            "by_code": by_code,
            "recent_errors": [
                {"code": r.error_code, "message": r.message, "time": r.timestamp}
                for r in self.error_history[-5:]
            ]
        }

    def clear_history(self):
        """에러 히스토리 초기화"""
        self.error_history.clear()


def error_handler(
    fallback_value: Any = None,
    reraise: bool = False,
    log_level: str = "error",
    recovery_actions: Dict[Type[Exception], RecoveryAction] = None,
    max_retries: int = 3
):
    """
    에러 핸들링 데코레이터

    사용법:
        @error_handler(fallback_value=None, reraise=False)
        def risky_function():
            pass

    Args:
        fallback_value: 에러 시 반환할 기본값
        reraise: 에러를 다시 발생시킬지 여부
        log_level: 로그 레벨
        recovery_actions: 예외별 복구 액션
        max_retries: 최대 재시도 횟수
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            retry_count = 0

            while True:
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    # 복구 액션 결정
                    action = RecoveryAction.ABORT
                    if recovery_actions:
                        for exc_type, act in recovery_actions.items():
                            if isinstance(e, exc_type):
                                action = act
                                break

                    # 로깅
                    log_method = getattr(logger, log_level)
                    log_method(
                        f"Error in {func.__name__}: {str(e)}",
                        exc_info=True,
                        extra={"context": {"retry_count": retry_count}}
                    )

                    # 복구 액션 처리
                    if action == RecoveryAction.RETRY and retry_count < max_retries:
                        retry_count += 1
                        wait_time = 2 ** retry_count
                        logger.warning(f"Retrying {func.__name__} in {wait_time}s (attempt {retry_count})")
                        time.sleep(wait_time)
                        continue

                    elif action == RecoveryAction.SKIP:
                        logger.info(f"Skipping {func.__name__} due to error")
                        return fallback_value

                    elif action == RecoveryAction.FALLBACK:
                        logger.info(f"Using fallback value for {func.__name__}")
                        return fallback_value

                    elif action == RecoveryAction.LOG_AND_CONTINUE:
                        return fallback_value

                    # ABORT 또는 기타
                    if reraise:
                        raise
                    return fallback_value

        return wrapper
    return decorator


class RetryContext:
    """재시도 컨텍스트 매니저"""

    def __init__(
        self,
        max_retries: int = 3,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
        backoff_factor: float = 2.0,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        logger: logging.Logger = None
    ):
        self.max_retries = max_retries
        self.exceptions = exceptions
        self.backoff_factor = backoff_factor
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.logger = logger or logging.getLogger(__name__)
        self.attempt = 0

    def __enter__(self):
        self.attempt = 0
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def should_retry(self, exception: Exception) -> bool:
        """재시도 여부 결정"""
        if not isinstance(exception, self.exceptions):
            return False

        self.attempt += 1
        if self.attempt > self.max_retries:
            return False

        delay = min(
            self.initial_delay * (self.backoff_factor ** (self.attempt - 1)),
            self.max_delay
        )

        self.logger.warning(
            f"Retry attempt {self.attempt}/{self.max_retries} in {delay:.1f}s"
        )
        time.sleep(delay)
        return True
