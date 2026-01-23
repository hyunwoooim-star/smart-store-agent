"""
test_market_researcher.py - 시장 조사 모듈 테스트
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analyzers.market_researcher import (
    MarketResearcher,
    MockMarketResearcher,
    MarketResearchResult,
    CompetitorProduct,
    create_researcher,
)


class TestCompetitorProduct:
    """CompetitorProduct 테스트"""

    def test_basic_product(self):
        """기본 상품 생성"""
        product = CompetitorProduct(
            title="테스트 상품",
            price=35000,
            url="https://example.com",
            source="네이버쇼핑"
        )
        assert product.title == "테스트 상품"
        assert product.price == 35000
        assert product.source == "네이버쇼핑"
        assert product.review_count == 0  # 기본값
        assert product.rating == 0.0  # 기본값

    def test_full_product(self):
        """전체 필드 상품 생성"""
        product = CompetitorProduct(
            title="인기 상품",
            price=42000,
            url="https://smartstore.naver.com/shop/1",
            source="스마트스토어",
            review_count=256,
            rating=4.7,
            thumbnail="https://img.example.com/thumb.jpg"
        )
        assert product.review_count == 256
        assert product.rating == 4.7
        assert product.thumbnail != ""


class TestMarketResearchResult:
    """MarketResearchResult 테스트"""

    def test_basic_result(self):
        """기본 결과"""
        result = MarketResearchResult(
            query="캠핑의자",
            competitors=[],
            price_range=(30000, 50000),
            average_price=40000,
            recommended_price=36000,
            price_strategy="테스트 전략",
            search_method="text"
        )
        assert result.query == "캠핑의자"
        assert result.average_price == 40000
        assert result.search_method == "text"

    def test_result_with_competitors(self):
        """경쟁사 포함 결과"""
        competitors = [
            CompetitorProduct(
                title="상품 A",
                price=35000,
                url="https://a.com",
                source="네이버"
            ),
            CompetitorProduct(
                title="상품 B",
                price=45000,
                url="https://b.com",
                source="쿠팡"
            ),
        ]

        result = MarketResearchResult(
            query="테스트",
            competitors=competitors,
            price_range=(35000, 45000),
            average_price=40000,
            recommended_price=36000,
            price_strategy="전략 설명",
            search_method="text"
        )
        assert len(result.competitors) == 2
        assert result.price_range[0] == 35000
        assert result.price_range[1] == 45000


class TestMarketResearcher:
    """MarketResearcher 테스트"""

    def test_init_without_keys(self):
        """API 키 없이 초기화"""
        researcher = MarketResearcher()
        assert researcher.naver_client_id is None or researcher.naver_client_id == ""
        # Mock 모드로 동작해야 함

    def test_init_with_keys(self):
        """API 키로 초기화"""
        researcher = MarketResearcher(
            naver_client_id="test_id",
            naver_client_secret="test_secret",
            serpapi_key="test_key"
        )
        assert researcher.naver_client_id == "test_id"
        assert researcher.serpapi_key == "test_key"

    def test_research_by_text_mock(self):
        """텍스트 검색 (Mock)"""
        researcher = MarketResearcher()  # API 키 없음 → Mock 모드
        result = researcher.research_by_text("캠핑의자", max_results=5)

        assert isinstance(result, MarketResearchResult)
        assert result.query == "캠핑의자"
        assert len(result.competitors) > 0
        assert result.average_price > 0
        assert result.recommended_price > 0
        assert result.search_method == "text"

    def test_research_by_image_mock(self):
        """이미지 검색 (Mock)"""
        researcher = MarketResearcher()  # API 키 없음 → Mock 모드
        result = researcher.research_by_image(
            "https://example.com/product.jpg",
            max_results=5
        )

        assert isinstance(result, MarketResearchResult)
        assert len(result.competitors) > 0
        assert result.search_method == "image"

    def test_price_strategy_generation(self):
        """가격 전략 생성"""
        researcher = MarketResearcher()
        result = researcher.research_by_text("유아 승용완구")

        # 가격 전략이 생성되었는지 확인
        assert result.price_strategy != ""
        assert "경쟁사" in result.price_strategy
        assert "추천 목표가" in result.price_strategy

    def test_recommended_price_logic(self):
        """추천 가격 로직 검증"""
        researcher = MarketResearcher()
        result = researcher.research_by_text("테스트 상품")

        # 추천가 = 평균가의 ~90% (단, 최저가 이상)
        assert result.recommended_price <= result.average_price
        assert result.recommended_price >= result.price_range[0]


class TestPriceParser:
    """가격 파싱 테스트"""

    def test_parse_korean_price(self):
        """한국 원화 파싱"""
        researcher = MarketResearcher()

        assert researcher._parse_price("45,000원") == 45000
        assert researcher._parse_price("₩38,500") == 38500
        assert researcher._parse_price("35000") == 35000

    def test_parse_usd_price(self):
        """USD 파싱 (환율 적용)"""
        researcher = MarketResearcher()

        price = researcher._parse_price("$50")
        assert price == 65000  # 50 * 1300

    def test_parse_cny_price(self):
        """CNY 파싱 (환율 적용)"""
        researcher = MarketResearcher()

        price = researcher._parse_price("¥100")
        assert price == 19000  # 100 * 190

    def test_parse_empty_price(self):
        """빈 가격"""
        researcher = MarketResearcher()

        assert researcher._parse_price("") == 0
        assert researcher._parse_price(None) == 0


class TestCleanHtml:
    """HTML 클리닝 테스트"""

    def test_clean_simple_html(self):
        """간단한 HTML 태그 제거"""
        researcher = MarketResearcher()

        assert researcher._clean_html("<b>테스트</b>") == "테스트"
        assert researcher._clean_html("<span class='red'>상품</span>") == "상품"

    def test_clean_nested_html(self):
        """중첩 HTML 태그 제거"""
        researcher = MarketResearcher()

        result = researcher._clean_html("<div><b>캠핑</b> <i>의자</i></div>")
        assert result == "캠핑 의자"


class TestMockMarketResearcher:
    """Mock 클래스 테스트"""

    def test_mock_text_search(self):
        """Mock 텍스트 검색"""
        mock = MockMarketResearcher()
        result = mock.research_by_text("테스트")

        assert isinstance(result, MarketResearchResult)
        assert len(result.competitors) == 2
        assert result.search_method == "text"

    def test_mock_image_search(self):
        """Mock 이미지 검색"""
        mock = MockMarketResearcher()
        result = mock.research_by_image("https://example.com/img.jpg")

        assert isinstance(result, MarketResearchResult)
        assert result.search_method == "text"  # Mock은 text 검색으로 대체


class TestCreateResearcher:
    """팩토리 함수 테스트"""

    def test_create_mock(self):
        """Mock 모드"""
        researcher = create_researcher(use_mock=True)
        assert isinstance(researcher, MockMarketResearcher)

    def test_create_real(self):
        """실제 모드"""
        researcher = create_researcher(use_mock=False)
        assert isinstance(researcher, MarketResearcher)


class TestIntegration:
    """통합 테스트"""

    def test_full_workflow_text(self):
        """텍스트 검색 전체 워크플로우"""
        researcher = create_researcher(use_mock=True)
        result = researcher.research_by_text("유아 승용완구 애벌레카")

        # 결과 검증
        assert result.query != ""
        assert len(result.competitors) >= 1
        assert result.price_range[0] <= result.price_range[1]
        assert result.average_price > 0
        assert result.recommended_price > 0
        assert result.price_strategy != ""

        # 경쟁사 정보 검증
        for comp in result.competitors:
            assert comp.title != ""
            assert comp.price > 0
            assert comp.source != ""

    def test_full_workflow_image(self):
        """이미지 검색 전체 워크플로우"""
        researcher = MarketResearcher()  # Mock 모드 (API 키 없음)
        result = researcher.research_by_image(
            "https://img.alicdn.com/imgextra/product.jpg"
        )

        # 결과 검증
        assert isinstance(result, MarketResearchResult)
        assert result.search_method == "image"


# pytest 실행용
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
