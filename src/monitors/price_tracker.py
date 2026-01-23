"""
price_tracker.py - 경쟁사 가격 추적 모듈 (Phase 6-3)

기능:
1. URL 기반 경쟁사 상품 추적
2. 가격 히스토리 저장
3. 가격 변동 감지 및 알림
4. 전략적 가격 조정 제안

Gemini CTO 권장: URL 기반 가격 모니터링 (Option A)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import json
import re


class PriceChangeType(Enum):
    """가격 변동 유형"""
    INCREASE = "increase"       # 가격 인상
    DECREASE = "decrease"       # 가격 인하
    NO_CHANGE = "no_change"     # 변동 없음
    INITIAL = "initial"         # 최초 등록


class AlertLevel(Enum):
    """알림 레벨"""
    INFO = "info"               # 정보성
    WARNING = "warning"         # 주의
    CRITICAL = "critical"       # 긴급


class MarketPlatform(Enum):
    """마켓 플랫폼"""
    NAVER = "naver"
    COUPANG = "coupang"
    GMARKET = "gmarket"
    ELEVEN = "11st"
    AUCTION = "auction"
    OTHER = "other"


@dataclass
class PricePoint:
    """가격 시점 데이터"""
    price: int                  # 가격 (원)
    timestamp: str              # 기록 시점 (ISO 형식)
    source: str = ""            # 데이터 출처


@dataclass
class CompetitorProduct:
    """경쟁사 상품 정보"""
    product_id: str             # 고유 식별자
    name: str                   # 상품명
    url: str                    # 상품 URL
    platform: MarketPlatform    # 판매 플랫폼
    current_price: int          # 현재 가격
    my_price: Optional[int] = None  # 내 상품 가격 (비교용)
    price_history: List[PricePoint] = field(default_factory=list)
    last_checked: str = ""      # 마지막 확인 시점
    is_active: bool = True      # 추적 활성화 여부
    tags: List[str] = field(default_factory=list)  # 태그 (예: "메인키워드", "서브키워드")
    notes: str = ""             # 메모


@dataclass
class PriceAlert:
    """가격 변동 알림"""
    alert_id: str
    product_id: str
    product_name: str
    platform: MarketPlatform
    change_type: PriceChangeType
    old_price: int
    new_price: int
    change_amount: int          # 변동 금액 (절대값)
    change_percent: float       # 변동률 (%)
    alert_level: AlertLevel
    message: str
    timestamp: str
    is_read: bool = False


@dataclass
class PricingStrategy:
    """가격 전략 제안"""
    product_id: str
    current_my_price: int
    avg_competitor_price: int
    min_competitor_price: int
    max_competitor_price: int
    recommended_price: int
    recommendation: str
    margin_at_recommended: float  # 추천가에서의 예상 마진율


class PriceTracker:
    """경쟁사 가격 추적기"""

    # 가격 변동 임계값
    ALERT_THRESHOLD_PERCENT = 5.0    # 5% 이상 변동 시 알림
    CRITICAL_THRESHOLD_PERCENT = 15.0  # 15% 이상 변동 시 긴급 알림

    # URL 패턴으로 플랫폼 감지
    PLATFORM_PATTERNS = {
        MarketPlatform.NAVER: [
            r"smartstore\.naver\.com",
            r"brand\.naver\.com",
            r"shopping\.naver\.com",
        ],
        MarketPlatform.COUPANG: [
            r"coupang\.com",
        ],
        MarketPlatform.GMARKET: [
            r"gmarket\.co\.kr",
        ],
        MarketPlatform.ELEVEN: [
            r"11st\.co\.kr",
        ],
        MarketPlatform.AUCTION: [
            r"auction\.co\.kr",
        ],
    }

    def __init__(self):
        self.products: Dict[str, CompetitorProduct] = {}
        self.alerts: List[PriceAlert] = []
        self._alert_counter = 0

    def detect_platform(self, url: str) -> MarketPlatform:
        """URL에서 플랫폼 감지"""
        for platform, patterns in self.PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return platform
        return MarketPlatform.OTHER

    def add_product(
        self,
        name: str,
        url: str,
        current_price: int,
        my_price: Optional[int] = None,
        tags: Optional[List[str]] = None,
        notes: str = ""
    ) -> CompetitorProduct:
        """경쟁 상품 추가"""
        product_id = f"comp_{len(self.products) + 1:04d}"
        platform = self.detect_platform(url)
        timestamp = datetime.now().isoformat()

        product = CompetitorProduct(
            product_id=product_id,
            name=name,
            url=url,
            platform=platform,
            current_price=current_price,
            my_price=my_price,
            price_history=[
                PricePoint(price=current_price, timestamp=timestamp, source="initial")
            ],
            last_checked=timestamp,
            tags=tags or [],
            notes=notes
        )

        self.products[product_id] = product
        return product

    def update_price(
        self,
        product_id: str,
        new_price: int,
        source: str = "manual"
    ) -> Optional[PriceAlert]:
        """가격 업데이트 및 변동 감지"""
        if product_id not in self.products:
            return None

        product = self.products[product_id]
        old_price = product.current_price
        timestamp = datetime.now().isoformat()

        # 가격 히스토리 추가
        product.price_history.append(
            PricePoint(price=new_price, timestamp=timestamp, source=source)
        )
        product.current_price = new_price
        product.last_checked = timestamp

        # 가격 변동 감지
        if old_price == new_price:
            return None

        change_amount = new_price - old_price
        change_percent = (change_amount / old_price) * 100 if old_price > 0 else 0
        change_type = PriceChangeType.INCREASE if change_amount > 0 else PriceChangeType.DECREASE

        # 알림 레벨 결정
        abs_percent = abs(change_percent)
        if abs_percent >= self.CRITICAL_THRESHOLD_PERCENT:
            alert_level = AlertLevel.CRITICAL
        elif abs_percent >= self.ALERT_THRESHOLD_PERCENT:
            alert_level = AlertLevel.WARNING
        else:
            alert_level = AlertLevel.INFO

        # 알림 메시지 생성
        message = self._generate_alert_message(
            product, change_type, old_price, new_price, change_percent
        )

        # 알림 생성
        self._alert_counter += 1
        alert = PriceAlert(
            alert_id=f"alert_{self._alert_counter:05d}",
            product_id=product_id,
            product_name=product.name,
            platform=product.platform,
            change_type=change_type,
            old_price=old_price,
            new_price=new_price,
            change_amount=abs(change_amount),
            change_percent=abs(change_percent),
            alert_level=alert_level,
            message=message,
            timestamp=timestamp
        )

        self.alerts.append(alert)
        return alert

    def _generate_alert_message(
        self,
        product: CompetitorProduct,
        change_type: PriceChangeType,
        old_price: int,
        new_price: int,
        change_percent: float
    ) -> str:
        """알림 메시지 생성"""
        direction = "인상" if change_type == PriceChangeType.INCREASE else "인하"
        emoji = "📈" if change_type == PriceChangeType.INCREASE else "📉"

        msg = f"{emoji} [{product.platform.value.upper()}] {product.name}\n"
        msg += f"가격 {direction}: {old_price:,}원 → {new_price:,}원 ({change_percent:+.1f}%)"

        # 내 가격과 비교
        if product.my_price:
            diff = new_price - product.my_price
            if diff > 0:
                msg += f"\n💡 내 가격({product.my_price:,}원)보다 {diff:,}원 비쌈"
            elif diff < 0:
                msg += f"\n⚠️ 내 가격({product.my_price:,}원)보다 {abs(diff):,}원 저렴"
            else:
                msg += f"\n⚖️ 내 가격과 동일"

        return msg

    def get_price_history(
        self,
        product_id: str,
        limit: int = 30
    ) -> List[PricePoint]:
        """가격 히스토리 조회"""
        if product_id not in self.products:
            return []

        history = self.products[product_id].price_history
        return history[-limit:] if len(history) > limit else history

    def get_unread_alerts(self) -> List[PriceAlert]:
        """읽지 않은 알림 조회"""
        return [a for a in self.alerts if not a.is_read]

    def get_alerts_by_level(self, level: AlertLevel) -> List[PriceAlert]:
        """레벨별 알림 조회"""
        return [a for a in self.alerts if a.alert_level == level]

    def mark_alert_read(self, alert_id: str) -> bool:
        """알림 읽음 처리"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.is_read = True
                return True
        return False

    def get_pricing_strategy(
        self,
        product_id: str,
        my_cost: int,
        target_margin: float = 30.0
    ) -> Optional[PricingStrategy]:
        """가격 전략 제안"""
        if product_id not in self.products:
            return None

        product = self.products[product_id]
        if not product.my_price:
            return None

        # 동일 카테고리 경쟁 상품들의 현재 가격
        competitor_prices = [p.current_price for p in self.products.values() if p.is_active]

        if not competitor_prices:
            return None

        avg_price = sum(competitor_prices) // len(competitor_prices)
        min_price = min(competitor_prices)
        max_price = max(competitor_prices)

        # 추천 가격 계산 (경쟁력 있으면서 마진 확보)
        # 목표 마진을 위한 최소 판매가
        min_price_for_margin = int(my_cost / (1 - target_margin / 100))

        # 경쟁사 평균보다 약간 낮거나 같게 설정 (마진이 허용하는 범위에서)
        if avg_price >= min_price_for_margin:
            recommended = min(avg_price, int(avg_price * 0.95))  # 5% 저렴하게
            if recommended < min_price_for_margin:
                recommended = min_price_for_margin
        else:
            # 마진을 위해서는 평균보다 비싸게 팔아야 함
            recommended = min_price_for_margin

        # 추천가에서의 마진율
        margin_at_recommended = ((recommended - my_cost) / recommended) * 100 if recommended > 0 else 0

        # 추천 메시지 생성
        if recommended <= min_price:
            recommendation = f"🔴 현재 시장 최저가({min_price:,}원) 이하. 차별화 전략 필요"
        elif recommended < avg_price:
            recommendation = f"🟢 경쟁 가격({avg_price:,}원) 대비 저렴. 가격 경쟁력 확보"
        elif margin_at_recommended < 15:
            recommendation = f"🟡 마진율 {margin_at_recommended:.1f}%로 박함. 비용 절감 또는 차별화 필요"
        else:
            recommendation = f"🟢 적정 마진({margin_at_recommended:.1f}%) 확보 가능"

        return PricingStrategy(
            product_id=product_id,
            current_my_price=product.my_price,
            avg_competitor_price=avg_price,
            min_competitor_price=min_price,
            max_competitor_price=max_price,
            recommended_price=recommended,
            recommendation=recommendation,
            margin_at_recommended=margin_at_recommended
        )

    def get_competitive_analysis(self, my_price: int) -> Dict:
        """경쟁력 분석"""
        if not self.products:
            return {
                "total_competitors": 0,
                "cheaper_count": 0,
                "same_count": 0,
                "expensive_count": 0,
                "position": "데이터 없음",
                "avg_competitor_price": 0,
            }

        prices = [p.current_price for p in self.products.values() if p.is_active]

        if not prices:
            return {
                "total_competitors": 0,
                "cheaper_count": 0,
                "same_count": 0,
                "expensive_count": 0,
                "position": "활성 경쟁사 없음",
                "avg_competitor_price": 0,
            }

        cheaper = sum(1 for p in prices if p < my_price)
        same = sum(1 for p in prices if p == my_price)
        expensive = sum(1 for p in prices if p > my_price)

        # 내 가격 포지션 결정
        total = len(prices)
        if cheaper == 0:
            position = "최저가"
        elif expensive == 0:
            position = "최고가"
        elif cheaper <= total * 0.3:
            position = "저가 그룹"
        elif cheaper >= total * 0.7:
            position = "고가 그룹"
        else:
            position = "중간 그룹"

        return {
            "total_competitors": total,
            "cheaper_count": cheaper,
            "same_count": same,
            "expensive_count": expensive,
            "position": position,
            "avg_competitor_price": sum(prices) // len(prices),
            "min_price": min(prices),
            "max_price": max(prices),
        }

    def export_to_dict(self) -> Dict:
        """데이터 내보내기"""
        return {
            "products": [
                {
                    "product_id": p.product_id,
                    "name": p.name,
                    "url": p.url,
                    "platform": p.platform.value,
                    "current_price": p.current_price,
                    "my_price": p.my_price,
                    "price_history": [
                        {"price": h.price, "timestamp": h.timestamp, "source": h.source}
                        for h in p.price_history
                    ],
                    "last_checked": p.last_checked,
                    "is_active": p.is_active,
                    "tags": p.tags,
                    "notes": p.notes,
                }
                for p in self.products.values()
            ],
            "alerts": [
                {
                    "alert_id": a.alert_id,
                    "product_id": a.product_id,
                    "product_name": a.product_name,
                    "change_type": a.change_type.value,
                    "old_price": a.old_price,
                    "new_price": a.new_price,
                    "change_percent": a.change_percent,
                    "alert_level": a.alert_level.value,
                    "message": a.message,
                    "timestamp": a.timestamp,
                    "is_read": a.is_read,
                }
                for a in self.alerts
            ],
        }

    def import_from_dict(self, data: Dict):
        """데이터 불러오기"""
        for p_data in data.get("products", []):
            product = CompetitorProduct(
                product_id=p_data["product_id"],
                name=p_data["name"],
                url=p_data["url"],
                platform=MarketPlatform(p_data["platform"]),
                current_price=p_data["current_price"],
                my_price=p_data.get("my_price"),
                price_history=[
                    PricePoint(h["price"], h["timestamp"], h.get("source", ""))
                    for h in p_data.get("price_history", [])
                ],
                last_checked=p_data.get("last_checked", ""),
                is_active=p_data.get("is_active", True),
                tags=p_data.get("tags", []),
                notes=p_data.get("notes", ""),
            )
            self.products[product.product_id] = product


class MockPriceTracker(PriceTracker):
    """테스트용 Mock 가격 추적기"""

    def __init__(self):
        super().__init__()
        self._setup_mock_data()

    def _setup_mock_data(self):
        """Mock 데이터 설정"""
        # 캠핑 의자 경쟁사들
        self.add_product(
            name="캠핑 릴렉스 체어 A",
            url="https://smartstore.naver.com/camping/products/12345",
            current_price=45000,
            my_price=42000,
            tags=["캠핑의자", "메인"]
        )

        self.add_product(
            name="초경량 캠핑의자 B",
            url="https://www.coupang.com/vp/products/67890",
            current_price=38000,
            my_price=42000,
            tags=["캠핑의자", "저가경쟁"]
        )

        self.add_product(
            name="프리미엄 캠핑체어 C",
            url="https://smartstore.naver.com/outdoor/products/11111",
            current_price=55000,
            my_price=42000,
            tags=["캠핑의자", "고가"]
        )


# 편의 함수
def create_tracker(use_mock: bool = False) -> PriceTracker:
    """가격 추적기 생성"""
    return MockPriceTracker() if use_mock else PriceTracker()
