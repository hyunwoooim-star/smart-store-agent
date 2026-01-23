"""
test_price_tracker.py - 경쟁사 가격 추적 테스트 (Phase 6-3)

테스트 항목:
1. 플랫폼 감지
2. 상품 추가/조회
3. 가격 업데이트 및 변동 감지
4. 알림 레벨 분류
5. 경쟁력 분석
6. 가격 전략 제안
7. 데이터 내보내기/불러오기

v3.6.1 (Gemini CTO 피드백 반영):
8. 하이브리드 임계값 테스트
9. 노출 등급(Tier) 테스트
10. 가격 라운딩 테스트
11. 엣지케이스 테스트
"""

import pytest
import sys
from pathlib import Path

# 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.monitors.price_tracker import (
    PriceTracker,
    MockPriceTracker,
    CompetitorProduct,
    PricePoint,
    PriceAlert,
    PricingStrategy,
    PriceChangeType,
    AlertLevel,
    MarketPlatform,
    ExposureTier,
    PricingStrategyType,
    create_tracker,
)


class TestPlatformDetection:
    """플랫폼 감지 테스트"""

    def setup_method(self):
        self.tracker = PriceTracker()

    def test_detect_naver_smartstore(self):
        """네이버 스마트스토어 URL 감지"""
        url = "https://smartstore.naver.com/camping/products/12345"
        assert self.tracker.detect_platform(url) == MarketPlatform.NAVER

    def test_detect_naver_brand(self):
        """네이버 브랜드스토어 URL 감지"""
        url = "https://brand.naver.com/outdoor/products/67890"
        assert self.tracker.detect_platform(url) == MarketPlatform.NAVER

    def test_detect_coupang(self):
        """쿠팡 URL 감지"""
        url = "https://www.coupang.com/vp/products/12345678"
        assert self.tracker.detect_platform(url) == MarketPlatform.COUPANG

    def test_detect_gmarket(self):
        """G마켓 URL 감지"""
        url = "http://item.gmarket.co.kr/item?goodscode=12345"
        assert self.tracker.detect_platform(url) == MarketPlatform.GMARKET

    def test_detect_11st(self):
        """11번가 URL 감지"""
        url = "https://www.11st.co.kr/products/12345"
        assert self.tracker.detect_platform(url) == MarketPlatform.ELEVEN

    def test_detect_auction(self):
        """옥션 URL 감지"""
        url = "http://itempage3.auction.co.kr/DetailView.aspx?itemno=12345"
        assert self.tracker.detect_platform(url) == MarketPlatform.AUCTION

    def test_detect_unknown(self):
        """알 수 없는 URL"""
        url = "https://www.somestore.com/product/12345"
        assert self.tracker.detect_platform(url) == MarketPlatform.OTHER


class TestProductManagement:
    """상품 관리 테스트"""

    def setup_method(self):
        self.tracker = PriceTracker()

    def test_add_product(self):
        """상품 추가"""
        product = self.tracker.add_product(
            name="캠핑 의자",
            url="https://smartstore.naver.com/shop/products/123",
            current_price=45000,
            my_price=42000,
            tags=["캠핑", "의자"]
        )

        assert product.product_id.startswith("comp_")
        assert product.name == "캠핑 의자"
        assert product.current_price == 45000
        assert product.my_price == 42000
        assert product.platform == MarketPlatform.NAVER
        assert len(product.price_history) == 1
        assert "캠핑" in product.tags

    def test_add_multiple_products(self):
        """복수 상품 추가"""
        p1 = self.tracker.add_product("상품 A", "https://coupang.com/a", 30000)
        p2 = self.tracker.add_product("상품 B", "https://coupang.com/b", 35000)
        p3 = self.tracker.add_product("상품 C", "https://coupang.com/c", 40000)

        assert len(self.tracker.products) == 3
        assert p1.product_id != p2.product_id != p3.product_id

    def test_product_initial_history(self):
        """초기 가격 히스토리"""
        product = self.tracker.add_product(
            name="테스트",
            url="https://test.com/1",
            current_price=10000
        )

        assert len(product.price_history) == 1
        assert product.price_history[0].price == 10000
        assert product.price_history[0].source == "initial"


