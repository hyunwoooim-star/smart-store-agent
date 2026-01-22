"""
review_analyzer.py - 리뷰 분석 모듈 (Phase 5.2)

경쟁사 리뷰 데이터를 분석하여:
1. 치명적 결함 (소싱 포기 사유)
2. 개선 요청 사항 (공장 협의용)
3. 마케팅 소구점 (상세페이지 강조점)

v3.5.2 업데이트:
- Pydantic 모델 추가 (JSON 검증 강화)
- Retry 로직 추가 (3회 재시도 + 지수 백오프)
- 에러 유형별 Exception 클래스

사용법:
    analyzer = ReviewAnalyzer(api_key="your_gemini_key")
    result = await analyzer.analyze(reviews_text)

    if result.verdict == "Drop":
        print("소싱 포기 권장")
"""

import json
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional, Literal
from enum import Enum

from pydantic import BaseModel, Field, validator


# ============================================================
# Custom Exceptions (Phase 5.2)
# ============================================================
class GeminiAPIError(Exception):
    """Gemini API 관련 기본 예외"""
    pass


class GeminiQuotaExceeded(GeminiAPIError):
    """API 할당량 초과"""
    pass


class GeminiTimeout(GeminiAPIError):
    """API 타임아웃"""
    pass


class GeminiInvalidKey(GeminiAPIError):
    """잘못된 API 키"""
    pass


class GeminiParseError(GeminiAPIError):
    """JSON 파싱 실패"""
    pass


# ============================================================
# Pydantic Models (Phase 5.2 - JSON 검증 강화)
# ============================================================
class CriticalDefectModel(BaseModel):
    """치명적 결함 (Pydantic)"""
    issue: str = Field(..., description="문제 설명")
    frequency: Literal["High", "Medium", "Low"] = Field(default="Medium", description="발생 빈도")
    quote: Optional[str] = Field(default=None, description="실제 리뷰 인용")


class ReviewAnalysisModel(BaseModel):
    """리뷰 분석 결과 (Pydantic) - Gemini 출력 검증용"""
    critical_defects: List[CriticalDefectModel] = Field(default_factory=list)
    improvement_requests: List[str] = Field(default_factory=list)
    marketing_hooks: List[str] = Field(default_factory=list)
    summary_one_line: str = Field(default="", description="한 줄 요약")
    sample_check_points: List[str] = Field(default_factory=list)
    verdict: Literal["Go", "Hold", "Drop"] = Field(default="Hold")

    @validator("verdict", pre=True)
    def normalize_verdict(cls, v):
        """verdict 정규화 (대소문자 무시)"""
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower == "go":
                return "Go"
            elif v_lower == "drop":
                return "Drop"
        return "Hold"


class Verdict(Enum):
    """소싱 판단"""
    GO = "Go"       # 소싱 진행
    HOLD = "Hold"   # 추가 검토 필요
    DROP = "Drop"   # 소싱 포기


@dataclass
class CriticalDefect:
    """치명적 결함"""
    issue: str              # 문제 설명
    frequency: str          # "High", "Medium", "Low"
    quote: Optional[str] = None  # 실제 리뷰 인용


@dataclass
class ReviewAnalysisResult:
    """리뷰 분석 결과"""
    critical_defects: List[CriticalDefect] = field(default_factory=list)
    improvement_requests: List[str] = field(default_factory=list)
    marketing_hooks: List[str] = field(default_factory=list)
    verdict: Verdict = Verdict.HOLD
    # v3.5.1 추가 (Gemini 피드백)
    summary_one_line: str = ""  # 한 줄 요약
    sample_check_points: List[str] = field(default_factory=list)  # 샘플 체크리스트
    raw_response: Optional[str] = None

    @property
    def summary(self) -> str:
        if self.verdict == Verdict.GO:
            return "✅ 소싱 진행 권장"
        elif self.verdict == Verdict.HOLD:
            return "⚠️ 추가 검토 필요"
        else:
            return "❌ 소싱 포기 권장"

    @property
    def has_critical_issues(self) -> bool:
        return any(d.frequency == "High" for d in self.critical_defects)


# 카테고리별 분석 포인트 (Dynamic Context Injection)
CATEGORY_CONTEXT = {
    "의류": "핏, 마감, 세탁 후 변형, 사이즈 정확도, 원단 품질",
    "가구": "조립 난이도, 냄새, 흔들림, 내구성, 배송 파손",
    "전자기기": "발열, 배터리 수명, 오작동, 소음, 호환성",
    "주방용품": "코팅 벗겨짐, 세척 편의성, 냄새 배임, 내열성",
    "캠핑/레저": "내구성, 무게, 방수 성능, 조립 편의성",
    "화장품": "피부 트러블, 발림성, 향, 지속력, 용량",
    "기타": "전반적인 품질, 가성비, 사용 편의성",
}

