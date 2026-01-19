"""exceptions.py 테스트"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.exceptions import (
    SmartStoreError,
    ValidationError,
    ConfigurationError,
    DataImportError,
    AnalysisError,
    APIError,
    GeminiAPIError,
    SupabaseError,
    ReportGenerationError,
    RateLimitError,
    NetworkError,
    TimeoutError,
    ErrorCodes,
)


class TestSmartStoreError:
    """SmartStoreError 테스트"""

    def test_basic_error(self):
        """기본 에러"""
        error = SmartStoreError("테스트 에러")
        assert error.message == "테스트 에러"
        assert error.error_code == "SSA_UNKNOWN"

    def test_error_with_code(self):
        """에러 코드 포함"""
        error = SmartStoreError("테스트", error_code="CUSTOM_CODE")
        assert error.error_code == "CUSTOM_CODE"

    def test_error_with_details(self):
        """상세 정보 포함"""
        error = SmartStoreError(
            "테스트",
            details={"key": "value"}
        )
        assert error.details["key"] == "value"

    def test_to_dict(self):
        """딕셔너리 변환"""
        error = SmartStoreError(
            "테스트",
            error_code="TEST_CODE",
            details={"field": "test"}
        )
        d = error.to_dict()

        assert d["error_code"] == "TEST_CODE"
        assert d["message"] == "테스트"
        assert d["details"]["field"] == "test"
        assert d["type"] == "SmartStoreError"

    def test_str_representation(self):
        """문자열 표현"""
        error = SmartStoreError("테스트 에러", error_code="TEST")
        assert str(error) == "[TEST] 테스트 에러"


class TestValidationError:
    """ValidationError 테스트"""

    def test_validation_error(self):
        """검증 에러"""
        error = ValidationError(
            "필수값입니다",
            field="product_name",
            value=None
        )
        assert error.field == "product_name"
        assert error.value is None
        assert error.error_code == "SSA_VALIDATION"

    def test_validation_error_details(self):
        """검증 에러 상세"""
        error = ValidationError(
            "범위 초과",
            field="price",
            value=10000000
        )
        assert error.details["field"] == "price"
        assert "10000000" in error.details["value"]


class TestConfigurationError:
    """ConfigurationError 테스트"""

    def test_config_error(self):
        """설정 에러"""
        error = ConfigurationError(
            "API 키가 설정되지 않았습니다",
            config_key="GEMINI_API_KEY"
        )
        assert error.config_key == "GEMINI_API_KEY"
        assert error.error_code == "SSA_CONFIG"


class TestDataImportError:
    """DataImportError 테스트"""

    def test_import_error(self):
        """임포트 에러"""
        error = DataImportError(
            "파일을 찾을 수 없습니다",
            file_path="/path/to/file.xlsx",
            row_number=None
        )
        assert error.file_path == "/path/to/file.xlsx"
        assert error.error_code == "SSA_IMPORT"

    def test_import_error_with_row(self):
        """행 번호 포함 임포트 에러"""
        error = DataImportError(
            "파싱 오류",
            file_path="/path/to/file.xlsx",
            row_number=42
        )
        assert error.row_number == 42
        assert error.details["row_number"] == 42


class TestAnalysisError:
    """AnalysisError 테스트"""

    def test_analysis_error(self):
        """분석 에러"""
        error = AnalysisError(
            "분석 실패",
            analysis_type="margin",
            stage="calculation"
        )
        assert error.analysis_type == "margin"
        assert error.stage == "calculation"
        assert error.error_code == "SSA_ANALYSIS"


class TestAPIError:
    """APIError 테스트"""

    def test_api_error(self):
        """API 에러"""
        error = APIError(
            "API 호출 실패",
            status_code=500,
            endpoint="/api/analyze"
        )
        assert error.status_code == 500
        assert error.endpoint == "/api/analyze"
        assert error.error_code == "SSA_API"


class TestGeminiAPIError:
    """GeminiAPIError 테스트"""

    def test_gemini_error(self):
        """Gemini API 에러"""
        error = GeminiAPIError(
            "API 키 무효",
            status_code=401,
            model="gemini-1.5-flash"
        )
        assert error.model == "gemini-1.5-flash"
        assert error.status_code == 401
        assert error.error_code == "SSA_GEMINI"


class TestSupabaseError:
    """SupabaseError 테스트"""

    def test_supabase_error(self):
        """Supabase 에러"""
        error = SupabaseError(
            "레코드 삽입 실패",
            table="keywords",
            operation="insert"
        )
        assert error.table == "keywords"
        assert error.operation == "insert"
        assert error.error_code == "SSA_SUPABASE"


class TestReportGenerationError:
    """ReportGenerationError 테스트"""

    def test_report_error(self):
        """리포트 생성 에러"""
        error = ReportGenerationError(
            "템플릿을 찾을 수 없습니다",
            report_type="opportunity",
            template="markdown"
        )
        assert error.report_type == "opportunity"
        assert error.template == "markdown"
        assert error.error_code == "SSA_REPORT"


class TestRateLimitError:
    """RateLimitError 테스트"""

    def test_rate_limit_error(self):
        """속도 제한 에러"""
        error = RateLimitError(
            "API 속도 제한 초과",
            retry_after=60
        )
        assert error.retry_after == 60
        assert error.error_code == "SSA_RATE_LIMIT"


class TestTimeoutError:
    """TimeoutError 테스트"""

    def test_timeout_error(self):
        """타임아웃 에러"""
        error = TimeoutError(
            "요청 시간 초과",
            timeout_seconds=30
        )
        assert error.timeout_seconds == 30
        assert error.error_code == "SSA_TIMEOUT"


class TestErrorCodes:
    """ErrorCodes 상수 테스트"""

    def test_error_codes_exist(self):
        """에러 코드 존재 확인"""
        assert ErrorCodes.UNKNOWN == "SSA_UNKNOWN"
        assert ErrorCodes.VALIDATION == "SSA_VALIDATION"
        assert ErrorCodes.CONFIG == "SSA_CONFIG"
        assert ErrorCodes.IMPORT_FAILED == "SSA_IMPORT_FAILED"
        assert ErrorCodes.GEMINI_API_ERROR == "SSA_GEMINI"
        assert ErrorCodes.SUPABASE_ERROR == "SSA_SUPABASE"
        assert ErrorCodes.RATE_LIMITED == "SSA_RATE_LIMIT"
        assert ErrorCodes.TIMEOUT == "SSA_TIMEOUT"


class TestErrorChaining:
    """에러 체이닝 테스트"""

    def test_error_with_cause(self):
        """원인 에러 포함"""
        original = ValueError("원본 에러")
        error = SmartStoreError(
            "래핑된 에러",
            cause=original
        )
        assert error.cause == original
        assert isinstance(error.cause, ValueError)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
