"""
config.py - 애플리케이션 설정 (v3.3)

DDD 구조에서 모든 설정값을 중앙 관리
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class MarketConfig:
    """마켓별 수수료 설정"""
    name: str
    fee_rate: float  # 판매 수수료율


# 마켓별 수수료 테이블
MARKET_FEES: Dict[str, MarketConfig] = {
    "naver": MarketConfig("네이버 스마트스토어", 0.055),
    "coupang": MarketConfig("쿠팡", 0.108),
    "amazon": MarketConfig("아마존", 0.15),
}


@dataclass
class AppConfig:
    """애플리케이션 전체 설정 (v3.3)

    변경점:
    - 마켓별 수수료 지원 (네이버, 쿠팡, 아마존)
    - CBM 기반 해운 비용 계산 추가
    """
    # 환율
    exchange_rate: float = 195              # 원/위안 (2026년 기준)

    # 세금
    vat_rate: float = 0.10                  # 부가세 10%
    simple_tariff_rate: float = 0.20        # 간이통관 관부가세 약 20%

    # 배송비
    shipping_rate_air: int = 8000           # 항공 kg당
    shipping_rate_sea: int = 3000           # 해운 kg당
    cbm_rate: int = 50000                   # CBM당 해운비 (m³)
    min_shipping_fee: int = 5000            # 최소 배송비
    domestic_shipping: int = 3000           # 국내 택배비

    # 부피무게 계수
    volume_weight_divisor: int = 6000       # 항공 표준

    # 숨겨진 비용 (강제 적용)
    return_allowance_rate: float = 0.05     # 반품/CS 충당금 5%
    ad_cost_rate: float = 0.10              # 광고비 10%
    packaging_cost: int = 500               # 포장비 (건당)

    # 마진 기준
    danger_margin: float = 0.15             # 15% 미만 = 위험
    warning_margin: float = 0.30            # 30% 미만 = 주의

    # 카테고리별 관세율
    tariff_rates: Dict[str, float] = None

    def __post_init__(self):
        if self.tariff_rates is None:
            self.tariff_rates = {
                "가구/인테리어": 0.08,
                "캠핑/레저": 0.08,
                "의류/패션": 0.13,
                "전자기기": 0.08,
                "생활용품": 0.08,
                "기타": 0.10,
            }


# 기본 설정 인스턴스
DEFAULT_CONFIG = AppConfig()
