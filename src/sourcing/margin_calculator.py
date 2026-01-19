"""
margin_calculator.py - 중국 사입 실제 마진 계산기 (v3.1 Final)

핵심 기능:
1. 부피무게(Volume Weight) 자동 계산 및 청구무게 적용
2. 숨겨진 비용(반품충당금, 광고비) 반영으로 현실적 마진 도출
3. 손익분기점(BEP) 및 목표 판매가 자동 산출
4. 2-Track 전략(셀플링 vs 사입) 추천
"""

from dataclasses import dataclass
from typing import Optional
import math


@dataclass
class ProductDimensions:
    """제품 박스 사이즈 (cm)"""
    length: float
    width: float
    height: float


@dataclass
class SourcingInput:
    """소싱 입력 데이터"""
    product_name: str
    wholesale_price_cny: float      # 1688 도매가 (위안)
    actual_weight_kg: float         # 실제 무게 (kg)
    dimensions: ProductDimensions   # 박스 사이즈 (부피무게 계산용)
    moq: int                        # 최소 주문 수량
    target_price_krw: int           # 목표 판매가 (원)
    category: str                   # 상품 카테고리 (관세율 결정용)
    supplier_rating: Optional[float] = None


@dataclass
class MarginResult:
    """마진 계산 결과"""
    # 비용 상세
    product_cost_krw: int
    tariff_krw: int
    vat_krw: int
    shipping_agency_fee_krw: int
    domestic_shipping_krw: int
    platform_fee_krw: int
    return_allowance_krw: int       # v3.1 신규: 반품 충당금
    ad_cost_krw: int                # v3.1 신규: 광고비

    # 무게 정보
    actual_weight_kg: float
    volume_weight_kg: float         # v3.1 신규: 부피무게
    billable_weight_kg: float       # v3.1 신규: 청구무게 (둘 중 큰 값)

    # 총계
    total_cost_krw: int
    profit_krw: int
    margin_percent: float

    # 마진 및 전략
    is_viable: bool
    risk_level: str
    recommendation: str
    breakeven_price_krw: int        # 손익분기 판매가
    target_margin_price_krw: int    # 목표 마진(30%) 달성 판매가


