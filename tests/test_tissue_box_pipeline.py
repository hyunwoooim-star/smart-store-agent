"""
티슈 박스 케이스 전체 파이프라인 테스트
1688 상품: ¥15.00 PU 가죽 티슈 케이스

테스트 항목:
1. 마진 계산 (LandedCostCalculator)
2. 시장 조사 (MarketResearcher)
3. Pre-Flight 체크
4. 종합 판정
"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.domain.models import Product, MarketType, RiskLevel
from src.domain.logic import LandedCostCalculator
from src.core.config import AppConfig
from src.analyzers.preflight_check import PreFlightChecker

def main():
    print("=" * 60)
    print("🧪 티슈 박스 케이스 전체 파이프라인 테스트")
    print("=" * 60)

    # ========== 상품 정보 (1688 스크린샷 기반) ==========
    product = Product(
        name="PU 가죽 티슈 케이스 화이트",
        price_cny=15.0,          # ¥15.00
        weight_kg=0.3,           # 예상 무게: 300g
        length_cm=25,            # 가로
        width_cm=14,             # 세로
        height_cm=10,            # 높이
        category="생활용품",
        moq=10                   # 최소 주문량
    )

    print("\n📦 [Step 1] 상품 정보")
    print("-" * 40)
    print(f"  상품명: {product.name}")
    print(f"  1688 가격: ¥{product.price_cny:.2f}")
    print(f"  무게: {product.weight_kg}kg")
    print(f"  크기: {product.length_cm}x{product.width_cm}x{product.height_cm}cm")
    print(f"  카테고리: {product.category}")
    print(f"  MOQ: {product.moq}개")

    # ========== 마진 계산 ==========
    print("\n💰 [Step 2] 마진 계산")
    print("-" * 40)

    config = AppConfig()
    calculator = LandedCostCalculator(config)

    # 목표 판매가 설정 (네이버 평균가 기준)
    # 티슈케이스 평균가: 약 15,000 ~ 25,000원
    target_price = 19900  # 테스트용 목표가

    result = calculator.calculate(
        product=product,
        target_price=target_price,
        market=MarketType.NAVER,
        shipping_method="항공",
        include_ad_cost=True
    )

    print(f"  📊 환율: {config.exchange_rate}원/위안")
    print(f"  📦 부피무게: {result.volume_weight_kg:.2f}kg")
    print(f"  📦 청구무게: {max(result.actual_weight_kg, result.volume_weight_kg):.2f}kg")
    print()

    # 비용 내역
    bd = result.breakdown
    print("  💸 비용 내역:")
    print(f"    - 상품 원가: ₩{bd.product_cost:,}")
    print(f"    - 중국 내 배송: ₩{bd.china_shipping:,}")
    print(f"    - 구매대행 수수료: ₩{bd.agency_fee:,}")
    print(f"    - 관세: ₩{bd.tariff:,}")
    print(f"    - 부가세: ₩{bd.vat:,}")
    print(f"    - 해외 배송: ₩{bd.shipping_international:,}")
    print(f"    - 국내 배송: ₩{bd.shipping_domestic:,}")
    print(f"    - 플랫폼 수수료: ₩{bd.platform_fee:,}")
    print(f"    - 광고비: ₩{bd.ad_cost:,}")
    print(f"    - 반품 충당금: ₩{bd.return_allowance:,}")
    print(f"    - 포장비: ₩{bd.packaging:,}")
    print()
    print(f"  📊 총 비용: ₩{result.total_cost:,}")
    print(f"  🎯 목표 판매가: ₩{target_price:,}")
    print(f"  💵 예상 수익: ₩{result.profit:,}")
    print(f"  📈 마진율: {result.margin_percent}%")
    print(f"  ⚖️ 손익분기점: ₩{result.breakeven_price:,}")

    # 리스크 레벨
    risk_emoji = {"SAFE": "🟢", "WARNING": "🟡", "DANGER": "🔴"}
    print(f"  {risk_emoji.get(result.risk_level.name, '⚪')} 리스크: {result.risk_level.name}")
    print(f"  💡 추천: {result.recommendation}")

    # ========== 시장 조사 ==========
    print("\n📊 [Step 3] 시장 조사 (네이버)")
    print("-" * 40)

    try:
        from src.analyzers.market_researcher import MarketResearcher

        researcher = MarketResearcher()
        market_result = researcher.research_by_text("티슈 케이스", max_results=10)

        print(f"  🔍 검색어: {market_result.query}")
        print(f"  👥 경쟁사 수: {len(market_result.competitors)}개")
        print(f"  💰 가격 범위: ₩{market_result.price_range[0]:,} ~ ₩{market_result.price_range[1]:,}")
        print(f"  📊 평균가: ₩{market_result.average_price:,}")
        print(f"  🎯 추천가: ₩{market_result.recommended_price:,}")
        print(f"  📝 가격 전략: {market_result.price_strategy}")

        if market_result.competitors:
            print("\n  🏪 상위 경쟁사:")
            for i, comp in enumerate(market_result.competitors[:5], 1):
                print(f"    {i}. {comp.title[:30]}... - ₩{comp.price:,}")

        # 시장가 기준 재계산
        if market_result.recommended_price:
            print(f"\n  📈 시장 추천가 기준 재계산: ₩{market_result.recommended_price:,}")
            result2 = calculator.calculate(
                product=product,
                target_price=market_result.recommended_price,
                market=MarketType.NAVER,
                shipping_method="항공",
                include_ad_cost=True
            )
            print(f"    → 예상 마진율: {result2.margin_percent}%")
            print(f"    → 예상 수익: ₩{result2.profit:,}")

    except Exception as e:
        print(f"  ⚠️ 시장 조사 실패: {e}")
        print("  (네이버 API 미설정 또는 네트워크 오류)")

    # ========== Pre-Flight 체크 ==========
    print("\n✅ [Step 4] Pre-Flight 체크")
    print("-" * 40)

    checker = PreFlightChecker(strict_mode=False)
    preflight_result = checker.check_product(product.name, "")

    if preflight_result.passed:
        print("  ✅ 금지어 검사 통과!")
    else:
        print(f"  ⚠️ 오류 {preflight_result.error_count}건, 경고 {preflight_result.warning_count}건")
        for v in preflight_result.violations[:5]:
            severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(v.severity, "⚪")
            print(f"    {severity_emoji} {v.type.value}: `{v.matched_text}` → {v.suggestion}")

    # ========== 최종 판정 ==========
    print("\n🎯 [Step 5] 최종 판정")
    print("=" * 60)

    # 종합 판정 로직
    if result.margin_percent >= 35:
        verdict = "🟢 GO"
        verdict_reason = f"마진율 {result.margin_percent}% - 진입 추천"
    elif result.margin_percent >= 25:
        verdict = "🟡 HOLD"
        verdict_reason = f"마진율 {result.margin_percent}% - 가격 조정 필요"
    else:
        verdict = "🔴 NO-GO"
        verdict_reason = f"마진율 {result.margin_percent}% - 수익성 부족"

    # Pre-Flight 위반 시 경고
    if not preflight_result.passed:
        verdict = "🟡 HOLD"
        verdict_reason += f" (금지어 {preflight_result.error_count}건)"

    print(f"\n  {verdict}")
    print(f"  사유: {verdict_reason}")
    print()
    print("=" * 60)
    print("🧪 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
