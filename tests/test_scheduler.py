"""
test_scheduler.py - 자동 모니터링 스케줄러 테스트 (Phase 9)

테스트 항목:
1. 스케줄러 시작/중지
2. 즉시 실행 (run_now)
3. 가격 체크 및 알림 생성
4. 콜백 동작
5. 상태 조회
6. 결과 기록
"""

import pytest
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

# 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.monitors.price_tracker import PriceTracker, AlertLevel
from src.monitors.scheduler import (
    PriceMonitorScheduler,
    SchedulerStatus,
    ScheduleJob,
    MonitoringResult,
    MockPriceFetcher,
    create_scheduler,
)


class TestSchedulerBasic:
    """스케줄러 기본 동작 테스트"""

    def setup_method(self):
        self.tracker = PriceTracker()
        # 테스트용 상품 추가
        self.tracker.add_product("상품A", "https://a.com", 30000)
        self.tracker.add_product("상품B", "https://b.com", 40000)
        self.scheduler = PriceMonitorScheduler(self.tracker)

    def teardown_method(self):
        # 테스트 후 스케줄러 정리
        if self.scheduler.status == SchedulerStatus.RUNNING:
            self.scheduler.stop()

    def test_initial_status(self):
        """초기 상태는 STOPPED"""
        assert self.scheduler.status == SchedulerStatus.STOPPED

    def test_start_scheduler(self):
        """스케줄러 시작"""
        result = self.scheduler.start(interval_hours=1, run_immediately=False)

        assert result is True
        assert self.scheduler.status == SchedulerStatus.RUNNING

    def test_start_already_running(self):
        """이미 실행 중인 스케줄러 재시작 시도"""
        self.scheduler.start(interval_hours=1, run_immediately=False)
        result = self.scheduler.start(interval_hours=1, run_immediately=False)

        assert result is False  # 이미 실행 중

    def test_stop_scheduler(self):
        """스케줄러 중지"""
        self.scheduler.start(interval_hours=1, run_immediately=False)
        result = self.scheduler.stop()

        assert result is True
        assert self.scheduler.status == SchedulerStatus.STOPPED

    def test_stop_not_running(self):
        """실행 중이 아닌 스케줄러 중지"""
        result = self.scheduler.stop()
        assert result is False

    def test_pause_resume(self):
        """일시정지 및 재개"""
        self.scheduler.start(interval_hours=1, run_immediately=False)

        self.scheduler.pause()
        assert self.scheduler.status == SchedulerStatus.PAUSED

        self.scheduler.resume()
        assert self.scheduler.status == SchedulerStatus.RUNNING


class TestSchedulerExecution:
    """스케줄러 실행 테스트"""

    def setup_method(self):
        self.tracker = PriceTracker()
        self.tracker.add_product("테스트", "https://test.com", 30000)
        self.scheduler = PriceMonitorScheduler(self.tracker)

    def teardown_method(self):
        if self.scheduler.status == SchedulerStatus.RUNNING:
            self.scheduler.stop()

    def test_run_now(self):
        """즉시 실행"""
        result = self.scheduler.run_now()

        assert isinstance(result, MonitoringResult)
        assert result.products_checked == 1
        assert result.timestamp != ""

    def test_run_now_with_alerts(self):
        """즉시 실행 - 알림 생성 (Mock으로 가격 변동 발생)"""
        # Mock fetcher로 가격 변동 강제
        def mock_fetcher(url):
            return 40000  # 30000 → 40000 (+33%)

        scheduler = PriceMonitorScheduler(self.tracker, mock_fetcher)
        result = scheduler.run_now()

        assert result.products_checked == 1
        # 33% 변동이므로 CRITICAL 알림 생성
        assert result.alerts_generated >= 1

    def test_start_with_immediate_run(self):
        """시작 시 즉시 실행"""
        result = self.scheduler.start(interval_hours=24, run_immediately=True)

        assert result is True
        # 약간의 대기 후 결과 확인
        time.sleep(0.2)

        results = self.scheduler.get_recent_results()
        assert len(results) >= 1


class TestSchedulerCallback:
    """콜백 테스트"""

    def setup_method(self):
        self.tracker = PriceTracker()
        self.tracker.add_product("콜백테스트", "https://callback.com", 10000)

        # 가격 변동을 강제하는 fetcher
        def force_change_fetcher(url):
            return 15000  # +50% 변동

        self.scheduler = PriceMonitorScheduler(self.tracker, force_change_fetcher)
        self.callback_called = False
        self.callback_alert = None

    def test_alert_callback(self):
        """알림 콜백 동작"""
        def my_callback(alert):
            self.callback_called = True
            self.callback_alert = alert

        self.scheduler.add_alert_callback(my_callback)
        self.scheduler.run_now()

        assert self.callback_called is True
        assert self.callback_alert is not None
        assert self.callback_alert.change_percent > 0

    def test_multiple_callbacks(self):
        """복수 콜백"""
        callback_count = [0]

        def callback1(alert):
            callback_count[0] += 1

        def callback2(alert):
            callback_count[0] += 1

        self.scheduler.add_alert_callback(callback1)
        self.scheduler.add_alert_callback(callback2)
        self.scheduler.run_now()

        assert callback_count[0] == 2  # 두 콜백 모두 호출


