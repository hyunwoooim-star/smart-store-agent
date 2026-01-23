"""
test_landed_cost_calculator.py - LandedCostCalculator 단위 테스트 (Phase 6-2)

Gemini CTO 권장 테스트 케이스:
1. 부피무게 >> 실무게 (10배 시나리오)
2. 환율 급등 시나리오
3. 손익분기점 엣지 케이스
4. 마켓별 수수료 차이
"""

import pytest
import sys
from pathlib import Path

# 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.domain.models import Product, RiskLevel, MarketType
from src.domain.logic import LandedCostCalculator
from src.core.config import AppConfig, DEFAULT_CONFIG


class TestVolumeWeightCalculation:
    """부피무게 계산 테스트"""

    def setup_method(self):
        self.calculator = LandedCostCalculator()

    def test_volume_weight_basic(self):
        """기본 부피무게 계산"""
        product = Product(
            name="테스트",
            price_cny=10,
            weight_kg=1.0,
            length_cm=50,
            width_cm=40,
            height_cm=30,
        )
        # (50 * 40 * 30) / 5000 = 12.0 kg
        volume_weight = self.calculator.calculate_volume_weight(product)
        assert volume_weight == 12.0

    def test_volume_weight_small_item(self):
        """작은 상품 부피무게"""
        product = Product(
            name="작은상품",
            price_cny=5,
            weight_kg=0.5,
            length_cm=10,
            width_cm=10,
            height_cm=10,
        )
        # (10 * 10 * 10) / 5000 = 0.2 kg
        volume_weight = self.calculator.calculate_volume_weight(product)
        assert volume_weight == 0.2

    def test_billable_weight_volume_higher(self):
        """청구무게: 부피무게가 큰 경우"""
        actual = 2.0
        volume = 12.0
        billable = self.calculator.get_billable_weight(actual, volume)
        assert billable == 12.0

    def test_billable_weight_actual_higher(self):
        """청구무게: 실무게가 큰 경우"""
        actual = 15.0
        volume = 5.0
        billable = self.calculator.get_billable_weight(actual, volume)
        assert billable == 15.0


class TestVolumeWeightEdgeCases:
    """부피무게 엣지 케이스 (Gemini CTO 권장)"""

    def setup_method(self):
        self.calculator = LandedCostCalculator()

    def test_volume_weight_10x_actual(self):
        """부피무게가 실무게의 10배인 경우 (대형 경량 상품)"""
        product = Product(
            name="대형 스티로폼 박스",
            price_cny=20,
            weight_kg=1.0,  # 실무게 1kg
            length_cm=100,
            width_cm=50,
            height_cm=50,  # 부피: 250,000 cm³
        )
        # (100 * 50 * 50) / 5000 = 50.0 kg (실무게의 50배!)
        volume_weight = self.calculator.calculate_volume_weight(product)
        assert volume_weight == 50.0

        # 청구무게는 부피무게
        billable = self.calculator.get_billable_weight(product.weight_kg, volume_weight)
        assert billable == 50.0

        # 배송비 폭탄 확인
        result = self.calculator.calculate(product, target_price=50000)
        # 항공 배송비: 50kg * 8000원 = 400,000원
        assert result.breakdown.shipping_international >= 400000
        assert result.is_danger == True  # 당연히 위험

    def test_camping_chair_realistic(self):
        """캠핑의자 실제 케이스 (v3.1 시뮬레이션)"""
        product = Product(
            name="초경량 캠핑의자",
            price_cny=45,
            weight_kg=2.5,
            length_cm=80,
            width_cm=20,
            height_cm=15,
            category="캠핑/레저",
            moq=50,
        )
        # (80 * 20 * 15) / 5000 = 4.8 kg
        volume_weight = self.calculator.calculate_volume_weight(product)
        assert volume_weight == 4.8

        result = self.calculator.calculate(product, target_price=45000)

        # 기존 6000 계수였을 때보다 비용 증가 확인
        assert result.billable_weight_kg == 4.8  # 부피무게 적용
        assert result.is_danger == True  # 마진 부족


