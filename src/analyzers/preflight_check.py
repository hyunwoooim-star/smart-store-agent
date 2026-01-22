"""
preflight_check.py - 상품 등록 전 사전 검사 모듈 (Phase 4)

네이버 스마트스토어 등록 전 금지어/위험 표현 검사
- 광고법 위반 표현 검사
- 의약품/건강기능식품 관련 금지어
- 허위/과장 광고 표현
- 상표권 침해 가능성

사용법:
    checker = PreFlightChecker()
    result = checker.check("최고의 다이어트 효과! 암 예방에 탁월!")
    if not result.passed:
        print(result.violations)
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum


class ViolationType(Enum):
    """위반 유형"""
    MEDICAL_CLAIM = "의료/건강 효능 주장"
    EXAGGERATION = "허위/과장 광고"
    SUPERLATIVE = "최상급 표현"
    GUARANTEE = "효과 보장 표현"
    COMPARISON = "비교 광고 (근거 없음)"
    TRADEMARK = "상표권 침해 가능성"
    PROHIBITED_WORD = "금지어 사용"
    PRICE_MANIPULATION = "가격 조작 표현"


@dataclass
class Violation:
    """개별 위반 사항"""
    type: ViolationType
    matched_text: str           # 매칭된 텍스트
    pattern: str                # 매칭된 패턴
    severity: str               # "high", "medium", "low"
    suggestion: Optional[str] = None  # 수정 제안


@dataclass
class PreFlightResult:
    """검사 결과"""
    passed: bool                        # 통과 여부
    violations: List[Violation] = field(default_factory=list)
    warning_count: int = 0
    error_count: int = 0

    @property
    def summary(self) -> str:
        if self.passed:
            return "✅ 검사 통과 - 등록 가능"
        return f"❌ 검사 실패 - 오류 {self.error_count}건, 경고 {self.warning_count}건"


class PreFlightChecker:
    """상품 등록 전 사전 검사기

    네이버 스마트스토어 정책 및 광고법 기준으로 검사

    Example:
        checker = PreFlightChecker()
        result = checker.check("암 예방에 최고! 100% 효과 보장!")

        if not result.passed:
            for v in result.violations:
                print(f"[{v.severity}] {v.type.value}: '{v.matched_text}'")
    """

    def __init__(self, strict_mode: bool = True):
        """
        Args:
            strict_mode: True면 경고도 실패로 처리
        """
        self.strict_mode = strict_mode
        self._init_patterns()

    def _init_patterns(self):
        """금지어 패턴 초기화"""

        # 1. 의료/건강 효능 주장 (HIGH - 의약품법 위반)
        self.medical_patterns = [
            # 질병 치료/예방
            (r"(암|당뇨|고혈압|심장병|뇌졸중|치매).{0,5}(예방|치료|완치|개선)", "질병 치료/예방 주장"),
            (r"(항암|항균|항바이러스|살균|멸균).{0,3}(효과|기능|작용)", "의약품 효능 주장"),
            (r"(면역력|면역).{0,5}(강화|증진|향상|높)", "면역 관련 효능"),
            (r"(혈압|혈당|콜레스테롤).{0,5}(낮추|조절|개선)", "의약품 효능 주장"),

            # 다이어트/체중
            (r"(살|체중|뱃살|지방).{0,5}(빠지|빼|감소|분해|연소)", "체중 감량 효능"),
            (r"다이어트.{0,5}(효과|효능|성공)", "다이어트 효능 주장"),

            # 피부/미용 (의약외품 아닌 경우)
            (r"(주름|기미|잡티|여드름).{0,5}(제거|개선|완화|치료)", "피부 치료 효능"),
            (r"(미백|화이트닝).{0,5}(효과|기능)", "미백 효능 (인증 필요)"),

            # 기타 건강 주장
            (r"(피로|스트레스).{0,5}(해소|회복|개선)", "건강기능 효능"),
            (r"(숙면|수면).{0,5}(도움|개선|유도)", "수면 관련 효능"),
            (r"(해독|디톡스|독소).{0,5}(제거|배출)", "해독 효능 주장"),
        ]

        # 2. 최상급/절대적 표현 (MEDIUM - 과장광고)
        self.superlative_patterns = [
            (r"(최고|최상|최강|최초|유일|독보적)", "최상급 표현"),
            (r"(세계\s?최초|국내\s?최초|업계\s?최초)", "최초 주장 (증빙 필요)"),
            (r"(1위|넘버원|No\.?\s?1|일등)", "순위 주장 (증빙 필요)"),
            (r"(완벽|완전|절대|100%)", "절대적 표현"),
            (r"(기적|놀라운|경이로운|혁신적)", "과장 형용사"),
        ]

        # 3. 효과 보장 표현 (HIGH - 허위광고)
        self.guarantee_patterns = [
            (r"(100%|백퍼센트).{0,5}(효과|만족|성공)", "100% 보장 주장"),
            (r"(무조건|반드시|확실히).{0,5}(효과|결과)", "효과 보장 표현"),
            (r"(돈\s?벌|수익).{0,5}(보장|확실)", "수익 보장 표현"),
            (r"(환불|반품).{0,5}(불가|안.{0,2}됨)", "환불 불가 (불법)"),
            (r"효과\s?(없으면|없을\s?시).{0,10}(환불|보상)", "조건부 보장"),
        ]

        # 4. 비교 광고 (MEDIUM - 근거 없으면 불법)
        self.comparison_patterns = [
            (r"(타사|경쟁사|다른\s?제품).{0,10}(보다|대비|비해)", "경쟁사 비교"),
            (r"(A사|B사|○○사).{0,5}(보다|대비)", "특정 업체 비교"),
            (r"(기존|일반).{0,5}제품.{0,5}(보다|대비|비해)", "기존 제품 비교"),
        ]

        # 5. 가격 조작 표현 (MEDIUM)
        self.price_patterns = [
            (r"(정가|원가|시중가).{0,5}\d+.{0,5}(할인|세일)", "정가 표시 (증빙 필요)"),
            (r"(\d+)%\s?(할인|세일|OFF)", "할인율 표시"),
            (r"(오늘만|한정|마감).{0,5}(할인|특가|세일)", "긴급 할인 표현"),
            (r"(원가|공장가|도매가).{0,5}(판매|직접)", "원가 판매 주장"),
        ]

        # 6. 네이버 금지 키워드 (플랫폼 정책)
        self.naver_prohibited = [
            "카카오톡", "카톡", "인스타", "인스타그램", "페이스북",
            "유튜브", "틱톡", "트위터", "라인", "위챗",
            "쿠팡", "11번가", "지마켓", "옥션", "위메프", "티몬",
            "직거래", "계좌이체", "현금결제", "카드결제 불가",
            "연락처", "전화번호", "휴대폰번호",
        ]

        # 7. 상표권 침해 가능성 (브랜드명)
        self.trademark_patterns = [
            (r"(정품|오리지널|본품).{0,5}(아님|아닌|X)", "정품 아님 표시"),
            (r"(스타일|st\.|풍|디자인).{0,3}$", "~스타일/풍 표현"),
            # 유명 브랜드 직접 사용 (예시)
            (r"(샤넬|구찌|루이비통|에르메스|프라다)", "명품 브랜드 언급"),
            (r"(나이키|아디다스|뉴발란스|반스)", "스포츠 브랜드 언급"),
            (r"(애플|삼성|LG|소니)", "전자 브랜드 언급"),
        ]

    def check(self, text: str) -> PreFlightResult:
        """텍스트 검사 실행

        Args:
            text: 검사할 상품명/설명 텍스트

        Returns:
            PreFlightResult: 검사 결과
        """
        violations = []

        # 1. 의료/건강 효능 (HIGH)
        for pattern, desc in self.medical_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.MEDICAL_CLAIM,
                    matched_text=match.group(),
                    pattern=desc,
                    severity="high",
                    suggestion="의약품/건강기능식품 인증 없이 효능 주장 불가"
                ))

        # 2. 최상급 표현 (MEDIUM)
        for pattern, desc in self.superlative_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.SUPERLATIVE,
                    matched_text=match.group(),
                    pattern=desc,
                    severity="medium",
                    suggestion="객관적 증빙 자료 필요 또는 표현 수정"
                ))

        # 3. 효과 보장 (HIGH)
        for pattern, desc in self.guarantee_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.GUARANTEE,
                    matched_text=match.group(),
                    pattern=desc,
                    severity="high",
                    suggestion="효과 보장 표현 삭제 필요"
                ))

        # 4. 비교 광고 (MEDIUM)
        for pattern, desc in self.comparison_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.COMPARISON,
                    matched_text=match.group(),
                    pattern=desc,
                    severity="medium",
                    suggestion="비교 광고는 객관적 근거 필요"
                ))

        # 5. 가격 조작 (MEDIUM)
        for pattern, desc in self.price_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.PRICE_MANIPULATION,
                    matched_text=match.group(),
                    pattern=desc,
                    severity="medium",
                    suggestion="가격 표시는 증빙 가능해야 함"
                ))

        # 6. 네이버 금지 키워드 (HIGH)
        for keyword in self.naver_prohibited:
            if keyword.lower() in text.lower():
                violations.append(Violation(
                    type=ViolationType.PROHIBITED_WORD,
                    matched_text=keyword,
                    pattern="네이버 금지 키워드",
                    severity="high",
                    suggestion="해당 키워드 삭제 필요"
                ))

        # 7. 상표권 (MEDIUM~HIGH)
        for pattern, desc in self.trademark_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.TRADEMARK,
                    matched_text=match.group(),
                    pattern=desc,
                    severity="medium",
                    suggestion="상표권 침해 주의 - 표현 수정 권장"
                ))

        # 결과 집계
        error_count = sum(1 for v in violations if v.severity == "high")
        warning_count = sum(1 for v in violations if v.severity in ("medium", "low"))

        passed = error_count == 0
        if self.strict_mode:
            passed = len(violations) == 0

        return PreFlightResult(
            passed=passed,
            violations=violations,
            error_count=error_count,
            warning_count=warning_count,
        )

    def check_product(self, name: str, description: str = "") -> PreFlightResult:
        """상품 전체 검사 (상품명 + 설명)

        Args:
            name: 상품명
            description: 상품 설명 (선택)

        Returns:
            PreFlightResult: 검사 결과
        """
        full_text = f"{name} {description}"
        return self.check(full_text)

    def get_safe_alternatives(self, violation: Violation) -> List[str]:
        """위반 표현의 안전한 대안 제시

        Args:
            violation: 위반 사항

        Returns:
            List[str]: 대안 표현 목록
        """
        alternatives = {
            ViolationType.SUPERLATIVE: [
                "고품질", "프리미엄", "인기 상품", "추천 상품",
                "베스트 셀러", "고객 만족도 높은",
            ],
            ViolationType.MEDICAL_CLAIM: [
                "건강한 생활 도움", "일상 활력", "편안한 사용감",
                "자연 유래 성분", "순한 제형",
            ],
            ViolationType.GUARANTEE: [
                "만족도 높은", "호평받는", "검증된 품질",
                "꼼꼼한 품질 관리", "정성껏 제작",
            ],
            ViolationType.EXAGGERATION: [
                "좋은 품질", "합리적인 가격", "실용적인",
                "편리한 사용", "만족스러운",
            ],
        }
        return alternatives.get(violation.type, [])

    def format_report(self, result: PreFlightResult) -> str:
        """검사 결과를 읽기 쉬운 리포트로 포맷

        Args:
            result: 검사 결과

        Returns:
            str: 포맷된 리포트 문자열
        """
        lines = [
            "=" * 50,
            "📋 Pre-Flight Check 결과",
            "=" * 50,
            "",
            result.summary,
            "",
        ]

        if result.violations:
            lines.append(f"발견된 문제: {len(result.violations)}건")
            lines.append("-" * 50)

            # 심각도별 정렬
            sorted_violations = sorted(
                result.violations,
                key=lambda v: (0 if v.severity == "high" else 1 if v.severity == "medium" else 2)
            )

            for i, v in enumerate(sorted_violations, 1):
                icon = "🔴" if v.severity == "high" else "🟡" if v.severity == "medium" else "🟢"
                lines.append(f"\n{i}. {icon} [{v.severity.upper()}] {v.type.value}")
                lines.append(f"   매칭: \"{v.matched_text}\"")
                lines.append(f"   패턴: {v.pattern}")
                if v.suggestion:
                    lines.append(f"   💡 제안: {v.suggestion}")

                # 대안 제시
                alternatives = self.get_safe_alternatives(v)
                if alternatives:
                    lines.append(f"   🔄 대안: {', '.join(alternatives[:3])}")

        lines.extend([
            "",
            "=" * 50,
        ])

        return "\n".join(lines)


# 편의 함수
def preflight_check(text: str, strict: bool = True) -> PreFlightResult:
    """간편 검사 함수

    Args:
        text: 검사할 텍스트
        strict: 엄격 모드 (경고도 실패 처리)

    Returns:
        PreFlightResult: 검사 결과
    """
    checker = PreFlightChecker(strict_mode=strict)
    return checker.check(text)
