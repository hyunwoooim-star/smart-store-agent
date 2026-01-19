"""
logging_config.py - 로깅 설정 (v3.1 Enhanced)

기능:
- 구조화된 로깅 (JSON 형식 지원)
- 성능 추적 (실행 시간 측정)
- 컨텍스트 로깅
- 로그 레벨별 파일 분리
"""

import os
import sys
import json
import logging
import functools
import time
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from dataclasses import dataclass, asdict


# 로그 디렉토리
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


class JSONFormatter(logging.Formatter):
    """JSON 형식 로그 포맷터"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 추가 컨텍스트
        if hasattr(record, "context"):
            log_data["context"] = record.context

        # 예외 정보
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """컬러 콘솔 로그 포맷터"""

    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[41m",   # Red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        # 컬러 적용
        color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname:8}{self.RESET}"

        # 기본 포맷
        result = super().format(record)

        return result


@dataclass
class LogContext:
    """로그 컨텍스트"""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    product_name: Optional[str] = None
    operation: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                result[key] = value
        return result


class ContextAdapter(logging.LoggerAdapter):
    """컨텍스트 포함 로거 어댑터"""

    def process(self, msg, kwargs):
        # 컨텍스트 추가
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        if hasattr(self.extra, "to_dict"):
            kwargs["extra"]["context"] = self.extra.to_dict()
        elif isinstance(self.extra, dict):
            kwargs["extra"]["context"] = self.extra

        return msg, kwargs


class PerformanceLogger:
    """성능 추적 로거"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    @contextmanager
    def track(self, operation: str, **context):
        """
        작업 실행 시간 추적

        사용법:
            with perf_logger.track("마진 계산", product="캠핑의자"):
                calculate_margin()
        """
        start_time = time.perf_counter()
        self.logger.info(f"시작: {operation}", extra={"context": context})

        try:
            yield
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            self.logger.error(
                f"실패: {operation} ({elapsed:.3f}s) - {str(e)}",
                extra={"context": {**context, "error": str(e), "duration_ms": elapsed * 1000}},
                exc_info=True
            )
            raise
        else:
            elapsed = time.perf_counter() - start_time
            self.logger.info(
                f"완료: {operation} ({elapsed:.3f}s)",
                extra={"context": {**context, "duration_ms": elapsed * 1000}}
            )

    def timed(self, operation: str = None):
        """
        함수 실행 시간 측정 데코레이터

        사용법:
            @perf_logger.timed("마진 계산")
            def calculate_margin():
                pass
        """
        def decorator(func: Callable):
            op_name = operation or func.__name__

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                with self.track(op_name):
                    return func(*args, **kwargs)

            return wrapper
        return decorator


def setup_logging(
    name: str = "smart_store",
    level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = True,
    json_format: bool = False,
    color_output: bool = True,
) -> logging.Logger:
    """
    로깅 설정

    Args:
        name: 로거 이름
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: 파일 로깅 여부
        log_to_console: 콘솔 로깅 여부
        json_format: JSON 형식 사용 여부
        color_output: 컬러 출력 사용 여부

    Returns:
        설정된 로거
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # 기존 핸들러 제거
    logger.handlers.clear()

    # 콘솔 핸들러
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)

        if json_format:
            console_handler.setFormatter(JSONFormatter())
        elif color_output and sys.stdout.isatty():
            console_handler.setFormatter(ColoredFormatter(
                fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                datefmt="%H:%M:%S"
            ))
        else:
            console_handler.setFormatter(logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            ))

        logger.addHandler(console_handler)

    # 파일 핸들러
    if log_to_file:
        # 일반 로그 (일별 로테이션)
        log_file = LOGS_DIR / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )

        if json_format:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(module)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            ))

        logger.addHandler(file_handler)

        # 에러 전용 로그
        error_file = LOGS_DIR / f"{name}_errors.log"
        error_handler = RotatingFileHandler(
            error_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(module)s:%(lineno)d\n%(message)s\n",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(error_handler)

    return logger


# 기본 로거
default_logger = setup_logging()


def get_logger(name: str = None) -> logging.Logger:
    """로거 반환"""
    if name:
        return setup_logging(name)
    return default_logger


def get_context_logger(
    name: str = None,
    context: LogContext = None,
    **kwargs
) -> ContextAdapter:
    """컨텍스트 포함 로거 반환"""
    logger = get_logger(name)
    ctx = context if context else LogContext(**kwargs)
    return ContextAdapter(logger, ctx)


def get_perf_logger(name: str = None) -> PerformanceLogger:
    """성능 추적 로거 반환"""
    logger = get_logger(name)
    return PerformanceLogger(logger)


# --- 테스트 ---
if __name__ == "__main__":
    # 기본 로거 테스트
    logger = get_logger("test")
    logger.debug("디버그 메시지")
    logger.info("정보 메시지")
    logger.warning("경고 메시지")
    logger.error("에러 메시지")

    # 컨텍스트 로거 테스트
    ctx_logger = get_context_logger("test.context", product_name="캠핑의자", operation="margin_calc")
    ctx_logger.info("컨텍스트 포함 로그")

    # 성능 추적 테스트
    perf_logger = get_perf_logger("test.perf")

    with perf_logger.track("테스트 작업", test_id=123):
        time.sleep(0.1)

    @perf_logger.timed("함수 실행")
    def sample_function():
        time.sleep(0.05)
        return "완료"

    sample_function()

    print(f"\n로그 파일 위치: {LOGS_DIR}")
