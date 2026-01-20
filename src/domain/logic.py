"""
logic.py - 핵심 비즈니스 로직 (v3.3 LandedCostCalculator)

DDD 원칙: 외부 의존성 없는 순수 파이썬 코드
- UI 프레임워크 독립적
- 테스트 용이
- 재사용 가능 (Next.js, FastAPI 등 어디든)

v3.3 변경점 (Gemini 피드백 반영):
- 마켓별 수수료 지원 (네이버 5.5%, 쿠팡 10.8%, 아마존 15%)
- CBM 기반 해운 비용 계산
- 숨겨진 비용 강제 적용 (반품, 광고, 포장)
- "망하는 상품 필터링" 전략 적용
"""

import math
from typing import Optional

from .models import (
    Product,
    CostResult,
    CostBreakdown,
    RiskLevel,
    MarketType,
)
from ..core.config import AppConfig, DEFAULT_CONFIG, MARKET_FEES


class LandedCostCalculator:
    """Landed Cost(도착원가) 계산기 v3.3

    "사장님의 돈을 지키는" 보수적 계산기.
    모든 숨겨진 비용을 포함하여 현실적인 마진 산출.
    """

    def __init__(self, config: Optional[AppConfig] = None):
        """
        Args:
            config: 애플리케이션 설정. None이면 기본값 사용.
        """
        self.config = config or DEFAULT_CONFIG

    def calculate_volume_weight(self, product: Product) -> float:
        """부피무게 계산: (가로 x 세로 x 높이) / 6000"""
        volume = product.length_cm * product.width_cm * product.height_cm
        return volume / self.config.volume_weight_divisor

    def calculate_cbm(self, product: Product) -> float:
        """CBM(Cubic Meter) 계산: 해운 비용 산정용"""
        return (product.length_cm * product.width_cm * product.height_cm) / 1_000_000

    def get_billable_weight(self, actual: float, volume: float) -> float:
        """청구무게 = Max(실무게, 부피무게)"""
        return max(actual, volume)

    def calculate(
        self,
        product: Product,
        target_price: int,
        market: MarketType = MarketType.NAVER,
        shipping_method: str = "항공",
        include_ad_cost: bool = True,
    ) -> CostResult:
        """마진 계산 실행

        Args:
            product: 상품 정보
            target_price: 목표 판매가 (원)
            market: 판매 마켓 (naver, coupang, amazon)
            shipping_method: 배송 방법 (항공/해운)
            include_ad_cost: 광고비 포함 여부

        Returns:
            CostResult: 상세 비용 분석 결과
        """
        cfg = self.config

        # 1. 상품 원가
        product_cost = int(product.price_cny * cfg.exchange_rate)

        # 2. 중국 내 비용 (구매대행 필수 비용)
        china_shipping = cfg.china_domestic_shipping  # 중국 내 배송비
        china_total = product_cost + china_shipping
        agency_fee = int(china_total * cfg.agency_fee_rate)  # 구매대행 수수료 10%

        # 3. 무게 계산
        volume_weight = self.calculate_volume_weight(product)
        billable_weight = self.get_billable_weight(product.weight_kg, volume_weight)

        # 4. 해외 배송비
        if shipping_method == "항공":
            shipping_international = int(billable_weight * cfg.shipping_rate_air)
        else:
            # 해운: CBM 기반 계산 (1 CBM당 75,000원, 최소 6,000원)
            cbm = self.calculate_cbm(product)
            shipping_international = max(
                int(cbm * cfg.cbm_rate),
                cfg.min_shipping_fee
            )

        # 5. 관부가세 (간이통관 기준 약 20%)
        # 과세가격 = 중국내비용 + 해운배송비
        taxable = china_total + shipping_international
        tariff_and_vat = int(taxable * cfg.simple_tariff_rate)  # 관부가세 통합
        tariff = int(tariff_and_vat * 0.4)  # 관세 약 40%
        vat = tariff_and_vat - tariff       # 부가세 약 60%

        # 6. 마켓 수수료
        market_config = MARKET_FEES.get(market.value, MARKET_FEES["naver"])
        platform_fee = int(target_price * market_config.fee_rate)

        # 7. 숨겨진 비용 (강제 적용)
        return_allowance = int(target_price * cfg.return_allowance_rate)
        ad_cost = int(target_price * cfg.ad_cost_rate) if include_ad_cost else 0
        packaging = cfg.packaging_cost

        # 8. 비용 집계
        breakdown = CostBreakdown(
            product_cost=product_cost,
            china_shipping=china_shipping,
            agency_fee=agency_fee,
            tariff=tariff,
            vat=vat,
            shipping_international=shipping_international,
            shipping_domestic=cfg.domestic_shipping,
            platform_fee=platform_fee,
            return_allowance=return_allowance,
            ad_cost=ad_cost,
            packaging=packaging,
        )

        total_cost = (
            product_cost +
            china_shipping +
            agency_fee +
            tariff +
            vat +
            shipping_international +
            cfg.domestic_shipping +
            platform_fee +
            return_allowance +
            ad_cost +
            packaging
        )

        # 9. 수익 계산
        profit = target_price - total_cost
        margin_percent = (profit / target_price * 100) if target_price > 0 else 0

        # 10. 위험도 판정
        if margin_percent >= cfg.warning_margin * 100:
            risk_level = RiskLevel.SAFE
        elif margin_percent >= cfg.danger_margin * 100:
            risk_level = RiskLevel.WARNING
        else:
            risk_level = RiskLevel.DANGER

        is_danger = risk_level == RiskLevel.DANGER

        # 11. 손익분기점 계산 (구매대행 비용 포함)
        fixed_costs = (
            product_cost + china_shipping + agency_fee +
            tariff + vat + shipping_international +
            cfg.domestic_shipping + packaging
        )
        breakeven_price = self._calculate_breakeven(
            fixed_costs, market, include_ad_cost
        )

        target_margin_price = self._calculate_target_margin(
            fixed_costs, market, 0.30, include_ad_cost
        )

        # 12. 추천 메시지
        recommendation = self._get_recommendation(
            margin_percent, product.moq, is_danger, breakeven_price, market
        )

        return CostResult(
            total_cost=total_cost,
            breakdown=breakdown,
            actual_weight_kg=product.weight_kg,
            volume_weight_kg=round(volume_weight, 2),
            billable_weight_kg=round(billable_weight, 2),
            target_price=target_price,
            profit=profit,
            margin_percent=round(margin_percent, 1),
            risk_level=risk_level,
            is_danger=is_danger,
            recommendation=recommendation,
            breakeven_price=breakeven_price,
            target_margin_price=target_margin_price,
        )

    def _calculate_breakeven(
        self, fixed_costs: int, market: MarketType, include_ad: bool
    ) -> int:
        """손익분기 판매가 = 고정비 / (1 - 변동비율)"""
        market_fee = MARKET_FEES.get(market.value, MARKET_FEES["naver"]).fee_rate
        variable_rate = market_fee + self.config.return_allowance_rate
        if include_ad:
            variable_rate += self.config.ad_cost_rate

        if variable_rate >= 1.0:
            return 0

        breakeven = fixed_costs / (1 - variable_rate)
        return int(math.ceil(breakeven / 1000) * 1000)

    def _calculate_target_margin(
        self, fixed_costs: int, market: MarketType, target_margin: float, include_ad: bool
    ) -> int:
        """목표 마진 달성 판매가"""
        market_fee = MARKET_FEES.get(market.value, MARKET_FEES["naver"]).fee_rate
        variable_rate = market_fee + self.config.return_allowance_rate
        if include_ad:
            variable_rate += self.config.ad_cost_rate

        denominator = 1 - variable_rate - target_margin
        if denominator <= 0:
            return 0

        target_price = fixed_costs / denominator
        return int(math.ceil(target_price / 1000) * 1000)

    def _get_recommendation(
        self, margin: float, moq: int, is_danger: bool,
        breakeven: int, market: MarketType
    ) -> str:
        """전략 추천 메시지 생성"""
        market_name = MARKET_FEES.get(market.value).name

        if is_danger:
            return f"🔴 진입 금지! 예상 마진 {margin:.1f}%로 수익 불가. 최소 {breakeven:,}원 이상 필요"

        if margin < 30:
            if moq <= 5:
                return f"🟡 {market_name} 구매대행으로 테스트 먼저. MOQ 낮아서 리스크 적음"
            else:
                return f"🟡 마진 {margin:.1f}%로 박함. MOQ {moq}개는 부담. 협상 필요"

        if moq <= 20:
            return f"🟢 {market_name} 진입 추천! 마진 {margin:.1f}% 우수. 소량 사입 시작"
        else:
            return f"🟢 마진 우수하나 MOQ {moq}개 주의. 처음엔 샘플로 품질 확인"


# 하위 호환성을 위한 별칭
MarginCalculator = LandedCostCalculator
