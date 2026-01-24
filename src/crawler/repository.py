"""
repository.py - 로컬 JSON 저장소 (v4.0)

Supabase 미설정 시 로컬 JSON 파일로 데이터 저장
Supabase 연동 시 이 파일을 교체하면 됨
"""

import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.domain.crawler_models import (
    SourcingKeyword,
    SourcingCandidate,
    UploadHistory,
    CandidateStatus
)


class CandidateRepository:
    """소싱 후보 저장소 (로컬 JSON)"""

    def __init__(self, data_dir: str = None):
        """
        Args:
            data_dir: 데이터 저장 디렉토리 (기본: project_root/data/crawler)
        """
        if data_dir is None:
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / "data" / "crawler"

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 파일 경로
        self.keywords_file = self.data_dir / "keywords.json"
        self.candidates_file = self.data_dir / "candidates.json"
        self.history_file = self.data_dir / "upload_history.json"

        # 초기 파일 생성
        self._init_files()

    def _init_files(self):
        """초기 파일 생성"""
        for file_path in [self.keywords_file, self.candidates_file, self.history_file]:
            if not file_path.exists():
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False)

    def _load_json(self, file_path: Path) -> List[Dict]:
        """JSON 파일 로드"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_json(self, file_path: Path, data: List[Dict]):
        """JSON 파일 저장"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ========== 키워드 관리 ==========

    def get_keywords(self, active_only: bool = True) -> List[SourcingKeyword]:
        """키워드 목록 조회"""
        data = self._load_json(self.keywords_file)
        keywords = [SourcingKeyword.from_dict(d) for d in data]

        if active_only:
            keywords = [k for k in keywords if k.is_active]

        return sorted(keywords, key=lambda k: k.priority)

    def add_keyword(self, keyword: SourcingKeyword) -> SourcingKeyword:
        """키워드 추가"""
        data = self._load_json(self.keywords_file)
        data.append(keyword.to_dict())
        self._save_json(self.keywords_file, data)
        return keyword

    def update_keyword(self, keyword: SourcingKeyword) -> SourcingKeyword:
        """키워드 업데이트"""
        data = self._load_json(self.keywords_file)
        for i, d in enumerate(data):
            if d.get("id") == keyword.id:
                data[i] = keyword.to_dict()
                break
        self._save_json(self.keywords_file, data)
        return keyword

    def delete_keyword(self, keyword_id: str) -> bool:
        """키워드 삭제"""
        data = self._load_json(self.keywords_file)
        original_len = len(data)
        data = [d for d in data if d.get("id") != keyword_id]
        self._save_json(self.keywords_file, data)
        return len(data) < original_len

    def get_keyword_by_id(self, keyword_id: str) -> Optional[SourcingKeyword]:
        """ID로 키워드 조회"""
        data = self._load_json(self.keywords_file)
        for d in data:
            if d.get("id") == keyword_id:
                return SourcingKeyword.from_dict(d)
        return None

    # ========== 후보 상품 관리 ==========

    def get_candidates(
        self,
        status: Optional[CandidateStatus] = None,
        keyword_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[SourcingCandidate]:
        """후보 상품 목록 조회"""
        data = self._load_json(self.candidates_file)
        candidates = [SourcingCandidate.from_dict(d) for d in data]

        # 필터링
        if status:
            candidates = [c for c in candidates if c.status == status]
        if keyword_id:
            candidates = [c for c in candidates if c.keyword_id == keyword_id]

        # 정렬 (마진율 높은 순)
        candidates = sorted(candidates, key=lambda c: c.estimated_margin_rate, reverse=True)

        return candidates[offset:offset + limit]

    def get_pending_candidates(self) -> List[SourcingCandidate]:
        """대기 중인 후보 목록"""
        return self.get_candidates(status=CandidateStatus.PENDING)

    def get_approved_candidates(self) -> List[SourcingCandidate]:
        """승인된 후보 목록"""
        return self.get_candidates(status=CandidateStatus.APPROVED)

    def get_candidates_by_status(self, status: CandidateStatus) -> List[SourcingCandidate]:
        """상태별 후보 목록 조회 (엑셀 추출용)"""
        return self.get_candidates(status=status)

    def add_candidate(self, candidate: SourcingCandidate) -> SourcingCandidate:
        """후보 추가"""
        data = self._load_json(self.candidates_file)
        data.append(candidate.to_dict())
        self._save_json(self.candidates_file, data)
        return candidate

    def update_candidate(self, candidate: SourcingCandidate) -> SourcingCandidate:
        """후보 업데이트"""
        candidate.updated_at = datetime.now()
        data = self._load_json(self.candidates_file)
        for i, d in enumerate(data):
            if d.get("id") == candidate.id:
                data[i] = candidate.to_dict()
                break
        self._save_json(self.candidates_file, data)
        return candidate

    def get_candidate_by_id(self, candidate_id: str) -> Optional[SourcingCandidate]:
        """ID로 후보 조회"""
        data = self._load_json(self.candidates_file)
        for d in data:
            if d.get("id") == candidate_id:
                return SourcingCandidate.from_dict(d)
        return None

    def approve_candidate(self, candidate_id: str) -> Optional[SourcingCandidate]:
        """후보 승인"""
        candidate = self.get_candidate_by_id(candidate_id)
        if candidate:
            candidate.status = CandidateStatus.APPROVED
            candidate.approved_at = datetime.now()
            return self.update_candidate(candidate)
        return None

    def reject_candidate(self, candidate_id: str, reason: str = "") -> Optional[SourcingCandidate]:
        """후보 반려"""
        candidate = self.get_candidate_by_id(candidate_id)
        if candidate:
            candidate.status = CandidateStatus.REJECTED
            candidate.rejected_reason = reason
            return self.update_candidate(candidate)
        return None

    def mark_uploaded(
        self,
        candidate_id: str,
        product_id: str,
        product_url: str
    ) -> Optional[SourcingCandidate]:
        """등록 완료 처리"""
        candidate = self.get_candidate_by_id(candidate_id)
        if candidate:
            candidate.status = CandidateStatus.UPLOADED
            candidate.naver_product_id = product_id
            candidate.naver_product_url = product_url
            candidate.uploaded_at = datetime.now()
            return self.update_candidate(candidate)
        return None

    def mark_failed(self, candidate_id: str, error: str) -> Optional[SourcingCandidate]:
        """등록 실패 처리"""
        candidate = self.get_candidate_by_id(candidate_id)
        if candidate:
            candidate.status = CandidateStatus.FAILED
            candidate.rejected_reason = error
            return self.update_candidate(candidate)
        return None

    def check_duplicate(self, source_url: str) -> bool:
        """중복 URL 체크"""
        data = self._load_json(self.candidates_file)
        for d in data:
            if d.get("source_url") == source_url:
                return True
        return False

    # ========== 통계 ==========

    def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        data = self._load_json(self.candidates_file)
        candidates = [SourcingCandidate.from_dict(d) for d in data]

        pending = [c for c in candidates if c.status == CandidateStatus.PENDING]
        approved = [c for c in candidates if c.status == CandidateStatus.APPROVED]
        uploaded = [c for c in candidates if c.status == CandidateStatus.UPLOADED]
        rejected = [c for c in candidates if c.status == CandidateStatus.REJECTED]

        avg_margin = 0.0
        if pending:
            avg_margin = sum(c.estimated_margin_rate for c in pending) / len(pending)

        return {
            "total": len(candidates),
            "pending": len(pending),
            "approved": len(approved),
            "uploaded": len(uploaded),
            "rejected": len(rejected),
            "avg_margin": avg_margin * 100,  # 퍼센트로 변환
            "keywords": len(self.get_keywords())
        }

    # ========== 업로드 히스토리 ==========

    def add_history(self, history: UploadHistory) -> UploadHistory:
        """히스토리 추가"""
        data = self._load_json(self.history_file)
        data.append(history.to_dict())
        self._save_json(self.history_file, data)
        return history

    def get_history(self, candidate_id: Optional[str] = None) -> List[UploadHistory]:
        """히스토리 조회"""
        data = self._load_json(self.history_file)
        histories = [UploadHistory.from_dict(d) for d in data]

        if candidate_id:
            histories = [h for h in histories if h.candidate_id == candidate_id]

        return sorted(histories, key=lambda h: h.created_at, reverse=True)

    # ========== 데이터 초기화 (테스트용) ==========

    def clear_all(self):
        """모든 데이터 삭제 (주의: 테스트용)"""
        self._save_json(self.keywords_file, [])
        self._save_json(self.candidates_file, [])
        self._save_json(self.history_file, [])

    def seed_sample_keywords(self):
        """샘플 키워드 추가 (테스트용)"""
        sample_keywords = [
            SourcingKeyword(keyword="데스크 정리함", category="홈인테리어", priority=1),
            SourcingKeyword(keyword="모니터 받침대", category="사무용품", priority=2),
            SourcingKeyword(keyword="틈새 수납장", category="홈인테리어", priority=3),
            SourcingKeyword(keyword="케이블 정리함", category="사무용품", priority=4),
            SourcingKeyword(keyword="미니 가습기", category="생활용품", priority=5),
        ]

        for kw in sample_keywords:
            self.add_keyword(kw)

        return sample_keywords
