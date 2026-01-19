"""
커스텀 예외 클래스

Smart Store Agent에서 사용하는 모든 커스텀 예외를 정의
"""

from typing import Optional, Dict, Any


class SmartStoreError(Exception):
    """기본 예외 클래스"""

    def __init__(
        self,
        message: str,
        error_code: str = None,
        details: Dict[str, Any] = None,
        cause: Exception = None
    ):
        """
        Args:
            message: 에러 메시지
            error_code: 에러 코드
            details: 추가 상세 정보
            cause: 원인 예외
        """
        self.message = message
        self.error_code = error_code or self._default_code()
        self.details = details or {}
        self.cause = cause
        super().__init__(self.message)

    def _default_code(self) -> str:
        return "SSA_UNKNOWN"

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "type": self.__class__.__name__
        }

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


class ValidationError(SmartStoreError):
    """데이터 검증 오류"""

    def __init__(
        self,
        message: str,
        field: str = None,
        value: Any = None,
        **kwargs
    ):
        self.field = field
        self.value = value
        details = kwargs.pop("details", {})
        details["field"] = field
        details["value"] = str(value)[:100]  # 값 길이 제한
        super().__init__(message, details=details, **kwargs)

    def _default_code(self) -> str:
        return "SSA_VALIDATION"


class ConfigurationError(SmartStoreError):
    """설정 오류"""

    def __init__(
        self,
        message: str,
        config_key: str = None,
        **kwargs
    ):
        self.config_key = config_key
        details = kwargs.pop("details", {})
        details["config_key"] = config_key
        super().__init__(message, details=details, **kwargs)

    def _default_code(self) -> str:
        return "SSA_CONFIG"


class DataImportError(SmartStoreError):
    """데이터 임포트 오류"""

    def __init__(
        self,
        message: str,
        file_path: str = None,
        row_number: int = None,
        **kwargs
    ):
        self.file_path = file_path
        self.row_number = row_number
        details = kwargs.pop("details", {})
        details["file_path"] = file_path
        details["row_number"] = row_number
        super().__init__(message, details=details, **kwargs)

    def _default_code(self) -> str:
        return "SSA_IMPORT"


class AnalysisError(SmartStoreError):
    """분석 오류"""

    def __init__(
        self,
        message: str,
        analysis_type: str = None,
        stage: str = None,
        **kwargs
    ):
        self.analysis_type = analysis_type
        self.stage = stage
        details = kwargs.pop("details", {})
        details["analysis_type"] = analysis_type
        details["stage"] = stage
        super().__init__(message, details=details, **kwargs)

    def _default_code(self) -> str:
        return "SSA_ANALYSIS"


class APIError(SmartStoreError):
    """API 호출 오류 (기본)"""

    def __init__(
        self,
        message: str,
        status_code: int = None,
        response_body: str = None,
        endpoint: str = None,
        **kwargs
    ):
        self.status_code = status_code
        self.response_body = response_body
        self.endpoint = endpoint
        details = kwargs.pop("details", {})
        details["status_code"] = status_code
        details["endpoint"] = endpoint
        super().__init__(message, details=details, **kwargs)

    def _default_code(self) -> str:
        return "SSA_API"


class GeminiAPIError(APIError):
    """Gemini API 오류"""

    def __init__(
        self,
        message: str,
        model: str = None,
        prompt_tokens: int = None,
        **kwargs
    ):
        self.model = model
        self.prompt_tokens = prompt_tokens
        details = kwargs.pop("details", {})
        details["model"] = model
        details["prompt_tokens"] = prompt_tokens
        super().__init__(message, details=details, **kwargs)

    def _default_code(self) -> str:
        return "SSA_GEMINI"


class SupabaseError(APIError):
    """Supabase 오류"""

    def __init__(
        self,
        message: str,
        table: str = None,
        operation: str = None,
        **kwargs
    ):
        self.table = table
        self.operation = operation
        details = kwargs.pop("details", {})
        details["table"] = table
        details["operation"] = operation
        super().__init__(message, details=details, **kwargs)

    def _default_code(self) -> str:
        return "SSA_SUPABASE"


class ReportGenerationError(SmartStoreError):
    """리포트 생성 오류"""

    def __init__(
        self,
        message: str,
        report_type: str = None,
        template: str = None,
        **kwargs
    ):
        self.report_type = report_type
        self.template = template
        details = kwargs.pop("details", {})
        details["report_type"] = report_type
        details["template"] = template
        super().__init__(message, details=details, **kwargs)

    def _default_code(self) -> str:
        return "SSA_REPORT"


class RateLimitError(APIError):
    """API 속도 제한 오류"""

    def __init__(
        self,
        message: str,
        retry_after: int = None,
        **kwargs
    ):
        self.retry_after = retry_after
        details = kwargs.pop("details", {})
        details["retry_after"] = retry_after
        super().__init__(message, details=details, **kwargs)

    def _default_code(self) -> str:
        return "SSA_RATE_LIMIT"


class NetworkError(SmartStoreError):
    """네트워크 오류"""

    def _default_code(self) -> str:
        return "SSA_NETWORK"


class TimeoutError(SmartStoreError):
    """타임아웃 오류"""

    def __init__(
        self,
        message: str,
        timeout_seconds: int = None,
        **kwargs
    ):
        self.timeout_seconds = timeout_seconds
        details = kwargs.pop("details", {})
        details["timeout_seconds"] = timeout_seconds
        super().__init__(message, details=details, **kwargs)

    def _default_code(self) -> str:
        return "SSA_TIMEOUT"


# 에러 코드 상수
class ErrorCodes:
    """에러 코드 상수"""

    # 일반
    UNKNOWN = "SSA_UNKNOWN"
    VALIDATION = "SSA_VALIDATION"
    CONFIG = "SSA_CONFIG"

    # 데이터
    IMPORT_FAILED = "SSA_IMPORT_FAILED"
    IMPORT_PARSE_ERROR = "SSA_IMPORT_PARSE"
    IMPORT_INVALID_FORMAT = "SSA_IMPORT_FORMAT"

    # 분석
    ANALYSIS_FAILED = "SSA_ANALYSIS_FAILED"
    MARGIN_CALC_FAILED = "SSA_MARGIN_CALC"
    KEYWORD_FILTER_FAILED = "SSA_KEYWORD_FILTER"

    # API
    API_ERROR = "SSA_API"
    GEMINI_API_ERROR = "SSA_GEMINI"
    GEMINI_QUOTA_EXCEEDED = "SSA_GEMINI_QUOTA"
    SUPABASE_ERROR = "SSA_SUPABASE"
    SUPABASE_AUTH_FAILED = "SSA_SUPABASE_AUTH"

    # 리포트
    REPORT_FAILED = "SSA_REPORT_FAILED"
    TEMPLATE_NOT_FOUND = "SSA_TEMPLATE_NOT_FOUND"

    # 네트워크
    NETWORK_ERROR = "SSA_NETWORK"
    TIMEOUT = "SSA_TIMEOUT"
    RATE_LIMITED = "SSA_RATE_LIMIT"
