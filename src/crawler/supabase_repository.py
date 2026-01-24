"""
supabase_repository.py - Supabase 기반 저장소 (v4.0)

Gemini CTO 권장: "로컬 JSON → Supabase PostgreSQL 마이그레이션"

장점:
- 멀티 디바이스 동기화
- 데이터 백업 자동화
- 실시간 대시보드 연동 가능
- SQL 쿼리로 고급 분석

사용법:
    # 환경변수 설정 필요
    # SUPABASE_URL=https://xxx.supabase.co
    # SUPABASE_KEY=eyJxxx...

    repo = SupabaseRepository()
    keywords = repo.get_keywords()
"""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from supabase import create_client, Client

from src.domain.crawler_models import (
    SourcingKeyword,
    SourcingCandidate,
    UploadHistory,
    CandidateStatus,
    CrawlRiskLevel
)


class SupabaseRepository:
    """Supabase 기반 소싱 저장소 (v4.0)

    CandidateRepository와 동일한 인터페이스 제공
    환경변수 SUPABASE_URL, SUPABASE_KEY 필요
    """

    def __init__(self, url: str = None, key: str = None):
        """
        Args:
            url: Supabase 프로젝트 URL
            key: Supabase anon/service key
        """
        self.url = url or os.getenv("SUPABASE_URL")
        self.key = key or os.getenv("SUPABASE_KEY")

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL과 SUPABASE_KEY 환경변수가 필요합니다.")

        self.client: Client = create_client(self.url, self.key)

    # ========== 키워드 관리 ==========

    def get_keywords(self, active_only: bool = True) -> List[SourcingKeyword]:
        """키워드 목록 조회"""
        query = self.client.table("sourcing_keywords").select("*")

        if active_only:
            query = query.eq("is_active", True)

        response = query.order("priority").execute()

        return [self._row_to_keyword(row) for row in response.data]

    def add_keyword(self, keyword: SourcingKeyword) -> SourcingKeyword:
        """키워드 추가"""
        data = {
            "id": keyword.id,
            "keyword": keyword.keyword,
            "category": keyword.category,
            "is_active": keyword.is_active,
            "priority": keyword.priority,
            "last_crawled_at": keyword.last_crawled_at.isoformat() if keyword.last_crawled_at else None,
            "created_at": keyword.created_at.isoformat()
        }

        response = self.client.table("sourcing_keywords").insert(data).execute()
        return self._row_to_keyword(response.data[0]) if response.data else keyword

    def update_keyword(self, keyword: SourcingKeyword) -> SourcingKeyword:
        """키워드 업데이트"""
        data = {
            "keyword": keyword.keyword,
            "category": keyword.category,
            "is_active": keyword.is_active,
            "priority": keyword.priority,
            "last_crawled_at": keyword.last_crawled_at.isoformat() if keyword.last_crawled_at else None
        }

        response = self.client.table("sourcing_keywords").update(data).eq("id", keyword.id).execute()
        return self._row_to_keyword(response.data[0]) if response.data else keyword

    def delete_keyword(self, keyword_id: str) -> bool:
        """키워드 삭제"""
        response = self.client.table("sourcing_keywords").delete().eq("id", keyword_id).execute()
        return len(response.data) > 0

    def get_keyword_by_id(self, keyword_id: str) -> Optional[SourcingKeyword]:
        """ID로 키워드 조회"""
        response = self.client.table("sourcing_keywords").select("*").eq("id", keyword_id).execute()
        return self._row_to_keyword(response.data[0]) if response.data else None

    # ========== 후보 상품 관리 ==========

    def get_candidates(
        self,
        status: Optional[CandidateStatus] = None,
        keyword_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[SourcingCandidate]:
        """후보 상품 목록 조회"""
        query = self.client.table("sourcing_candidates").select("*")

        if status:
            query = query.eq("status", status.value)
        if keyword_id:
            query = query.eq("keyword_id", keyword_id)

        response = query.order("estimated_margin_rate", desc=True).range(offset, offset + limit - 1).execute()

        return [self._row_to_candidate(row) for row in response.data]

    def get_pending_candidates(self) -> List[SourcingCandidate]:
        """대기 중인 후보 목록"""
        return self.get_candidates(status=CandidateStatus.PENDING)

    def get_approved_candidates(self) -> List[SourcingCandidate]:
        """승인된 후보 목록"""
        return self.get_candidates(status=CandidateStatus.APPROVED)

    def get_candidates_by_status(self, status: CandidateStatus) -> List[SourcingCandidate]:
        """상태별 후보 목록"""
        return self.get_candidates(status=status)

    def add_candidate(self, candidate: SourcingCandidate) -> SourcingCandidate:
        """후보 추가"""
        data = self._candidate_to_row(candidate)
        response = self.client.table("sourcing_candidates").insert(data).execute()
        return self._row_to_candidate(response.data[0]) if response.data else candidate

    def update_candidate(self, candidate: SourcingCandidate) -> SourcingCandidate:
        """후보 업데이트"""
        data = self._candidate_to_row(candidate)
        # id는 업데이트에서 제외
        del data["id"]

        response = self.client.table("sourcing_candidates").update(data).eq("id", candidate.id).execute()
        return self._row_to_candidate(response.data[0]) if response.data else candidate

    def get_candidate_by_id(self, candidate_id: str) -> Optional[SourcingCandidate]:
        """ID로 후보 조회"""
        response = self.client.table("sourcing_candidates").select("*").eq("id", candidate_id).execute()
        return self._row_to_candidate(response.data[0]) if response.data else None

    def approve_candidate(self, candidate_id: str) -> Optional[SourcingCandidate]:
        """후보 승인"""
        data = {
            "status": CandidateStatus.APPROVED.value,
            "approved_at": datetime.now().isoformat()
        }
        response = self.client.table("sourcing_candidates").update(data).eq("id", candidate_id).execute()
        return self._row_to_candidate(response.data[0]) if response.data else None

    def reject_candidate(self, candidate_id: str, reason: str = "") -> Optional[SourcingCandidate]:
        """후보 반려"""
        data = {
            "status": CandidateStatus.REJECTED.value,
            "rejected_reason": reason
        }
        response = self.client.table("sourcing_candidates").update(data).eq("id", candidate_id).execute()
        return self._row_to_candidate(response.data[0]) if response.data else None

    def mark_uploaded(
        self,
        candidate_id: str,
        product_id: str,
        product_url: str
    ) -> Optional[SourcingCandidate]:
        """등록 완료 처리"""
        data = {
            "status": CandidateStatus.UPLOADED.value,
            "naver_product_id": product_id,
            "naver_product_url": product_url,
            "uploaded_at": datetime.now().isoformat()
        }
        response = self.client.table("sourcing_candidates").update(data).eq("id", candidate_id).execute()
        return self._row_to_candidate(response.data[0]) if response.data else None

    def mark_failed(self, candidate_id: str, error: str) -> Optional[SourcingCandidate]:
        """등록 실패 처리"""
        data = {
            "status": CandidateStatus.FAILED.value,
            "rejected_reason": error
        }
        response = self.client.table("sourcing_candidates").update(data).eq("id", candidate_id).execute()
        return self._row_to_candidate(response.data[0]) if response.data else None

    def check_duplicate(self, source_url: str) -> bool:
        """중복 URL 체크"""
        response = self.client.table("sourcing_candidates").select("id").eq("source_url", source_url).execute()
        return len(response.data) > 0

    # ========== 통계 ==========

    def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        # 전체 카운트
        all_response = self.client.table("sourcing_candidates").select("id, status, estimated_margin_rate").execute()
        candidates = all_response.data

        pending = [c for c in candidates if c["status"] == "pending"]
        approved = [c for c in candidates if c["status"] == "approved"]
        uploaded = [c for c in candidates if c["status"] == "uploaded"]
        rejected = [c for c in candidates if c["status"] == "rejected"]

        avg_margin = 0.0
        if pending:
            avg_margin = sum(float(c["estimated_margin_rate"] or 0) for c in pending) / len(pending)

        keywords_response = self.client.table("sourcing_keywords").select("id").eq("is_active", True).execute()

        return {
            "total": len(candidates),
            "pending": len(pending),
            "approved": len(approved),
            "uploaded": len(uploaded),
            "rejected": len(rejected),
            "avg_margin": avg_margin * 100,
            "keywords": len(keywords_response.data)
        }

    # ========== 업로드 히스토리 ==========

    def add_history(self, history: UploadHistory) -> UploadHistory:
        """히스토리 추가"""
        data = {
            "id": history.id,
            "candidate_id": history.candidate_id,
            "platform": history.platform,
            "status": history.status,
            "response_data": history.response_data,
            "error_message": history.error_message,
            "created_at": history.created_at.isoformat()
        }

        response = self.client.table("upload_history").insert(data).execute()
        return self._row_to_history(response.data[0]) if response.data else history

    def get_history(self, candidate_id: Optional[str] = None) -> List[UploadHistory]:
        """히스토리 조회"""
        query = self.client.table("upload_history").select("*")

        if candidate_id:
            query = query.eq("candidate_id", candidate_id)

        response = query.order("created_at", desc=True).execute()

        return [self._row_to_history(row) for row in response.data]

    # ========== 설정 관리 ==========

    def get_setting(self, key: str) -> Optional[Dict[str, Any]]:
        """설정 조회"""
        response = self.client.table("app_settings").select("value").eq("key", key).execute()
        return response.data[0]["value"] if response.data else None

    def set_setting(self, key: str, value: Dict[str, Any], description: str = "") -> bool:
        """설정 저장"""
        data = {
            "key": key,
            "value": value,
            "description": description
        }
        response = self.client.table("app_settings").upsert(data).execute()
        return len(response.data) > 0

    def get_all_settings(self) -> Dict[str, Any]:
        """모든 설정 조회"""
        response = self.client.table("app_settings").select("key, value").execute()
        return {row["key"]: row["value"] for row in response.data}

    # ========== 데이터 초기화 ==========

    def clear_all(self):
        """모든 데이터 삭제 (주의: 테스트용)"""
        self.client.table("upload_history").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        self.client.table("sourcing_candidates").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        self.client.table("sourcing_keywords").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    def seed_sample_keywords(self) -> List[SourcingKeyword]:
        """샘플 키워드 추가 (테스트용)"""
        sample_keywords = [
            SourcingKeyword(keyword="데스크 정리함", category="홈인테리어", priority=1),
            SourcingKeyword(keyword="모니터 받침대", category="사무용품", priority=2),
            SourcingKeyword(keyword="틈새 수납장", category="홈인테리어", priority=3),
            SourcingKeyword(keyword="케이블 정리함", category="사무용품", priority=4),
            SourcingKeyword(keyword="미니 가습기", category="생활용품", priority=5),
        ]

        for kw in sample_keywords:
            try:
                self.add_keyword(kw)
            except Exception:
                pass  # 중복 무시

        return sample_keywords

    # ========== Private: 변환 헬퍼 ==========

    def _row_to_keyword(self, row: Dict) -> SourcingKeyword:
        """DB row → SourcingKeyword"""
        return SourcingKeyword(
            id=row.get("id", ""),
            keyword=row.get("keyword", ""),
            category=row.get("category", ""),
            is_active=row.get("is_active", True),
            priority=row.get("priority", 5),
            last_crawled_at=datetime.fromisoformat(row["last_crawled_at"]) if row.get("last_crawled_at") else None,
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now()
        )

    def _row_to_candidate(self, row: Dict) -> SourcingCandidate:
        """DB row → SourcingCandidate"""
        return SourcingCandidate(
            id=row.get("id", ""),
            source_url=row.get("source_url", ""),
            source_title=row.get("source_title", ""),
            source_price_cny=float(row.get("source_price_cny", 0)),
            source_images=row.get("source_images", []),
            source_shop_name=row.get("source_shop_name", ""),
            source_shop_rating=float(row.get("source_shop_rating", 0)),
            source_sales_count=row.get("source_sales_count", 0),
            title_kr=row.get("title_kr", ""),
            estimated_cost_krw=row.get("estimated_cost_krw", 0),
            estimated_margin_rate=float(row.get("estimated_margin_rate", 0)),
            recommended_price=row.get("recommended_price", 0),
            breakeven_price=row.get("breakeven_price", 0),
            risk_level=CrawlRiskLevel(row.get("risk_level", "safe")),
            risk_reasons=row.get("risk_reasons", []),
            naver_min_price=row.get("naver_min_price", 0),
            naver_avg_price=row.get("naver_avg_price", 0),
            naver_max_price=row.get("naver_max_price", 0),
            competitor_count=row.get("competitor_count", 0),
            status=CandidateStatus(row.get("status", "pending")),
            approved_at=datetime.fromisoformat(row["approved_at"]) if row.get("approved_at") else None,
            rejected_reason=row.get("rejected_reason", ""),
            naver_product_id=row.get("naver_product_id", ""),
            naver_product_url=row.get("naver_product_url", ""),
            uploaded_at=datetime.fromisoformat(row["uploaded_at"]) if row.get("uploaded_at") else None,
            keyword_id=row.get("keyword_id", ""),
            keyword=row.get("keyword", ""),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else datetime.now()
        )

    def _candidate_to_row(self, c: SourcingCandidate) -> Dict:
        """SourcingCandidate → DB row"""
        return {
            "id": c.id,
            "source_url": c.source_url,
            "source_title": c.source_title,
            "source_price_cny": c.source_price_cny,
            "source_images": c.source_images,
            "source_shop_name": c.source_shop_name,
            "source_shop_rating": c.source_shop_rating,
            "source_sales_count": c.source_sales_count,
            "title_kr": c.title_kr,
            "estimated_cost_krw": c.estimated_cost_krw,
            "estimated_margin_rate": c.estimated_margin_rate,
            "recommended_price": c.recommended_price,
            "breakeven_price": c.breakeven_price,
            "risk_level": c.risk_level.value,
            "risk_reasons": c.risk_reasons,
            "naver_min_price": c.naver_min_price,
            "naver_avg_price": c.naver_avg_price,
            "naver_max_price": c.naver_max_price,
            "competitor_count": c.competitor_count,
            "status": c.status.value,
            "approved_at": c.approved_at.isoformat() if c.approved_at else None,
            "rejected_reason": c.rejected_reason,
            "naver_product_id": c.naver_product_id,
            "naver_product_url": c.naver_product_url,
            "uploaded_at": c.uploaded_at.isoformat() if c.uploaded_at else None,
            "keyword_id": c.keyword_id,
            "keyword": c.keyword,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat()
        }

    def _row_to_history(self, row: Dict) -> UploadHistory:
        """DB row → UploadHistory"""
        return UploadHistory(
            id=row.get("id", ""),
            candidate_id=row.get("candidate_id", ""),
            platform=row.get("platform", "naver"),
            status=row.get("status", "pending"),
            response_data=row.get("response_data", {}),
            error_message=row.get("error_message", ""),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now()
        )


# ============================================================
# 팩토리 함수: 환경에 따라 저장소 자동 선택
# ============================================================
def get_repository():
    """환경변수에 따라 적절한 Repository 반환

    SUPABASE_URL과 SUPABASE_KEY가 있으면 SupabaseRepository,
    없으면 CandidateRepository (로컬 JSON) 사용
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if supabase_url and supabase_key:
        print("[Repository] Supabase 모드 활성화")
        return SupabaseRepository()
    else:
        print("[Repository] 로컬 JSON 모드 (SUPABASE_URL/KEY 미설정)")
        from src.crawler.repository import CandidateRepository
        return CandidateRepository()