class TestPriceUpdate:
    """가격 업데이트 테스트"""

    def setup_method(self):
        self.tracker = PriceTracker()
        self.product = self.tracker.add_product(
            name="테스트 상품",
            url="https://test.com/product",
            current_price=10000,
            my_price=9000
        )

    def test_price_update_no_change(self):
        """가격 변동 없음"""
        alert = self.tracker.update_price(self.product.product_id, 10000)
        assert alert is None

    def test_price_increase_small(self):
        """소폭 가격 인상 (5% 미만)"""
        alert = self.tracker.update_price(self.product.product_id, 10400)  # +4%

        assert alert is not None
        assert alert.change_type == PriceChangeType.INCREASE
        assert alert.old_price == 10000
        assert alert.new_price == 10400
        assert alert.alert_level == AlertLevel.INFO

    def test_price_increase_medium(self):
        """중간 가격 인상 (5~15%)"""
        alert = self.tracker.update_price(self.product.product_id, 11000)  # +10%

        assert alert is not None
        assert alert.change_type == PriceChangeType.INCREASE
        assert alert.alert_level == AlertLevel.WARNING

    def test_price_increase_critical(self):
        """급격한 가격 인상 (15% 이상)"""
        alert = self.tracker.update_price(self.product.product_id, 12000)  # +20%

        assert alert is not None
        assert alert.change_type == PriceChangeType.INCREASE
        assert alert.alert_level == AlertLevel.CRITICAL

    def test_price_decrease(self):
        """가격 인하"""
        alert = self.tracker.update_price(self.product.product_id, 8500)  # -15%

        assert alert is not None
        assert alert.change_type == PriceChangeType.DECREASE
        assert alert.alert_level == AlertLevel.CRITICAL  # 15% 변동

    def test_price_history_accumulation(self):
        """가격 히스토리 누적"""
        self.tracker.update_price(self.product.product_id, 11000)
        self.tracker.update_price(self.product.product_id, 12000)
        self.tracker.update_price(self.product.product_id, 11500)

        history = self.tracker.get_price_history(self.product.product_id)
        assert len(history) == 4  # 초기 + 3번 업데이트


class TestAlertManagement:
    """알림 관리 테스트"""

    def setup_method(self):
        self.tracker = PriceTracker()
        product = self.tracker.add_product(
            name="알림 테스트",
            url="https://test.com/alert",
            current_price=10000,
            my_price=9500
        )
        # 알림 생성
        self.tracker.update_price(product.product_id, 11000)  # +10%
        self.tracker.update_price(product.product_id, 13000)  # +18%
        self.product_id = product.product_id

    def test_unread_alerts(self):
        """읽지 않은 알림"""
        unread = self.tracker.get_unread_alerts()
        assert len(unread) == 2

    def test_mark_alert_read(self):
        """알림 읽음 처리"""
        unread = self.tracker.get_unread_alerts()
        alert_id = unread[0].alert_id

        result = self.tracker.mark_alert_read(alert_id)
        assert result is True

        unread_after = self.tracker.get_unread_alerts()
        assert len(unread_after) == 1

    def test_alerts_by_level(self):
        """레벨별 알림 조회"""
        warning = self.tracker.get_alerts_by_level(AlertLevel.WARNING)
        critical = self.tracker.get_alerts_by_level(AlertLevel.CRITICAL)

        assert len(warning) >= 1
        assert len(critical) >= 1

    def test_alert_message_content(self):
        """알림 메시지 내용"""
        alerts = self.tracker.alerts
        assert len(alerts) > 0

        # 메시지에 필수 정보 포함 확인
        msg = alerts[0].message
        assert "알림 테스트" in msg or "원" in msg


