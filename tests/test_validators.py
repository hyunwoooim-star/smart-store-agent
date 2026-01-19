"""validators.py 테스트"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.validators import (
    DataValidator,
    ValidationError,
    ValidationResult,
    ValidationSeverity,
    validate_sourcing_input,
    validate_keyword_data,
    validate_review_data,
    BatchValidator,
)


class TestDataValidator:
    """DataValidator 테스트"""

    def test_required_with_value(self):
        """필수값 검증 - 값 있음"""
        result = DataValidator.required("test", "field")
        assert result.is_valid == True
        assert len(result.errors) == 0

    def test_required_without_value(self):
        """필수값 검증 - 값 없음"""
        result = DataValidator.required(None, "field")
        assert result.is_valid == False
        assert len(result.errors) == 1

    def test_required_empty_string(self):
        """필수값 검증 - 빈 문자열"""
        result = DataValidator.required("", "field")
        assert result.is_valid == False

    def test_positive_number_valid(self):
        """양수 검증 - 유효"""
        result = DataValidator.positive_number(10, "field")
        assert result.is_valid == True

    def test_positive_number_zero(self):
        """양수 검증 - 0"""
        result = DataValidator.positive_number(0, "field")
        assert result.is_valid == False

    def test_positive_number_negative(self):
        """양수 검증 - 음수"""
        result = DataValidator.positive_number(-5, "field")
        assert result.is_valid == False

    def test_non_negative_zero(self):
        """0 이상 검증 - 0"""
        result = DataValidator.non_negative(0, "field")
        assert result.is_valid == True

    def test_non_negative_negative(self):
        """0 이상 검증 - 음수"""
        result = DataValidator.non_negative(-1, "field")
        assert result.is_valid == False

    def test_range_check_valid(self):
        """범위 검증 - 유효"""
        result = DataValidator.range_check(50, "field", 0, 100)
        assert result.is_valid == True

    def test_range_check_below_min(self):
        """범위 검증 - 최소값 미달"""
        result = DataValidator.range_check(-5, "field", 0, 100)
        assert result.is_valid == False

    def test_range_check_above_max(self):
        """범위 검증 - 최대값 초과"""
        result = DataValidator.range_check(150, "field", 0, 100)
        assert result.is_valid == False

    def test_string_length_valid(self):
        """문자열 길이 검증 - 유효"""
        result = DataValidator.string_length("hello", "field", 1, 10)
        assert result.is_valid == True

    def test_string_length_too_short(self):
        """문자열 길이 검증 - 너무 짧음"""
        result = DataValidator.string_length("hi", "field", 5, 10)
        assert result.is_valid == False

    def test_string_length_too_long(self):
        """문자열 길이 검증 - 너무 김"""
        result = DataValidator.string_length("hello world", "field", 1, 5)
        assert result.is_valid == False

    def test_one_of_valid(self):
        """허용값 검증 - 유효"""
        result = DataValidator.one_of("apple", "field", ["apple", "banana", "orange"])
        assert result.is_valid == True

    def test_one_of_invalid(self):
        """허용값 검증 - 무효"""
        result = DataValidator.one_of("grape", "field", ["apple", "banana", "orange"])
        assert result.is_valid == False

    def test_dimensions_valid(self):
        """박스 크기 검증 - 유효"""
        result = DataValidator.dimensions((80, 20, 15))
        assert result.is_valid == True

    def test_dimensions_invalid_count(self):
        """박스 크기 검증 - 값 개수 오류"""
        result = DataValidator.dimensions((80, 20))
        assert result.is_valid == False

    def test_dimensions_negative(self):
        """박스 크기 검증 - 음수"""
        result = DataValidator.dimensions((80, -20, 15))
        assert result.is_valid == False

    def test_dimensions_large_warning(self):
        """박스 크기 검증 - 큰 크기 경고"""
        result = DataValidator.dimensions((200, 200, 200))
        assert result.is_valid == True
        assert len(result.warnings) == 1

    def test_price_krw_valid(self):
        """원화 가격 검증 - 유효"""
        result = DataValidator.price_krw(45000, "field")
        assert result.is_valid == True

    def test_price_krw_negative(self):
        """원화 가격 검증 - 음수"""
        result = DataValidator.price_krw(-1000, "field")
        assert result.is_valid == False

    def test_price_krw_low_warning(self):
        """원화 가격 검증 - 낮은 가격 경고"""
        result = DataValidator.price_krw(500, "field")
        assert result.is_valid == True
        assert len(result.warnings) == 1


class TestValidationResult:
    """ValidationResult 테스트"""

    def test_add_error(self):
        """에러 추가"""
        result = ValidationResult(is_valid=True)
        result.add_error("field", "error message")

        assert result.is_valid == False
        assert len(result.errors) == 1

    def test_add_warning(self):
        """경고 추가"""
        result = ValidationResult(is_valid=True)
        result.add_warning("field", "warning message")

        assert result.is_valid == True
        assert len(result.warnings) == 1

    def test_merge(self):
        """결과 병합"""
        result1 = ValidationResult(is_valid=True)
        result1.add_warning("field1", "warning")

        result2 = ValidationResult(is_valid=True)
        result2.add_error("field2", "error")

        result1.merge(result2)

        assert result1.is_valid == False
        assert len(result1.issues) == 2


class TestSourcingInputValidation:
    """소싱 입력 검증 테스트"""

    def test_valid_input(self):
        """유효한 입력"""
        data = {
            "product_name": "캠핑의자",
            "wholesale_price_cny": 45,
            "actual_weight_kg": 2.5,
            "target_price_krw": 45000,
            "moq": 50,
            "dimensions": (80, 20, 15),
            "category": "캠핑/레저"
        }
        result = validate_sourcing_input(data)
        assert result.is_valid == True

    def test_missing_required(self):
        """필수값 누락"""
        data = {
            "wholesale_price_cny": 45,
        }
        result = validate_sourcing_input(data)
        assert result.is_valid == False
        assert len(result.errors) >= 1

    def test_invalid_category(self):
        """잘못된 카테고리"""
        data = {
            "product_name": "테스트",
            "wholesale_price_cny": 45,
            "actual_weight_kg": 2.5,
            "target_price_krw": 45000,
            "category": "존재하지않는카테고리"
        }
        result = validate_sourcing_input(data)
        assert result.is_valid == False


class TestKeywordDataValidation:
    """키워드 데이터 검증 테스트"""

    def test_valid_keyword(self):
        """유효한 키워드"""
        data = {
            "keyword": "캠핑의자",
            "monthly_search_volume": 45000,
            "competition_rate": 0.56,
            "opportunity_score": 8.0
        }
        result = validate_keyword_data(data)
        assert result.is_valid == True

    def test_missing_keyword(self):
        """키워드 누락"""
        data = {
            "monthly_search_volume": 45000,
        }
        result = validate_keyword_data(data)
        assert result.is_valid == False

    def test_invalid_competition_rate(self):
        """잘못된 경쟁강도"""
        data = {
            "keyword": "테스트",
            "competition_rate": 150,  # 100 초과
        }
        result = validate_keyword_data(data)
        assert result.is_valid == False


class TestReviewDataValidation:
    """리뷰 데이터 검증 테스트"""

    def test_valid_review(self):
        """유효한 리뷰"""
        data = {
            "content": "품질이 좋아요",
            "rating": 5
        }
        result = validate_review_data(data)
        assert result.is_valid == True

    def test_missing_content(self):
        """내용 누락"""
        data = {
            "rating": 5
        }
        result = validate_review_data(data)
        assert result.is_valid == False

    def test_invalid_rating(self):
        """잘못된 평점"""
        data = {
            "content": "테스트",
            "rating": 10,  # 5 초과
        }
        result = validate_review_data(data)
        assert result.is_valid == False


class TestBatchValidator:
    """배치 검증 테스트"""

    def test_batch_validation(self):
        """배치 검증"""
        items = [
            {"keyword": "테스트1", "monthly_search_volume": 1000},
            {"keyword": "", "monthly_search_volume": 2000},  # 무효
            {"keyword": "테스트3", "monthly_search_volume": 3000},
        ]

        batch = BatchValidator(validate_keyword_data)
        result = batch.validate_batch(items)

        # 하나가 무효이므로 전체 무효
        assert result.is_valid == False
        assert len(batch.get_invalid_indices()) == 1

    def test_get_valid_items(self):
        """유효한 항목만 반환"""
        items = [
            {"keyword": "테스트1", "monthly_search_volume": 1000},
            {"keyword": "", "monthly_search_volume": 2000},
            {"keyword": "테스트3", "monthly_search_volume": 3000},
        ]

        batch = BatchValidator(validate_keyword_data)
        valid_items = batch.get_valid_items(items)

        assert len(valid_items) == 2


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
