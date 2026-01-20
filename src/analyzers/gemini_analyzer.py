"""
gemini_analyzer.py - Gemini AI 분석 모듈 (v3.2)

핵심 기능:
1. 불만 패턴 TOP 5 분석
2. Semantic Gap 식별 (고객 기대 vs 실제 제품)
3. 개선 카피라이팅 생성
4. 스펙 체크리스트 추출

v3.2 변경사항 (Gemini 피드백 반영):
- 마스터 시스템 프롬프트 추가 (베테랑 MD 페르소나)
- 비판적 사고 + 보수적 마진 + 근거 중심 원칙 적용
- JSON 출력 강제 규칙 강화
"""

import os
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum

# Google Generative AI (설치 필요: pip install google-generativeai)
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None


class AnalysisType(Enum):
    """분석 유형"""
    COMPLAINT_PATTERN = "complaint_pattern"
    SEMANTIC_GAP = "semantic_gap"
    COPYWRITING = "copywriting"
    SPEC_CHECKLIST = "spec_checklist"
    FULL_ANALYSIS = "full_analysis"


@dataclass
class ComplaintPattern:
    """불만 패턴"""
    rank: int
    category: str
    description: str
    frequency: str              # "높음", "중간", "낮음"
    severity: str               # "심각", "보통", "경미"
    example_quotes: List[str] = field(default_factory=list)
    suggested_solution: str = ""


@dataclass
class SemanticGap:
    """시맨틱 갭 (고객 기대 vs 실제)"""
    gap_type: str               # "품질", "기능", "가격", "디자인" 등
    customer_expectation: str   # 고객이 기대한 것
    actual_reality: str         # 실제 상황
    impact_level: str           # "높음", "중간", "낮음"
    opportunity: str            # 개선 기회


@dataclass
class CopywritingSuggestion:
    """카피라이팅 제안"""
    original_pain_point: str    # 원래 불만
    suggested_copy: str         # 제안 카피
    target_audience: str        # 타겟 고객
    key_benefit: str            # 핵심 혜택
    tone: str                   # 톤앤매너


@dataclass
class SpecCheckItem:
    """스펙 체크 항목"""
    category: str               # "필수", "권장", "선택"
    item: str                   # 체크 항목
    reason: str                 # 이유
    verification_method: str    # 검증 방법


@dataclass
class GeminiAnalysisResult:
    """Gemini 분석 결과"""
    success: bool
    analysis_type: AnalysisType
    raw_response: str = ""

    # 분석 결과
    complaint_patterns: List[ComplaintPattern] = field(default_factory=list)
    semantic_gaps: List[SemanticGap] = field(default_factory=list)
    copywriting_suggestions: List[CopywritingSuggestion] = field(default_factory=list)
    spec_checklist: List[SpecCheckItem] = field(default_factory=list)

    # 요약
    summary: str = ""
    key_insights: List[str] = field(default_factory=list)

    # 에러
    error: Optional[str] = None


