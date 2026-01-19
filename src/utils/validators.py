"""
validators.py - 데이터 검증 유틸리티 (v3.1)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class ValidationError(Exception):
    """검증 오류"""
    pass


@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class DataValidator:
    """데이터 검증기"""

    @staticmethod
    def validate_required(value: Any, field_name: str) -> Optional[str]:
        """필수값 검증"""
        if value is None:
            return f"{field_name}은(는) 필수입니다."
        if isinstance(value, str) and not value.strip():
            return f"{field_name}은(는) 비어있을 수 없습니다."
        return None

    @staticmethod
    def validate_positive(value: float, field_name: str) -> Optional[str]:
        """양수 검증"""
        if value is None:
            return None
        if value < 0:
            return f"{field_name}은(는) 0 이상이어야 합니다."
        return None

    @staticmethod
    def validate_range(value: float, min_val: float, max_val: float, field_name: str) -> Optional[str]:
        """범위 검증"""
        if value is None:
            return None
        if value < min_val or value > max_val:
            return f"{field_name}은(는) {min_val}~{max_val} 범위여야 합니다."
        return None


def validate_sourcing_input(data: Dict[str, Any]) -> ValidationResult:
    """소싱 입력 데이터 검증"""
    errors = []
    warnings = []
    validator = DataValidator()

    required_fields = ["product_name", "wholesale_price_cny", "target_price_krw"]
    for field in required_fields:
        error = validator.validate_required(data.get(field), field)
        if error:
            errors.append(error)

    numeric_fields = ["wholesale_price_cny", "actual_weight_kg", "target_price_krw", "moq"]
    for field in numeric_fields:
        if field in data:
            error = validator.validate_positive(data.get(field, 0), field)
            if error:
                errors.append(error)

    if data.get("moq", 0) >= 50:
        warnings.append("MOQ가 50개 이상입니다. 재고 리스크에 유의하세요.")

    return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_keyword_data(data: Dict[str, Any]) -> ValidationResult:
    """키워드 데이터 검증"""
    errors = []
    warnings = []
    validator = DataValidator()

    error = validator.validate_required(data.get("keyword"), "keyword")
    if error:
        errors.append(error)

    search_volume = data.get("monthly_search_volume", 0)
    if search_volume < 0:
        errors.append("검색량은 0 이상이어야 합니다.")
    elif search_volume < 1000:
        warnings.append("검색량이 1,000 미만입니다.")

    return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_review_data(data: Dict[str, Any]) -> ValidationResult:
    """리뷰 데이터 검증"""
    errors = []
    warnings = []
    validator = DataValidator()

    error = validator.validate_required(data.get("content"), "content")
    if error:
        errors.append(error)

    rating = data.get("rating")
    if rating is not None:
        error = validator.validate_range(rating, 1, 5, "rating")
        if error:
            errors.append(error)

    return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
