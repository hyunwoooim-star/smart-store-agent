"""도메인 모듈 (v3.3) - 순수 비즈니스 로직"""
from .models import (
    Product,
    CostResult,
    CostBreakdown,
    RiskLevel,
    MarketType,
    SupplierRisk,
)
from .logic import LandedCostCalculator, MarginCalculator

__all__ = [
    # 모델
    "Product",
    "CostResult",
    "CostBreakdown",
    "RiskLevel",
    "MarketType",
    "SupplierRisk",
    # 로직
    "LandedCostCalculator",
    "MarginCalculator",  # 하위 호환성
]
