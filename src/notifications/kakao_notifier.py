"""
kakao_notifier.py - 카카오톡 알림 (v4.0)

카카오톡 '나에게 보내기' API 연동

사용법:
1. Kakao Developers에서 앱 생성
2. 카카오 로그인 동의항목에서 'talk_message' 권한 설정
3. REST API 키 발급
4. OAuth 토큰 발급 (refresh token 필요)

참고: https://developers.kakao.com/docs/latest/ko/message/rest-api
"""

import os
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import requests

from src.domain.crawler_models import CrawlStats


@dataclass
class KakaoNotifierConfig:
    """카카오 알림 설정"""
    access_token: str = ""
    refresh_token: str = ""
    client_id: str = ""                 # REST API 키
    use_mock: bool = False


class KakaoNotifier:
    """카카오톡 알림 전송"""

    SEND_ME_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    TOKEN_REFRESH_URL = "https://kauth.kakao.com/oauth/token"

    def __init__(self, config: KakaoNotifierConfig = None):
        self.config = config or KakaoNotifierConfig(
            access_token=os.getenv("KAKAO_ACCESS_TOKEN", ""),
            refresh_token=os.getenv("KAKAO_REFRESH_TOKEN", ""),
            client_id=os.getenv("KAKAO_CLIENT_ID", ""),
        )

        if not self.config.access_token:
            self.config.use_mock = True
            print("[KakaoNotifier] KAKAO_ACCESS_TOKEN 없음. Mock 모드 활성화")

    def send_crawl_complete(self, stats: CrawlStats) -> bool:
        """크롤링 완료 알림

        Args:
            stats: 크롤링 통계

        Returns:
            bool: 전송 성공 여부
        """
        template = self._build_crawl_complete_template(stats)
        return self._send_message(template)

    def send_morning_briefing(
        self,
        pending_count: int,
        avg_margin: float
    ) -> bool:
        """모닝 브리핑 알림

        Args:
            pending_count: 대기 중인 후보 수
            avg_margin: 평균 마진율

        Returns:
            bool: 전송 성공 여부
        """
        template = self._build_morning_briefing_template(pending_count, avg_margin)
        return self._send_message(template)

    def send_upload_complete(
        self,
        success_count: int,
        failed_count: int
    ) -> bool:
        """등록 완료 알림

        Args:
            success_count: 성공 수
            failed_count: 실패 수

        Returns:
            bool: 전송 성공 여부
        """
        template = self._build_upload_complete_template(success_count, failed_count)
        return self._send_message(template)

    def send_error(self, error_message: str) -> bool:
        """오류 알림

        Args:
            error_message: 오류 메시지

        Returns:
            bool: 전송 성공 여부
        """
        template = {
            "object_type": "text",
            "text": f"[Night Crawler 오류]\n\n{error_message}",
            "link": {
                "web_url": "http://localhost:8501",
                "mobile_web_url": "http://localhost:8501"
            }
        }
        return self._send_message(template)

    def _build_crawl_complete_template(self, stats: CrawlStats) -> Dict:
        """크롤링 완료 템플릿"""
        return {
            "object_type": "feed",
            "content": {
                "title": "Night Crawler 완료!",
                "description": f"밤새 {stats.saved_candidates}개의 상품을 찾았습니다.\n"
                              f"처리 키워드: {stats.crawled_keywords}/{stats.total_keywords}개\n"
                              f"소요 시간: {stats.duration_minutes:.0f}분",
                "image_url": "https://i.imgur.com/YQFcFi7.png",  # 크롤러 아이콘
                "link": {
                    "web_url": "http://localhost:8501",
                    "mobile_web_url": "http://localhost:8501"
                }
            },
            "buttons": [
                {
                    "title": "대시보드 열기",
                    "link": {
                        "web_url": "http://localhost:8501",
                        "mobile_web_url": "http://localhost:8501"
                    }
                }
            ]
        }

    def _build_morning_briefing_template(
        self,
        pending_count: int,
        avg_margin: float
    ) -> Dict:
        """모닝 브리핑 템플릿"""
        return {
            "object_type": "feed",
            "content": {
                "title": "Good Morning!",
                "description": f"검토 대기 중: {pending_count}개\n"
                              f"평균 마진율: {avg_margin:.1f}%\n\n"
                              f"대시보드에서 승인/반려를 결정해주세요.",
                "image_url": "https://i.imgur.com/SJeFkKA.png",  # 모닝 아이콘
                "link": {
                    "web_url": "http://localhost:8501",
                    "mobile_web_url": "http://localhost:8501"
                }
            },
            "buttons": [
                {
                    "title": "검토하러 가기",
                    "link": {
                        "web_url": "http://localhost:8501",
                        "mobile_web_url": "http://localhost:8501"
                    }
                }
            ]
        }

    def _build_upload_complete_template(
        self,
        success_count: int,
        failed_count: int
    ) -> Dict:
        """등록 완료 템플릿"""
        total = success_count + failed_count
        return {
            "object_type": "feed",
            "content": {
                "title": "상품 등록 완료!",
                "description": f"성공: {success_count}개\n"
                              f"실패: {failed_count}개\n\n"
                              f"스마트스토어에서 확인해보세요.",
                "image_url": "https://i.imgur.com/KL8nFcJ.png",  # 완료 아이콘
                "link": {
                    "web_url": "https://sell.smartstore.naver.com/",
                    "mobile_web_url": "https://sell.smartstore.naver.com/"
                }
            },
            "buttons": [
                {
                    "title": "스마트스토어 열기",
                    "link": {
                        "web_url": "https://sell.smartstore.naver.com/",
                        "mobile_web_url": "https://sell.smartstore.naver.com/"
                    }
                }
            ]
        }

    def _send_message(self, template: Dict) -> bool:
        """카카오톡 메시지 전송

        Args:
            template: 메시지 템플릿

        Returns:
            bool: 전송 성공 여부
        """
        if self.config.use_mock:
            print("[KakaoNotifier] Mock 모드 - 메시지 출력:")
            print(json.dumps(template, indent=2, ensure_ascii=False))
            return True

        try:
            headers = {
                "Authorization": f"Bearer {self.config.access_token}",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            data = {
                "template_object": json.dumps(template, ensure_ascii=False)
            }

            response = requests.post(
                self.SEND_ME_URL,
                headers=headers,
                data=data,
                timeout=10
            )

            if response.status_code == 200:
                print("[KakaoNotifier] 메시지 전송 성공")
                return True
            elif response.status_code == 401:
                # 토큰 만료 시 갱신 시도
                print("[KakaoNotifier] 토큰 만료. 갱신 시도...")
                if self._refresh_token():
                    # 재시도
                    return self._send_message(template)
                else:
                    print("[KakaoNotifier] 토큰 갱신 실패")
                    return False
            else:
                print(f"[KakaoNotifier] 전송 실패: {response.status_code}")
                print(response.text)
                return False

        except Exception as e:
            print(f"[KakaoNotifier] 오류: {e}")
            return False

    def _refresh_token(self) -> bool:
        """액세스 토큰 갱신

        Returns:
            bool: 갱신 성공 여부
        """
        if not self.config.refresh_token or not self.config.client_id:
            return False

        try:
            data = {
                "grant_type": "refresh_token",
                "client_id": self.config.client_id,
                "refresh_token": self.config.refresh_token
            }

            response = requests.post(
                self.TOKEN_REFRESH_URL,
                data=data,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                self.config.access_token = result.get("access_token", "")
                # refresh_token도 갱신될 수 있음
                if "refresh_token" in result:
                    self.config.refresh_token = result["refresh_token"]
                print("[KakaoNotifier] 토큰 갱신 성공")
                return True
            else:
                print(f"[KakaoNotifier] 토큰 갱신 실패: {response.status_code}")
                return False

        except Exception as e:
            print(f"[KakaoNotifier] 토큰 갱신 오류: {e}")
            return False


# CLI 테스트용
if __name__ == "__main__":
    notifier = KakaoNotifier()

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

    # 모닝 브리핑 테스트
    notifier.send_morning_briefing(42, 38.5)