# Gemini 분석 프롬프트 (Phase 5.1 - v3.5.1 업데이트)
REVIEW_ANALYSIS_PROMPT = """당신은 연 매출 100억 쇼핑몰의 수석 MD이자 상품 기획자입니다.
수집된 리뷰 데이터를 분석하여, 이 상품을 소싱할 때 '반드시 개선해야 할 점'과 '강조해야 할 점'을 도출하십시오.

[상품 카테고리] {category}
[카테고리별 중점 분석 포인트] {category_focus}

[분석 지침]
1. **Noise Filtering**: "배송이 늦어요", "박스가 찌그러졌어요" 같은 단순 CS는 무시하십시오. 오직 '제품 자체'에 집중하십시오.
2. **Severity Scoring**: 같은 불만이 반복되면 가중치를 높이십시오.
3. **Sentiment Gap**: 고객이 기대했으나 실망한 포인트(Gap)를 찾으십시오.
4. **Category Specific Check**: 위에 명시된 카테고리별 중점 포인트에 집중하십시오.

[출력 형식 (JSON만 출력 - 마크다운/인사말 금지)]
{{
  "critical_defects": [
    {{"issue": "세탁 후 수축 심함", "frequency": "High", "quote": "한 번 빨았더니 아기 옷이 됐어요"}}
  ],
  "improvement_requests": [
    "마감 실밥 처리 강화 요청",
    "매뉴얼에 한국어 설명 추가 필요"
  ],
  "marketing_hooks": [
    "예상보다 훨씬 가벼움 (무게 강조)",
    "색감이 화면과 똑같음 (실사 강조)"
  ],
  "summary_one_line": "마감 이슈가 있으나 가격 대비 성능이 우수하여 소싱 추천",
  "sample_check_points": [
    "실밥 마감 상태 확인",
    "세탁 테스트 진행",
    "실측 사이즈 측정"
  ],
  "verdict": "Go"
}}

[verdict 기준]
- "Go": 치명적 결함 없음, 소싱 진행 권장
- "Hold": 일부 이슈 있으나 샘플 확인 후 결정
- "Drop": 치명적 결함으로 소싱 포기 권장

[리뷰 데이터]
{reviews}
"""


