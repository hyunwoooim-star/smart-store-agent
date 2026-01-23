"""
test_alibaba_scraper.py - 1688 스크래퍼 테스트 (Phase 7)

테스트 항목:
1. 가격 파싱 (범위 → 최대값)
2. 무게/사이즈 변환
3. Mock 스크래퍼 동작
4. 도메인 모델 변환
"""

import pytest
import asyncio
import sys
from pathlib import Path

# 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.alibaba_scraper import (
    AlibabaScraper,
    MockAlibabaScraper,
    ScrapedProduct,
    scrape_1688,
)


class TestPriceParsing:
    """가격 파싱 테스트 (방어적 계산: 최대값 선택)"""

    def setup_method(self):
        # API 토큰 없이 테스트하기 위해 임시로 토큰 설정
        import os
        self.original_token = os.getenv("APIFY_API_TOKEN")
        os.environ["APIFY_API_TOKEN"] = "test_token_for_parsing"
        self.scraper = AlibabaScraper()

    def teardown_method(self):
        import os
        if self.original_token:
            os.environ["APIFY_API_TOKEN"] = self.original_token
        elif "APIFY_API_TOKEN" in os.environ:
            del os.environ["APIFY_API_TOKEN"]

    def test_single_price(self):
        """단일 가격"""
        assert self.scraper._extract_max_price("10.00") == 10.0
        assert self.scraper._extract_max_price(10.0) == 10.0
        assert self.scraper._extract_max_price(10) == 10.0

    def test_price_range_dash(self):
        """범위 가격 (대시)"""
        assert self.scraper._extract_max_price("10.00-20.00") == 20.0
        assert self.scraper._extract_max_price("10-20") == 20.0

    def test_price_range_tilde(self):
        """범위 가격 (물결)"""
        assert self.scraper._extract_max_price("10~20") == 20.0
        assert self.scraper._extract_max_price("¥10~¥20") == 20.0

    def test_price_range_chinese(self):
        """범위 가격 (중국어)"""
        assert self.scraper._extract_max_price("10至20") == 20.0

    def test_price_dict(self):
        """dict 형태 가격"""
        assert self.scraper._extract_max_price({"min": 10, "max": 20}) == 20.0
        assert self.scraper._extract_max_price({"low": 5, "high": 15}) == 15.0
        assert self.scraper._extract_max_price({"price": 30}) == 30.0

    def test_price_list(self):
        """리스트 형태 가격"""
        assert self.scraper._extract_max_price([10, 20, 30]) == 30.0
        assert self.scraper._extract_max_price([5.5, 8.8]) == 8.8

    def test_price_with_currency(self):
        """통화 기호 포함"""
        assert self.scraper._extract_max_price("¥45.00") == 45.0
        assert self.scraper._extract_max_price("￥100") == 100.0
        assert self.scraper._extract_max_price("$50") == 50.0

    def test_price_with_comma(self):
        """천 단위 구분자"""
        assert self.scraper._extract_max_price("1,000") == 1000.0
        assert self.scraper._extract_max_price("10,000.50") == 10000.5

    def test_price_empty(self):
        """빈 값"""
        assert self.scraper._extract_max_price(None) == 0.0
        assert self.scraper._extract_max_price("") == 0.0
        assert self.scraper._extract_max_price({}) == 0.0


class TestWeightParsing:
    """무게 파싱 테스트"""

    def setup_method(self):
        import os
        self.original_token = os.getenv("APIFY_API_TOKEN")
        os.environ["APIFY_API_TOKEN"] = "test_token_for_weight"
        self.scraper = AlibabaScraper()

    def teardown_method(self):
        import os
        if self.original_token:
            os.environ["APIFY_API_TOKEN"] = self.original_token
        elif "APIFY_API_TOKEN" in os.environ:
            del os.environ["APIFY_API_TOKEN"]

    def test_weight_kg(self):
        """kg 단위"""
        assert self.scraper._convert_weight("2.5kg") == 2.5
        assert self.scraper._convert_weight("2.5 kg") == 2.5
        assert self.scraper._convert_weight(2.5) == 2.5

    def test_weight_g_to_kg(self):
        """g → kg 변환"""
        assert self.scraper._convert_weight("2500g") == 2.5
        assert self.scraper._convert_weight("500g") == 0.5

    def test_weight_auto_detect(self):
        """단위 자동 감지 (100 이상 → g)"""
        assert self.scraper._convert_weight(2500) == 2.5
        assert self.scraper._convert_weight(50) == 50.0  # 50kg

    def test_weight_from_specs(self):
        """스펙에서 무게 추출"""
        data = {}
        specs = {"重量": "2.5kg", "材质": "알루미늄"}
        result = self.scraper._parse_weight(data, specs)
        assert result == 2.5


