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
    """Supabase 클라이언트"""

    # 테이블명
    TABLE_KEYWORDS = "keywords"
    TABLE_ANALYSES = "analyses"
    TABLE_REPORTS = "reports"

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