class TestCompetitiveAnalysis:
    """경쟁력 분석 테스트"""

    def setup_method(self):
        self.tracker = PriceTracker()
        # 경쟁 상품들 추가
        self.tracker.add_product("상품A", "https://a.com", 30000)
        self.tracker.add_product("상품B", "https://b.com", 35000)
        self.tracker.add_product("상품C", "https://c.com", 40000)
        self.tracker.add_product("상품D", "https://d.com", 45000)
        self.tracker.add_product("상품E", "https://e.com", 50000)

    def test_analysis_cheapest(self):
        """최저가 분석"""
        analysis = self.tracker.get_competitive_analysis(25000)  # 모든 경쟁사보다 저렴

        assert analysis["position"] == "최저가"
        assert analysis["cheaper_count"] == 0
        assert analysis["expensive_count"] == 5

    def test_analysis_most_expensive(self):
        """최고가 분석"""
        analysis = self.tracker.get_competitive_analysis(55000)  # 모든 경쟁사보다 비쌈

        assert analysis["position"] == "최고가"
        assert analysis["cheaper_count"] == 5
        assert analysis["expensive_count"] == 0

    def test_analysis_middle(self):
        """중간 가격 분석"""
        analysis = self.tracker.get_competitive_analysis(40000)  # 중간

        assert analysis["total_competitors"] == 5
        assert analysis["avg_competitor_price"] == 40000
        assert analysis["min_price"] == 30000
        assert analysis["max_price"] == 50000

    def test_analysis_no_competitors(self):
        """경쟁사 없음"""
        empty_tracker = PriceTracker()
        analysis = empty_tracker.get_competitive_analysis(30000)

        assert analysis["total_competitors"] == 0
        assert analysis["position"] == "데이터 없음"


class TestPricingStrategy:
    """가격 전략 테스트"""

    def setup_method(self):
        self.tracker = PriceTracker()
        # 내 상품 (my_price 설정)
        self.my_product = self.tracker.add_product(
            name="내 상품",
            url="https://myshop.com/product",
            current_price=40000,
            my_price=40000
        )
        # 경쟁 상품들
        self.tracker.add_product("경쟁A", "https://a.com", 35000)
        self.tracker.add_product("경쟁B", "https://b.com", 42000)
        self.tracker.add_product("경쟁C", "https://c.com", 45000)

    def test_strategy_calculation(self):
        """전략 계산"""
        strategy = self.tracker.get_pricing_strategy(
            self.my_product.product_id,
            my_cost=25000,  # 원가
            target_margin=30.0  # 목표 마진
        )

        assert strategy is not None
        assert strategy.current_my_price == 40000
        assert strategy.min_competitor_price == 35000
        assert strategy.max_competitor_price == 45000
        assert strategy.recommended_price > 0
        assert strategy.margin_at_recommended >= 0

    def test_strategy_recommendation_message(self):
        """전략 추천 메시지"""
        strategy = self.tracker.get_pricing_strategy(
            self.my_product.product_id,
            my_cost=20000,
            target_margin=30.0
        )

        assert strategy is not None
        assert strategy.recommendation != ""
        # 메시지에 이모지 또는 가격 정보 포함
        assert "🟢" in strategy.recommendation or "🔴" in strategy.recommendation or "🟡" in strategy.recommendation

    def test_strategy_none_for_invalid_product(self):
        """존재하지 않는 상품"""
        strategy = self.tracker.get_pricing_strategy("invalid_id", 10000)
        assert strategy is None


class TestDataExportImport:
    """데이터 내보내기/불러오기 테스트"""

    def setup_method(self):
        self.tracker = PriceTracker()
        self.product = self.tracker.add_product(
            name="내보내기 테스트",
            url="https://export.com/test",
            current_price=30000,
            my_price=28000,
            tags=["테스트", "내보내기"],
            notes="테스트 메모"
        )
        self.tracker.update_price(self.product.product_id, 32000)

    def test_export_products(self):
        """상품 데이터 내보내기"""
        data = self.tracker.export_to_dict()

        assert "products" in data
        assert len(data["products"]) == 1
        assert data["products"][0]["name"] == "내보내기 테스트"
        assert len(data["products"][0]["price_history"]) == 2

    def test_export_alerts(self):
        """알림 데이터 내보내기"""
        data = self.tracker.export_to_dict()

        assert "alerts" in data
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["change_type"] == "increase"

    def test_import_products(self):
        """상품 데이터 불러오기"""
        data = self.tracker.export_to_dict()

        new_tracker = PriceTracker()
        new_tracker.import_from_dict(data)

        assert len(new_tracker.products) == 1
        imported_product = list(new_tracker.products.values())[0]
        assert imported_product.name == "내보내기 테스트"
        assert imported_product.current_price == 32000  # 업데이트된 가격
        assert len(imported_product.price_history) == 2


