"""
메트릭 수집 모듈

시스템 성능 및 사용량 메트릭 수집 및 관리
"""

import time
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum
from collections import deque
import threading


class MetricType(Enum):
    """메트릭 타입"""
    COUNTER = "counter"      # 증가만 하는 카운터
    GAUGE = "gauge"          # 현재값 게이지
    HISTOGRAM = "histogram"  # 분포 히스토그램
    TIMER = "timer"          # 실행 시간


@dataclass
class Metric:
    """메트릭 데이터"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class MetricSummary:
    """메트릭 요약 통계"""
    name: str
    count: int
    total: float
    min_value: float
    max_value: float
    avg_value: float
    last_value: float
    p50: float  # 중앙값
    p95: float  # 95 퍼센타일
    p99: float  # 99 퍼센타일


class MetricsCollector:
    """메트릭 수집기"""

    def __init__(self, max_history: int = 1000):
        """
        Args:
            max_history: 유지할 최대 메트릭 히스토리 수
        """
        self.max_history = max_history
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, deque] = {}
        self._timers: Dict[str, deque] = {}
        self._lock = threading.Lock()

    def increment(
        self,
        name: str,
        value: float = 1,
        labels: Dict[str, str] = None
    ):
        """카운터 증가"""
        with self._lock:
            key = self._make_key(name, labels)
            self._counters[key] = self._counters.get(key, 0) + value

    def gauge(
        self,
        name: str,
        value: float,
        labels: Dict[str, str] = None
    ):
        """게이지 설정"""
        with self._lock:
            key = self._make_key(name, labels)
            self._gauges[key] = value

    def histogram(
        self,
        name: str,
        value: float,
        labels: Dict[str, str] = None
    ):
        """히스토그램에 값 추가"""
        with self._lock:
            key = self._make_key(name, labels)
            if key not in self._histograms:
                self._histograms[key] = deque(maxlen=self.max_history)
            self._histograms[key].append(value)

    def timer_start(self, name: str) -> float:
        """타이머 시작"""
        return time.perf_counter()

    def timer_stop(
        self,
        name: str,
        start_time: float,
        labels: Dict[str, str] = None
    ):
        """타이머 종료 및 기록"""
        elapsed = time.perf_counter() - start_time
        with self._lock:
            key = self._make_key(name, labels)
            if key not in self._timers:
                self._timers[key] = deque(maxlen=self.max_history)
            self._timers[key].append(elapsed * 1000)  # milliseconds

    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """메트릭 키 생성"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_counter(self, name: str, labels: Dict[str, str] = None) -> float:
        """카운터 값 조회"""
        key = self._make_key(name, labels)
        return self._counters.get(key, 0)

    def get_gauge(self, name: str, labels: Dict[str, str] = None) -> float:
        """게이지 값 조회"""
        key = self._make_key(name, labels)
        return self._gauges.get(key, 0)

    def get_histogram_summary(
        self,
        name: str,
        labels: Dict[str, str] = None
    ) -> Optional[MetricSummary]:
        """히스토그램 요약 조회"""
        key = self._make_key(name, labels)
        values = self._histograms.get(key)
        if not values:
            return None

        sorted_values = sorted(values)
        count = len(sorted_values)

        return MetricSummary(
            name=name,
            count=count,
            total=sum(sorted_values),
            min_value=min(sorted_values),
            max_value=max(sorted_values),
            avg_value=statistics.mean(sorted_values),
            last_value=sorted_values[-1],
            p50=self._percentile(sorted_values, 50),
            p95=self._percentile(sorted_values, 95),
            p99=self._percentile(sorted_values, 99),
        )

    def get_timer_summary(
        self,
        name: str,
        labels: Dict[str, str] = None
    ) -> Optional[MetricSummary]:
        """타이머 요약 조회"""
        key = self._make_key(name, labels)
        values = self._timers.get(key)
        if not values:
            return None

        sorted_values = sorted(values)
        count = len(sorted_values)

        return MetricSummary(
            name=name,
            count=count,
            total=sum(sorted_values),
            min_value=min(sorted_values),
            max_value=max(sorted_values),
            avg_value=statistics.mean(sorted_values),
            last_value=sorted_values[-1],
            p50=self._percentile(sorted_values, 50),
            p95=self._percentile(sorted_values, 95),
            p99=self._percentile(sorted_values, 99),
        )

    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """퍼센타일 계산"""
        if not sorted_values:
            return 0
        k = (len(sorted_values) - 1) * percentile / 100
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_values) else f
        return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])

    def get_all_metrics(self) -> Dict[str, Any]:
        """모든 메트릭 조회"""
        result = {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {},
            "timers": {},
        }

        for key in self._histograms:
            summary = self.get_histogram_summary(key)
            if summary:
                result["histograms"][key] = {
                    "count": summary.count,
                    "avg": summary.avg_value,
                    "p95": summary.p95,
                }

        for key in self._timers:
            summary = self.get_timer_summary(key)
            if summary:
                result["timers"][key] = {
                    "count": summary.count,
                    "avg_ms": round(summary.avg_value, 2),
                    "p95_ms": round(summary.p95, 2),
                }

        return result

    def reset(self):
        """모든 메트릭 초기화"""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._timers.clear()


# 전역 메트릭 수집기
_global_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """전역 메트릭 수집기 반환"""
    return _global_metrics


class MetricsContext:
    """메트릭 컨텍스트 매니저 (타이머용)"""

    def __init__(
        self,
        name: str,
        collector: MetricsCollector = None,
        labels: Dict[str, str] = None
    ):
        self.name = name
        self.collector = collector or _global_metrics
        self.labels = labels
        self.start_time = None

    def __enter__(self):
        self.start_time = self.collector.timer_start(self.name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.collector.timer_stop(self.name, self.start_time, self.labels)
        return False


def timed(name: str = None, labels: Dict[str, str] = None):
    """실행 시간 측정 데코레이터"""
    def decorator(func):
        metric_name = name or f"{func.__module__}.{func.__name__}"

        def wrapper(*args, **kwargs):
            with MetricsContext(metric_name, labels=labels):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# 프리셋 메트릭 이름
class MetricNames:
    """메트릭 이름 상수"""
    # API 호출
    API_CALLS = "api_calls_total"
    API_ERRORS = "api_errors_total"
    API_LATENCY = "api_latency_ms"

    # 분석
    ANALYSES_TOTAL = "analyses_total"
    ANALYSIS_DURATION = "analysis_duration_ms"

    # 마진 계산
    MARGIN_CALCULATIONS = "margin_calculations_total"
    MARGIN_CALC_DURATION = "margin_calc_duration_ms"

    # 리뷰 필터링
    REVIEWS_PROCESSED = "reviews_processed_total"
    COMPLAINTS_DETECTED = "complaints_detected_total"

    # 리포트
    REPORTS_GENERATED = "reports_generated_total"
    REPORT_GEN_DURATION = "report_gen_duration_ms"

    # 에러
    ERRORS_TOTAL = "errors_total"

    # 시스템
    ACTIVE_SESSIONS = "active_sessions"
    MEMORY_USAGE = "memory_usage_bytes"
