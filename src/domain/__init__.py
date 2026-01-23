"""도메인 모듈 (v4.0) - 순수 비즈니스 로직"""
from .models import (
    Product,
    CostResult,
    CostBreakdown,
    RiskLevel,
    MarketType,
    SupplierRisk,
)
from .logic import LandedCostCalculator, MarginCalculator
from .crawler_models import (
    SourcingKeyword,
    SourcingCandidate,
    UploadHistory,
    CrawlStats,
    DetailPageContent,
    CandidateStatus,
    CrawlRiskLevel,
)

__all__ = [
    # 기본 모델
    "Product",
    "CostResult",
    "CostBreakdown",
    "RiskLevel",
    "MarketType",
    "SupplierRisk",
    # 크롤러 모델 (v4.0)
    "SourcingKeyword",
    "SourcingCandidate",
    "UploadHistory",
    "CrawlStats",
    "DetailPageContent",
    "CandidateStatus",
    "CrawlRiskLevel",
    # 로직
    "LandedCostCalculator",
    "MarginCalculator",  # 하위 호환성
]