class TestMockTracker:
    """Mock 추적기 테스트"""

    def test_mock_has_sample_data(self):
        """Mock 데이터 존재"""
        tracker = MockPriceTracker()

        assert len(tracker.products) >= 3

    def test_mock_products_have_prices(self):
        """Mock 상품 가격 확인"""
        tracker = MockPriceTracker()

        for product in tracker.products.values():
            assert product.current_price > 0
            assert product.my_price is not None

    def test_create_tracker_mock(self):
        """create_tracker(use_mock=True)"""
        tracker = create_tracker(use_mock=True)
        assert isinstance(tracker, MockPriceTracker)

    def test_create_tracker_real(self):
        """create_tracker(use_mock=False)"""
        tracker = create_tracker(use_mock=False)
        assert isinstance(tracker, PriceTracker)
        assert not isinstance(tracker, MockPriceTracker)


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def setup_method(self):
        self.tracker = PriceTracker()

    def test_update_nonexistent_product(self):
        """존재하지 않는 상품 업데이트"""
        alert = self.tracker.update_price("invalid_id", 10000)
        assert alert is None

    def test_get_history_nonexistent_product(self):
        """존재하지 않는 상품 히스토리"""
        history = self.tracker.get_price_history("invalid_id")
        assert history == []

    def test_price_history_limit(self):
        """히스토리 제한"""
        product = self.tracker.add_product("제한 테스트", "https://test.com", 10000)

        # 50개 가격 업데이트
        for i in range(50):
            self.tracker.update_price(product.product_id, 10000 + (i * 100))

        # 제한된 히스토리 조회
        history = self.tracker.get_price_history(product.product_id, limit=10)
        assert len(history) == 10

    def test_zero_price(self):
        """0원 가격 처리"""
        product = self.tracker.add_product("무료 상품", "https://test.com", 0)
        alert = self.tracker.update_price(product.product_id, 10000)

        # 0에서 변동 시 퍼센트 계산 예외 처리
        assert alert is not None
        assert alert.change_percent == 0  # 0으로 나누기 방지

    def test_mark_read_invalid_alert(self):
        """존재하지 않는 알림 읽음 처리"""
        result = self.tracker.mark_alert_read("invalid_alert")
        assert result is False


# ============================================
# v3.6.1 Gemini CTO 피드백 반영 테스트
# ============================================

class TestHybridThreshold:
    """Q1: 하이브리드 임계값 테스트 (% AND 절대금액)"""

    def setup_method(self):
        self.tracker = PriceTracker()

    def test_low_price_high_percent_info(self):
        """저가 상품 큰 퍼센트 변동 → INFO (절대금액 미달)

        5,000원 상품에서 +10% (500원 변동)
        퍼센트 조건은 충족하지만 절대금액(1,000원) 미달
        """
        product = self.tracker.add_product("저가 상품", "https://test.com", 5000)
        alert = self.tracker.update_price(product.product_id, 5500)  # +10%, +500원

        assert alert is not None
        assert alert.change_percent == 10.0
        assert alert.change_amount == 500
        # 절대금액 조건 미달로 INFO
        assert alert.alert_level == AlertLevel.INFO

    def test_high_price_small_percent_warning(self):
        """고가 상품 작은 퍼센트 큰 금액 → WARNING

        100,000원 상품에서 +5% (5,000원 변동)
        퍼센트 조건(5%) AND 절대금액 조건(1,000원) 모두 충족
        """
        product = self.tracker.add_product("고가 상품", "https://test.com", 100000)
        alert = self.tracker.update_price(product.product_id, 105000)  # +5%, +5,000원

        assert alert is not None
        assert alert.change_percent == 5.0
        assert alert.change_amount == 5000
        assert alert.alert_level == AlertLevel.WARNING

    def test_both_conditions_met_critical(self):
        """두 조건 모두 충족 → CRITICAL

        50,000원 상품에서 +20% (10,000원 변동)
        """
        product = self.tracker.add_product("테스트", "https://test.com", 50000)
        alert = self.tracker.update_price(product.product_id, 60000)  # +20%, +10,000원

        assert alert is not None
        assert alert.change_percent == 20.0
        assert alert.change_amount == 10000
        assert alert.alert_level == AlertLevel.CRITICAL

    def test_neither_condition_met_info(self):
        """두 조건 모두 미충족 → INFO

        50,000원 상품에서 +1% (500원 변동)
        """
        product = self.tracker.add_product("테스트", "https://test.com", 50000)
        alert = self.tracker.update_price(product.product_id, 50500)  # +1%, +500원

        assert alert is not None
        assert alert.change_percent == 1.0
        assert alert.change_amount == 500
        assert alert.alert_level == AlertLevel.INFO