class GeminiAnalyzer:
    """Gemini AI 분석기 (v3.2 - 마스터 프롬프트 적용)"""

    # Gemini 모델 설정
    DEFAULT_MODEL = "gemini-1.5-flash"

    # =========================================================
    # 마스터 시스템 프롬프트 (Gemini 피드백 반영)
    # "10년차 베테랑 MD + 깐깐한 품질 관리자" 페르소나
    # =========================================================
    SYSTEM_PROMPT = """당신은 '10년 차 베테랑 MD'이자 '깐깐한 품질 관리자'입니다.
당신의 목표는 "사장님의 돈을 지키는 것"입니다.

[분석 원칙]
1. 비판적 사고: 판매자의 상세페이지는 모두 "광고"라고 가정하고, 리뷰의 "진짜 불만"에 집중하세요.
2. 보수적 마진: 배송비, 관세, 반품비는 항상 최악의 상황(최대치)을 가정하여 계산하세요.
3. 근거 중심: "좋아 보입니다" 같은 모호한 말 금지. "리뷰 30%가 내구성을 지적함"처럼 숫자로 말하세요.

[출력 제한]
- 모든 출력은 반드시 JSON 포맷을 준수하세요.
- 마크다운이나 잡담(인사말)은 절대 포함하지 마세요.
- 코드 블록(```)도 사용하지 마세요. 순수 JSON만 출력하세요.
"""

    # 프롬프트 템플릿
    PROMPTS = {
        AnalysisType.COMPLAINT_PATTERN: """
아래 불만 리뷰들을 분석하여 TOP 5 불만 패턴을 도출해주세요.
'단순 변심'은 제외하고, '제품의 구조적 결함'만 집중 분석하세요.

## 분석 요청
{reviews}

## 출력 형식 (JSON)
{{
    "patterns": [
        {{
            "rank": 1,
            "category": "카테고리명",
            "description": "불만 설명",
            "frequency": "높음/중간/낮음",
            "severity": "심각/보통/경미",
            "example_quotes": ["인용1", "인용2"],
            "suggested_solution": "해결 방안"
        }}
    ],
    "summary": "전체 요약",
    "key_insights": ["인사이트1", "인사이트2"]
}}

JSON만 출력하세요.
""",

        AnalysisType.SEMANTIC_GAP: """
당신은 고객 경험 분석 전문가입니다.

아래 리뷰들에서 "고객이 기대한 것"과 "실제 경험한 것" 사이의 갭을 분석해주세요.

## 분석 요청
{reviews}

## 출력 형식 (JSON)
{{
    "gaps": [
        {{
            "gap_type": "유형 (품질/기능/가격/디자인 등)",
            "customer_expectation": "고객이 기대한 것",
            "actual_reality": "실제 상황",
            "impact_level": "높음/중간/낮음",
            "opportunity": "개선 기회"
        }}
    ],
    "summary": "전체 요약"
}}

JSON만 출력하세요.
""",

        AnalysisType.COPYWRITING: """
아래 불만 사항들을 해소하는 상품 카피를 작성해주세요.

[중요 지침]
- '최고예요' 같은 뻔한 말 금지
- 고객이 '내 불안을 해소해줬다'고 느낄 수 있는 문제 해결 중심 카피 작성
- 예시: "허리 아픈 캠핑의자" → "3시간 앉아도 뻐근하지 않은 S자 곡선"

## 불만 사항
{complaints}

## 상품 정보
{product_info}

## 출력 형식 (JSON)
{{
    "suggestions": [
        {{
            "original_pain_point": "원래 불만",
            "suggested_copy": "제안 카피 (30자 이내)",
            "target_audience": "타겟 고객",
            "key_benefit": "핵심 혜택",
            "tone": "톤앤매너"
        }}
    ]
}}

JSON만 출력하세요.
""",

        AnalysisType.SPEC_CHECKLIST: """
당신은 품질관리 전문가입니다.

아래 불만 사항들을 바탕으로, 신규 소싱 시 반드시 확인해야 할 스펙 체크리스트를 만들어주세요.

## 불만 사항
{complaints}

## 상품 카테고리
{category}

## 출력 형식 (JSON)
{{
    "checklist": [
        {{
            "category": "필수/권장/선택",
            "item": "체크 항목",
            "reason": "이유",
            "verification_method": "검증 방법"
        }}
    ]
}}

JSON만 출력하세요.
""",

        AnalysisType.FULL_ANALYSIS: """
당신은 이커머스 상품 분석 전문가입니다.

아래 리뷰 데이터를 종합 분석해주세요.

## 리뷰 데이터
{reviews}

## 상품 정보
{product_info}

## 분석 항목
1. TOP 5 불만 패턴
2. 시맨틱 갭 (고객 기대 vs 실제)
3. 개선 카피라이팅 제안
4. 소싱 시 스펙 체크리스트

## 출력 형식 (JSON)
{{
    "complaint_patterns": [...],
    "semantic_gaps": [...],
    "copywriting_suggestions": [...],
    "spec_checklist": [...],
    "summary": "전체 요약",
    "key_insights": ["인사이트1", "인사이트2", "인사이트3"]
}}

JSON만 출력하세요.
"""
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Gemini API 키 (없으면 환경변수에서 읽음)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = None
        self._initialized = False

    def initialize(self) -> bool:
        """API 초기화"""
        if not GENAI_AVAILABLE:
            return False

        if not self.api_key:
            return False

        try:
            genai.configure(api_key=self.api_key)
            # 시스템 프롬프트 적용 (v3.2)
            self.model = genai.GenerativeModel(
                self.DEFAULT_MODEL,
                system_instruction=self.SYSTEM_PROMPT
            )
            self._initialized = True
            return True
        except Exception:
            return False

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """JSON 응답 파싱"""
        try:
            # JSON 블록 추출 시도
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0]
            else:
                json_str = response_text

            return json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError):
            return {}

    def analyze_complaints(self, reviews_text: str) -> GeminiAnalysisResult:
        """불만 패턴 분석"""
        result = GeminiAnalysisResult(
            success=False,
            analysis_type=AnalysisType.COMPLAINT_PATTERN
        )

        if not self._initialized:
            if not self.initialize():
                result.error = "Gemini API가 초기화되지 않았습니다. API 키를 확인하세요."
                return result

        try:
            prompt = self.PROMPTS[AnalysisType.COMPLAINT_PATTERN].format(reviews=reviews_text)
            response = self.model.generate_content(prompt)
            result.raw_response = response.text

            parsed = self._parse_json_response(response.text)

            if "patterns" in parsed:
                for p in parsed["patterns"]:
                    result.complaint_patterns.append(ComplaintPattern(
                        rank=p.get("rank", 0),
                        category=p.get("category", ""),
                        description=p.get("description", ""),
                        frequency=p.get("frequency", ""),
                        severity=p.get("severity", ""),
                        example_quotes=p.get("example_quotes", []),
                        suggested_solution=p.get("suggested_solution", "")
                    ))

            result.summary = parsed.get("summary", "")
            result.key_insights = parsed.get("key_insights", [])
            result.success = True

        except Exception as e:
            result.error = str(e)

        return result

    def analyze_semantic_gaps(self, reviews_text: str) -> GeminiAnalysisResult:
        """시맨틱 갭 분석"""
        result = GeminiAnalysisResult(
            success=False,
            analysis_type=AnalysisType.SEMANTIC_GAP
        )

        if not self._initialized:
            if not self.initialize():
                result.error = "Gemini API가 초기화되지 않았습니다."
                return result

        try:
            prompt = self.PROMPTS[AnalysisType.SEMANTIC_GAP].format(reviews=reviews_text)
            response = self.model.generate_content(prompt)
            result.raw_response = response.text

            parsed = self._parse_json_response(response.text)

            if "gaps" in parsed:
                for g in parsed["gaps"]:
                    result.semantic_gaps.append(SemanticGap(
                        gap_type=g.get("gap_type", ""),
                        customer_expectation=g.get("customer_expectation", ""),
                        actual_reality=g.get("actual_reality", ""),
                        impact_level=g.get("impact_level", ""),
                        opportunity=g.get("opportunity", "")
                    ))

            result.summary = parsed.get("summary", "")
            result.success = True

        except Exception as e:
            result.error = str(e)

        return result

    def generate_copywriting(self, complaints: str, product_info: str) -> GeminiAnalysisResult:
        """카피라이팅 생성"""
        result = GeminiAnalysisResult(
            success=False,
            analysis_type=AnalysisType.COPYWRITING
        )

        if not self._initialized:
            if not self.initialize():
                result.error = "Gemini API가 초기화되지 않았습니다."
                return result

        try:
            prompt = self.PROMPTS[AnalysisType.COPYWRITING].format(
                complaints=complaints,
                product_info=product_info
            )
            response = self.model.generate_content(prompt)
            result.raw_response = response.text

            parsed = self._parse_json_response(response.text)

            if "suggestions" in parsed:
                for s in parsed["suggestions"]:
                    result.copywriting_suggestions.append(CopywritingSuggestion(
                        original_pain_point=s.get("original_pain_point", ""),
                        suggested_copy=s.get("suggested_copy", ""),
                        target_audience=s.get("target_audience", ""),
                        key_benefit=s.get("key_benefit", ""),
                        tone=s.get("tone", "")
                    ))

            result.success = True

        except Exception as e:
            result.error = str(e)

        return result

    def generate_spec_checklist(self, complaints: str, category: str) -> GeminiAnalysisResult:
        """스펙 체크리스트 생성"""
        result = GeminiAnalysisResult(
            success=False,
            analysis_type=AnalysisType.SPEC_CHECKLIST
        )

        if not self._initialized:
            if not self.initialize():
                result.error = "Gemini API가 초기화되지 않았습니다."
                return result

        try:
            prompt = self.PROMPTS[AnalysisType.SPEC_CHECKLIST].format(
                complaints=complaints,
                category=category
            )
            response = self.model.generate_content(prompt)
            result.raw_response = response.text

            parsed = self._parse_json_response(response.text)

            if "checklist" in parsed:
                for c in parsed["checklist"]:
                    result.spec_checklist.append(SpecCheckItem(
                        category=c.get("category", ""),
                        item=c.get("item", ""),
                        reason=c.get("reason", ""),
                        verification_method=c.get("verification_method", "")
                    ))

            result.success = True

        except Exception as e:
            result.error = str(e)

        return result

    def analyze_reviews(self, keyword: str, reviews: list) -> dict:
        """
        리뷰 데이터를 분석하여 불만 패턴, 카피라이팅, 스펙 체크리스트 도출

        Args:
            keyword: 분석 키워드
            reviews: 리뷰 리스트 [{"text": "리뷰내용"}, ...]

        Returns:
            분석 결과 딕셔너리
        """
        print(f"🤖 [Gemini] Analyzing {len(reviews)} reviews for '{keyword}'...")

        # 리뷰 텍스트만 추출하여 프롬프트 컨텍스트로 구성
        review_text_blob = "\n".join([r['text'] for r in reviews[:50]])  # 토큰 제한

        prompt = f"""
당신은 프로페셔널한 e-커머스 상품 기획자입니다.
다음은 '{keyword}' 상품에 대한 고객 리뷰 샘플입니다.

[리뷰 데이터]
{review_text_blob}

[지시사항]
1. **불만 패턴 분석**: 실제 구매자들이 느끼는 가장 큰 불만 3가지를 찾으세요. (단순 "별로예요"는 제외, 구체적 이유만)
2. **Semantic Gap**: 시장에 없지만 고객이 원하는 니즈(Gap)를 찾으세요.
3. **개선 카피라이팅**: 위 불만을 해결했음을 강조하는 대책으로 상세페이지 하드카피 1개 - 중요: 허위 과장을 막기 위해, 각 카피를 쓰기 위해 제품이 갖춰야 할 '필수 스펙'!
4. **스펙 체크리스트**: 소싱 시 판매자가 반드시 확인해야 할 체크리스트를 만드세요.

[출력 형식]
반드시 아래 JSON 포맷으로만 출력하세요. 마크다운이나 설명 금지.
{{
    "complaint_patterns": [
        {{"pattern": "불만 내용 요약", "frequency": "예상 빈도(높음/중간/낮음)"}}
    ],
    "semantic_gaps": ["니즈1", "니즈2"],
    "copywriting_suggestions": [
        {{"copy": "카피 문구", "required_spec": "필수 스펙 (예: 무게 1.5kg 이하)"}}
    ],
    "spec_checklist": ["체크항목1", "체크항목2"]
}}
"""

        try:
            response = self.model.generate_content(prompt)
            return self._parse_json_response(response.text)
        except Exception as e:
            print(f"❌ [Gemini] API Error: {str(e)}")
            return self._get_fallback_data()

    def _get_fallback_data(self) -> dict:
        """API 실패 시 기본 데이터 반환 (테스트용)"""
        return {
            "error": "API Error",
            "complaint_patterns": [],
            "copywriting_suggestions": []
        }

    def full_analysis(self, reviews_text: str, product_info: str) -> GeminiAnalysisResult:
        """종합 분석"""
        result = GeminiAnalysisResult(
            success=False,
            analysis_type=AnalysisType.FULL_ANALYSIS
        )

        if not self._initialized:
            if not self.initialize():
                result.error = "Gemini API가 초기화되지 않았습니다."
                return result

        try:
            prompt = self.PROMPTS[AnalysisType.FULL_ANALYSIS].format(
                reviews=reviews_text,
                product_info=product_info
            )
            response = self.model.generate_content(prompt)
            result.raw_response = response.text

            parsed = self._parse_json_response(response.text)

            # 불만 패턴
            if "complaint_patterns" in parsed:
                for p in parsed["complaint_patterns"]:
                    result.complaint_patterns.append(ComplaintPattern(
                        rank=p.get("rank", 0),
                        category=p.get("category", ""),
                        description=p.get("description", ""),
                        frequency=p.get("frequency", ""),
                        severity=p.get("severity", ""),
                        example_quotes=p.get("example_quotes", []),
                        suggested_solution=p.get("suggested_solution", "")
                    ))

            # 시맨틱 갭
            if "semantic_gaps" in parsed:
                for g in parsed["semantic_gaps"]:
                    result.semantic_gaps.append(SemanticGap(
                        gap_type=g.get("gap_type", ""),
                        customer_expectation=g.get("customer_expectation", ""),
                        actual_reality=g.get("actual_reality", ""),
                        impact_level=g.get("impact_level", ""),
                        opportunity=g.get("opportunity", "")
                    ))

            # 카피라이팅
            if "copywriting_suggestions" in parsed:
                for s in parsed["copywriting_suggestions"]:
                    result.copywriting_suggestions.append(CopywritingSuggestion(
                        original_pain_point=s.get("original_pain_point", ""),
                        suggested_copy=s.get("suggested_copy", ""),
                        target_audience=s.get("target_audience", ""),
                        key_benefit=s.get("key_benefit", ""),
                        tone=s.get("tone", "")
                    ))

            # 스펙 체크리스트
            if "spec_checklist" in parsed:
                for c in parsed["spec_checklist"]:
                    result.spec_checklist.append(SpecCheckItem(
                        category=c.get("category", ""),
                        item=c.get("item", ""),
                        reason=c.get("reason", ""),
                        verification_method=c.get("verification_method", "")
                    ))

            result.summary = parsed.get("summary", "")
            result.key_insights = parsed.get("key_insights", [])
            result.success = True

        except Exception as e:
            result.error = str(e)

        return result