class MarginCalculator:
    """마진 계산기 v3.1"""

    # --- 상수 설정 (v3.1 확정값) ---
    EXCHANGE_RATE = 190                 # 환율 (원/위안)
    VAT_RATE = 0.10                     # 부가세 (10%)
    NAVER_FEE_RATE = 0.055              # 네이버 수수료 (5.5%)
    RETURN_ALLOWANCE_RATE = 0.05        # 반품/CS 충당금 (5%)
    AD_COST_RATE = 0.10                 # 광고비 (10%)
    VOLUME_WEIGHT_DIVISOR = 6000        # 부피무게 계수 (항공 표준)
    DOMESTIC_SHIPPING = 3000            # 국내 택배비 (건당)

    # 카테고리별 관세율
    TARIFF_RATES = {
        "가구/인테리어": 0.08,
        "캠핑/레저": 0.08,
        "의류/패션": 0.13,
        "전자기기": 0.08,
        "생활용품": 0.08,
        "기타": 0.10
    }

    # 배대지 요금표 (예시: kg당 요금, 실제로는 구간별 요금표 적용 필요)
    # 기본 1kg: 8000원, 추가 0.5kg당 가격 등 복잡하지만 여기선 단순화
    SHIPPING_AGENCY_RATES = {
        "항공": 8000,   # kg당
        "해운": 3000,   # kg당
    }

    def calculate_volume_weight(self, dims: ProductDimensions) -> float:
        """부피무게 = (가로 x 세로 x 높이) / 6000"""
        volume = dims.length * dims.width * dims.height
        return volume / self.VOLUME_WEIGHT_DIVISOR

    def get_billable_weight(self, actual_weight: float, volume_weight: float) -> float:
        """청구무게 = Max(실무게, 부피무게)"""
        return max(actual_weight, volume_weight)

    def calculate(self, input_data: SourcingInput, shipping_method: str = "항공",
                  include_ad_cost: bool = True) -> MarginResult:
        """실제 마진 계산 실행"""

        # 1. 상품 원가
        product_cost_krw = int(input_data.wholesale_price_cny * self.EXCHANGE_RATE)

        # 2. 관세 (상품 원가 기준)
        tariff_rate = self.TARIFF_RATES.get(input_data.category, 0.10)
        tariff_krw = int(product_cost_krw * tariff_rate)

        # 3. 무게 및 배대지 비용 계산
        volume_weight = self.calculate_volume_weight(input_data.dimensions)
        billable_weight = self.get_billable_weight(input_data.actual_weight_kg, volume_weight)

        # 배대지 비용 (단순화: 무게 × kg당 요금) - 실제로는 구간별 요금표 적용 필요
        shipping_rate = self.SHIPPING_AGENCY_RATES.get(shipping_method, 8000)
        shipping_agency_fee_krw = int(billable_weight * shipping_rate)

        # 4. 부가세 (과세가격 = 물품가격 + 관세 + 운임)
        # 관세청 과세운임은 별도 기준이 있으나, 도수적으로 배대지 비용 전체 포함하여 계산
        taxable_amount = product_cost_krw + tariff_krw + shipping_agency_fee_krw
        vat_krw = int(taxable_amount * self.VAT_RATE)

        # 5. 판매 수수료 및 충당금
        platform_fee_krw = int(input_data.target_price_krw * self.NAVER_FEE_RATE)
        return_allowance_krw = int(input_data.target_price_krw * self.RETURN_ALLOWANCE_RATE)
        ad_cost_krw = int(input_data.target_price_krw * self.AD_COST_RATE) if include_ad_cost else 0

        # 6. 총 비용 및 이익
        total_cost_krw = (
            product_cost_krw +
            tariff_krw +
            vat_krw +
            shipping_agency_fee_krw +
            self.DOMESTIC_SHIPPING +
            platform_fee_krw +
            return_allowance_krw +
            ad_cost_krw
        )

        profit_krw = input_data.target_price_krw - total_cost_krw
        margin_percent = (profit_krw / input_data.target_price_krw * 100) if input_data.target_price_krw > 0 else 0

        # 7. 분석 지표 산출
        is_viable = margin_percent >= 15  # 최소 기준 (광고비 포함 시)

        if margin_percent >= 30:
            risk_level = "LOW"
        elif margin_percent >= 15:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        breakeven_price = self._calculate_breakeven_price(
            product_cost_krw, tariff_krw, vat_krw,
            shipping_agency_fee_krw, self.DOMESTIC_SHIPPING, include_ad_cost
        )

        target_margin_price = self._calculate_target_margin_price(
            product_cost_krw, tariff_krw, vat_krw,
            shipping_agency_fee_krw, self.DOMESTIC_SHIPPING, 0.30, include_ad_cost
        )

        recommendation = self._get_recommendation(margin_percent, input_data.moq, is_viable, breakeven_price)

        return MarginResult(
            product_cost_krw=product_cost_krw,
            tariff_krw=tariff_krw,
            vat_krw=vat_krw,
            shipping_agency_fee_krw=shipping_agency_fee_krw,
            domestic_shipping_krw=self.DOMESTIC_SHIPPING,
            platform_fee_krw=platform_fee_krw,
            return_allowance_krw=return_allowance_krw,
            ad_cost_krw=ad_cost_krw,
            actual_weight_kg=input_data.actual_weight_kg,
            volume_weight_kg=round(volume_weight, 2),
            billable_weight_kg=round(billable_weight, 2),
            total_cost_krw=total_cost_krw,
            profit_krw=profit_krw,
            margin_percent=round(margin_percent, 1),
            is_viable=is_viable,
            risk_level=risk_level,
            recommendation=recommendation,
            breakeven_price_krw=breakeven_price,
            target_margin_price_krw=target_margin_price
        )

    def _calculate_breakeven_price(self, product, tariff, vat, shipping, domestic,
                                    include_ad: bool) -> int:
        """손익분기 판매가 = 고정비 / (1 - 변동비율)"""
        fixed_costs = product + tariff + vat + shipping + domestic

        # 변동비율: 수수료 + 반품 + (광고)
        variable_rate = self.NAVER_FEE_RATE + self.RETURN_ALLOWANCE_RATE
        if include_ad:
            variable_rate += self.AD_COST_RATE

        if variable_rate >= 1.0:
            return 0  # 이론상 불가능

        breakeven = fixed_costs / (1 - variable_rate)
        return int(math.ceil(breakeven / 1000) * 1000)  # 1000원 단위 올림

    def _calculate_target_margin_price(self, product, tariff, vat, shipping, domestic,
                                        target_margin: float, include_ad: bool) -> int:
        """목표 마진 달성가"""
        fixed_costs = product + tariff + vat + shipping + domestic

        variable_rate = self.NAVER_FEE_RATE + self.RETURN_ALLOWANCE_RATE
        if include_ad:
            variable_rate += self.AD_COST_RATE

        denominator = 1 - variable_rate - target_margin
        if denominator <= 0:
            return 0  # 달성 불가

        target_price = fixed_costs / denominator
        return int(math.ceil(target_price / 1000) * 1000)

    def _get_recommendation(self, margin: float, moq: int, is_viable: bool, breakeven: int) -> str:
        """2-Track 전략 추천 로직"""
        if not is_viable:
            return f"❌ 수익성 부족 (예상마진 {margin}%). 최소 {breakeven:,}원 이상 필요"

        if moq <= 5:
            return "✅ 소량 테스트 가능 (셀플링). 5개 이하 샘플 주문하여 품질 확인 후 진행"
        elif moq <= 20:
            if margin >= 30:
                return "✅ 마진 우수 & MOQ 낮음. 소량 사입(20개 내외) 추천."
            else:
                return "🟡 마진 보통. 사입보다는 구매대행(위탁) 형태로 시장성 테스트 먼저"
        else:
            return "⚠️ MOQ 부담(50개↑). 초보 셀러에게 비추천. 반드시 낮게 깎을 수 있는 가능성 확인"


