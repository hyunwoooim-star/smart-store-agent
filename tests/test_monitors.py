"""monitors 모듈 테스트"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from monitors.metrics import (
    MetricsCollector,
    Metric,
    MetricType,
    MetricsContext,
    get_metrics,
    timed,
)
from monitors.health import (
    HealthChecker,
    HealthStatus,
    ComponentHealth,
    check_disk_space,
    check_api_key,
    create_file_check,
)


class TestMetricsCollector:
    """MetricsCollector 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.collector = MetricsCollector()

    def test_counter_increment(self):
        """카운터 증가"""
        self.collector.increment("test_counter")
        self.collector.increment("test_counter")
        self.collector.increment("test_counter", 5)

        assert self.collector.get_counter("test_counter") == 7

    def test_counter_with_labels(self):
        """라벨 포함 카운터"""
        self.collector.increment("api_calls", labels={"endpoint": "/analyze"})
        self.collector.increment("api_calls", labels={"endpoint": "/analyze"})
        self.collector.increment("api_calls", labels={"endpoint": "/report"})

        assert self.collector.get_counter("api_calls", {"endpoint": "/analyze"}) == 2
        assert self.collector.get_counter("api_calls", {"endpoint": "/report"}) == 1

    def test_gauge(self):
        """게이지 설정"""
        self.collector.gauge("memory_usage", 75.5)
        self.collector.gauge("memory_usage", 80.0)

        assert self.collector.get_gauge("memory_usage") == 80.0

    def test_histogram(self):
        """히스토그램"""
        for i in range(10):
            self.collector.histogram("request_size", i * 100)

        summary = self.collector.get_histogram_summary("request_size")

        assert summary is not None
        assert summary.count == 10
        assert summary.min_value == 0
        assert summary.max_value == 900
        assert summary.avg_value == 450

    def test_timer(self):
        """타이머"""
        start = self.collector.timer_start("operation")
        time.sleep(0.01)  # 10ms
        self.collector.timer_stop("operation", start)

        summary = self.collector.get_timer_summary("operation")

        assert summary is not None
        assert summary.count == 1
        assert summary.avg_value >= 10  # 최소 10ms

    def test_get_all_metrics(self):
        """모든 메트릭 조회"""
        self.collector.increment("counter1")
        self.collector.gauge("gauge1", 50)
        self.collector.histogram("hist1", 100)

        all_metrics = self.collector.get_all_metrics()

        assert "counters" in all_metrics
        assert "gauges" in all_metrics
        assert "histograms" in all_metrics
        assert "timers" in all_metrics

    def test_reset(self):
        """초기화"""
        self.collector.increment("counter")
        self.collector.gauge("gauge", 50)

        self.collector.reset()

        assert self.collector.get_counter("counter") == 0
        assert self.collector.get_gauge("gauge") == 0


class TestMetricsContext:
    """MetricsContext 테스트"""

    def test_context_manager(self):
        """컨텍스트 매니저"""
        collector = MetricsCollector()

        with MetricsContext("test_operation", collector):
            time.sleep(0.01)

        summary = collector.get_timer_summary("test_operation")
        assert summary is not None
        assert summary.count == 1


class TestTimedDecorator:
    """timed 데코레이터 테스트"""

    def test_timed_decorator(self):
        """데코레이터 테스트"""
        collector = get_metrics()
        collector.reset()

        @timed("decorated_function")
        def sample_function():
            time.sleep(0.01)
            return "done"

        result = sample_function()

        assert result == "done"


class TestHealthChecker:
    """HealthChecker 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.checker = HealthChecker()

    def test_register_check(self):
        """헬스 체크 등록"""
        def dummy_check():
            return ComponentHealth(
                name="dummy",
                status=HealthStatus.HEALTHY,
                message="OK"
            )

        self.checker.register("dummy", dummy_check)
        result = self.checker.check_component("dummy")

        assert result.status == HealthStatus.HEALTHY
        assert result.message == "OK"

    def test_unknown_component(self):
        """등록 안된 컴포넌트"""
        result = self.checker.check_component("unknown")

        assert result.status == HealthStatus.UNKNOWN
        assert "등록되지 않은" in result.message

    def test_check_all(self):
        """전체 체크"""
        def healthy_check():
            return ComponentHealth("healthy", HealthStatus.HEALTHY, "OK")

        def unhealthy_check():
            return ComponentHealth("unhealthy", HealthStatus.UNHEALTHY, "Error")

        self.checker.register("healthy", healthy_check)
        self.checker.register("unhealthy", unhealthy_check)

        system = self.checker.check_all()

        assert system.status == HealthStatus.UNHEALTHY
        assert "healthy" in system.components
        assert "unhealthy" in system.components

    def test_uptime(self):
        """업타임"""
        uptime = self.checker.get_uptime()
        assert uptime >= 0


class TestDiskCheck:
    """디스크 체크 테스트"""

    def test_disk_space_check(self):
        """디스크 공간 체크"""
        result = check_disk_space(".")

        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
        assert "total_gb" in result.details


class TestApiKeyCheck:
    """API 키 체크 테스트"""

    def test_api_key_not_set(self):
        """API 키 미설정"""
        result = check_api_key("TEST_KEY", "NONEXISTENT_KEY")

        assert result.status == HealthStatus.UNHEALTHY


class TestFileCheck:
    """파일 체크 테스트"""

    def test_existing_file(self):
        """존재하는 파일"""
        check = create_file_check(__file__)
        result = check()

        assert result.status == HealthStatus.HEALTHY
        assert "size_bytes" in result.details

    def test_nonexistent_file(self):
        """존재하지 않는 파일"""
        check = create_file_check("/nonexistent/file.txt")
        result = check()

        assert result.status == HealthStatus.UNHEALTHY


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