# --- Mock Analyzer (API 키 없이 테스트용) ---
class MockGeminiAnalyzer(GeminiAnalyzer):
    """테스트용 Mock Analyzer"""

    def __init__(self):
        super().__init__()
        self._initialized = True  # 항상 초기화된 상태

    def initialize(self) -> bool:
        return True

    def analyze_complaints(self, reviews_text: str) -> GeminiAnalysisResult:
        """Mock 불만 패턴 분석"""
        return GeminiAnalysisResult(
            success=True,
            analysis_type=AnalysisType.COMPLAINT_PATTERN,
            complaint_patterns=[
                ComplaintPattern(
                    rank=1,
                    category="품질",
                    description="전체적인 제품 품질이 기대 이하",
                    frequency="높음",
                    severity="심각",
                    example_quotes=["품질이 너무 별로", "싸구려 느낌"],
                    suggested_solution="품질 검수 강화 및 샘플 테스트 필수"
                ),
                ComplaintPattern(
                    rank=2,
                    category="내구성",
                    description="사용 며칠 만에 파손/고장",
                    frequency="중간",
                    severity="심각",
                    example_quotes=["일주일 만에 부러짐", "내구성 약함"],
                    suggested_solution="내구성 테스트 및 보강재 적용 제품 선택"
                ),
            ],
            summary="품질과 내구성이 주요 불만 사항입니다.",
            key_insights=[
                "저가 제품의 품질 문제가 가장 큰 불만",
                "내구성 관련 불만이 반품/환불로 이어짐",
                "상세 스펙 검증으로 대부분 예방 가능"
            ]
        )


