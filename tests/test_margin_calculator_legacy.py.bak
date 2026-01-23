"""margin_calculator.py 테스트"""

import sys
from pathlib import Path

# 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sourcing.margin_calculator import (
    MarginCalculator,
    SourcingInput,
    ProductDimensions,
    MarginResult
)


class TestMarginCalculator:
    """마진 계산기 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.calculator = MarginCalculator()

    def test_volume_weight_calculation(self):
        """부피무게 계산 테스트"""
        dims = ProductDimensions(length=80, width=20, height=15)
        volume_weight = self.calculator.calculate_volume_weight(dims)

        # 80 * 20 * 15 / 6000 = 4.0 kg
        assert volume_weight == 4.0

    def test_billable_weight_volume_higher(self):
        """청구무게 테스트 - 부피무게가 큰 경우"""
        actual = 2.5
        volume = 4.0
        billable = self.calculator.get_billable_weight(actual, volume)

        assert billable == 4.0  # 부피무게 적용

    def test_billable_weight_actual_higher(self):
        """청구무게 테스트 - 실무게가 큰 경우"""
        actual = 5.0
        volume = 3.0
        billable = self.calculator.get_billable_weight(actual, volume)

        assert billable == 5.0  # 실무게 적용

    def test_margin_calculation_camping_chair(self):
        """캠핑의자 마진 계산 테스트 (v3.1 시뮬레이션)"""
        input_data = SourcingInput(
            product_name="초경량 캠핑 의자",
            wholesale_price_cny=45,
            actual_weight_kg=2.5,
            dimensions=ProductDimensions(80, 20, 15),
            moq=50,
            target_price_krw=45000,
            category="캠핑/레저"
        )

        result = self.calculator.calculate(input_data)

        # 검증
        assert isinstance(result, MarginResult)
        assert result.product_cost_krw == 8550  # 45 * 190
        assert result.volume_weight_kg == 4.0   # 80*20*15/6000
        assert result.billable_weight_kg == 4.0  # max(2.5, 4.0)

        # 마진율이 음수여야 함 (계획서 v3.1 기준)
        assert result.margin_percent < 0
        assert result.is_viable == False
        assert result.risk_level == "HIGH"

    def test_margin_calculation_high_margin_product(self):
        """고마진 상품 테스트"""
        input_data = SourcingInput(
            product_name="테스트 상품",
            wholesale_price_cny=10,           # 낮은 원가
            actual_weight_kg=0.5,
            dimensions=ProductDimensions(10, 10, 10),  # 작은 부피
            moq=5,
            target_price_krw=50000,           # 높은 판매가
            category="기타"
        )

        result = self.calculator.calculate(input_data)

        # 고마진이어야 함
        assert result.margin_percent > 30
        assert result.is_viable == True
        assert result.risk_level == "LOW"

    def test_tariff_rates(self):
        """카테고리별 관세율 테스트"""
        assert MarginCalculator.TARIFF_RATES["캠핑/레저"] == 0.08
        assert MarginCalculator.TARIFF_RATES["의류/패션"] == 0.13
        assert MarginCalculator.TARIFF_RATES["전자기기"] == 0.08
        assert MarginCalculator.TARIFF_RATES["기타"] == 0.10

    def test_constants(self):
        """상수값 테스트 (v3.1 확정값)"""
        assert MarginCalculator.EXCHANGE_RATE == 190
        assert MarginCalculator.VAT_RATE == 0.10
        assert MarginCalculator.NAVER_FEE_RATE == 0.055
        assert MarginCalculator.RETURN_ALLOWANCE_RATE == 0.05
        assert MarginCalculator.AD_COST_RATE == 0.10
        assert MarginCalculator.VOLUME_WEIGHT_DIVISOR == 6000
        assert MarginCalculator.DOMESTIC_SHIPPING == 3000

    def test_breakeven_price(self):
        """손익분기 판매가 계산 테스트"""
        input_data = SourcingInput(
            product_name="테스트",
            wholesale_price_cny=45,
            actual_weight_kg=2.5,
            dimensions=ProductDimensions(80, 20, 15),
            moq=50,
            target_price_krw=45000,
            category="캠핑/레저"
        )

        result = self.calculator.calculate(input_data)

        # 손익분기 판매가가 목표 판매가보다 높아야 함 (마진 음수이므로)
        assert result.breakeven_price_krw > input_data.target_price_krw

    def test_recommendation_viable(self):
        """추천 메시지 테스트 - 수익성 있는 경우"""
        input_data = SourcingInput(
            product_name="소형 상품",
            wholesale_price_cny=5,
            actual_weight_kg=0.1,
            dimensions=ProductDimensions(10, 10, 5),
            moq=3,  # 소량 MOQ
            target_price_krw=30000,
            category="기타"
        )

        result = self.calculator.calculate(input_data)

        # 수익성이 있고 MOQ가 낮으면 소량 테스트 추천
        assert "소량 테스트" in result.recommendation or "✅" in result.recommendation

    def test_recommendation_not_viable(self):
        """추천 메시지 테스트 - 수익성 없는 경우"""
        input_data = SourcingInput(
            product_name="대형 상품",
            wholesale_price_cny=100,
            actual_weight_kg=10,
            dimensions=ProductDimensions(100, 50, 50),
            moq=100,
            target_price_krw=30000,  # 낮은 판매가
            category="가구/인테리어"
        )

        result = self.calculator.calculate(input_data)

        # 수익성 부족 메시지
        assert "수익성 부족" in result.recommendation or "❌" in result.recommendation


# pytest 실행용
if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
