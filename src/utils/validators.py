"""
validators.py - 데이터 검증 유틸리티 (v3.2)

테스트 호환성 개선:
- ValidationSeverity enum 추가
- DataValidator 메서드 확장
- BatchValidator 클래스 추가
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum


class ValidationError(Exception):
    """검증 오류"""
    pass


class ValidationSeverity(Enum):
    """검증 심각도"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """검증 이슈"""
    field: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR


@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=list)

    def add_error(self, field_name: str, message: str):
        """에러 추가"""
        self.is_valid = False
        self.errors.append(message)
        self.issues.append(ValidationIssue(field=field_name, message=message, severity=ValidationSeverity.ERROR))

    def add_warning(self, field_name: str, message: str):
        """경고 추가"""
        self.warnings.append(message)
        self.issues.append(ValidationIssue(field=field_name, message=message, severity=ValidationSeverity.WARNING))

    def merge(self, other: "ValidationResult"):
        """다른 결과 병합"""
        if not other.is_valid:
            self.is_valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.issues.extend(other.issues)


# 허용된 카테고리 목록
VALID_CATEGORIES = [
    "가구/인테리어",
    "캠핑/레저",
    "의류/패션",
    "전자기기",
    "생활용품",
    "주방용품",
    "화장품",
    "기타",
]


class DataValidator:
    """데이터 검증기"""

    @staticmethod
    def validate_required(value: Any, field_name: str) -> Optional[str]:
        """필수값 검증 (레거시)"""
        if value is None:
            return f"{field_name}은(는) 필수입니다."
        if isinstance(value, str) and not value.strip():
            return f"{field_name}은(는) 비어있을 수 없습니다."
        return None

    @staticmethod
    def validate_positive(value: float, field_name: str) -> Optional[str]:
        """양수 검증 (레거시)"""
        if value is None:
            return None
        if value < 0:
            return f"{field_name}은(는) 0 이상이어야 합니다."
        return None

    @staticmethod
    def validate_range(value: float, min_val: float, max_val: float, field_name: str) -> Optional[str]:
        """범위 검증 (레거시)"""
        if value is None:
            return None
        if value < min_val or value > max_val:
            return f"{field_name}은(는) {min_val}~{max_val} 범위여야 합니다."
        return None

    # === 새로운 API (테스트 호환) ===

    @staticmethod
    def required(value: Any, field_name: str) -> ValidationResult:
        """필수값 검증"""
        result = ValidationResult()
        if value is None:
            result.add_error(field_name, f"{field_name}은(는) 필수입니다.")
        elif isinstance(value, str) and not value.strip():
            result.add_error(field_name, f"{field_name}은(는) 비어있을 수 없습니다.")
        return result

    @staticmethod
    def positive_number(value: float, field_name: str) -> ValidationResult:
        """양수 검증 (0 제외)"""
        result = ValidationResult()
        if value is None:
            return result
        if value <= 0:
            result.add_error(field_name, f"{field_name}은(는) 0보다 커야 합니다.")
        return result

    @staticmethod
    def non_negative(value: float, field_name: str) -> ValidationResult:
        """0 이상 검증"""
        result = ValidationResult()
        if value is None:
            return result
        if value < 0:
            result.add_error(field_name, f"{field_name}은(는) 0 이상이어야 합니다.")
        return result

    @staticmethod
    def range_check(value: float, field_name: str, min_val: float, max_val: float) -> ValidationResult:
        """범위 검증"""
        result = ValidationResult()
        if value is None:
            return result
        if value < min_val or value > max_val:
            result.add_error(field_name, f"{field_name}은(는) {min_val}~{max_val} 범위여야 합니다.")
        return result

    @staticmethod
    def string_length(value: str, field_name: str, min_len: int, max_len: int) -> ValidationResult:
        """문자열 길이 검증"""
        result = ValidationResult()
        if value is None:
            return result
        if len(value) < min_len:
            result.add_error(field_name, f"{field_name}은(는) 최소 {min_len}자 이상이어야 합니다.")
        elif len(value) > max_len:
            result.add_error(field_name, f"{field_name}은(는) 최대 {max_len}자 이하여야 합니다.")
        return result

    @staticmethod
    def one_of(value: Any, field_name: str, allowed: List[Any]) -> ValidationResult:
        """허용값 검증"""
        result = ValidationResult()
        if value is None:
            return result
        if value not in allowed:
            result.add_error(field_name, f"{field_name}은(는) {allowed} 중 하나여야 합니다.")
        return result

    @staticmethod
    def dimensions(dims: Tuple[float, ...]) -> ValidationResult:
        """박스 크기 검증 (가로, 세로, 높이)"""
        result = ValidationResult()
        if dims is None:
            return result
        if len(dims) != 3:
            result.add_error("dimensions", "박스 크기는 (가로, 세로, 높이) 3개 값이 필요합니다.")
            return result
        for i, d in enumerate(dims):
            if d <= 0:
                result.add_error("dimensions", f"박스 크기의 {i+1}번째 값은 0보다 커야 합니다.")
        # 큰 박스 경고
        if all(d >= 150 for d in dims):
            result.add_warning("dimensions", "박스 크기가 매우 큽니다. 배송비가 높을 수 있습니다.")
        return result

    @staticmethod
    def price_krw(value: float, field_name: str) -> ValidationResult:
        """원화 가격 검증"""
        result = ValidationResult()
        if value is None:
            return result
        if value < 0:
            result.add_error(field_name, f"{field_name}은(는) 0 이상이어야 합니다.")
        elif value < 1000:
            result.add_warning(field_name, f"{field_name}이(가) 1,000원 미만입니다. 확인해주세요.")
        return result


def validate_sourcing_input(data: Dict[str, Any]) -> ValidationResult:
    """소싱 입력 데이터 검증"""
    result = ValidationResult()

    # 필수 필드
    required_fields = ["product_name", "wholesale_price_cny", "target_price_krw"]
    for field_name in required_fields:
        r = DataValidator.required(data.get(field_name), field_name)
        result.merge(r)

    # 숫자 필드
    numeric_fields = ["wholesale_price_cny", "actual_weight_kg", "target_price_krw"]
    for field_name in numeric_fields:
        if field_name in data and data[field_name] is not None:
            r = DataValidator.positive_number(data.get(field_name, 0), field_name)
            result.merge(r)

    # MOQ 검증
    moq = data.get("moq", 0)
    if moq is not None:
        r = DataValidator.non_negative(moq, "moq")
        result.merge(r)
        if moq >= 50:
            result.add_warning("moq", "MOQ가 50개 이상입니다. 재고 리스크에 유의하세요.")

    # 박스 크기 검증
    dims = data.get("dimensions")
    if dims is not None:
        r = DataValidator.dimensions(dims)
        result.merge(r)

    # 카테고리 검증
    category = data.get("category")
    if category is not None:
        r = DataValidator.one_of(category, "category", VALID_CATEGORIES)
        result.merge(r)

    return result


def validate_keyword_data(data: Dict[str, Any]) -> ValidationResult:
    """키워드 데이터 검증"""
    result = ValidationResult()

    # 키워드 필수
    r = DataValidator.required(data.get("keyword"), "keyword")
    result.merge(r)

    # 검색량 검증
    search_volume = data.get("monthly_search_volume", 0)
    if search_volume is not None:
        r = DataValidator.non_negative(search_volume, "monthly_search_volume")
        result.merge(r)
        if 0 < search_volume < 1000:
            result.add_warning("monthly_search_volume", "검색량이 1,000 미만입니다.")

    # 경쟁강도 검증 (0~100 또는 0~1)
    competition_rate = data.get("competition_rate")
    if competition_rate is not None:
        if competition_rate > 1:
            # 0~100 스케일로 가정
            r = DataValidator.range_check(competition_rate, "competition_rate", 0, 100)
        else:
            # 0~1 스케일로 가정
            r = DataValidator.range_check(competition_rate, "competition_rate", 0, 1)
        result.merge(r)

    return result


def validate_review_data(data: Dict[str, Any]) -> ValidationResult:
    """리뷰 데이터 검증"""
    result = ValidationResult()

    # 내용 필수
    r = DataValidator.required(data.get("content"), "content")
    result.merge(r)

    # 평점 검증
    rating = data.get("rating")
    if rating is not None:
        r = DataValidator.range_check(rating, "rating", 1, 5)
        result.merge(r)

    return result


class BatchValidator:
    """배치 검증기"""

    def __init__(self, validator_func: Callable[[Dict], ValidationResult]):
        """
        Args:
            validator_func: 단일 항목 검증 함수
        """
        self.validator_func = validator_func
        self._results: List[Tuple[int, ValidationResult]] = []

    def validate_batch(self, items: List[Dict]) -> ValidationResult:
        """배치 검증"""
        self._results = []
        overall = ValidationResult()

        for i, item in enumerate(items):
            r = self.validator_func(item)
            self._results.append((i, r))
            overall.merge(r)

        return overall

    def get_invalid_indices(self) -> List[int]:
        """무효한 항목 인덱스 반환"""
        return [i for i, r in self._results if not r.is_valid]

    def get_valid_items(self, items: List[Dict]) -> List[Dict]:
        """유효한 항목만 반환"""
        # validate_batch가 호출되지 않았으면 먼저 실행
        if not self._results:
            self.validate_batch(items)
        invalid_indices = set(self.get_invalid_indices())
        return [item for i, item in enumerate(items) if i not in invalid_indices]
