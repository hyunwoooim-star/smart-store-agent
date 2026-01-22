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
    # v3.5 추가 (Gemini 피드백 반영)
    FUNCTIONAL_COSMETIC = "기능성화장품 표현 (인증 필요)"
    CHILDREN_PRODUCT = "아동용 제품 주의사항"
    INTELLECTUAL_PROPERTY = "지식재산권 침해 가능성"
    # v3.5.1 추가 (Gemini 피드백 - 의료기기법 위반)
    MEDICAL_DEVICE = "의료기기 오인 표현 (인증 필요)"


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

        # ============================================
        # v3.5 추가 패턴 (Gemini 피드백 반영)
        # ============================================

        # 8. 기능성화장품 표현 (HIGH - 식약처 인증 필요)
        self.functional_cosmetic_patterns = [
            (r"(자외선|UV).{0,5}(차단|방어|보호)", "자외선 차단 (기능성 인증 필요)"),
            (r"(SPF|PA)\s*\d+", "자외선차단지수 표시 (인증 필요)"),
            (r"(주름).{0,5}(개선|완화|케어)", "주름 개선 (기능성 인증 필요)"),
            (r"(미백|화이트닝|브라이트닝)", "미백 기능 (인증 필요)"),
            (r"(탈모).{0,5}(예방|방지|완화|개선)", "탈모 관련 (의약외품 인증 필요)"),
            (r"(여드름|아크네).{0,5}(예방|개선|치료)", "여드름 관련 (인증 필요)"),
            (r"(아토피|피부염).{0,5}(개선|완화|치료)", "피부질환 관련 (의약품)"),
        ]

        # 9. 아동용 제품 주의사항 (HIGH - KC 인증 등)
        self.children_product_patterns = [
            (r"(유아|아기|어린이|키즈|베이비).{0,10}(장난감|완구)", "아동용 완구 (KC 인증 필수)"),
            (r"(유아|아기|어린이).{0,10}(식품|간식|음식)", "아동용 식품 (HACCP 등)"),
            (r"(유아|아기).{0,10}(화장품|로션|크림)", "영유아 화장품 (안전 기준)"),
            (r"(유아|아기|어린이).{0,5}용", "아동용 제품 (인증 확인 필요)"),
            (r"(\d+)개월.{0,5}(이상|부터|사용)", "사용 연령 표시 (검증 필요)"),
            (r"(출산|임산부|임신).{0,5}(선물|용품)", "임산부/출산 용품"),
        ]

        # 10. 지식재산권 침해 (HIGH - 디자인/캐릭터)
        self.ip_patterns = [
            # 유명 캐릭터
            (r"(디즈니|마블|픽사|산리오)", "디즈니/산리오 캐릭터 (라이선스 필요)"),
            (r"(미키마우스|미니마우스|엘사|스파이더맨|아이언맨)", "캐릭터명 (라이선스)"),
            (r"(헬로키티|마이멜로디|시나모롤|쿠로미)", "산리오 캐릭터"),
            (r"(짱구|뽀로로|핑크퐁|아기상어|카카오프렌즈)", "국내 캐릭터"),
            (r"(라이언|어피치|무지|콘|네오|제이지|튜브)", "카카오프렌즈 캐릭터"),
            # 디자인 카피
            (r"(OEM|ODM).{0,5}(가능|제작)", "OEM/ODM 언급 (B2B 전용)"),
            (r"(레플리카|레플|짝퉁|모조품)", "모조품 관련 (불법)"),
            (r"(~풍|~스타일|~느낌|~감성).{0,5}(디자인|제품)", "디자인 카피 암시"),
        ]

        # 11. 의료기기 오인 표현 (CRITICAL - 의료기기법 위반)
        # 일반 공산품에 의학적 효능 암시 → 경찰서 가는 케이스
        self.medical_device_patterns = [
            # 치료/교정 관련
            (r"(치료|치료용|치료기)", "치료 표현 (의료기기 인증 필요)"),
            (r"(교정|교정기|교정용)", "교정 표현 (의료기기)"),
            (r"(거북목|일자목).{0,5}(교정|개선|치료)", "거북목 교정 (의료기기)"),
            (r"(자세).{0,5}(교정|개선|치료)", "자세 교정 (의료기기)"),
            (r"(척추|허리|목).{0,5}(교정|치료)", "척추/허리 교정 (의료기기)"),

            # 통증 관련
            (r"(통증).{0,5}(완화|개선|치료|제거)", "통증 완화 (의료기기 효능)"),
            (r"(근육통|관절통|두통|어깨통증|허리통증).{0,5}(완화|해소)", "통증 완화 표현"),

            # 혈액/순환 관련
            (r"(혈액순환|혈행).{0,5}(개선|촉진|증진)", "혈액순환 개선 (의료기기)"),
            (r"(혈류|혈관).{0,5}(개선|확장)", "혈류 관련 (의료기기)"),

            # 척추/디스크 관련
            (r"(디스크|추간판).{0,5}(예방|치료|개선)", "디스크 관련 (의료기기)"),
            (r"(허리디스크|목디스크)", "디스크 언급 (의료적 표현)"),

            # 기타 의료적 표현
            (r"(재활|물리치료|테라피)", "재활/치료 표현"),
            (r"(의료용|의료기기|의료기)", "의료 관련 표현"),
            (r"(적외선|원적외선).{0,5}(치료|효과)", "적외선 치료 (의료기기)"),

            # v3.5.1 추가: 미용기기/마사지기 관련 (Gemini 피드백 - 최근 적발 빈도 급증)
            (r"(EMS|저주파|고주파).{0,5}(지방|분해|다이어트|살빠짐|셀룰라이트)", "미용기기 과대광고 (지방분해 주장)"),
            (r"(리프팅|탄력).{0,5}(재생|회복|치료)", "피부 재생 (의료기기 오인)"),
            (r"(비염|축농증).{0,5}(치료|완화|개선)", "비염 치료 (의료기기)"),
            (r"(코골이).{0,5}(방지|치료|완화|개선)", "코골이 방지 (의료기기)"),
            (r"(마사지건|안마기|마사지기).{0,5}(치료|재활|통증)", "마사지기 의료 효능 주장"),
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

        # ============================================
        # v3.5 추가 검사 (Gemini 피드백 반영)
        # ============================================

        # 8. 기능성화장품 (HIGH)
        for pattern, desc in self.functional_cosmetic_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.FUNCTIONAL_COSMETIC,
                    matched_text=match.group(),
                    pattern=desc,
                    severity="high",
                    suggestion="기능성화장품은 식약처 인증 필요. 인증 없으면 표현 삭제"
                ))

        # 9. 아동용 제품 (HIGH)
        for pattern, desc in self.children_product_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.CHILDREN_PRODUCT,
                    matched_text=match.group(),
                    pattern=desc,
                    severity="high",
                    suggestion="아동용 제품은 KC인증/HACCP 등 필수. 인증서 확인 필요"
                ))

        # 10. 지식재산권 (HIGH)
        for pattern, desc in self.ip_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.INTELLECTUAL_PROPERTY,
                    matched_text=match.group(),
                    pattern=desc,
                    severity="high",
                    suggestion="캐릭터/디자인 라이선스 확인 필수. 무단 사용 시 법적 문제"
                ))

        # 11. 의료기기 오인 (CRITICAL - 가장 위험)
        for pattern, desc in self.medical_device_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.MEDICAL_DEVICE,
                    matched_text=match.group(),
                    pattern=desc,
                    severity="high",
                    suggestion="의료기기 인증 없이 사용 불가. '도움', '관리', '케어' 등으로 순화하세요."
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
            # v3.5 추가 대안
            ViolationType.FUNCTIONAL_COSMETIC: [
                "피부 보습", "촉촉한 사용감", "부드러운 발림성",
                "산뜻한 마무리", "데일리 케어",
            ],
            ViolationType.CHILDREN_PRODUCT: [
                "온 가족 사용", "순한 성분", "피부 자극 테스트 완료",
                "안전한 소재", "친환경 소재",
            ],
            ViolationType.INTELLECTUAL_PROPERTY: [
                "오리지널 디자인", "자체 제작", "독창적인 디자인",
                "심플 디자인", "모던 스타일",
            ],
            ViolationType.MEDICAL_DEVICE: [
                "자세 도움", "바른 자세 습관", "편안한 사용감",
                "일상 관리", "컨디션 케어", "릴렉스",
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
