"""
supabase_client.py - Supabase 연동용 싱글톤 클라이언트 (v3.1)

Gemini Step 3 지침에 따라 구현:
- 분석 결과 DB 저장
- 관계형 데이터 (RDB) + JSONB 구조
"""

import os
from typing import Optional, Dict, Any, List
from dataclasses import asdict

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class SupabaseManager:
    """Supabase 싱글톤 매니저"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseManager, cls).__new__(cls)
            cls._instance.init_client()
        return cls._instance

    def init_client(self):
        """클라이언트 초기화"""
        self.client: Optional[Client] = None
        self._initialized = False

        if not SUPABASE_AVAILABLE:
            print("⚠️ supabase 패키지가 설치되지 않았습니다. pip install supabase")
            return

        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")

        if not url or not key:
            print("⚠️ Supabase URL 또는 Key가 .env에 설정되지 않았습니다.")
            return

        try:
            self.client = create_client(url, key)
            self._initialized = True
            print("✅ Supabase 클라이언트 초기화 완료")
        except Exception as e:
            print(f"❌ Supabase 초기화 실패: {e}")

    @property
    def is_ready(self) -> bool:
        """클라이언트 준비 상태"""
        return self._initialized and self.client is not None

    def save_analysis_result(
        self,
        keyword: str,
        margin_result: Dict[str, Any],
        ai_result: Optional[Dict[str, Any]] = None,
        report_md: str = ""
    ) -> Optional[int]:
        """
        분석 결과를 DB에 저장

        Args:
            keyword: 분석 키워드
            margin_result: MarginResult를 dict로 변환한 데이터
            ai_result: AI 분석 결과 (complaints, copywriting, spec_checklist 등)
            report_md: 마크다운 리포트 내용

        Returns:
            저장된 요청 ID (실패 시 None)
        """
        if not self.is_ready:
            print("⚠️ Supabase가 초기화되지 않았습니다.")
            return None

        try:
            # 1. 요청 기록 생성 (또는 기존 ID 조회)
            request_data = {
                "keyword": keyword,
                "status": "completed"
            }

            req_res = self.client.table("market_analysis_requests").insert(request_data).execute()
            request_id = req_res.data[0]['id']

            # 2. 상세 결과 저장
            result_data = {
                "request_id": request_id,
                "keyword": keyword,
                "margin_data": margin_result,  # JSONB
                "ai_analysis": ai_result or {},  # JSONB
                "report_content": report_md
            }

            self.client.table("analysis_results").insert(result_data).execute()
            print(f"✅ [Supabase] Saved analysis results for '{keyword}' (ID: {request_id})")
            return request_id

        except Exception as e:
            print(f"❌ [Supabase] Error saving data: {str(e)}")
            return None

    def get_analysis_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 분석 기록 조회"""
        if not self.is_ready:
            return []

        try:
            res = self.client.table("analysis_results") \
                .select("*") \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
            return res.data
        except Exception as e:
            print(f"❌ [Supabase] Error fetching history: {str(e)}")
            return []

    def get_analysis_by_keyword(self, keyword: str) -> Optional[Dict[str, Any]]:
        """키워드로 분석 결과 조회"""
        if not self.is_ready:
            return None

        try:
            res = self.client.table("analysis_results") \
                .select("*") \
                .eq("keyword", keyword) \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()

            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            print(f"❌ [Supabase] Error fetching by keyword: {str(e)}")
            return None

    def update_request_status(self, request_id: int, status: str) -> bool:
        """요청 상태 업데이트"""
        if not self.is_ready:
            return False

        try:
            self.client.table("market_analysis_requests") \
                .update({"status": status}) \
                .eq("id", request_id) \
                .execute()
            return True
        except Exception as e:
            print(f"❌ [Supabase] Error updating status: {str(e)}")
            return False


# 싱글톤 인스턴스
db_manager = SupabaseManager()


# --- Mock Manager (테스트용) ---
class MockSupabaseManager:
    """테스트용 Mock Supabase Manager"""

    def __init__(self):
        self._data = []
        self._counter = 1

    @property
    def is_ready(self) -> bool:
        return True

    def save_analysis_result(
        self,
        keyword: str,
        margin_result: Dict[str, Any],
        ai_result: Optional[Dict[str, Any]] = None,
        report_md: str = ""
    ) -> int:
        """Mock 저장"""
        record = {
            "id": self._counter,
            "keyword": keyword,
            "margin_data": margin_result,
            "ai_analysis": ai_result or {},
            "report_content": report_md
        }
        self._data.append(record)
        self._counter += 1
        print(f"✅ [Mock] Saved analysis for '{keyword}' (ID: {record['id']})")
        return record["id"]

    def get_analysis_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Mock 기록 조회"""
        return self._data[-limit:][::-1]

    def get_analysis_by_keyword(self, keyword: str) -> Optional[Dict[str, Any]]:
        """Mock 키워드 조회"""
        for record in reversed(self._data):
            if record["keyword"] == keyword:
                return record
        return None


# --- 테스트 실행 ---
if __name__ == "__main__":
    print("="*60)
    print("🗄️ Supabase 클라이언트 테스트 (v3.1)")
    print("="*60)

    # Mock으로 테스트
    mock_db = MockSupabaseManager()

    # 샘플 데이터 저장
    sample_margin = {
        "margin_rate": -28.0,
        "total_cost": 57582,
        "is_viable": False
    }

    sample_ai = {
        "complaints": [{"category": "품질", "description": "품질 불만"}],
        "copywriting": ["초경량 캠핑의자"],
        "spec_checklist": ["무게 확인", "하중 테스트"]
    }

    record_id = mock_db.save_analysis_result(
        keyword="캠핑의자",
        margin_result=sample_margin,
        ai_result=sample_ai,
        report_md="# 테스트 리포트"
    )

    print(f"\n저장된 ID: {record_id}")

    # 조회
    history = mock_db.get_analysis_history()
    print(f"\n최근 기록: {len(history)}건")

    result = mock_db.get_analysis_by_keyword("캠핑의자")
    if result:
        print(f"키워드 조회 성공: {result['keyword']}")

    print("\n" + "="*60)
    print("✅ Supabase 클라이언트 모듈 준비 완료")
    print("   실제 사용 시 .env에 SUPABASE_URL, SUPABASE_KEY 설정 필요")
    print("="*60 + "\n")
