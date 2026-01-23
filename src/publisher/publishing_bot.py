"""
publishing_bot.py - 상품 등록 봇 (v4.0)

승인된 상품을 자동으로 등록하는 봇

워크플로우:
1. 승인된 후보 목록 가져오기
2. 상세페이지 콘텐츠 생성 (PAS)
3. 네이버 스마트스토어 등록
4. 결과 기록 및 알림
"""

import asyncio
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass, field

from src.domain.crawler_models import (
    SourcingCandidate,
    UploadHistory,
    CandidateStatus
)
from src.crawler.repository import CandidateRepository
from src.publisher.content_generator import ContentGenerator, ContentGeneratorConfig
from src.publisher.naver_uploader import NaverUploader, NaverUploaderConfig, UploadResult


@dataclass
class PublishingStats:
    """퍼블리싱 통계"""
    total_candidates: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


@dataclass
class PublishingBotConfig:
    """퍼블리싱 봇 설정"""
    max_products_per_run: int = 10      # 실행당 최대 등록 수
    delay_between_uploads: int = 5      # 등록 간 대기 (초)
    use_ai_content: bool = True         # AI 콘텐츠 생성 사용


class PublishingBot:
    """상품 등록 봇"""

    def __init__(
        self,
        config: PublishingBotConfig = None,
        repository: CandidateRepository = None,
        content_generator: ContentGenerator = None,
        uploader: NaverUploader = None
    ):
        self.config = config or PublishingBotConfig()
        self.repository = repository or CandidateRepository()
        self.content_generator = content_generator or ContentGenerator(
            ContentGeneratorConfig(use_ai=self.config.use_ai_content)
        )
        self.uploader = uploader or NaverUploader()

        self.stats = PublishingStats()
        self._should_stop = False

    async def process_approved(self) -> PublishingStats:
        """승인된 상품 일괄 등록

        Returns:
            PublishingStats: 등록 통계
        """
        print("[PublishingBot] 승인된 상품 등록 시작!")
        self.stats = PublishingStats(start_time=datetime.now())
        self._should_stop = False

        try:
            # 승인된 후보 가져오기
            candidates = self.repository.get_approved_candidates()
            self.stats.total_candidates = len(candidates)

            if not candidates:
                print("[PublishingBot] 등록할 상품이 없습니다.")
                return self.stats

            print(f"[PublishingBot] 등록 대상: {len(candidates)}개")

            # 최대 개수 제한
            candidates = candidates[:self.config.max_products_per_run]

            for i, candidate in enumerate(candidates, 1):
                if self._should_stop:
                    print("[PublishingBot] 중단 요청됨")
                    break

                print(f"\n[PublishingBot] [{i}/{len(candidates)}] {candidate.title_kr}")

                try:
                    result = await self._process_candidate(candidate)

                    if result.success:
                        self.stats.success_count += 1
                        print(f"  등록 성공: {result.product_url}")
                    else:
                        self.stats.failed_count += 1
                        print(f"  등록 실패: {result.error_message}")
                        self.stats.errors.append(f"{candidate.title_kr}: {result.error_message}")

                except Exception as e:
                    self.stats.failed_count += 1
                    error_msg = f"{candidate.title_kr}: {str(e)}"
                    print(f"  오류: {e}")
                    self.stats.errors.append(error_msg)

                # 등록 간 대기
                if i < len(candidates) and not self._should_stop:
                    print(f"  {self.config.delay_between_uploads}초 대기...")
                    await asyncio.sleep(self.config.delay_between_uploads)

        except Exception as e:
            print(f"[PublishingBot] 치명적 오류: {e}")
            self.stats.errors.append(f"Fatal: {str(e)}")

        finally:
            self.stats.end_time = datetime.now()
            self._print_summary()

        return self.stats

    async def _process_candidate(self, candidate: SourcingCandidate) -> UploadResult:
        """단일 후보 처리

        Args:
            candidate: 소싱 후보

        Returns:
            UploadResult: 등록 결과
        """
        # 1. 상세페이지 콘텐츠 생성
        print("  콘텐츠 생성 중...")
        content = await self.content_generator.generate(candidate)

        # 2. 네이버 등록
        print("  네이버 등록 중...")
        result = await self.uploader.upload_product(candidate, content)

        # 3. 결과 기록
        if result.success:
            # 등록 완료 처리
            self.repository.mark_uploaded(
                candidate.id,
                result.product_id,
                result.product_url
            )
        else:
            # 등록 실패 처리
            self.repository.mark_failed(candidate.id, result.error_message)

        # 4. 히스토리 저장
        history = UploadHistory(
            candidate_id=candidate.id,
            platform="naver",
            status="success" if result.success else "failed",
            response_data=result.raw_response or {},
            error_message=result.error_message,
        )
        self.repository.add_history(history)

        return result

    async def process_single(self, candidate_id: str) -> UploadResult:
        """단일 상품 등록

        Args:
            candidate_id: 후보 ID

        Returns:
            UploadResult: 등록 결과
        """
        candidate = self.repository.get_candidate_by_id(candidate_id)

        if not candidate:
            return UploadResult(
                success=False,
                error_message=f"후보를 찾을 수 없습니다: {candidate_id}"
            )

        if candidate.status != CandidateStatus.APPROVED:
            return UploadResult(
                success=False,
                error_message=f"승인되지 않은 상품입니다. 현재 상태: {candidate.status.value}"
            )

        return await self._process_candidate(candidate)

    def stop(self):
        """등록 중단 요청"""
        self._should_stop = True
        print("[PublishingBot] 중단 요청됨. 현재 작업 완료 후 종료합니다.")

    def _print_summary(self):
        """결과 요약 출력"""
        print("\n" + "=" * 50)
        print("[PublishingBot] 상품 등록 완료!")
        print("=" * 50)
        print(f"  대상: {self.stats.total_candidates}개")
        print(f"  성공: {self.stats.success_count}개")
        print(f"  실패: {self.stats.failed_count}개")
        print(f"  소요 시간: {self.stats.duration_seconds:.1f}초")
        if self.stats.errors:
            print(f"  오류 목록:")
            for err in self.stats.errors[:5]:
                print(f"    - {err}")
        print("=" * 50)

    # ========== 동기 메서드 (Streamlit용) ==========

    def process_approved_sync(self) -> PublishingStats:
        """승인된 상품 일괄 등록 (동기)"""
        return asyncio.run(self.process_approved())

    def process_single_sync(self, candidate_id: str) -> UploadResult:
        """단일 상품 등록 (동기)"""
        return asyncio.run(self.process_single(candidate_id))


# CLI 테스트용
async def main():
    """CLI 테스트"""
    bot = PublishingBot()
    stats = await bot.process_approved()
    print(f"\n결과: 성공 {stats.success_count}, 실패 {stats.failed_count}")


if __name__ == "__main__":
    asyncio.run(main())
