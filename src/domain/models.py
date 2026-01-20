"""
models.py - 도메인 모델 (v3.3)

순수 파이썬 데이터 클래스. 외부 의존성 없음.
UI 프레임워크가 바뀌어도 이 파일은 그대로 사용 가능.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from enum import Enum


class RiskLevel(Enum):
    """위험도 레벨"""
    SAFE = "safe"           # 🟢 30% 이상
    WARNING = "warning"     # 🟡 15~30%
    DANGER = "danger"       # 🔴 15% 미만


class MarketType(Enum):
    """판매 마켓 종류"""
    NAVER = "naver"
    COUPANG = "coupang"
    AMAZON = "amazon"


@dataclass
class Product:
    """상품 정보"""
    name: str                       # 상품명
    price_cny: float                # 도매가 (위안)
    weight_kg: float                # 실제 무게 (kg)
    length_cm: float                # 가로 (cm)
    width_cm: float                 # 세로 (cm)
    height_cm: float                # 높이 (cm)
    category: str = "기타"          # 카테고리
    moq: int = 1                    # 최소 주문 수량
    supplier_rating: Optional[float] = None  # 공급업체 평점


@dataclass
class CostBreakdown:
    """비용 세부 내역"""
    product_cost: int               # 상품 원가 (원)
    china_shipping: int             # 중국 내 배송비 (신규)
    agency_fee: int                 # 구매대행 수수료 (신규)
    tariff: int                     # 관세
    vat: int                        # 부가세
    shipping_international: int     # 해외 배송비
    shipping_domestic: int          # 국내 택배비
    platform_fee: int               # 마켓 수수료
    return_allowance: int           # 반품 충당금
    ad_cost: int                    # 광고비
    packaging: int                  # 포장비


@dataclass
class CostResult:
    """마진 계산 결과"""
    # 비용 정보
    total_cost: int                 # 총 비용
    breakdown: CostBreakdown        # 비용 세부 내역

    # 무게 정보
    actual_weight_kg: float         # 실제 무게
    volume_weight_kg: float         # 부피 무게
    billable_weight_kg: float       # 청구 무게

    # 수익 정보
    target_price: int               # 목표 판매가
    profit: int                     # 예상 수익
    margin_percent: float           # 마진율 (%)

    # 위험도 분석
    risk_level: RiskLevel           # 위험 레벨
    is_danger: bool                 # 진입 금지 여부
    recommendation: str             # AI 추천 메시지

    # 손익분기점
    breakeven_price: int            # 손익분기 판매가
    target_margin_price: int        # 목표 마진(30%) 달성가


@dataclass
class SupplierRisk:
    """공급업체 위험 분석"""
    supplier_name: str
    risk_score: float               # 0~100 (높을수록 위험)
    red_flags: list = field(default_factory=list)
    recommendation: str = ""
