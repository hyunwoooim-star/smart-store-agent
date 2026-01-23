"""
scheduler.py - 자동 가격 모니터링 스케줄러 (Phase 9)

기능:
1. 주기적 가격 체크 (매일 오전 9시 등)
2. 가격 변동 시 알림 생성
3. 스케줄 관리 (시작/중지/상태 확인)

사용법:
    scheduler = PriceMonitorScheduler(tracker)
    scheduler.start(interval_hours=24)  # 24시간마다 체크
    scheduler.stop()
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from enum import Enum
import threading
import time
import logging

from .price_tracker import PriceTracker, PriceAlert, AlertLevel


class SchedulerStatus(Enum):
    """스케줄러 상태"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


@dataclass
class ScheduleJob:
    """스케줄 작업"""
    job_id: str
    name: str
    interval_seconds: int
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0
    error_count: int = 0
    is_active: bool = True


@dataclass
class MonitoringResult:
    """모니터링 결과"""
    timestamp: str
    products_checked: int
    alerts_generated: int
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0


class PriceMonitorScheduler:
    """가격 모니터링 스케줄러

    간단한 스레드 기반 스케줄러. APScheduler 없이도 동작.
    """

    def __init__(
        self,
        tracker: PriceTracker,
        price_fetcher: Optional[Callable[[str], int]] = None
    ):
        """
        Args:
            tracker: PriceTracker 인스턴스
            price_fetcher: URL → 가격 반환 함수 (실제 스크래핑용)
                          None이면 Mock 데이터 사용
        """
        self.tracker = tracker
        self.price_fetcher = price_fetcher
        self.status = SchedulerStatus.STOPPED
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._job: Optional[ScheduleJob] = None
        self._results: List[MonitoringResult] = []
        self._max_results = 100  # 최근 100개 결과만 저장

        # 콜백
        self._on_alert_callbacks: List[Callable[[PriceAlert], None]] = []

        # 로깅
        self.logger = logging.getLogger(__name__)

    def add_alert_callback(self, callback: Callable[[PriceAlert], None]):
        """알림 발생 시 콜백 등록

        예: 슬랙/텔레그램 알림 연동
        """
        self._on_alert_callbacks.append(callback)

    def start(
        self,
        interval_hours: float = 24,
        run_immediately: bool = True
    ) -> bool:
        """스케줄러 시작

        Args:
            interval_hours: 체크 간격 (시간)
            run_immediately: 시작 직후 즉시 실행 여부

        Returns:
            성공 여부
        """
        if self.status == SchedulerStatus.RUNNING:
            self.logger.warning("Scheduler already running")
            return False

        interval_seconds = int(interval_hours * 3600)

        self._job = ScheduleJob(
            job_id="price_monitor_001",
            name="경쟁사 가격 모니터링",
            interval_seconds=interval_seconds,
        )

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(interval_seconds, run_immediately),
            daemon=True
        )
        self._thread.start()
        self.status = SchedulerStatus.RUNNING

        self.logger.info(f"Scheduler started: interval={interval_hours}h")
        return True

    def stop(self) -> bool:
        """스케줄러 중지"""
        if self.status == SchedulerStatus.STOPPED:
            return False

        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

        self.status = SchedulerStatus.STOPPED
        self.logger.info("Scheduler stopped")
        return True

    def pause(self):
        """스케줄러 일시정지"""
        if self.status == SchedulerStatus.RUNNING:
            self.status = SchedulerStatus.PAUSED
            self.logger.info("Scheduler paused")

    def resume(self):
        """스케줄러 재개"""
        if self.status == SchedulerStatus.PAUSED:
            self.status = SchedulerStatus.RUNNING
            self.logger.info("Scheduler resumed")

    def run_now(self) -> MonitoringResult:
        """즉시 실행 (수동 트리거)"""
        return self._check_prices()

    def _run_loop(self, interval_seconds: int, run_immediately: bool):
        """스케줄 루프"""
        if run_immediately:
            self._check_prices()

        while not self._stop_event.is_set():
            # 다음 실행 시간 계산
            if self._job:
                next_run = datetime.now() + timedelta(seconds=interval_seconds)
                self._job.next_run = next_run.isoformat()

            # 대기 (1초 단위로 체크하여 빠른 중지 가능)
            for _ in range(interval_seconds):
                if self._stop_event.is_set():
                    return
                if self.status == SchedulerStatus.PAUSED:
                    time.sleep(1)
                    continue
                time.sleep(1)

            # 실행
            if self.status == SchedulerStatus.RUNNING:
                self._check_prices()

    def _check_prices(self) -> MonitoringResult:
        """가격 체크 실행"""
        start_time = time.perf_counter()
        timestamp = datetime.now().isoformat()
        products_checked = 0
        alerts_generated = 0
        errors = []

        try:
            for product_id, product in self.tracker.products.items():
                if not product.is_active:
                    continue

                try:
                    # 새 가격 가져오기
                    if self.price_fetcher:
                        new_price = self.price_fetcher(product.url)
                    else:
                        # Mock: 현재 가격에서 ±5% 랜덤 변동
                        import random
                        change = random.uniform(-0.05, 0.05)
                        new_price = int(product.current_price * (1 + change))
                        # 100원 단위 라운딩
                        new_price = round(new_price, -2)

                    # 가격 업데이트
                    alert = self.tracker.update_price(
                        product_id,
                        new_price,
                        source="scheduler"
                    )

                    products_checked += 1

                    if alert:
                        alerts_generated += 1
                        # 콜백 실행
                        for callback in self._on_alert_callbacks:
                            try:
                                callback(alert)
                            except Exception as e:
                                self.logger.error(f"Callback error: {e}")

                except Exception as e:
                    errors.append(f"{product.name}: {str(e)}")
                    self.logger.error(f"Error checking {product.name}: {e}")

        except Exception as e:
            errors.append(f"General error: {str(e)}")
            self.logger.error(f"Scheduler error: {e}")

        # 결과 기록
        duration_ms = (time.perf_counter() - start_time) * 1000

        result = MonitoringResult(
            timestamp=timestamp,
            products_checked=products_checked,
            alerts_generated=alerts_generated,
            errors=errors,
            duration_ms=duration_ms
        )

        self._results.append(result)
        if len(self._results) > self._max_results:
            self._results = self._results[-self._max_results:]

        # Job 상태 업데이트
        if self._job:
            self._job.last_run = timestamp
            self._job.run_count += 1
            if errors:
                self._job.error_count += len(errors)

        self.logger.info(
            f"Price check completed: {products_checked} products, "
            f"{alerts_generated} alerts, {duration_ms:.1f}ms"
        )

        return result

    def get_status(self) -> Dict:
        """스케줄러 상태 조회"""
        return {
            "status": self.status.value,
            "job": {
                "id": self._job.job_id if self._job else None,
                "name": self._job.name if self._job else None,
                "interval_seconds": self._job.interval_seconds if self._job else None,
                "last_run": self._job.last_run if self._job else None,
                "next_run": self._job.next_run if self._job else None,
                "run_count": self._job.run_count if self._job else 0,
                "error_count": self._job.error_count if self._job else 0,
            } if self._job else None,
            "products_count": len(self.tracker.products),
            "active_products": sum(1 for p in self.tracker.products.values() if p.is_active),
        }

    def get_recent_results(self, limit: int = 10) -> List[MonitoringResult]:
        """최근 실행 결과 조회"""
        return self._results[-limit:]

    def get_summary(self) -> Dict:
        """요약 통계"""
        if not self._results:
            return {
                "total_runs": 0,
                "total_alerts": 0,
                "avg_duration_ms": 0,
                "error_rate": 0,
            }

        total_runs = len(self._results)
        total_alerts = sum(r.alerts_generated for r in self._results)
        avg_duration = sum(r.duration_ms for r in self._results) / total_runs
        runs_with_errors = sum(1 for r in self._results if r.errors)

        return {
            "total_runs": total_runs,
            "total_alerts": total_alerts,
            "avg_duration_ms": round(avg_duration, 2),
            "error_rate": round(runs_with_errors / total_runs * 100, 1),
        }


class MockPriceFetcher:
    """테스트용 Mock 가격 Fetcher"""

    def __init__(self, base_prices: Optional[Dict[str, int]] = None):
        """
        Args:
            base_prices: URL → 기본 가격 매핑
        """
        self.base_prices = base_prices or {}
        self._call_count = 0

    def __call__(self, url: str) -> int:
        """URL에서 가격 반환 (Mock)"""
        import random

        self._call_count += 1
        base = self.base_prices.get(url, 30000)

        # ±10% 랜덤 변동
        change = random.uniform(-0.10, 0.10)
        new_price = int(base * (1 + change))

        # 100원 단위 라운딩
        return round(new_price, -2)


# 편의 함수
def create_scheduler(
    tracker: PriceTracker,
    use_mock: bool = True
) -> PriceMonitorScheduler:
    """스케줄러 생성

    Args:
        tracker: PriceTracker 인스턴스
        use_mock: Mock 가격 fetcher 사용 여부
    """
    fetcher = None if use_mock else None  # 실제 fetcher는 추후 구현
    return PriceMonitorScheduler(tracker, fetcher)