class TestDimensionParsing:
    """치수 파싱 테스트"""

    def setup_method(self):
        import os
        self.original_token = os.getenv("APIFY_API_TOKEN")
        os.environ["APIFY_API_TOKEN"] = "test_token_for_dimension"
        self.scraper = AlibabaScraper()

    def teardown_method(self):
        import os
        if self.original_token:
            os.environ["APIFY_API_TOKEN"] = self.original_token
        elif "APIFY_API_TOKEN" in os.environ:
            del os.environ["APIFY_API_TOKEN"]

    def test_dimension_string(self):
        """'가로x세로x높이' 문자열"""
        result = self.scraper._parse_dimension_string("80*20*15cm")
        assert result == {"length": 80.0, "width": 20.0, "height": 15.0}

    def test_dimension_string_variations(self):
        """다양한 구분자"""
        assert self.scraper._parse_dimension_string("80x20x15")["length"] == 80.0
        assert self.scraper._parse_dimension_string("80X20X15")["width"] == 20.0
        assert self.scraper._parse_dimension_string("80×20×15")["height"] == 15.0

    def test_dimension_mm_to_cm(self):
        """mm → cm 변환"""
        assert self.scraper._convert_dimension("100mm") == 10.0
        assert self.scraper._convert_dimension("500mm") == 50.0

    def test_dimension_from_specs(self):
        """스펙에서 치수 추출"""
        data = {}
        specs = {"包装尺寸": "80*20*15cm"}
        result = self.scraper._parse_dimensions(data, specs)
        assert result["length"] == 80.0
        assert result["width"] == 20.0
        assert result["height"] == 15.0


class TestMockScraper:
    """Mock 스크래퍼 테스트"""

    def test_mock_scrape(self):
        """Mock 데이터 반환"""
        scraper = MockAlibabaScraper()
        result = asyncio.run(scraper.scrape("https://detail.1688.com/offer/test.html"))

        assert isinstance(result, ScrapedProduct)
        assert result.price_cny > 0
        assert result.name != ""
        assert result.moq > 0

    def test_mock_to_domain(self):
        """Mock → 도메인 모델 변환"""
        scraper = MockAlibabaScraper()
        scraped = asyncio.run(scraper.scrape("mock"))
        product = scraper.to_domain_product(scraped, "캠핑/레저")

        from src.domain.models import Product
        assert isinstance(product, Product)
        assert product.price_cny == scraped.price_cny
        assert product.category == "캠핑/레저"


class TestConvenienceFunction:
    """편의 함수 테스트"""

    def test_scrape_1688_mock(self):
        """scrape_1688() with mock"""
        result = asyncio.run(scrape_1688("mock", use_mock=True))

        assert isinstance(result, ScrapedProduct)
        assert result.price_cny > 0


class TestScrapedProductDataclass:
    """ScrapedProduct 데이터클래스 테스트"""

    def test_create_scraped_product(self):
        """기본 생성"""
        product = ScrapedProduct(
            url="https://test.com",
            name="Test Product",
            price_cny=45.0,
        )

        assert product.url == "https://test.com"
        assert product.name == "Test Product"
        assert product.price_cny == 45.0
        assert product.moq == 1  # 기본값

    def test_scraped_product_full(self):
        """모든 필드 포함"""
        product = ScrapedProduct(
            url="https://test.com",
            name="Full Product",
            price_cny=100.0,
            image_url="https://img.com/a.jpg",
            weight_kg=2.5,
            length_cm=80,
            width_cm=20,
            height_cm=15,
            moq=50,
            raw_specs={"材质": "알루미늄"},
        )

        assert product.weight_kg == 2.5
        assert product.moq == 50
        assert product.raw_specs["材质"] == "알루미늄"


class TestResultParsing:
    """Apify 결과 파싱 테스트"""

    def setup_method(self):
        import os
        self.original_token = os.getenv("APIFY_API_TOKEN")
        os.environ["APIFY_API_TOKEN"] = "test_token_for_parsing"
        self.scraper = AlibabaScraper()

    def teardown_method(self):
        import os
        if self.original_token:
            os.environ["APIFY_API_TOKEN"] = self.original_token
        elif "APIFY_API_TOKEN" in os.environ:
            del os.environ["APIFY_API_TOKEN"]

    def test_parse_result_basic(self):
        """기본 결과 파싱"""
        data = {
            "subject": "测试产品",
            "price": "45.00",
            "mainImage": "https://img.com/a.jpg",
        }

        result = self.scraper._parse_result("https://test.com", data)

        assert result.name == "测试产品"
        assert result.price_cny == 45.0
        assert result.image_url == "https://img.com/a.jpg"

    def test_parse_result_alternative_fields(self):
        """대체 필드명으로 파싱"""
        data = {
            "title": "Alternative Title",
            "currentPrice": "99.50",
        }

        result = self.scraper._parse_result("https://test.com", data)

        assert result.name == "Alternative Title"
        assert result.price_cny == 99.5

    def test_parse_result_with_specs(self):
        """스펙 포함 결과 파싱"""
        data = {
            "subject": "스펙 테스트",
            "price": "50",
            "attributes": {
                "重量": "2.5kg",
                "尺寸": "80*20*15cm",
            },
        }

        result = self.scraper._parse_result("https://test.com", data)

        assert result.raw_specs is not None
        assert "重量" in result.raw_specs

    def test_extract_moq(self):
        """MOQ 추출"""
        data1 = {"moq": 50}
        data2 = {"minOrder": 100}
        data3 = {"minOrderQuantity": "30"}

        assert self.scraper._extract_moq(data1) == 50
        assert self.scraper._extract_moq(data2) == 100
        assert self.scraper._extract_moq(data3) == 30

    def test_extract_image_array(self):
        """이미지 배열에서 첫 번째 추출"""
        data = {
            "images": ["https://img.com/1.jpg", "https://img.com/2.jpg"]
        }

        result = self.scraper._extract_image(data)
        assert result == "https://img.com/1.jpg"


# pytest 실행용
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
