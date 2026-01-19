"""gap_reporter.py 테스트"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from generators.gap_reporter import (
    GapReporter,
    OpportunityReport,
    OpportunityScore
)


class TestGapReporter:
    """리포트 생성기 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.reporter = GapReporter(output_dir="test_output")

    def teardown_method(self):
        """테스트 정리"""
        # 테스트 출력 디렉토리 정리
        import shutil
        if os.path.exists("test_output"):
            shutil.rmtree("test_output")

    def test_create_report_basic(self):
        """기본 리포트 생성 테스트"""
        report = self.reporter.create_report(
            product_name="테스트 상품",
            category="테스트"
        )

        assert isinstance(report, OpportunityReport)
        assert report.product_name == "테스트 상품"
        assert report.category == "테스트"
        assert report.report_id is not None

    def test_create_report_with_data(self):
        """데이터 포함 리포트 생성 테스트"""
        keywords = [
            {"keyword": "테스트", "monthly_search_volume": 10000, "competition_rate": 0.5, "opportunity_score": 10.0}
        ]
        margin = {
            "margin_percent": 25.0,
            "is_viable": True,
            "total_cost_krw": 30000,
            "breakeven_price_krw": 35000
        }

        report = self.reporter.create_report(
            product_name="테스트 상품",
            category="테스트",
            keywords=keywords,
            margin_result=margin
        )

        assert len(report.target_keywords) == 1
        assert report.margin_analysis["margin_percent"] == 25.0

    def test_opportunity_score_calculation(self):
        """기회 점수 계산 테스트"""
        score = OpportunityScore(
            keyword_score=70,
            margin_score=80,
            competition_score=60,
            risk_score=20
        )
        total = score.calculate_total()

        assert total > 0
        assert score.total_score == total

    def test_keyword_score_calculation(self):
        """키워드 점수 계산 테스트"""
        keywords = [
            {"opportunity_score": 10.0, "monthly_search_volume": 50000},
            {"opportunity_score": 8.0, "monthly_search_volume": 30000},
        ]

        score = self.reporter._calculate_keyword_score(keywords)
        assert score > 0
        assert score <= 100

    def test_margin_score_calculation(self):
        """마진 점수 계산 테스트"""
        # 30% 이상 → 100점
        assert self.reporter._calculate_margin_score(35) == 100.0

        # 20% 이상 → 80점
        assert self.reporter._calculate_margin_score(25) == 80.0

        # 15% 이상 → 60점
        assert self.reporter._calculate_margin_score(17) == 60.0

        # 음수 → 0점
        assert self.reporter._calculate_margin_score(-10) == 0.0

    def test_competition_score_calculation(self):
        """경쟁 점수 계산 테스트"""
        # 낮은 경쟁 → 높은 점수
        assert self.reporter._calculate_competition_score(0.2) == 100.0
        assert self.reporter._calculate_competition_score(0.4) == 80.0

        # 높은 경쟁 → 낮은 점수
        assert self.reporter._calculate_competition_score(3.0) == 20.0
        assert self.reporter._calculate_competition_score(10.0) == 10.0

    def test_to_markdown(self):
        """마크다운 변환 테스트"""
        report = self.reporter.create_report(
            product_name="마크다운 테스트",
            category="테스트"
        )

        markdown = self.reporter.to_markdown(report)

        assert "# " in markdown  # 헤더
        assert "마크다운 테스트" in markdown
        assert "종합 점수" in markdown

    def test_to_json(self):
        """JSON 변환 테스트"""
        report = self.reporter.create_report(
            product_name="JSON 테스트",
            category="테스트"
        )

        json_str = self.reporter.to_json(report)
        data = json.loads(json_str)

        assert data["product_name"] == "JSON 테스트"
        assert "opportunity_score" in data
        assert "total_score" in data["opportunity_score"]

    def test_save_report(self):
        """리포트 저장 테스트"""
        report = self.reporter.create_report(
            product_name="저장 테스트",
            category="테스트"
        )

        filepath = self.reporter.save_report(report)

        assert os.path.exists(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "저장 테스트" in content

    def test_recommendation_generation(self):
        """추천 생성 테스트"""
        # 고점수 + 고마진 → 강력 추천
        score = OpportunityScore(keyword_score=80, margin_score=90, competition_score=70, risk_score=10)
        score.calculate_total()
        margin = {"margin_percent": 25}

        rec = self.reporter._generate_recommendation(score, margin, [])
        assert "추천" in rec or "✅" in rec

    def test_action_items_generation(self):
        """액션 아이템 생성 테스트"""
        score = OpportunityScore()
        score.keyword_score = 70

        margin = {"margin_percent": 10}  # 낮은 마진
        patterns = [{"category": "품질"}]

        items = self.reporter._generate_action_items(score, margin, patterns)

        assert len(items) > 0
        # 마진이 낮으면 가격/비용 관련 액션이 있어야 함
        assert any("판매가" in item or "비용" in item or "SEO" in item for item in items)

    def test_risk_score_calculation(self):
        """리스크 점수 계산 테스트"""
        # 리스크 없음 → 0점
        assert self.reporter._calculate_risk_score([]) == 0

        # 리스크 많음 → 높은 점수
        risks = ["리스크1", "리스크2", "리스크3", "리스크4"]
        assert self.reporter._calculate_risk_score(risks) >= 60


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