# --- 테스트 실행 코드 ---
if __name__ == "__main__":
    print("="*60)
    print("🤖 Gemini 분석기 테스트 (v3.1)")
    print("="*60)

    # Mock Analyzer로 테스트 (API 키 불필요)
    analyzer = MockGeminiAnalyzer()

    sample_reviews = """
    1. 품질이 너무 별로예요. 사진과 다르고 실밥도 나와있음.
    2. 배송은 빠른데 냄새가 심해요. 환기 필요.
    3. 일주일 만에 부러졌어요. 내구성 약함.
    4. 가격 대비 그냥 그래요.
    5. 색상이 사진과 완전 다름. 실망.
    """

    print("\n[불만 패턴 분석 (Mock)]")
    result = analyzer.analyze_complaints(sample_reviews)

    if result.success:
        print(f"\n요약: {result.summary}")

        print("\n불만 패턴 TOP:")
        for pattern in result.complaint_patterns:
            print(f"\n  #{pattern.rank} {pattern.category}")
            print(f"    설명: {pattern.description}")
            print(f"    빈도: {pattern.frequency}, 심각도: {pattern.severity}")
            print(f"    해결방안: {pattern.suggested_solution}")

        print("\n핵심 인사이트:")
        for insight in result.key_insights:
            print(f"  - {insight}")
    else:
        print(f"분석 실패: {result.error}")

    print("\n" + "="*60)
    print("✅ Gemini 분석기 모듈 준비 완료")
    print("   실제 사용 시 GEMINI_API_KEY 환경변수 설정 필요")
    print("="*60 + "\n")