class TestSchedulerStatus:
    """상태 조회 테스트"""

    def setup_method(self):
        self.tracker = PriceTracker()
        self.tracker.add_product("상태테스트", "https://status.com", 25000)
        self.scheduler = PriceMonitorScheduler(self.tracker)

    def teardown_method(self):
        if self.scheduler.status == SchedulerStatus.RUNNING:
            self.scheduler.stop()

    def test_get_status_stopped(self):
        """중지 상태 조회"""
        status = self.scheduler.get_status()

        assert status["status"] == "stopped"
        assert status["products_count"] == 1

    def test_get_status_running(self):
        """실행 중 상태 조회"""
        self.scheduler.start(interval_hours=1, run_immediately=False)
        status = self.scheduler.get_status()

        assert status["status"] == "running"
        assert status["job"] is not None
        assert status["job"]["interval_seconds"] == 3600

    def test_get_summary_empty(self):
        """빈 요약"""
        summary = self.scheduler.get_summary()

        assert summary["total_runs"] == 0
        assert summary["total_alerts"] == 0

    def test_get_summary_after_runs(self):
        """실행 후 요약"""
        self.scheduler.run_now()
        self.scheduler.run_now()
        self.scheduler.run_now()

        summary = self.scheduler.get_summary()

        assert summary["total_runs"] == 3
        assert summary["avg_duration_ms"] >= 0


class TestSchedulerResults:
    """결과 기록 테스트"""

    def setup_method(self):
        self.tracker = PriceTracker()
        self.tracker.add_product("결과테스트", "https://result.com", 20000)
        self.scheduler = PriceMonitorScheduler(self.tracker)

    def test_results_recorded(self):
        """결과 기록 확인"""
        self.scheduler.run_now()
        results = self.scheduler.get_recent_results()

        assert len(results) == 1
        assert results[0].products_checked == 1

    def test_results_limit(self):
        """결과 제한 (limit 파라미터)"""
        for _ in range(5):
            self.scheduler.run_now()

        results = self.scheduler.get_recent_results(limit=3)
        assert len(results) == 3

    def test_results_max_storage(self):
        """최대 저장 개수 (100개)"""
        self.scheduler._max_results = 10  # 테스트용으로 줄임

        for _ in range(15):
            self.scheduler.run_now()

        results = self.scheduler.get_recent_results(limit=20)
        assert len(results) <= 10


class TestMockPriceFetcher:
    """Mock Fetcher 테스트"""

    def test_mock_fetcher_default(self):
        """기본 Mock Fetcher"""
        fetcher = MockPriceFetcher()
        price = fetcher("https://any.com")

        # 기본 30000 ±10%
        assert 27000 <= price <= 33000

    def test_mock_fetcher_custom_base(self):
        """커스텀 기본 가격"""
        fetcher = MockPriceFetcher({"https://custom.com": 50000})
        price = fetcher("https://custom.com")

        # 50000 ±10%
        assert 45000 <= price <= 55000

    def test_mock_fetcher_rounding(self):
        """100원 단위 라운딩"""
        fetcher = MockPriceFetcher()
        price = fetcher("https://any.com")

        assert price % 100 == 0


class TestCreateScheduler:
    """create_scheduler 편의 함수 테스트"""

    def test_create_with_mock(self):
        """Mock 모드로 생성"""
        tracker = PriceTracker()
        scheduler = create_scheduler(tracker, use_mock=True)

        assert isinstance(scheduler, PriceMonitorScheduler)

    def test_create_without_mock(self):
        """실제 모드로 생성"""
        tracker = PriceTracker()
        scheduler = create_scheduler(tracker, use_mock=False)

        assert isinstance(scheduler, PriceMonitorScheduler)


class TestSchedulerEdgeCases:
    """엣지 케이스 테스트"""

    def test_empty_tracker(self):
        """빈 트래커로 실행"""
        tracker = PriceTracker()  # 상품 없음
        scheduler = PriceMonitorScheduler(tracker)

        result = scheduler.run_now()

        assert result.products_checked == 0
        assert result.alerts_generated == 0

    def test_inactive_products(self):
        """비활성 상품 스킵"""
        tracker = PriceTracker()
        product = tracker.add_product("비활성", "https://inactive.com", 30000)
        product.is_active = False

        scheduler = PriceMonitorScheduler(tracker)
        result = scheduler.run_now()

        assert result.products_checked == 0

    def test_fetcher_error_handling(self):
        """Fetcher 에러 처리"""
        tracker = PriceTracker()
        tracker.add_product("에러테스트", "https://error.com", 30000)

        def error_fetcher(url):
            raise Exception("Network error")

        scheduler = PriceMonitorScheduler(tracker, error_fetcher)
        result = scheduler.run_now()

        assert len(result.errors) > 0
        assert "에러테스트" in result.errors[0]


# pytest 실행용
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
