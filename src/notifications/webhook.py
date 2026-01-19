"""
웹훅 알림 모듈

외부 서비스(Slack, Discord, 커스텀)로 알림 전송
"""

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum
import threading
import logging

from .events import Event, EventType, EventEmitter, get_event_emitter


class WebhookType(Enum):
    """웹훅 타입"""
    SLACK = "slack"
    DISCORD = "discord"
    GENERIC = "generic"


@dataclass
class WebhookConfig:
    """웹훅 설정"""
    name: str
    url: str
    webhook_type: WebhookType = WebhookType.GENERIC
    events: List[EventType] = field(default_factory=list)
    enabled: bool = True
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 10


class WebhookNotifier:
    """웹훅 알림 전송"""

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        self._configs: Dict[str, WebhookConfig] = {}
        self._emitter = get_event_emitter()

    def add_webhook(self, config: WebhookConfig):
        """웹훅 추가"""
        self._configs[config.name] = config

        # 이벤트 구독
        if config.events:
            for event_type in config.events:
                self._emitter.on(event_type, lambda e, cfg=config: self._handle_event(e, cfg))
        else:
            # 모든 이벤트 구독
            self._emitter.on_all(lambda e, cfg=config: self._handle_event(e, cfg))

    def remove_webhook(self, name: str):
        """웹훅 제거"""
        if name in self._configs:
            del self._configs[name]

    def _handle_event(self, event: Event, config: WebhookConfig):
        """이벤트 처리"""
        if not config.enabled:
            return

        # 비동기 전송
        thread = threading.Thread(
            target=self._send,
            args=(config, event)
        )
        thread.daemon = True
        thread.start()

    def _send(self, config: WebhookConfig, event: Event):
        """웹훅 전송"""
        try:
            payload = self._format_payload(config, event)
            headers = {"Content-Type": "application/json", **config.headers}

            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                config.url,
                data=data,
                headers=headers,
                method="POST"
            )

            with urllib.request.urlopen(request, timeout=config.timeout) as response:
                if response.status != 200:
                    self.logger.warning(
                        f"Webhook {config.name} returned status {response.status}"
                    )

        except urllib.error.URLError as e:
            self.logger.error(f"Webhook {config.name} failed: {e}")
        except Exception as e:
            self.logger.error(f"Webhook {config.name} error: {e}")

    def _format_payload(self, config: WebhookConfig, event: Event) -> Dict[str, Any]:
        """페이로드 포맷팅"""
        if config.webhook_type == WebhookType.SLACK:
            return self._format_slack(event)
        elif config.webhook_type == WebhookType.DISCORD:
            return self._format_discord(event)
        else:
            return self._format_generic(event)

    def _format_slack(self, event: Event) -> Dict[str, Any]:
        """Slack 포맷"""
        color = self._get_color(event.event_type)
        emoji = self._get_emoji(event.event_type)

        fields = []
        for key, value in event.data.items():
            fields.append({
                "title": key,
                "value": str(value)[:100],
                "short": len(str(value)) < 30
            })

        return {
            "attachments": [{
                "color": color,
                "title": f"{emoji} {event.event_type.value}",
                "text": event.data.get("message", ""),
                "fields": fields,
                "footer": f"Smart Store Agent • {event.source}",
                "ts": int(datetime.fromisoformat(event.timestamp).timestamp())
            }]
        }

    def _format_discord(self, event: Event) -> Dict[str, Any]:
        """Discord 포맷"""
        color = int(self._get_color(event.event_type).lstrip("#"), 16)
        emoji = self._get_emoji(event.event_type)

        fields = []
        for key, value in list(event.data.items())[:10]:
            fields.append({
                "name": key,
                "value": str(value)[:100],
                "inline": len(str(value)) < 30
            })

        return {
            "embeds": [{
                "title": f"{emoji} {event.event_type.value}",
                "description": event.data.get("message", ""),
                "color": color,
                "fields": fields,
                "footer": {"text": f"Smart Store Agent • {event.source}"},
                "timestamp": event.timestamp
            }]
        }

    def _format_generic(self, event: Event) -> Dict[str, Any]:
        """일반 포맷"""
        return event.to_dict()

    def _get_color(self, event_type: EventType) -> str:
        """이벤트 색상"""
        colors = {
            EventType.ANALYSIS_COMPLETED: "#22c55e",  # green
            EventType.ANALYSIS_FAILED: "#ef4444",     # red
            EventType.MARGIN_WARNING: "#eab308",      # yellow
            EventType.REPORT_GENERATED: "#3b82f6",    # blue
            EventType.ERROR_OCCURRED: "#ef4444",      # red
            EventType.HEALTH_CHECK_FAILED: "#f97316", # orange
        }
        return colors.get(event_type, "#6b7280")  # gray default

    def _get_emoji(self, event_type: EventType) -> str:
        """이벤트 이모지"""
        emojis = {
            EventType.ANALYSIS_STARTED: "🚀",
            EventType.ANALYSIS_COMPLETED: "✅",
            EventType.ANALYSIS_FAILED: "❌",
            EventType.MARGIN_CALCULATED: "💰",
            EventType.MARGIN_WARNING: "⚠️",
            EventType.REVIEWS_FILTERED: "📝",
            EventType.COMPLAINTS_DETECTED: "🔍",
            EventType.REPORT_GENERATED: "📊",
            EventType.REPORT_SAVED: "💾",
            EventType.ERROR_OCCURRED: "🚨",
            EventType.SYSTEM_STARTED: "🟢",
            EventType.SYSTEM_STOPPED: "🔴",
            EventType.HEALTH_CHECK_FAILED: "🏥",
        }
        return emojis.get(event_type, "📌")

    def send_direct(
        self,
        webhook_name: str,
        message: str,
        title: str = "",
        data: Dict[str, Any] = None
    ) -> bool:
        """직접 메시지 전송"""
        if webhook_name not in self._configs:
            self.logger.error(f"Webhook {webhook_name} not found")
            return False

        config = self._configs[webhook_name]
        event = Event(
            event_type=EventType.SYSTEM_STARTED,  # 임시
            data={"message": message, "title": title, **(data or {})}
        )

        try:
            self._send(config, event)
            return True
        except Exception as e:
            self.logger.error(f"Direct send failed: {e}")
            return False

    def test_webhook(self, webhook_name: str) -> bool:
        """웹훅 테스트"""
        return self.send_direct(
            webhook_name,
            "This is a test message from Smart Store Agent",
            title="🧪 Webhook Test"
        )


# 전역 웹훅 노티파이어
_global_notifier: Optional[WebhookNotifier] = None


def get_notifier() -> WebhookNotifier:
    """전역 노티파이어 반환"""
    global _global_notifier
    if _global_notifier is None:
        _global_notifier = WebhookNotifier()
    return _global_notifier


def setup_slack_webhook(url: str, name: str = "slack", events: List[EventType] = None):
    """Slack 웹훅 설정"""
    notifier = get_notifier()
    notifier.add_webhook(WebhookConfig(
        name=name,
        url=url,
        webhook_type=WebhookType.SLACK,
        events=events or []
    ))


def setup_discord_webhook(url: str, name: str = "discord", events: List[EventType] = None):
    """Discord 웹훅 설정"""
    notifier = get_notifier()
    notifier.add_webhook(WebhookConfig(
        name=name,
        url=url,
        webhook_type=WebhookType.DISCORD,
        events=events or []
    ))
