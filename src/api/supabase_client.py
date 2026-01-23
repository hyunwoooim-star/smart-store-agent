"""
supabase_client.py - Supabase 데이터베이스 연동 (v3.1)

기능:
1. 분석 결과 저장
2. 키워드 데이터 저장/조회
3. 리포트 히스토리 관리
"""

import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

# Supabase 클라이언트 (설치 필요: pip install supabase)
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None


@dataclass
class KeywordRecord:
    """키워드 레코드"""
    keyword: str
    monthly_search_volume: int
    total_products: int
    competition_rate: float
    opportunity_score: float
    category: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class AnalysisRecord:
    """분석 결과 레코드"""
    report_id: str
    product_name: str
    category: str
    margin_percent: float
    total_score: float
    is_viable: bool
    recommendation: str
    created_at: Optional[str] = None
    raw_data: Optional[Dict] = None


class SupabaseClient:
    """Supabase 클라이언트 (v3.5.2 - 캐싱 레이어 추가)"""

    # 테이블명
    TABLE_KEYWORDS = "keywords"
    TABLE_ANALYSES = "analyses"
    TABLE_REPORTS = "reports"
    TABLE_SCRAPE_CACHE = "scrape_cache"  # Phase 5.2 캐싱 테이블

    # 캐시 유효 기간 (일)
    CACHE_TTL_DAYS_1688 = 3     # 1688 상품 정보: 3일
    CACHE_TTL_DAYS_REVIEW = 7   # 리뷰 분석: 7일

    def __init__(self, url: str = None, key: str = None):
        """
        Args:
            url: Supabase URL (환경변수 SUPABASE_URL)
            key: Supabase API Key (환경변수 SUPABASE_KEY)
        """
        self.url = url or os.getenv("SUPABASE_URL", "")
        self.key = key or os.getenv("SUPABASE_KEY", "")
        self.client: Optional[Client] = None
        self._initialized = False

    def initialize(self) -> bool:
        """클라이언트 초기화"""
        if not SUPABASE_AVAILABLE:
            print("⚠️ supabase 패키지가 설치되지 않았습니다. pip install supabase")
            return False

        if not self.url or not self.key:
            print("⚠️ SUPABASE_URL 또는 SUPABASE_KEY가 설정되지 않았습니다.")
            return False

        try:
            self.client = create_client(self.url, self.key)
            self._initialized = True
            return True
        except Exception as e:
            print(f"⚠️ Supabase 연결 실패: {e}")
            return False

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._initialized and self.client is not None

    # --- 키워드 관련 ---

    def save_keywords(self, keywords: List[KeywordRecord]) -> bool:
        """키워드 저장"""
        if not self.is_connected():
            return False

        try:
            data = []
            for kw in keywords:
                record = asdict(kw)
                record["created_at"] = datetime.now().isoformat()
                data.append(record)

            self.client.table(self.TABLE_KEYWORDS).insert(data).execute()
            return True
        except Exception as e:
            print(f"키워드 저장 실패: {e}")
            return False

    def get_keywords(self, category: str = None, limit: int = 100) -> List[Dict]:
        """키워드 조회"""
        if not self.is_connected():
            return []

        try:
            query = self.client.table(self.TABLE_KEYWORDS).select("*")

            if category:
                query = query.eq("category", category)

            query = query.order("opportunity_score", desc=True).limit(limit)
            result = query.execute()

            return result.data if result.data else []
        except Exception as e:
            print(f"키워드 조회 실패: {e}")
            return []

    def search_keywords(self, search_term: str, limit: int = 20) -> List[Dict]:
        """키워드 검색"""
        if not self.is_connected():
            return []

        try:
            result = (
                self.client.table(self.TABLE_KEYWORDS)
                .select("*")
                .ilike("keyword", f"%{search_term}%")
                .order("opportunity_score", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data if result.data else []
        except Exception as e:
            print(f"키워드 검색 실패: {e}")
            return []

    # --- 분석 결과 관련 ---

    def save_analysis(self, analysis: AnalysisRecord) -> bool:
        """분석 결과 저장"""
        if not self.is_connected():
            return False

        try:
            record = asdict(analysis)
            record["created_at"] = datetime.now().isoformat()

            self.client.table(self.TABLE_ANALYSES).insert(record).execute()
            return True
        except Exception as e:
            print(f"분석 결과 저장 실패: {e}")
            return False

    def get_analyses(self, product_name: str = None, limit: int = 50) -> List[Dict]:
        """분석 결과 조회"""
        if not self.is_connected():
            return []

        try:
            query = self.client.table(self.TABLE_ANALYSES).select("*")

            if product_name:
                query = query.ilike("product_name", f"%{product_name}%")

            query = query.order("created_at", desc=True).limit(limit)
            result = query.execute()

            return result.data if result.data else []
        except Exception as e:
            print(f"분석 결과 조회 실패: {e}")
            return []

    def get_analysis_by_id(self, report_id: str) -> Optional[Dict]:
        """ID로 분석 결과 조회"""
        if not self.is_connected():
            return None

        try:
            result = (
                self.client.table(self.TABLE_ANALYSES)
                .select("*")
                .eq("report_id", report_id)
                .single()
                .execute()
            )
            return result.data
        except Exception as e:
            print(f"분석 결과 조회 실패: {e}")
            return None

    # --- 리포트 관련 ---

    def save_report(self, report_id: str, content: str, format: str = "markdown") -> bool:
        """리포트 저장"""
        if not self.is_connected():
            return False

        try:
            record = {
                "report_id": report_id,
                "content": content,
                "format": format,
                "created_at": datetime.now().isoformat()
            }

            self.client.table(self.TABLE_REPORTS).insert(record).execute()
            return True
        except Exception as e:
            print(f"리포트 저장 실패: {e}")
            return False

    def get_report(self, report_id: str) -> Optional[str]:
        """리포트 조회"""
        if not self.is_connected():
            return None

        try:
            result = (
                self.client.table(self.TABLE_REPORTS)
                .select("content")
                .eq("report_id", report_id)
                .single()
                .execute()
            )
            return result.data.get("content") if result.data else None
        except Exception as e:
            print(f"리포트 조회 실패: {e}")
            return None

    # --- 캐싱 레이어 (Phase 5.2 - Gemini CTO 조언) ---

    def get_cached_scrape(self, url: str) -> Optional[Dict]:
        """캐시된 스크래핑 결과 조회

        Args:
            url: 1688 상품 URL

        Returns:
            캐시된 데이터 (있고 유효하면) / None (없거나 만료)
        """
        if not self.is_connected():
            return None

        try:
            from datetime import datetime, timedelta

            # URL 정규화 (쿼리 파라미터 제거)
            normalized_url = self._normalize_url(url)

            result = (
                self.client.table(self.TABLE_SCRAPE_CACHE)
                .select("*")
                .eq("url", normalized_url)
                .single()
                .execute()
            )

            if not result.data:
                return None

            # TTL 체크
            created_at = datetime.fromisoformat(result.data["created_at"].replace("Z", "+00:00"))
            ttl_days = self.CACHE_TTL_DAYS_1688
            if datetime.now(created_at.tzinfo) - created_at > timedelta(days=ttl_days):
                # 캐시 만료 - 삭제
                self.client.table(self.TABLE_SCRAPE_CACHE).delete().eq("url", normalized_url).execute()
                return None

            print(f"✅ [Cache Hit] {normalized_url[:50]}...")
            return result.data.get("data")

        except Exception as e:
            # 캐시 미스는 정상 동작
            return None

    def save_scrape_cache(self, url: str, data: Dict) -> bool:
        """스크래핑 결과 캐시 저장

        Args:
            url: 1688 상품 URL
            data: 스크래핑 결과 데이터

        Returns:
            성공 여부
        """
        if not self.is_connected():
            return False

        try:
            normalized_url = self._normalize_url(url)

            record = {
                "url": normalized_url,
                "data": data,
                "created_at": datetime.now().isoformat()
            }

            # Upsert (있으면 업데이트, 없으면 삽입)
            self.client.table(self.TABLE_SCRAPE_CACHE).upsert(
                record, on_conflict="url"
            ).execute()

            print(f"💾 [Cache Save] {normalized_url[:50]}...")
            return True

        except Exception as e:
            print(f"캐시 저장 실패: {e}")
            return False

    def get_cached_review(self, product_name: str, category: str) -> Optional[Dict]:
        """캐시된 리뷰 분석 결과 조회"""
        if not self.is_connected():
            return None

        try:
            from datetime import datetime, timedelta

            # 캐시 키 생성
            cache_key = f"review:{category}:{product_name[:50]}"

            result = (
                self.client.table(self.TABLE_SCRAPE_CACHE)
                .select("*")
                .eq("url", cache_key)
                .single()
                .execute()
            )

            if not result.data:
                return None

            # TTL 체크 (리뷰는 7일)
            created_at = datetime.fromisoformat(result.data["created_at"].replace("Z", "+00:00"))
            if datetime.now(created_at.tzinfo) - created_at > timedelta(days=self.CACHE_TTL_DAYS_REVIEW):
                self.client.table(self.TABLE_SCRAPE_CACHE).delete().eq("url", cache_key).execute()
                return None

            print(f"✅ [Review Cache Hit] {cache_key[:30]}...")
            return result.data.get("data")

        except Exception:
            return None

    def save_review_cache(self, product_name: str, category: str, data: Dict) -> bool:
        """리뷰 분석 결과 캐시 저장"""
        if not self.is_connected():
            return False

        try:
            cache_key = f"review:{category}:{product_name[:50]}"

            record = {
                "url": cache_key,
                "data": data,
                "created_at": datetime.now().isoformat()
            }

            self.client.table(self.TABLE_SCRAPE_CACHE).upsert(
                record, on_conflict="url"
            ).execute()

            print(f"💾 [Review Cache Save] {cache_key[:30]}...")
            return True

        except Exception as e:
            print(f"리뷰 캐시 저장 실패: {e}")
            return False

    def _normalize_url(self, url: str) -> str:
        """URL 정규화 (쿼리 파라미터 제거)"""
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(url)
        # 쿼리 파라미터 제거
        normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
        return normalized

    def clear_expired_cache(self) -> int:
        """만료된 캐시 정리 (배치 작업용)"""
        if not self.is_connected():
            return 0

        try:
            from datetime import datetime, timedelta

            # 가장 오래된 TTL 기준으로 삭제 (7일)
            cutoff = (datetime.now() - timedelta(days=self.CACHE_TTL_DAYS_REVIEW)).isoformat()

            result = (
                self.client.table(self.TABLE_SCRAPE_CACHE)
                .delete()
                .lt("created_at", cutoff)
                .execute()
            )

            count = len(result.data) if result.data else 0
            print(f"🗑️ [Cache Cleanup] {count}개 삭제")
            return count

        except Exception as e:
            print(f"캐시 정리 실패: {e}")
            return 0

    # --- 통계 ---

    def get_stats(self) -> Dict[str, int]:
        """통계 조회"""
        if not self.is_connected():
            return {}

        try:
            keywords_count = len(self.client.table(self.TABLE_KEYWORDS).select("id", count="exact").execute().data or [])
            analyses_count = len(self.client.table(self.TABLE_ANALYSES).select("id", count="exact").execute().data or [])
            reports_count = len(self.client.table(self.TABLE_REPORTS).select("id", count="exact").execute().data or [])

            return {
                "keywords": keywords_count,
                "analyses": analyses_count,
                "reports": reports_count
            }
        except Exception:
            return {}


# --- Mock 클라이언트 (테스트용) ---
class MockSupabaseClient(SupabaseClient):
    """테스트용 Mock 클라이언트"""

    def __init__(self):
        super().__init__()
        self._initialized = True
        self._keywords: List[Dict] = []
        self._analyses: List[Dict] = []
        self._reports: List[Dict] = []

    def initialize(self) -> bool:
        return True

    def is_connected(self) -> bool:
        return True

    def save_keywords(self, keywords: List[KeywordRecord]) -> bool:
        for kw in keywords:
            record = asdict(kw)
            record["created_at"] = datetime.now().isoformat()
            self._keywords.append(record)
        return True

    def get_keywords(self, category: str = None, limit: int = 100) -> List[Dict]:
        data = self._keywords
        if category:
            data = [d for d in data if d.get("category") == category]
        return sorted(data, key=lambda x: x.get("opportunity_score", 0), reverse=True)[:limit]

    def save_analysis(self, analysis: AnalysisRecord) -> bool:
        record = asdict(analysis)
        record["created_at"] = datetime.now().isoformat()
        self._analyses.append(record)
        return True

    def get_analyses(self, product_name: str = None, limit: int = 50) -> List[Dict]:
        data = self._analyses
        if product_name:
            data = [d for d in data if product_name.lower() in d.get("product_name", "").lower()]
        return data[:limit]


# --- 팩토리 ---
def get_supabase_client(use_mock: bool = False) -> SupabaseClient:
    """Supabase 클라이언트 반환"""
    if use_mock:
        return MockSupabaseClient()

    client = SupabaseClient()
    client.initialize()
    return client


# --- 테스트 ---
if __name__ == "__main__":
    print("="*50)
    print("🗄️ Supabase 클라이언트 테스트")
    print("="*50)

    # Mock 클라이언트로 테스트
    client = get_supabase_client(use_mock=True)

    print(f"\n연결 상태: {'✅ 연결됨' if client.is_connected() else '❌ 미연결'}")

    # 키워드 저장 테스트
    test_keywords = [
        KeywordRecord(
            keyword="캠핑의자",
            monthly_search_volume=45000,
            total_products=25000,
            competition_rate=0.56,
            opportunity_score=8.0,
            category="캠핑/레저"
        ),
        KeywordRecord(
            keyword="초경량 캠핑의자",
            monthly_search_volume=8500,
            total_products=3200,
            competition_rate=0.38,
            opportunity_score=17.7,
            category="캠핑/레저"
        ),
    ]

    print("\n[키워드 저장]")
    if client.save_keywords(test_keywords):
        print("  ✅ 저장 성공")
    else:
        print("  ❌ 저장 실패")

    print("\n[키워드 조회]")
    keywords = client.get_keywords(category="캠핑/레저")
    for kw in keywords:
        print(f"  - {kw['keyword']}: 검색량 {kw['monthly_search_volume']:,}")

    # 분석 결과 저장 테스트
    test_analysis = AnalysisRecord(
        report_id="test_001",
        product_name="초경량 캠핑 의자",
        category="캠핑/레저",
        margin_percent=-28.0,
        total_score=35.5,
        is_viable=False,
        recommendation="❌ 수익성 부족"
    )

    print("\n[분석 결과 저장]")
    if client.save_analysis(test_analysis):
        print("  ✅ 저장 성공")

    print("\n" + "="*50)
    print("✅ Supabase 클라이언트 모듈 준비 완료")
    print("   실제 사용 시 SUPABASE_URL, SUPABASE_KEY 환경변수 설정 필요")
    print("="*50)
