"""
이벤트 시스템

애플리케이션 이벤트 발행 및 구독 시스템
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional
from enum import Enum
import threading


class EventType(Enum):
    """이벤트 유형"""
    # 분석 관련
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_COMPLETED = "analysis.completed"
    ANALYSIS_FAILED = "analysis.failed"

    # 마진 계산
    MARGIN_CALCULATED = "margin.calculated"
    MARGIN_WARNING = "margin.warning"

    # 리뷰 분석
    REVIEWS_FILTERED = "reviews.filtered"
    COMPLAINTS_DETECTED = "complaints.detected"

    # 리포트
    REPORT_GENERATED = "report.generated"
    REPORT_SAVED = "report.saved"

    # 에러
    ERROR_OCCURRED = "error.occurred"
    ERROR_RECOVERED = "error.recovered"

    # 시스템
    SYSTEM_STARTED = "system.started"
    SYSTEM_STOPPED = "system.stopped"
    HEALTH_CHECK_FAILED = "health.check_failed"


@dataclass
class Event:
    """이벤트 데이터"""
    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = ""
    correlation_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
            "correlation_id": self.correlation_id,
        }


EventHandler = Callable[[Event], None]


class EventEmitter:
    """이벤트 발행/구독 시스템"""

    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._global_handlers: List[EventHandler] = []
        self._lock = threading.Lock()

    def on(self, event_type: EventType, handler: EventHandler):
        """특정 이벤트 구독"""
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def on_all(self, handler: EventHandler):
        """모든 이벤트 구독"""
        with self._lock:
            self._global_handlers.append(handler)

    def off(self, event_type: EventType, handler: EventHandler):
        """이벤트 구독 해제"""
        with self._lock:
            if event_type in self._handlers:
                try:
                    self._handlers[event_type].remove(handler)
                except ValueError:
                    pass

    def emit(
        self,
        event_type: EventType,
        data: Dict[str, Any] = None,
        source: str = "",
        correlation_id: str = ""
    ):
        """이벤트 발행"""
        event = Event(
            event_type=event_type,
            data=data or {},
            source=source,
            correlation_id=correlation_id
        )

        # 특정 이벤트 핸들러 호출
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # 핸들러 에러는 무시하고 계속
                pass

        # 전역 핸들러 호출
        for handler in self._global_handlers:
            try:
                handler(event)
            except Exception as e:
                pass

    def emit_async(
        self,
        event_type: EventType,
        data: Dict[str, Any] = None,
        source: str = "",
        correlation_id: str = ""
    ):
        """비동기 이벤트 발행"""
        thread = threading.Thread(
            target=self.emit,
            args=(event_type, data, source, correlation_id)
        )
        thread.daemon = True
        thread.start()


# 전역 이벤트 이미터
_global_emitter = EventEmitter()


def get_event_emitter() -> EventEmitter:
    """전역 이벤트 이미터 반환"""
    return _global_emitter


def emit_event(
    event_type: EventType,
    data: Dict[str, Any] = None,
    source: str = "",
    correlation_id: str = ""
):
    """전역 이벤트 발행"""
    _global_emitter.emit(event_type, data, source, correlation_id)


def subscribe(event_type: EventType, handler: EventHandler):
    """이벤트 구독"""
    _global_emitter.on(event_type, handler)


# 편의 함수들
def emit_analysis_started(product_name: str, **kwargs):
    """분석 시작 이벤트"""
    emit_event(
        EventType.ANALYSIS_STARTED,
        {"product_name": product_name, **kwargs},
        source="analyzer"
    )


def emit_analysis_completed(product_name: str, result: Dict[str, Any], **kwargs):
    """분석 완료 이벤트"""
    emit_event(
        EventType.ANALYSIS_COMPLETED,
        {"product_name": product_name, "result": result, **kwargs},
        source="analyzer"
    )


def emit_analysis_failed(product_name: str, error: str, **kwargs):
    """분석 실패 이벤트"""
    emit_event(
        EventType.ANALYSIS_FAILED,
        {"product_name": product_name, "error": error, **kwargs},
        source="analyzer"
    )


def emit_margin_warning(product_name: str, margin_percent: float, **kwargs):
    """마진 경고 이벤트"""
    emit_event(
        EventType.MARGIN_WARNING,
        {"product_name": product_name, "margin_percent": margin_percent, **kwargs},
        source="margin_calculator"
    )


def emit_report_generated(report_id: str, filepath: str, **kwargs):
    """리포트 생성 이벤트"""
    emit_event(
        EventType.REPORT_GENERATED,
        {"report_id": report_id, "filepath": filepath, **kwargs},
        source="reporter"
    )


def emit_error(error_code: str, message: str, **kwargs):
    """에러 이벤트"""
    emit_event(
        EventType.ERROR_OCCURRED,
        {"error_code": error_code, "message": message, **kwargs},
        source="error_handler"
    )