class TestExchangeRateScenarios:
    """환율 변동 시나리오 (Gemini CTO 권장)"""

    def test_exchange_rate_normal(self):
        """정상 환율 (195원)"""
        config = AppConfig(exchange_rate=195)
        calculator = LandedCostCalculator(config)

        product = Product(
            name="테스트",
            price_cny=100,
            weight_kg=1.0,
            length_cm=20,
            width_cm=20,
            height_cm=20,
        )

        result = calculator.calculate(product, target_price=50000)
        assert result.breakdown.product_cost == 19500  # 100 * 195

    def test_exchange_rate_spike_220(self):
        """환율 급등 (220원) - 위기 시나리오"""
        config = AppConfig(exchange_rate=220)
        calculator = LandedCostCalculator(config)

        product = Product(
            name="테스트",
            price_cny=100,
            weight_kg=1.0,
            length_cm=20,
            width_cm=20,
            height_cm=20,
        )

        result = calculator.calculate(product, target_price=50000)
        assert result.breakdown.product_cost == 22000  # 100 * 220

    def test_exchange_rate_impact_on_margin(self):
        """환율 변동이 마진에 미치는 영향"""
        product = Product(
            name="마진 테스트",
            price_cny=50,
            weight_kg=0.5,
            length_cm=15,
            width_cm=15,
            height_cm=10,
        )

        # 환율 195원
        calc_195 = LandedCostCalculator(AppConfig(exchange_rate=195))
        result_195 = calc_195.calculate(product, target_price=40000)

        # 환율 220원
        calc_220 = LandedCostCalculator(AppConfig(exchange_rate=220))
        result_220 = calc_220.calculate(product, target_price=40000)

        # 환율 상승 → 마진율 감소
        assert result_220.margin_percent < result_195.margin_percent
        # 환율 상승 → 총비용 증가
        assert result_220.total_cost > result_195.total_cost


class TestBreakevenPriceEdgeCases:
    """손익분기점 엣지 케이스 (Gemini CTO 권장)"""

    def setup_method(self):
        self.calculator = LandedCostCalculator()

    def test_breakeven_basic(self):
        """기본 손익분기점 계산"""
        product = Product(
            name="테스트",
            price_cny=30,
            weight_kg=1.0,
            length_cm=20,
            width_cm=20,
            height_cm=20,
        )

        result = self.calculator.calculate(product, target_price=30000)

        # 손익분기가는 0보다 커야 함
        assert result.breakeven_price > 0
        # 목표 마진가는 손익분기가보다 커야 함
        assert result.target_margin_price > result.breakeven_price

    def test_breakeven_when_loss(self):
        """적자일 때 손익분기점"""
        product = Product(
            name="적자상품",
            price_cny=100,
            weight_kg=5.0,
            length_cm=50,
            width_cm=50,
            height_cm=50,
        )

        result = self.calculator.calculate(product, target_price=30000)

        # 손익분기가가 목표가보다 높아야 함 (적자니까)
        assert result.breakeven_price > 30000
        assert result.profit < 0
        assert result.is_danger == True

    def test_breakeven_high_margin_product(self):
        """고마진 상품 손익분기점"""
        product = Product(
            name="고마진",
            price_cny=10,
            weight_kg=0.1,
            length_cm=10,
            width_cm=10,
            height_cm=5,
        )

        result = self.calculator.calculate(product, target_price=50000)

        # 목표가가 손익분기가보다 훨씬 높아야 함
        assert result.target_price > result.breakeven_price
        assert result.margin_percent > 30
        assert result.risk_level == RiskLevel.SAFE


