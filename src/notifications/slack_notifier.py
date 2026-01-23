"""
slack_notifier.py - 슬랙 알림 (v4.0)

Night Crawler 결과 알림 전송

사용법:
1. 슬랙 워크스페이스에서 앱 생성
2. Incoming Webhook URL 발급
3. SLACK_WEBHOOK_URL 환경변수 설정
"""

import os
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import requests

from src.domain.crawler_models import CrawlStats


@dataclass
class SlackNotifierConfig:
    """슬랙 알림 설정"""
    webhook_url: str = ""
    channel: str = "#smart-store"       # 기본 채널
    username: str = "Night Crawler Bot"
    icon_emoji: str = ":spider:"
    use_mock: bool = False


class SlackNotifier:
    """슬랙 알림 전송"""

    def __init__(self, config: SlackNotifierConfig = None):
        self.config = config or SlackNotifierConfig(
            webhook_url=os.getenv("SLACK_WEBHOOK_URL", "")
        )

        if not self.config.webhook_url:
            self.config.use_mock = True
            print("[SlackNotifier] SLACK_WEBHOOK_URL 없음. Mock 모드 활성화")

    def send_crawl_complete(self, stats: CrawlStats) -> bool:
        """크롤링 완료 알림

        Args:
            stats: 크롤링 통계

        Returns:
            bool: 전송 성공 여부
        """
        blocks = self._build_crawl_complete_blocks(stats)
        return self._send_message(blocks)

    def send_morning_briefing(
        self,
        pending_count: int,
        top_candidates: List[Dict[str, Any]]
    ) -> bool:
        """모닝 브리핑 알림

        Args:
            pending_count: 대기 중인 후보 수
            top_candidates: 상위 후보 목록 (마진율 기준)

        Returns:
            bool: 전송 성공 여부
        """
        blocks = self._build_morning_briefing_blocks(pending_count, top_candidates)
        return self._send_message(blocks)

    def send_upload_complete(
        self,
        success_count: int,
        failed_count: int,
        product_urls: List[str]
    ) -> bool:
        """등록 완료 알림

        Args:
            success_count: 성공 수
            failed_count: 실패 수
            product_urls: 등록된 상품 URL 목록

        Returns:
            bool: 전송 성공 여부
        """
        blocks = self._build_upload_complete_blocks(success_count, failed_count, product_urls)
        return self._send_message(blocks)

    def send_error(self, error_message: str, context: str = "") -> bool:
        """오류 알림

        Args:
            error_message: 오류 메시지
            context: 오류 컨텍스트

        Returns:
            bool: 전송 성공 여부
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Night Crawler 오류 발생",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*오류 내용:*\n```{error_message}```"
                }
            },
        ]

        if context:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"컨텍스트: {context}"
                    }
                ]
            })

        return self._send_message(blocks)

    def _build_crawl_complete_blocks(self, stats: CrawlStats) -> List[Dict]:
        """크롤링 완료 메시지 블록 생성"""
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Night Crawler 크롤링 완료!",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*처리 키워드:*\n{stats.crawled_keywords}/{stats.total_keywords}개"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*발견 상품:*\n{stats.total_products_found}개"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*저장된 후보:*\n{stats.saved_candidates}개"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*소요 시간:*\n{stats.duration_minutes:.1f}분"
                    }
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"주인님, 밤새 *{stats.saved_candidates}개*의 꿀템을 찾아뒀습니다!\n대시보드에서 확인해주세요."
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "대시보드 열기",
                        "emoji": True
                    },
                    "url": "http://localhost:8501",
                    "action_id": "button-action"
                }
            }
        ]

    def _build_morning_briefing_blocks(
        self,
        pending_count: int,
        top_candidates: List[Dict[str, Any]]
    ) -> List[Dict]:
        """모닝 브리핑 메시지 블록 생성"""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Good Morning! 모닝 브리핑",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"검토 대기 중인 상품이 *{pending_count}개* 있습니다."
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*오늘의 추천 상품 (마진율 기준):*"
                }
            }
        ]

        # 상위 후보 추가 (최대 5개)
        for i, c in enumerate(top_candidates[:5], 1):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{i}. *{c.get('title', '상품명')}*\n"
                            f"   마진: {c.get('margin', 0):.0%} | "
                            f"추천가: {c.get('price', 0):,}원"
                }
            })

        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "대시보드에서 검토하기",
                        "emoji": True
                    },
                    "style": "primary",
                    "url": "http://localhost:8501"
                }
            ]
        })

        return blocks

    def _build_upload_complete_blocks(
        self,
        success_count: int,
        failed_count: int,
        product_urls: List[str]
    ) -> List[Dict]:
        """등록 완료 메시지 블록 생성"""
        total = success_count + failed_count
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "상품 등록 완료!",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*성공:*\n{success_count}개"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*실패:*\n{failed_count}개"
                    }
                ]
            }
        ]

        # 등록된 상품 링크 추가 (최대 5개)
        if product_urls:
            links_text = "\n".join([f"<{url}|상품 보기>" for url in product_urls[:5]])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*등록된 상품:*\n{links_text}"
                }
            })

        return blocks

    def _send_message(self, blocks: List[Dict]) -> bool:
        """슬랙 메시지 전송

        Args:
            blocks: 메시지 블록 리스트

        Returns:
            bool: 전송 성공 여부
        """
        if self.config.use_mock:
            print("[SlackNotifier] Mock 모드 - 메시지 출력:")
            print(json.dumps(blocks, indent=2, ensure_ascii=False))
            return True

        try:
            payload = {
                "channel": self.config.channel,
                "username": self.config.username,
                "icon_emoji": self.config.icon_emoji,
                "blocks": blocks
            }

            response = requests.post(
                self.config.webhook_url,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                print("[SlackNotifier] 메시지 전송 성공")
                return True
            else:
                print(f"[SlackNotifier] 전송 실패: {response.status_code}")
                return False

        except Exception as e:
            print(f"[SlackNotifier] 오류: {e}")
            return False


# CLI 테스트용
if __name__ == "__main__":
    notifier = SlackNotifier()

    # 크롤링 완료 테스트
    stats = CrawlStats(
        total_keywords=5,
        crawled_keywords=5,
        total_products_found=120,
        saved_candidates=42,
        start_time=datetime(2026, 1, 25, 1, 0),
        end_time=datetime(2026, 1, 25, 7, 30)
    )
    notifier.send_crawl_complete(stats)
