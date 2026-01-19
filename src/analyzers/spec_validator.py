"""
spec_validator.py - AI 생성 카피 ↔ 실제 스펙 검증 (v3.1)

핵심 기능:
1. AI 생성 카피와 실제 스펙 일치 검증
2. 허위/과장 광고 방지
3. 검증 리포트 생성
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class ValidationStatus(Enum):
    """검증 상태"""
    PASS = "pass"           # 검증 통과
    WARNING = "warning"     # 경고 (확인 필요)
    FAIL = "fail"           # 검증 실패 (수정 필요)
    UNVERIFIED = "unverified"  # 검증 불가 (스펙 정보 없음)


@dataclass
class SpecData:
    """상품 스펙 데이터"""
    product_name: str
    category: str

    # 기본 스펙
    weight_kg: Optional[float] = None
    dimensions_cm: Optional[Tuple[float, float, float]] = None  # 가로, 세로, 높이
    material: Optional[str] = None
    color: Optional[str] = None
    origin: Optional[str] = None          # 원산지

    # 성능 스펙
    max_load_kg: Optional[float] = None   # 최대 하중
    waterproof_rating: Optional[str] = None  # 방수 등급
    battery_capacity: Optional[str] = None
    power_consumption: Optional[str] = None

    # 인증/규격
    certifications: List[str] = field(default_factory=list)  # KC, CE 등

    # 추가 스펙 (딕셔너리)
    extra_specs: Dict[str, str] = field(default_factory=dict)


@dataclass
class CopyClaimData:
    """카피에서 추출한 주장"""
    claim_text: str         # 원본 카피 문구
    claim_type: str         # "수치", "성능", "품질", "비교" 등
    extracted_value: Optional[str] = None  # 추출된 값


@dataclass
class ValidationItem:
    """개별 검증 항목"""
    claim: CopyClaimData
    status: ValidationStatus
    spec_reference: Optional[str] = None  # 참조한 스펙
    reason: str = ""
    suggestion: str = ""


@dataclass
class ValidationResult:
    """검증 결과"""
    product_name: str
    total_claims: int
    passed: int
    warnings: int
    failed: int
    unverified: int

    items: List[ValidationItem] = field(default_factory=list)
    overall_status: ValidationStatus = ValidationStatus.PASS

    # 리스크 평가
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH
    risk_reasons: List[str] = field(default_factory=list)


class SpecValidator:
    """스펙 검증기"""

    # 수치 관련 패턴
    NUMBER_PATTERNS = {
        "weight": [
            r"(\d+(?:\.\d+)?)\s*(?:kg|킬로|키로)",
            r"(\d+(?:\.\d+)?)\s*(?:g|그램)",
            r"무게\s*(\d+(?:\.\d+)?)",
        ],
        "dimension": [
            r"(\d+)\s*[xX×]\s*(\d+)\s*[xX×]\s*(\d+)",
            r"가로\s*(\d+).*세로\s*(\d+).*높이\s*(\d+)",
        ],
        "load": [
            r"(\d+)\s*(?:kg|킬로).*(?:하중|지지|견딤)",
            r"최대\s*(\d+)\s*(?:kg|킬로)",
        ],
        "percentage": [
            r"(\d+)\s*%",
        ],
        "time": [
            r"(\d+)\s*시간",
            r"(\d+)\s*분",
        ],
    }

    # 과장 표현 패턴 (경고 대상)
    EXAGGERATION_PATTERNS = [
        r"최고급",
        r"최상의",
        r"완벽한",
        r"100%",
        r"무조건",
        r"절대",
        r"세계 최초",
        r"국내 유일",
        r"1위",
        r"가장 [가-힣]+",
    ]

    # 비교 표현 패턴 (검증 필요)
    COMPARISON_PATTERNS = [
        r"타사 대비",
        r"기존 제품보다",
        r"(\d+)\s*배",
        r"더\s+[가-힣]+",
        r"보다\s+[가-힣]+",
    ]

    # 성능 주장 패턴
    PERFORMANCE_PATTERNS = [
        r"방수",
        r"방진",
        r"내구성",
        r"견고",
        r"튼튼",
        r"가벼운|경량|초경량",
        r"대용량",
        r"고속",
        r"저소음",
    ]

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """정규식 패턴 컴파일"""
        self.exaggeration_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.EXAGGERATION_PATTERNS
        ]
        self.comparison_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.COMPARISON_PATTERNS
        ]
        self.performance_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.PERFORMANCE_PATTERNS
        ]

    def _extract_claims(self, copy_text: str) -> List[CopyClaimData]:
        """카피에서 주장 추출"""
        claims = []

        # 문장 단위 분리
        sentences = re.split(r'[.!?\n]', copy_text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # 수치 주장 확인
            for claim_type, patterns in self.NUMBER_PATTERNS.items():
                for pattern in patterns:
                    match = re.search(pattern, sentence)
                    if match:
                        claims.append(CopyClaimData(
                            claim_text=sentence,
                            claim_type=f"수치_{claim_type}",
                            extracted_value=match.group(1)
                        ))
                        break

            # 과장 표현 확인
            for pattern in self.exaggeration_compiled:
                if pattern.search(sentence):
                    claims.append(CopyClaimData(
                        claim_text=sentence,
                        claim_type="과장표현",
                        extracted_value=pattern.pattern
                    ))
                    break

            # 비교 표현 확인
            for pattern in self.comparison_compiled:
                if pattern.search(sentence):
                    claims.append(CopyClaimData(
                        claim_text=sentence,
                        claim_type="비교표현"
                    ))
                    break

            # 성능 주장 확인
            for pattern in self.performance_compiled:
                if pattern.search(sentence):
                    claims.append(CopyClaimData(
                        claim_text=sentence,
                        claim_type="성능주장"
                    ))
                    break

        return claims

    def _validate_weight_claim(self, claim: CopyClaimData, spec: SpecData) -> ValidationItem:
        """무게 주장 검증"""
        if spec.weight_kg is None:
            return ValidationItem(
                claim=claim,
                status=ValidationStatus.UNVERIFIED,
                reason="스펙에 무게 정보가 없습니다.",
                suggestion="공급업체에 정확한 무게 확인 필요"
            )

        try:
            claimed_weight = float(claim.extracted_value)

            # kg로 단위 통일 (g 단위인 경우 변환)
            if "g" in claim.claim_text.lower() or "그램" in claim.claim_text:
                claimed_weight = claimed_weight / 1000

            # 10% 오차 허용
            tolerance = spec.weight_kg * 0.1

            if abs(claimed_weight - spec.weight_kg) <= tolerance:
                return ValidationItem(
                    claim=claim,
                    status=ValidationStatus.PASS,
                    spec_reference=f"실제 무게: {spec.weight_kg}kg",
                    reason="무게 주장이 스펙과 일치합니다."
                )
            else:
                return ValidationItem(
                    claim=claim,
                    status=ValidationStatus.FAIL,
                    spec_reference=f"실제 무게: {spec.weight_kg}kg",
                    reason=f"주장 무게({claimed_weight}kg)와 실제 무게({spec.weight_kg}kg) 불일치",
                    suggestion="정확한 무게로 수정 필요"
                )

        except (ValueError, TypeError):
            return ValidationItem(
                claim=claim,
                status=ValidationStatus.WARNING,
                reason="무게 값 파싱 실패",
                suggestion="무게 표기 형식 확인 필요"
            )

    def _validate_load_claim(self, claim: CopyClaimData, spec: SpecData) -> ValidationItem:
        """하중 주장 검증"""
        if spec.max_load_kg is None:
            return ValidationItem(
                claim=claim,
                status=ValidationStatus.UNVERIFIED,
                reason="스펙에 최대 하중 정보가 없습니다.",
                suggestion="공급업체에 최대 하중 테스트 결과 확인 필요"
            )

        try:
            claimed_load = float(claim.extracted_value)

            if claimed_load <= spec.max_load_kg:
                return ValidationItem(
                    claim=claim,
                    status=ValidationStatus.PASS,
                    spec_reference=f"최대 하중: {spec.max_load_kg}kg",
                    reason="하중 주장이 스펙 범위 내입니다."
                )
            else:
                return ValidationItem(
                    claim=claim,
                    status=ValidationStatus.FAIL,
                    spec_reference=f"최대 하중: {spec.max_load_kg}kg",
                    reason=f"주장 하중({claimed_load}kg)이 실제 최대 하중({spec.max_load_kg}kg) 초과",
                    suggestion=f"최대 {spec.max_load_kg}kg 이하로 수정 필요"
                )

        except (ValueError, TypeError):
            return ValidationItem(
                claim=claim,
                status=ValidationStatus.WARNING,
                reason="하중 값 파싱 실패"
            )

    def _validate_exaggeration(self, claim: CopyClaimData) -> ValidationItem:
        """과장 표현 검증"""
        return ValidationItem(
            claim=claim,
            status=ValidationStatus.WARNING,
            reason=f"과장 표현 감지: {claim.extracted_value}",
            suggestion="객관적 근거 없이 사용 시 허위광고 위험. 수정 권장."
        )

    def _validate_comparison(self, claim: CopyClaimData) -> ValidationItem:
        """비교 표현 검증"""
        return ValidationItem(
            claim=claim,
            status=ValidationStatus.WARNING,
            reason="비교 표현 감지",
            suggestion="비교 대상과 근거 자료 필요. 없으면 삭제 권장."
        )

    def _validate_performance(self, claim: CopyClaimData, spec: SpecData) -> ValidationItem:
        """성능 주장 검증"""
        claim_lower = claim.claim_text.lower()

        # 방수 주장 검증
        if "방수" in claim_lower:
            if spec.waterproof_rating:
                return ValidationItem(
                    claim=claim,
                    status=ValidationStatus.PASS,
                    spec_reference=f"방수등급: {spec.waterproof_rating}",
                    reason="방수 인증 있음"
                )
            else:
                return ValidationItem(
                    claim=claim,
                    status=ValidationStatus.WARNING,
                    reason="방수 등급 정보 없음",
                    suggestion="IPX 등급 등 객관적 방수 테스트 결과 필요"
                )

        # 경량 주장 검증
        if any(kw in claim_lower for kw in ["가벼운", "경량", "초경량"]):
            if spec.weight_kg:
                # 카테고리별 경량 기준 (예시)
                lightweight_thresholds = {
                    "캠핑/레저": 2.0,
                    "가구/인테리어": 5.0,
                    "전자기기": 1.0,
                }
                threshold = lightweight_thresholds.get(spec.category, 3.0)

                if spec.weight_kg <= threshold:
                    return ValidationItem(
                        claim=claim,
                        status=ValidationStatus.PASS,
                        spec_reference=f"무게: {spec.weight_kg}kg (기준: {threshold}kg 이하)",
                        reason="경량 기준 충족"
                    )
                else:
                    return ValidationItem(
                        claim=claim,
                        status=ValidationStatus.FAIL,
                        spec_reference=f"무게: {spec.weight_kg}kg (기준: {threshold}kg 이하)",
                        reason=f"경량 기준({threshold}kg) 미충족",
                        suggestion="'경량' 표현 삭제 또는 수정 필요"
                    )
            else:
                return ValidationItem(
                    claim=claim,
                    status=ValidationStatus.UNVERIFIED,
                    reason="무게 정보 없음"
                )

        # 기타 성능 주장
        return ValidationItem(
            claim=claim,
            status=ValidationStatus.WARNING,
            reason="성능 주장 검증 필요",
            suggestion="객관적 테스트 결과로 뒷받침 필요"
        )

    def validate(self, copy_text: str, spec: SpecData) -> ValidationResult:
        """
        카피 텍스트 검증

        Args:
            copy_text: 검증할 카피 텍스트
            spec: 상품 스펙 데이터

        Returns:
            ValidationResult: 검증 결과
        """
        result = ValidationResult(
            product_name=spec.product_name,
            total_claims=0,
            passed=0,
            warnings=0,
            failed=0,
            unverified=0
        )

        # 주장 추출
        claims = self._extract_claims(copy_text)
        result.total_claims = len(claims)

        # 각 주장 검증
        for claim in claims:
            if claim.claim_type.startswith("수치_weight"):
                item = self._validate_weight_claim(claim, spec)
            elif claim.claim_type.startswith("수치_load"):
                item = self._validate_load_claim(claim, spec)
            elif claim.claim_type == "과장표현":
                item = self._validate_exaggeration(claim)
            elif claim.claim_type == "비교표현":
                item = self._validate_comparison(claim)
            elif claim.claim_type == "성능주장":
                item = self._validate_performance(claim, spec)
            else:
                item = ValidationItem(
                    claim=claim,
                    status=ValidationStatus.UNVERIFIED,
                    reason="자동 검증 불가"
                )

            result.items.append(item)

            # 카운트
            if item.status == ValidationStatus.PASS:
                result.passed += 1
            elif item.status == ValidationStatus.WARNING:
                result.warnings += 1
            elif item.status == ValidationStatus.FAIL:
                result.failed += 1
            else:
                result.unverified += 1

        # 전체 상태 및 리스크 평가
        if result.failed > 0:
            result.overall_status = ValidationStatus.FAIL
            result.risk_level = "HIGH"
            result.risk_reasons.append(f"검증 실패 {result.failed}건 - 수정 필수")
        elif result.warnings > 2:
            result.overall_status = ValidationStatus.WARNING
            result.risk_level = "MEDIUM"
            result.risk_reasons.append(f"경고 {result.warnings}건 - 검토 필요")
        else:
            result.overall_status = ValidationStatus.PASS
            result.risk_level = "LOW"

        return result

    def generate_report(self, result: ValidationResult) -> str:
        """검증 리포트 생성"""
        lines = [
            f"# 스펙 검증 리포트",
            f"",
            f"## 상품: {result.product_name}",
            f"",
            f"## 요약",
            f"- 총 검증 항목: {result.total_claims}건",
            f"- 통과: {result.passed}건",
            f"- 경고: {result.warnings}건",
            f"- 실패: {result.failed}건",
            f"- 미검증: {result.unverified}건",
            f"",
            f"## 전체 상태: {result.overall_status.value.upper()}",
            f"## 리스크 레벨: {result.risk_level}",
        ]

        if result.risk_reasons:
            lines.append("")
            lines.append("### 리스크 사유:")
            for reason in result.risk_reasons:
                lines.append(f"- {reason}")

        if result.items:
            lines.append("")
            lines.append("## 상세 검증 결과")

            for i, item in enumerate(result.items, 1):
                status_emoji = {
                    ValidationStatus.PASS: "✅",
                    ValidationStatus.WARNING: "⚠️",
                    ValidationStatus.FAIL: "❌",
                    ValidationStatus.UNVERIFIED: "❓",
                }
                lines.append(f"")
                lines.append(f"### {i}. {status_emoji[item.status]} [{item.status.value.upper()}]")
                lines.append(f"- 원문: \"{item.claim.claim_text}\"")
                lines.append(f"- 유형: {item.claim.claim_type}")
                lines.append(f"- 사유: {item.reason}")
                if item.spec_reference:
                    lines.append(f"- 스펙 참조: {item.spec_reference}")
                if item.suggestion:
                    lines.append(f"- 제안: {item.suggestion}")

        return "\n".join(lines)


# --- 테스트 실행 코드 ---
if __name__ == "__main__":
    print("="*60)
    print("✓ 스펙 검증기 테스트 (v3.1)")
    print("="*60)

    validator = SpecValidator()

    # 샘플 스펙
    spec = SpecData(
        product_name="초경량 캠핑 의자",
        category="캠핑/레저",
        weight_kg=2.5,
        dimensions_cm=(80, 20, 15),
        max_load_kg=120,
        material="알루미늄 합금"
    )

    # 검증할 카피
    copy_text = """
    초경량 1.8kg 캠핑의자! 최고급 알루미늄 소재로 150kg까지 거뜬히 버팁니다.
    타사 대비 30% 더 가벼운 완벽한 휴대성.
    방수 원단으로 비 와도 걱정 없어요.
    """

    print(f"\n[검증 대상 카피]")
    print(copy_text)

    result = validator.validate(copy_text, spec)

    print(f"\n[검증 결과]")
    print(f"  전체 상태: {result.overall_status.value}")
    print(f"  리스크 레벨: {result.risk_level}")
    print(f"  통과/경고/실패/미검증: {result.passed}/{result.warnings}/{result.failed}/{result.unverified}")

    print("\n" + "-"*60)
    print(validator.generate_report(result))
    print("-"*60)

    print("\n" + "="*60)
    print("✅ 스펙 검증기 모듈 준비 완료")
    print("="*60 + "\n")