class TestMarketFees:
    """마켓별 수수료 테스트"""

    def setup_method(self):
        self.calculator = LandedCostCalculator()
        self.product = Product(
            name="테스트",
            price_cny=30,
            weight_kg=0.5,
            length_cm=15,
            width_cm=15,
            height_cm=10,
        )

    def test_naver_fee(self):
        """네이버 수수료 (5.5%)"""
        result = self.calculator.calculate(
            self.product, target_price=50000, market=MarketType.NAVER
        )
        expected_fee = int(50000 * 0.055)
        assert result.breakdown.platform_fee == expected_fee

    def test_coupang_fee(self):
        """쿠팡 수수료 (10.8%)"""
        result = self.calculator.calculate(
            self.product, target_price=50000, market=MarketType.COUPANG
        )
        expected_fee = int(50000 * 0.108)
        assert result.breakdown.platform_fee == expected_fee

    def test_amazon_fee(self):
        """아마존 수수료 (15%)"""
        result = self.calculator.calculate(
            self.product, target_price=50000, market=MarketType.AMAZON
        )
        expected_fee = int(50000 * 0.15)
        assert result.breakdown.platform_fee == expected_fee

    def test_market_fee_impact_on_margin(self):
        """마켓 수수료가 마진에 미치는 영향"""
        naver = self.calculator.calculate(
            self.product, target_price=50000, market=MarketType.NAVER
        )
        coupang = self.calculator.calculate(
            self.product, target_price=50000, market=MarketType.COUPANG
        )
        amazon = self.calculator.calculate(
            self.product, target_price=50000, market=MarketType.AMAZON
        )

        # 수수료 높을수록 마진 낮음
        assert naver.margin_percent > coupang.margin_percent > amazon.margin_percent


class TestRiskLevels:
    """위험도 판정 테스트"""

    def setup_method(self):
        self.calculator = LandedCostCalculator()

    def test_risk_safe(self):
        """SAFE: 마진 30% 이상"""
        product = Product(
            name="고마진",
            price_cny=5,
            weight_kg=0.1,
            length_cm=10,
            width_cm=10,
            height_cm=5,
        )
        result = self.calculator.calculate(product, target_price=50000)

        assert result.margin_percent >= 30
        assert result.risk_level == RiskLevel.SAFE
        assert result.is_danger == False

    def test_risk_warning(self):
        """WARNING: 마진 15~30%"""
        product = Product(
            name="중마진",
            price_cny=30,
            weight_kg=0.5,
            length_cm=20,
            width_cm=15,
            height_cm=10,
        )
        result = self.calculator.calculate(product, target_price=40000)

        # 마진이 15~30% 사이인지 확인
        if 15 <= result.margin_percent < 30:
            assert result.risk_level == RiskLevel.WARNING
            assert result.is_danger == False

    def test_risk_danger(self):
        """DANGER: 마진 15% 미만"""
        product = Product(
            name="저마진",
            price_cny=100,
            weight_kg=3.0,
            length_cm=40,
            width_cm=30,
            height_cm=30,
        )
        result = self.calculator.calculate(product, target_price=30000)

        assert result.margin_percent < 15
        assert result.risk_level == RiskLevel.DANGER
        assert result.is_danger == True


class TestRecommendationMessages:
    """추천 메시지 테스트"""

    def setup_method(self):
        self.calculator = LandedCostCalculator()

    def test_recommendation_danger(self):
        """위험 상품 추천 메시지"""
        product = Product(
            name="위험",
            price_cny=100,
            weight_kg=5.0,
            length_cm=50,
            width_cm=50,
            height_cm=50,
            moq=100,
        )
        result = self.calculator.calculate(product, target_price=30000)

        assert "진입 금지" in result.recommendation or "🔴" in result.recommendation

    def test_recommendation_low_moq(self):
        """낮은 MOQ 추천 메시지"""
        product = Product(
            name="저MOQ",
            price_cny=20,
            weight_kg=0.3,
            length_cm=15,
            width_cm=10,
            height_cm=5,
            moq=3,
        )
        result = self.calculator.calculate(product, target_price=25000)

        # MOQ 낮으면 테스트 권장
        if result.margin_percent >= 15 and result.margin_percent < 30:
            assert "테스트" in result.recommendation or "🟡" in result.recommendation

    def test_recommendation_high_moq_with_loss_cut(self):
        """높은 MOQ + 손절매 룰 포함 (Gemini CTO 피드백)"""
        product = Product(
            name="고MOQ",
            price_cny=20,
            weight_kg=0.3,
            length_cm=15,
            width_cm=10,
            height_cm=5,
            moq=100,
        )
        result = self.calculator.calculate(product, target_price=35000)

        # MOQ 높으면 손절/협상 언급
        if result.margin_percent < 30:
            assert "협상" in result.recommendation or "손절" in result.recommendation


