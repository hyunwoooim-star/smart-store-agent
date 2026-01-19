"""events.py 테스트"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from notifications.events import (
    EventType,
    Event,
    EventEmitter,
    get_event_emitter,
    emit_event,
    subscribe,
    emit_analysis_started,
    emit_analysis_completed,
    emit_margin_warning,
)


class TestEvent:
    """Event 테스트"""

    def test_event_creation(self):
        """이벤트 생성"""
        event = Event(
            event_type=EventType.ANALYSIS_COMPLETED,
            data={"product": "캠핑의자"}
        )

        assert event.event_type == EventType.ANALYSIS_COMPLETED
        assert event.data["product"] == "캠핑의자"
        assert event.timestamp is not None

    def test_event_to_dict(self):
        """딕셔너리 변환"""
        event = Event(
            event_type=EventType.ERROR_OCCURRED,
            data={"error": "테스트"},
            source="test"
        )

        d = event.to_dict()

        assert d["event_type"] == "error.occurred"
        assert d["data"]["error"] == "테스트"
        assert d["source"] == "test"


class TestEventEmitter:
    """EventEmitter 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.emitter = EventEmitter()
        self.received_events = []

    def test_subscribe_and_emit(self):
        """구독 및 발행"""
        def handler(event: Event):
            self.received_events.append(event)

        self.emitter.on(EventType.ANALYSIS_COMPLETED, handler)
        self.emitter.emit(EventType.ANALYSIS_COMPLETED, {"result": "success"})

        assert len(self.received_events) == 1
        assert self.received_events[0].data["result"] == "success"

    def test_multiple_handlers(self):
        """다중 핸들러"""
        count = {"value": 0}

        def handler1(event):
            count["value"] += 1

        def handler2(event):
            count["value"] += 10

        self.emitter.on(EventType.MARGIN_CALCULATED, handler1)
        self.emitter.on(EventType.MARGIN_CALCULATED, handler2)
        self.emitter.emit(EventType.MARGIN_CALCULATED)

        assert count["value"] == 11

    def test_global_handler(self):
        """전역 핸들러"""
        events = []

        def global_handler(event):
            events.append(event)

        self.emitter.on_all(global_handler)
        self.emitter.emit(EventType.ANALYSIS_STARTED)
        self.emitter.emit(EventType.ANALYSIS_COMPLETED)

        assert len(events) == 2

    def test_unsubscribe(self):
        """구독 해제"""
        def handler(event):
            self.received_events.append(event)

        self.emitter.on(EventType.ERROR_OCCURRED, handler)
        self.emitter.emit(EventType.ERROR_OCCURRED)

        self.emitter.off(EventType.ERROR_OCCURRED, handler)
        self.emitter.emit(EventType.ERROR_OCCURRED)

        assert len(self.received_events) == 1

    def test_emit_with_source(self):
        """소스 포함 발행"""
        received = []

        def handler(event):
            received.append(event)

        self.emitter.on(EventType.REPORT_GENERATED, handler)
        self.emitter.emit(
            EventType.REPORT_GENERATED,
            {"report_id": "R123"},
            source="reporter"
        )

        assert received[0].source == "reporter"

    def test_handler_error_isolation(self):
        """핸들러 에러 격리"""
        count = {"value": 0}

        def failing_handler(event):
            raise Exception("Test error")

        def working_handler(event):
            count["value"] += 1

        self.emitter.on(EventType.SYSTEM_STARTED, failing_handler)
        self.emitter.on(EventType.SYSTEM_STARTED, working_handler)
        self.emitter.emit(EventType.SYSTEM_STARTED)

        # 실패한 핸들러에도 불구하고 다른 핸들러는 실행됨
        assert count["value"] == 1


class TestEventTypes:
    """EventType 테스트"""

    def test_event_type_values(self):
        """이벤트 타입 값"""
        assert EventType.ANALYSIS_STARTED.value == "analysis.started"
        assert EventType.ANALYSIS_COMPLETED.value == "analysis.completed"
        assert EventType.MARGIN_WARNING.value == "margin.warning"
        assert EventType.ERROR_OCCURRED.value == "error.occurred"


class TestConvenienceFunctions:
    """편의 함수 테스트"""

    def test_emit_analysis_started(self):
        """분석 시작 이벤트"""
        emitter = get_event_emitter()
        events = []

        emitter.on(EventType.ANALYSIS_STARTED, lambda e: events.append(e))
        emit_analysis_started("테스트 상품", category="테스트")

        assert len(events) >= 1

    def test_emit_analysis_completed(self):
        """분석 완료 이벤트"""
        emitter = get_event_emitter()
        events = []

        emitter.on(EventType.ANALYSIS_COMPLETED, lambda e: events.append(e))
        emit_analysis_completed("테스트 상품", {"score": 75})

        assert len(events) >= 1

    def test_emit_margin_warning(self):
        """마진 경고 이벤트"""
        emitter = get_event_emitter()
        events = []

        emitter.on(EventType.MARGIN_WARNING, lambda e: events.append(e))
        emit_margin_warning("저마진 상품", 5.0)

        assert len(events) >= 1


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
