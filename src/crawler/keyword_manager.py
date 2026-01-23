"""
keyword_manager.py - 키워드 관리자 (v4.0)

소싱 키워드 관리 및 크롤링 스케줄링
"""

from typing import List, Optional
from datetime import datetime, timedelta

from src.domain.crawler_models import SourcingKeyword
from src.crawler.repository import CandidateRepository


class KeywordManager:
    """키워드 관리자"""

    def __init__(self, repository: CandidateRepository = None):
        self.repository = repository or CandidateRepository()

    def get_active_keywords(self) -> List[SourcingKeyword]:
        """활성 키워드 목록 (우선순위 순)"""
        return self.repository.get_keywords(active_only=True)

    def get_keywords_to_crawl(self, max_keywords: int = 5) -> List[SourcingKeyword]:
        """크롤링 대상 키워드 선택

        선택 기준:
        1. 활성 상태
        2. 우선순위 높은 순
        3. 마지막 크롤링이 24시간 이상 지난 것 우선
        """
        keywords = self.get_active_keywords()

        # 크롤링이 필요한 키워드 필터링
        now = datetime.now()
        threshold = now - timedelta(hours=24)

        # 24시간 내 크롤링 안 된 것 우선
        needs_crawl = []
        recent_crawl = []

        for kw in keywords:
            if kw.last_crawled_at is None or kw.last_crawled_at < threshold:
                needs_crawl.append(kw)
            else:
                recent_crawl.append(kw)

        # 우선순위 정렬
        needs_crawl.sort(key=lambda k: k.priority)
        recent_crawl.sort(key=lambda k: k.priority)

        # 합쳐서 반환
        result = needs_crawl + recent_crawl
        return result[:max_keywords]

    def add_keyword(self, keyword: str, category: str = "", priority: int = 5) -> SourcingKeyword:
        """키워드 추가"""
        kw = SourcingKeyword(
            keyword=keyword,
            category=category,
            priority=priority
        )
        return self.repository.add_keyword(kw)

    def update_keyword_priority(self, keyword_id: str, priority: int) -> Optional[SourcingKeyword]:
        """키워드 우선순위 변경"""
        kw = self.repository.get_keyword_by_id(keyword_id)
        if kw:
            kw.priority = priority
            return self.repository.update_keyword(kw)
        return None

    def deactivate_keyword(self, keyword_id: str) -> Optional[SourcingKeyword]:
        """키워드 비활성화"""
        kw = self.repository.get_keyword_by_id(keyword_id)
        if kw:
            kw.is_active = False
            return self.repository.update_keyword(kw)
        return None

    def activate_keyword(self, keyword_id: str) -> Optional[SourcingKeyword]:
        """키워드 활성화"""
        kw = self.repository.get_keyword_by_id(keyword_id)
        if kw:
            kw.is_active = True
            return self.repository.update_keyword(kw)
        return None

    def mark_crawled(self, keyword_id: str) -> Optional[SourcingKeyword]:
        """크롤링 완료 표시"""
        kw = self.repository.get_keyword_by_id(keyword_id)
        if kw:
            kw.last_crawled_at = datetime.now()
            return self.repository.update_keyword(kw)
        return None

    def get_keyword_stats(self) -> dict:
        """키워드 통계"""
        all_keywords = self.repository.get_keywords(active_only=False)
        active = [k for k in all_keywords if k.is_active]

        now = datetime.now()
        threshold = now - timedelta(hours=24)
        recent = [k for k in active if k.last_crawled_at and k.last_crawled_at >= threshold]

        return {
            "total": len(all_keywords),
            "active": len(active),
            "inactive": len(all_keywords) - len(active),
            "crawled_today": len(recent),
            "pending_crawl": len(active) - len(recent)
        }

    def bulk_add_keywords(self, keywords: List[dict]) -> List[SourcingKeyword]:
        """키워드 일괄 추가

        Args:
            keywords: [{"keyword": "...", "category": "...", "priority": 5}, ...]
        """
        result = []
        for kw_data in keywords:
            kw = self.add_keyword(
                keyword=kw_data.get("keyword", ""),
                category=kw_data.get("category", ""),
                priority=kw_data.get("priority", 5)
            )
            result.append(kw)
        return result

    def seed_default_keywords(self) -> List[SourcingKeyword]:
        """기본 키워드 시드 (홈인테리어/수납 카테고리 - Gemini CTO 추천)"""
        default_keywords = [
            {"keyword": "데스크 정리함", "category": "홈인테리어", "priority": 1},
            {"keyword": "모니터 받침대 서랍", "category": "사무용품", "priority": 2},
            {"keyword": "틈새 수납장", "category": "홈인테리어", "priority": 2},
            {"keyword": "케이블 정리함", "category": "사무용품", "priority": 3},
            {"keyword": "화장품 정리함", "category": "홈인테리어", "priority": 3},
            {"keyword": "신발 정리대", "category": "홈인테리어", "priority": 4},
            {"keyword": "옷장 정리함", "category": "홈인테리어", "priority": 4},
            {"keyword": "주방 수납장", "category": "홈인테리어", "priority": 5},
        ]
        return self.bulk_add_keywords(default_keywords)
