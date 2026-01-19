"""gemini_analyzer.py 테스트"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from analyzers.gemini_analyzer import (
    GeminiAnalyzer,
    MockGeminiAnalyzer,
    GeminiAnalysisResult,
    AnalysisType,
    ComplaintPattern,
    SemanticGap,
    CopywritingSuggestion,
    SpecCheckItem
)


class TestGeminiAnalyzer:
    """Gemini 분석기 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.analyzer = MockGeminiAnalyzer()

    def test_mock_analyzer_initialization(self):
        """Mock 분석기 초기화 테스트"""
        assert self.analyzer.initialize() == True
        assert self.analyzer._initialized == True

    def test_analyze_complaints(self):
        """불만 패턴 분석 테스트"""
        reviews = """
        1. 품질이 너무 별로예요.
        2. 냄새가 심해요.
        3. 일주일 만에 부러졌어요.
        """

        result = self.analyzer.analyze_complaints(reviews)

        assert result.success == True
        assert result.analysis_type == AnalysisType.COMPLAINT_PATTERN
        assert len(result.complaint_patterns) > 0

    def test_complaint_pattern_structure(self):
        """불만 패턴 구조 테스트"""
        pattern = ComplaintPattern(
            rank=1,
            category="품질",
            description="품질 불만",
            frequency="높음",
            severity="심각",
            example_quotes=["품질이 별로"],
            suggested_solution="품질 검수 강화"
        )

        assert pattern.rank == 1
        assert pattern.category == "품질"
        assert pattern.frequency == "높음"
        assert len(pattern.example_quotes) == 1

    def test_semantic_gap_structure(self):
        """시맨틱 갭 구조 테스트"""
        gap = SemanticGap(
            gap_type="품질",
            customer_expectation="고품질 제품",
            actual_reality="저품질",
            impact_level="높음",
            opportunity="품질 개선 기회"
        )

        assert gap.gap_type == "품질"
        assert gap.impact_level == "높음"

    def test_copywriting_suggestion_structure(self):
        """카피라이팅 제안 구조 테스트"""
        suggestion = CopywritingSuggestion(
            original_pain_point="품질 불만",
            suggested_copy="검증된 품질, 믿을 수 있는 선택",
            target_audience="품질 중시 소비자",
            key_benefit="검증된 품질",
            tone="신뢰"
        )

        assert suggestion.suggested_copy != ""
        assert suggestion.tone == "신뢰"

    def test_spec_check_item_structure(self):
        """스펙 체크 항목 구조 테스트"""
        item = SpecCheckItem(
            category="필수",
            item="무게 확인",
            reason="배송비 계산",
            verification_method="저울 측정"
        )

        assert item.category == "필수"
        assert item.item == "무게 확인"

    def test_analysis_result_structure(self):
        """분석 결과 구조 테스트"""
        result = GeminiAnalysisResult(
            success=True,
            analysis_type=AnalysisType.FULL_ANALYSIS,
            summary="테스트 요약",
            key_insights=["인사이트1", "인사이트2"]
        )

        assert result.success == True
        assert len(result.key_insights) == 2

    def test_mock_complaint_patterns(self):
        """Mock 불만 패턴 분석 결과 테스트"""
        result = self.analyzer.analyze_complaints("테스트 리뷰")

        if result.success:
            assert len(result.complaint_patterns) >= 1

            first_pattern = result.complaint_patterns[0]
            assert first_pattern.rank == 1
            assert first_pattern.category != ""
            assert first_pattern.suggested_solution != ""

    def test_analysis_types(self):
        """분석 유형 테스트"""
        assert AnalysisType.COMPLAINT_PATTERN.value == "complaint_pattern"
        assert AnalysisType.SEMANTIC_GAP.value == "semantic_gap"
        assert AnalysisType.COPYWRITING.value == "copywriting"
        assert AnalysisType.SPEC_CHECKLIST.value == "spec_checklist"
        assert AnalysisType.FULL_ANALYSIS.value == "full_analysis"

    def test_prompts_exist(self):
        """프롬프트 템플릿 존재 테스트"""
        assert AnalysisType.COMPLAINT_PATTERN in GeminiAnalyzer.PROMPTS
        assert AnalysisType.SEMANTIC_GAP in GeminiAnalyzer.PROMPTS
        assert AnalysisType.COPYWRITING in GeminiAnalyzer.PROMPTS
        assert AnalysisType.SPEC_CHECKLIST in GeminiAnalyzer.PROMPTS
        assert AnalysisType.FULL_ANALYSIS in GeminiAnalyzer.PROMPTS

    def test_real_analyzer_without_api_key(self):
        """API 키 없는 실제 분석기 테스트"""
        real_analyzer = GeminiAnalyzer()  # API 키 없음

        # 초기화 실패해야 함
        assert real_analyzer.initialize() == False

    def test_result_with_error(self):
        """에러 포함 결과 테스트"""
        result = GeminiAnalysisResult(
            success=False,
            analysis_type=AnalysisType.COMPLAINT_PATTERN,
            error="API 키가 설정되지 않았습니다."
        )

        assert result.success == False
        assert result.error is not None
        assert "API" in result.error


class TestMockGeminiAnalyzer:
    """Mock Gemini 분석기 상세 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.mock = MockGeminiAnalyzer()

    def test_always_initialized(self):
        """항상 초기화된 상태 테스트"""
        assert self.mock._initialized == True

    def test_analyze_returns_mock_data(self):
        """Mock 데이터 반환 테스트"""
        result = self.mock.analyze_complaints("아무 텍스트")

        assert result.success == True
        assert result.summary != ""
        assert len(result.key_insights) > 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
