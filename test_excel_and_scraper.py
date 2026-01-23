"""
test_excel_and_scraper.py - Phase 6 테스트 스크립트

실행:
    python test_excel_and_scraper.py

테스트 항목:
1. Mock 스크래퍼 동작 확인
2. 엑셀 생성기 동작 확인
3. 통합 테스트 (스크래핑 → 마진 계산 → 엑셀 생성)
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_mock_scraper():
    """1. Mock 스크래퍼 테스트"""
    print("\n" + "=" * 50)
    print("1. Mock 스크래퍼 테스트")
    print("=" * 50)

    from src.adapters.alibaba_scraper import MockAlibabaScraper

    async def run_test():
        scraper = MockAlibabaScraper()
        result = await scraper.scrape("https://detail.1688.com/offer/test.html")

        print(f"  상품명: {result.name}")
        print(f"  가격: {result.price_cny} CNY")
        print(f"  무게: {result.weight_kg} kg")
        print(f"  크기: {result.length_cm}x{result.width_cm}x{result.height_cm} cm")
        print(f"  MOQ: {result.moq}")
        print(f"  스펙: {result.raw_specs}")

        # 도메인 모델 변환
        product = scraper.to_domain_product(result, "캠핑/레저")
        print(f"  → 도메인 모델 변환 성공: {product.name}")

        return result

    result = asyncio.run(run_test())
    print("✅ Mock 스크래퍼 테스트 완료!")
    return result


def test_excel_generator():
    """2. 엑셀 생성기 테스트"""
    print("\n" + "=" * 50)
    print("2. 엑셀 생성기 테스트")
    print("=" * 50)

    try:
        from src.generators.excel_generator import NaverExcelGenerator, NaverProductData

        # 테스트 데이터
        products = [
            NaverProductData(
                product_name="초경량 캠핑의자 접이식 릴렉스체어",
                sale_price=45000,
                category_id="50000803",
                origin="중국",
                shipping_fee=3000,
                cost_price=28500,
                margin_rate=25.5,
                breakeven_price=35000,
                risk_level="warning",
                source_url="https://detail.1688.com/offer/123456.html",
                source_price_cny=45.0,
                moq=50,
            ),
            NaverProductData(
                product_name="휴대용 LED 캠핑랜턴 충전식",
                sale_price=25000,
                category_id="50000804",
                origin="중국",
                shipping_fee=3000,
                cost_price=12000,
                margin_rate=42.0,
                breakeven_price=15000,
                risk_level="safe",
                source_url="https://detail.1688.com/offer/789012.html",
                source_price_cny=25.0,
                moq=100,
            ),
            NaverProductData(
                product_name="저품질 상품 (위험)",
                sale_price=10000,
                origin="중국",
                cost_price=9500,
                margin_rate=5.0,
                breakeven_price=9500,
                risk_level="danger",
            ),
        ]

        generator = NaverExcelGenerator()
        output_path = "output/test_phase6_products.xlsx"
        filepath = generator.generate(products, output_path)

        print(f"  생성된 파일: {filepath}")
        print(f"  상품 수: {len(products)}개")
        print("✅ 엑셀 생성기 테스트 완료!")
        return filepath

    except ImportError as e:
        print(f"❌ openpyxl 설치 필요: pip install openpyxl")
        print(f"  에러: {e}")
        return None


def test_margin_calculator():
    """3. 마진 계산기 테스트"""
    print("\n" + "=" * 50)
    print("3. 마진 계산기 테스트")
    print("=" * 50)

    from src.domain.models import Product, MarketType
    from src.domain.logic import LandedCostCalculator
    from src.core.config import AppConfig

    config = AppConfig(exchange_rate=195)
    calculator = LandedCostCalculator(config)

    product = Product(
        name="캠핑의자",
        price_cny=45.0,
        weight_kg=2.5,
        length_cm=80,
        width_cm=20,
        height_cm=15,
        category="캠핑/레저",
        moq=50
    )

    result = calculator.calculate(
        product=product,
        target_price=45000,
        market=MarketType.NAVER,
        shipping_method="항공"
    )

    print(f"  상품: {product.name}")
    print(f"  도매가: {product.price_cny} CNY")
    print(f"  목표 판매가: 45,000원")
    print(f"  ---")
    print(f"  총 비용: {result.total_cost:,}원")
    print(f"  예상 수익: {result.profit:,}원")
    print(f"  마진율: {result.margin_percent}%")
    print(f"  위험도: {result.risk_level.value}")
    print(f"  손익분기가: {result.breakeven_price:,}원")
    print("✅ 마진 계산기 테스트 완료!")

    return result


def test_integration():
    """4. 통합 테스트 (스크래핑 → 마진 계산 → 엑셀)"""
    print("\n" + "=" * 50)
    print("4. 통합 테스트")
    print("=" * 50)

    from src.adapters.alibaba_scraper import MockAlibabaScraper
    from src.domain.models import MarketType
    from src.domain.logic import LandedCostCalculator
    from src.core.config import AppConfig

    async def run_integration():
        # 1. 스크래핑
        print("  [1/3] 스크래핑...")
        scraper = MockAlibabaScraper()
        scraped = await scraper.scrape("https://detail.1688.com/offer/test.html")
        product = scraper.to_domain_product(scraped, "캠핑/레저")

        # 2. 마진 계산
        print("  [2/3] 마진 계산...")
        config = AppConfig(exchange_rate=195)
        calculator = LandedCostCalculator(config)
        result = calculator.calculate(product, target_price=45000, market=MarketType.NAVER)

        # 3. 엑셀 생성
        print("  [3/3] 엑셀 생성...")
        try:
            from src.generators.excel_generator import NaverExcelGenerator, create_naver_product_from_analysis

            naver_data = create_naver_product_from_analysis(
                product_name=product.name,
                sale_price=45000,
                cost_result=result,
                scraped_product=scraped,
            )

            generator = NaverExcelGenerator()
            filepath = generator.generate([naver_data], "output/integration_test.xlsx")
            print(f"  → 파일 생성: {filepath}")

        except ImportError:
            print("  → 엑셀 생성 스킵 (openpyxl 없음)")

        return result

    result = asyncio.run(run_integration())
    print("✅ 통합 테스트 완료!")
    return result


def main():
    """메인 테스트 실행"""
    print("\n🚀 Phase 6 테스트 시작\n")

    # 1. Mock 스크래퍼
    test_mock_scraper()

    # 2. 마진 계산기
    test_margin_calculator()

    # 3. 엑셀 생성기
    test_excel_generator()

    # 4. 통합 테스트
    test_integration()

    print("\n" + "=" * 50)
    print("🎉 모든 테스트 완료!")
    print("=" * 50)


if __name__ == "__main__":
    main()