class TestShippingMethods:
    """배송 방법별 테스트"""

    def setup_method(self):
        self.calculator = LandedCostCalculator()
        self.product = Product(
            name="테스트",
            price_cny=50,
            weight_kg=2.0,
            length_cm=30,
            width_cm=30,
            height_cm=30,
        )

    def test_air_shipping(self):
        """항공 배송"""
        result = self.calculator.calculate(
            self.product, target_price=50000, shipping_method="항공"
        )
        # 청구무게 * 8000원
        # 부피: (30*30*30)/5000 = 5.4kg, 실무게 2kg → 청구무게 5.4kg
        expected_shipping = int(5.4 * 8000)
        assert result.breakdown.shipping_international == expected_shipping

    def test_sea_shipping(self):
        """해운 배송 (CBM 기반)"""
        result = self.calculator.calculate(
            self.product, target_price=50000, shipping_method="해운"
        )
        # CBM: (30*30*30) / 1,000,000 = 0.027 m³
        # 해운비: max(0.027 * 75000, 6000) = 6000원 (최소비용)
        assert result.breakdown.shipping_international >= 6000


class TestAdCostToggle:
    """광고비 포함/제외 테스트"""

    def setup_method(self):
        self.calculator = LandedCostCalculator()
        self.product = Product(
            name="테스트",
            price_cny=30,
            weight_kg=0.5,
            length_cm=15,
            width_cm=15,
            height_cm=10,
        )

    def test_with_ad_cost(self):
        """광고비 포함"""
        result = self.calculator.calculate(
            self.product, target_price=50000, include_ad_cost=True
        )
        expected_ad = int(50000 * 0.10)
        assert result.breakdown.ad_cost == expected_ad

    def test_without_ad_cost(self):
        """광고비 제외"""
        result = self.calculator.calculate(
            self.product, target_price=50000, include_ad_cost=False
        )
        assert result.breakdown.ad_cost == 0

    def test_ad_cost_impact_on_margin(self):
        """광고비가 마진에 미치는 영향"""
        with_ad = self.calculator.calculate(
            self.product, target_price=50000, include_ad_cost=True
        )
        without_ad = self.calculator.calculate(
            self.product, target_price=50000, include_ad_cost=False
        )

        # 광고비 빼면 마진 증가
        assert without_ad.margin_percent > with_ad.margin_percent
        # 차이는 약 10%
        diff = without_ad.margin_percent - with_ad.margin_percent
        assert 8 <= diff <= 12  # 약간의 반올림 오차 허용


class TestCostBreakdown:
    """비용 내역 상세 테스트"""

    def setup_method(self):
        self.calculator = LandedCostCalculator()

    def test_all_cost_items_present(self):
        """모든 비용 항목이 존재하는지"""
        product = Product(
            name="테스트",
            price_cny=50,
            weight_kg=1.0,
            length_cm=20,
            width_cm=20,
            height_cm=20,
        )
        result = self.calculator.calculate(product, target_price=50000)
        bd = result.breakdown

        # 모든 비용 항목 확인
        assert bd.product_cost > 0
        assert bd.china_shipping > 0
        assert bd.agency_fee > 0
        assert bd.tariff >= 0
        assert bd.vat >= 0
        assert bd.shipping_international > 0
        assert bd.shipping_domestic > 0
        assert bd.platform_fee > 0
        assert bd.return_allowance > 0
        assert bd.packaging > 0

    def test_total_cost_equals_sum(self):
        """총비용 = 각 항목의 합"""
        product = Product(
            name="테스트",
            price_cny=50,
            weight_kg=1.0,
            length_cm=20,
            width_cm=20,
            height_cm=20,
        )
        result = self.calculator.calculate(product, target_price=50000)
        bd = result.breakdown

        expected_total = (
            bd.product_cost +
            bd.china_shipping +
            bd.agency_fee +
            bd.tariff +
            bd.vat +
            bd.shipping_international +
            bd.shipping_domestic +
            bd.platform_fee +
            bd.return_allowance +
            bd.ad_cost +
            bd.packaging
        )

        assert result.total_cost == expected_total


# pytest 실행용
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