class ReviewAnalyzer:
    """리뷰 분석기 (Gemini API 사용) - v3.5.2

    Phase 5.2 업데이트:
    - Pydantic 모델로 JSON 검증 강화
    - 3회 재시도 + 지수 백오프
    - 에러 유형별 예외 처리

    Example:
        analyzer = ReviewAnalyzer(api_key="your_key")
        result = await analyzer.analyze("좋아요! 근데 실밥이 좀...")

        print(result.verdict)  # Verdict.HOLD
        print(result.marketing_hooks)  # ["..."]
    """

    # 재시도 설정
    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 4]  # 지수 백오프: 1초, 2초, 4초

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Google API 키 (환경변수 GOOGLE_API_KEY 사용 가능)
        """
        import os
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY 환경변수 또는 api_key 파라미터 필요")

    def _classify_error(self, error: Exception) -> GeminiAPIError:
        """에러 유형 분류"""
        msg = str(error).lower()
        if "quota" in msg or "429" in msg or "rate" in msg:
            return GeminiQuotaExceeded(f"API 할당량 초과: {error}")
        elif "timeout" in msg or "timed out" in msg:
            return GeminiTimeout(f"API 타임아웃: {error}")
        elif "api_key" in msg or "invalid" in msg or "401" in msg:
            return GeminiInvalidKey(f"잘못된 API 키: {error}")
        else:
            return GeminiAPIError(f"Gemini API 오류: {error}")

    async def analyze(self, reviews_text: str, category: str = "기타") -> ReviewAnalysisResult:
        """리뷰 텍스트 분석 (비동기 + 재시도)

        Args:
            reviews_text: 분석할 리뷰 텍스트 (줄바꿈으로 구분)
            category: 상품 카테고리 (의류, 가구, 전자기기 등)

        Returns:
            ReviewAnalysisResult: 분석 결과
        """
        import asyncio
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        category_focus = CATEGORY_CONTEXT.get(category, CATEGORY_CONTEXT["기타"])
        prompt = REVIEW_ANALYSIS_PROMPT.format(
            reviews=reviews_text,
            category=category,
            category_focus=category_focus
        )

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await model.generate_content_async(prompt)
                return self._parse_response_with_pydantic(response.text)
            except GeminiParseError as e:
                # JSON 파싱 실패 시 재시도
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    print(f"[Retry {attempt + 1}/{self.MAX_RETRIES}] JSON 파싱 실패, {self.RETRY_DELAYS[attempt]}초 후 재시도...")
                    await asyncio.sleep(self.RETRY_DELAYS[attempt])
            except Exception as e:
                classified_error = self._classify_error(e)
                # 할당량 초과나 인증 오류는 재시도 불필요
                if isinstance(classified_error, (GeminiQuotaExceeded, GeminiInvalidKey)):
                    raise classified_error
                last_error = classified_error
                if attempt < self.MAX_RETRIES - 1:
                    print(f"[Retry {attempt + 1}/{self.MAX_RETRIES}] {classified_error}, {self.RETRY_DELAYS[attempt]}초 후 재시도...")
                    await asyncio.sleep(self.RETRY_DELAYS[attempt])

        # 모든 재시도 실패
        print(f"모든 재시도 실패: {last_error}")
        return ReviewAnalysisResult(
            verdict=Verdict.HOLD,
            raw_response=str(last_error)
        )

    def analyze_sync(self, reviews_text: str, category: str = "기타") -> ReviewAnalysisResult:
        """동기 버전 리뷰 분석 (재시도 포함)

        Args:
            reviews_text: 분석할 리뷰 텍스트
            category: 상품 카테고리 (의류, 가구, 전자기기 등)

        Returns:
            ReviewAnalysisResult: 분석 결과
        """
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        category_focus = CATEGORY_CONTEXT.get(category, CATEGORY_CONTEXT["기타"])
        prompt = REVIEW_ANALYSIS_PROMPT.format(
            reviews=reviews_text,
            category=category,
            category_focus=category_focus
        )

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = model.generate_content(prompt)
                return self._parse_response_with_pydantic(response.text)
            except GeminiParseError as e:
                # JSON 파싱 실패 시 재시도
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    print(f"[Retry {attempt + 1}/{self.MAX_RETRIES}] JSON 파싱 실패, {self.RETRY_DELAYS[attempt]}초 후 재시도...")
                    time.sleep(self.RETRY_DELAYS[attempt])
            except Exception as e:
                classified_error = self._classify_error(e)
                # 할당량 초과나 인증 오류는 재시도 불필요
                if isinstance(classified_error, (GeminiQuotaExceeded, GeminiInvalidKey)):
                    raise classified_error
                last_error = classified_error
                if attempt < self.MAX_RETRIES - 1:
                    print(f"[Retry {attempt + 1}/{self.MAX_RETRIES}] {classified_error}, {self.RETRY_DELAYS[attempt]}초 후 재시도...")
                    time.sleep(self.RETRY_DELAYS[attempt])

        # 모든 재시도 실패
        print(f"모든 재시도 실패: {last_error}")
        return ReviewAnalysisResult(
            verdict=Verdict.HOLD,
            raw_response=str(last_error)
        )

    def _parse_response_with_pydantic(self, response_text: str) -> ReviewAnalysisResult:
        """Pydantic을 사용한 Gemini 응답 파싱 (v3.5.2)

        Args:
            response_text: Gemini 응답 텍스트

        Returns:
            ReviewAnalysisResult: 파싱된 결과

        Raises:
            GeminiParseError: JSON 파싱 실패 시
        """
        try:
            # JSON 추출 (코드 블록 제거)
            json_str = response_text.strip()
            json_str = re.sub(r'^```json\s*', '', json_str)
            json_str = re.sub(r'\s*```$', '', json_str)
            # 일반 코드 블록도 제거
            json_str = re.sub(r'^```\s*', '', json_str)

            # Pydantic 모델로 검증
            data = json.loads(json_str)
            validated = ReviewAnalysisModel(**data)

            # Pydantic -> dataclass 변환
            critical_defects = [
                CriticalDefect(
                    issue=d.issue,
                    frequency=d.frequency,
                    quote=d.quote
                )
                for d in validated.critical_defects
            ]

            verdict_map = {"Go": Verdict.GO, "Hold": Verdict.HOLD, "Drop": Verdict.DROP}
            verdict = verdict_map.get(validated.verdict, Verdict.HOLD)

            return ReviewAnalysisResult(
                critical_defects=critical_defects,
                improvement_requests=validated.improvement_requests,
                marketing_hooks=validated.marketing_hooks,
                verdict=verdict,
                summary_one_line=validated.summary_one_line,
                sample_check_points=validated.sample_check_points,
                raw_response=response_text
            )

        except json.JSONDecodeError as e:
            raise GeminiParseError(f"JSON 파싱 실패: {e}")
        except Exception as e:
            raise GeminiParseError(f"Pydantic 검증 실패: {e}")

    def _parse_response(self, response_text: str) -> ReviewAnalysisResult:
        """레거시 파싱 (하위 호환용)"""
        try:
            return self._parse_response_with_pydantic(response_text)
        except GeminiParseError:
            return ReviewAnalysisResult(
                verdict=Verdict.HOLD,
                raw_response=response_text
            )

    def format_report(self, result: ReviewAnalysisResult) -> str:
        """분석 결과 리포트 포맷

        Args:
            result: 분석 결과

        Returns:
            str: 포맷된 리포트
        """
        lines = [
            "=" * 50,
            "📊 리뷰 분석 결과 (Phase 5.1)",
            "=" * 50,
            "",
            f"판정: {result.summary}",
        ]

        # 한 줄 요약 (v3.5.1 추가)
        if result.summary_one_line:
            lines.append(f"📝 {result.summary_one_line}")
        lines.append("")

        # 치명적 결함
        if result.critical_defects:
            lines.append("🚨 치명적 결함")
            lines.append("-" * 30)
            for i, d in enumerate(result.critical_defects, 1):
                freq_icon = "🔴" if d.frequency == "High" else "🟡" if d.frequency == "Medium" else "🟢"
                lines.append(f"  {i}. {freq_icon} {d.issue} [{d.frequency}]")
                if d.quote:
                    lines.append(f"     💬 \"{d.quote}\"")
            lines.append("")

        # 개선 요청
        if result.improvement_requests:
            lines.append("🔧 공장 협의 사항")
            lines.append("-" * 30)
            for item in result.improvement_requests:
                lines.append(f"  • {item}")
            lines.append("")

        # 마케팅 소구점
        if result.marketing_hooks:
            lines.append("💡 상세페이지 강조점")
            lines.append("-" * 30)
            for item in result.marketing_hooks:
                lines.append(f"  • {item}")
            lines.append("")

        # 샘플 체크리스트 (v3.5.1 추가)
        if result.sample_check_points:
            lines.append("✅ 샘플 수령 시 체크리스트")
            lines.append("-" * 30)
            for i, item in enumerate(result.sample_check_points, 1):
                lines.append(f"  {i}. {item}")
            lines.append("")

        lines.append("=" * 50)
        return "\n".join(lines)


# 편의 함수
def analyze_reviews(reviews_text: str, api_key: Optional[str] = None) -> ReviewAnalysisResult:
    """간편 리뷰 분석 함수 (동기)

    Args:
        reviews_text: 분석할 리뷰 텍스트
        api_key: Google API 키 (선택)

    Returns:
        ReviewAnalysisResult: 분석 결과
    """
    analyzer = ReviewAnalyzer(api_key=api_key)
    return analyzer.analyze_sync(reviews_text)


# Mock 분석기 (테스트용)
class MockReviewAnalyzer:
    """Mock 리뷰 분석기 (테스트/데모용)"""

    def analyze_sync(self, reviews_text: str, category: str = "기타") -> ReviewAnalysisResult:
        """Mock 분석 결과 반환"""
        return ReviewAnalysisResult(
            critical_defects=[
                CriticalDefect(
                    issue="세탁 후 수축 심함",
                    frequency="High",
                    quote="한 번 빨았더니 아기 옷이 됐어요"
                ),
                CriticalDefect(
                    issue="실밥 마감 불량",
                    frequency="Medium",
                    quote="실밥이 좀 튀어나와 있어요"
                ),
            ],
            improvement_requests=[
                "세탁 시 수축률 개선 요청 (Pre-shrunk 처리)",
                "실밥 마감 2중 검수 요청",
                "사이즈 가이드 정확도 개선",
            ],
            marketing_hooks=[
                "색감이 사진과 똑같음 (실사 강조)",
                "예상보다 두꺼운 원단 (고급스러움)",
                "빠른 배송 만족 (익일배송 강조)",
            ],
            verdict=Verdict.HOLD,
            summary_one_line="마감 이슈가 있으나 가격 대비 성능이 우수하여 샘플 확인 후 결정",
            sample_check_points=[
                "실밥 마감 상태 꼼꼼히 확인",
                "세탁 테스트 진행 (수축률 확인)",
                "실측 사이즈 측정 후 가이드와 비교",
                "지퍼/단추 등 부자재 작동 확인",
            ],
            raw_response="Mock response"
        )

    def format_report(self, result: ReviewAnalysisResult) -> str:
        """리포트 포맷"""
        analyzer = ReviewAnalyzer.__new__(ReviewAnalyzer)
        return analyzer.format_report(result)