class TestExposureTier:
    """Q3: 노출 등급 (Tier) 테스트"""

    def setup_method(self):
        self.tracker = PriceTracker()
        # 경쟁 상품들 (최저가 30,000원)
        self.tracker.add_product("최저가", "https://a.com", 30000)
        self.tracker.add_product("중간", "https://b.com", 35000)
        self.tracker.add_product("고가", "https://c.com", 45000)

    def test_tier1_exposure(self):
        """Tier 1 노출권 (+2% 이내)"""
        # 30,000원 최저가 대비 30,600원 = +2%
        tier = self.tracker.get_exposure_tier(30600, 30000)
        assert tier == ExposureTier.TIER1_EXPOSURE

    def test_tier1_same_price(self):
        """Tier 1 동일 가격"""
        tier = self.tracker.get_exposure_tier(30000, 30000)
        assert tier == ExposureTier.TIER1_EXPOSURE

    def test_tier1_cheaper(self):
        """Tier 1 최저가보다 저렴"""
        tier = self.tracker.get_exposure_tier(29000, 30000)
        assert tier == ExposureTier.TIER1_EXPOSURE

    def test_tier2_defense(self):
        """Tier 2 방어권 (+2~10%)"""
        # 30,000원 대비 33,000원 = +10%
        tier = self.tracker.get_exposure_tier(33000, 30000)
        assert tier == ExposureTier.TIER2_DEFENSE

    def test_tier3_out(self):
        """Tier 3 이탈권 (+10% 초과)"""
        # 30,000원 대비 34,000원 = +13%
        tier = self.tracker.get_exposure_tier(34000, 30000)
        assert tier == ExposureTier.TIER3_OUT

    def test_competitive_analysis_has_tier(self):
        """경쟁력 분석에 Tier 포함 확인"""
        analysis = self.tracker.get_competitive_analysis(30500)  # +1.67%

        assert "exposure_tier" in analysis
        assert "tier_message" in analysis
        assert analysis["exposure_tier"] == ExposureTier.TIER1_EXPOSURE.value


class TestPriceRounding:
    """코드리뷰: 가격 라운딩 (100원 단위) 테스트"""

    def test_round_price_down(self):
        """내림 라운딩"""
        assert PriceTracker.round_price(14237) == 14200

    def test_round_price_up(self):
        """올림 라운딩"""
        assert PriceTracker.round_price(14250) == 14200  # 정확히 50은 banker's rounding

    def test_round_price_55(self):
        """55 이상은 올림"""
        assert PriceTracker.round_price(14255) == 14300

    def test_round_price_already_rounded(self):
        """이미 100원 단위"""
        assert PriceTracker.round_price(14200) == 14200

    def test_round_price_zero(self):
        """0원"""
        assert PriceTracker.round_price(0) == 0