# --- 테스트 실행 코드 ---
if __name__ == "__main__":
    # 캠핑의자 시뮬레이션 데이터
    input_data = SourcingInput(
        product_name="초경량 캠핑 의자",
        wholesale_price_cny=45,             # 약 8,550원
        actual_weight_kg=2.5,               # 실무게
        dimensions=ProductDimensions(80, 20, 15),  # 박스: 부피가 큼
        moq=50,
        target_price_krw=45000,
        category="캠핑/레저"
    )

    calculator = MarginCalculator()
    result = calculator.calculate(input_data)

    print("\n" + "="*60)
    print(f"📦 [{input_data.product_name}] 마진 분석 결과 (v3.1)")
    print("="*60)
    print(f"\n1. 무게 분석")
    print(f"   - 실무게: {result.actual_weight_kg} kg")
    print(f"   - 부피무게: {result.volume_weight_kg} kg (적용됨 ⭐)" if result.volume_weight_kg > result.actual_weight_kg else f"   - 부피무게: {result.volume_weight_kg} kg")
    print(f"   - 청구무게: {result.billable_weight_kg} kg")

    print(f"\n2. 비용 상세")
    print(f"   - 상품원가: {result.product_cost_krw:,} 원")
    print(f"   - 해외배송비: {result.shipping_agency_fee_krw:,} 원 (부피무게 적용)")
    print(f"   - 관부가세: {result.tariff_krw + result.vat_krw:,} 원")
    print(f"   - 마케팅/운영비: {result.ad_cost_krw + result.return_allowance_krw:,} 원")

    print(f"\n3. 최종 성적표")
    print(f"   - 총 비용: {result.total_cost_krw:,} 원")
    print(f"   - 예상 수익: {result.profit_krw:,} 원")
    print(f"   - 마진율: {result.margin_percent}%")
    print(f"   - 손익분기점: {result.breakeven_price_krw:,} 원")

    print(f"\n🤖 AI 조언: {result.recommendation}")
    print("="*60 + "\n")