class TestPricingStrategyV2:
    """Q2: 가격 전략 v2 테스트 (최저가-100원 방식)"""

    def setup_method(self):
        self.tracker = PriceTracker()
        self.my_product = self.tracker.add_product(
            name="내 상품",
            url="https://myshop.com/product",
            current_price=40000,
            my_price=40000
        )
        # 경쟁 상품들 (최저가 35,000원)
        self.tracker.add_product("경쟁A", "https://a.com", 35000)
        self.tracker.add_product("경쟁B", "https://b.com", 42000)
        self.tracker.add_product("경쟁C", "https://c.com", 45000)

    def test_price_leadership_strategy(self):
        """마진 여유 있을 때 → PRICE_LEADERSHIP"""
        strategy = self.tracker.get_pricing_strategy(
            self.my_product.product_id,
            my_cost=20000,  # 원가 낮음
            target_margin=30.0
        )

        assert strategy is not None
        assert strategy.strategy_type == PricingStrategyType.PRICE_LEADERSHIP
        # 최저가(35,000) - 100 = 34,900 → 라운딩 34,900
        assert strategy.recommended_price == 34900
        assert "노출 우위" in strategy.recommendation or "최저가" in strategy.recommendation

    def test_premium_positioning_strategy(self):
        """마진 방어 불가 시 → PREMIUM_POSITIONING"""
        strategy = self.tracker.get_pricing_strategy(
            self.my_product.product_id,
            my_cost=30000,  # 원가 높음 (마진 방어선 > 최저가)
            target_margin=30.0
        )

        assert strategy is not None
        assert strategy.strategy_type == PricingStrategyType.PREMIUM_POSITIONING
        # 마진 방어선: 30000 / 0.7 = 42857 → 라운딩 42900
        assert strategy.recommended_price >= 42800
        assert "차별화" in strategy.recommendation or "경쟁 불가" in strategy.recommendation

    def test_strategy_has_exposure_tier(self):
        """전략에 노출 등급 포함"""
        strategy = self.tracker.get_pricing_strategy(
            self.my_product.product_id,
            my_cost=20000,
            target_margin=30.0
        )

        assert strategy is not None
        assert hasattr(strategy, "exposure_tier")
        assert strategy.exposure_tier in [
            ExposureTier.TIER1_EXPOSURE,
            ExposureTier.TIER2_DEFENSE,
            ExposureTier.TIER3_OUT
        ]


class TestGeminiEdgeCases:
    """Gemini CTO Q5: 추가 엣지케이스 테스트"""

    def setup_method(self):
        self.tracker = PriceTracker()

    def test_sold_out_product_handling(self):
        """품절 상품 처리 (가격 0원으로 들어온 경우)

        TODO: 실제 구현에서는 품절 상품을 평균 계산에서 제외해야 함
        현재는 0원으로 처리되는 케이스 테스트
        """
        self.tracker.add_product("정상", "https://a.com", 30000)
        self.tracker.add_product("품절", "https://b.com", 0)  # 품절 = 가격 0
        self.tracker.add_product("정상2", "https://c.com", 40000)

        analysis = self.tracker.get_competitive_analysis(35000)

        # 0원 상품도 포함되어 평균이 낮아짐 (개선 포인트)
        assert analysis["total_competitors"] == 3
        assert analysis["min_price"] == 0

    def test_price_change_from_to_zero(self):
        """가격 → 0원 변경 (품절 처리)"""
        product = self.tracker.add_product("품절 예정", "https://test.com", 30000)
        alert = self.tracker.update_price(product.product_id, 0)

        assert alert is not None
        assert alert.change_type == PriceChangeType.DECREASE
        assert alert.new_price == 0

    def test_very_high_price_change(self):
        """극단적 가격 변동 (999% 인상)"""
        product = self.tracker.add_product("테스트", "https://test.com", 1000)
        alert = self.tracker.update_price(product.product_id, 10990)  # +999%

        assert alert is not None
        assert alert.change_percent > 900
        assert alert.alert_level == AlertLevel.CRITICAL

    def test_min_competitor_price_zero(self):
        """최저가가 0원일 때 Tier 계산"""
        tier = self.tracker.get_exposure_tier(30000, 0)
        assert tier == ExposureTier.TIER3_OUT  # 0으로 나누기 방지


# pytest 실행용
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
