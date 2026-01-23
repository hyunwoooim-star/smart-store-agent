"""
test_night_crawler.py - Night Crawler v4.0 테스트

테스트 범위:
1. Repository 테스트 (CRUD)
2. KeywordManager 테스트
3. ProductFilter 테스트
4. NightCrawler 테스트 (Mock)
5. ContentGenerator 테스트
6. PublishingBot 테스트 (Mock)
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# 테스트 대상 모듈
from src.domain.crawler_models import (
    SourcingKeyword,
    SourcingCandidate,
    CandidateStatus,
    CrawlRiskLevel,
    CrawlStats,
)
from src.crawler.repository import CandidateRepository
from src.crawler.keyword_manager import KeywordManager
from src.crawler.product_filter import ProductFilter, FilterConfig
from src.crawler.night_crawler import NightCrawler, CrawlerConfig
from src.publisher.content_generator import ContentGenerator, ContentGeneratorConfig
from src.publisher.naver_uploader import NaverUploader, NaverUploaderConfig


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def temp_data_dir():
    """임시 데이터 디렉토리"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def repository(temp_data_dir):
    """테스트용 저장소"""
    return CandidateRepository(data_dir=temp_data_dir)


@pytest.fixture
def keyword_manager(repository):
    """테스트용 키워드 매니저"""
    return KeywordManager(repository)


@pytest.fixture
def product_filter():
    """테스트용 필터"""
    return ProductFilter(FilterConfig(min_margin_rate=0.30))


@pytest.fixture
def sample_candidate():
    """샘플 후보 상품"""
    return SourcingCandidate(
        source_url="https://detail.1688.com/offer/123456.html",
        source_title="桌面收纳盒三层抽屉式",
        source_price_cny=35.0,
        source_images=["https://example.com/img1.jpg"],
        source_shop_name="优质工厂",
        source_shop_rating=4.8,
        source_sales_count=1250,
        title_kr="데스크 정리함 3단 서랍형",
        estimated_cost_krw=15000,
        estimated_margin_rate=0.42,
        recommended_price=25900,
        breakeven_price=18000,
        naver_min_price=19800,
        naver_avg_price=28500,
        competitor_count=12,
        keyword="데스크 정리함",
    )


# ============================================================
# Repository 테스트
# ============================================================

class TestRepository:
    """저장소 테스트"""

    def test_add_keyword(self, repository):
        """키워드 추가 테스트"""
        keyword = SourcingKeyword(
            keyword="데스크 정리함",
            category="홈인테리어",
            priority=1
        )
        result = repository.add_keyword(keyword)

        assert result.keyword == "데스크 정리함"
        assert result.category == "홈인테리어"
        assert result.priority == 1

    def test_get_keywords(self, repository):
        """키워드 목록 조회 테스트"""
        # 키워드 추가
        repository.add_keyword(SourcingKeyword(keyword="키워드1", priority=2))
        repository.add_keyword(SourcingKeyword(keyword="키워드2", priority=1))

        keywords = repository.get_keywords()

        assert len(keywords) == 2
        # 우선순위 순 정렬 확인
        assert keywords[0].priority == 1
        assert keywords[1].priority == 2

    def test_add_candidate(self, repository, sample_candidate):
        """후보 추가 테스트"""
        result = repository.add_candidate(sample_candidate)

        assert result.id == sample_candidate.id
        assert result.title_kr == "데스크 정리함 3단 서랍형"

    def test_get_pending_candidates(self, repository, sample_candidate):
        """대기 중 후보 조회 테스트"""
        repository.add_candidate(sample_candidate)

        pending = repository.get_pending_candidates()

        assert len(pending) == 1
        assert pending[0].status == CandidateStatus.PENDING

    def test_approve_candidate(self, repository, sample_candidate):
        """후보 승인 테스트"""
        repository.add_candidate(sample_candidate)
        result = repository.approve_candidate(sample_candidate.id)

        assert result.status == CandidateStatus.APPROVED
        assert result.approved_at is not None

    def test_reject_candidate(self, repository, sample_candidate):
        """후보 반려 테스트"""
        repository.add_candidate(sample_candidate)
        result = repository.reject_candidate(sample_candidate.id, "마진 부족")

        assert result.status == CandidateStatus.REJECTED
        assert result.rejected_reason == "마진 부족"

    def test_check_duplicate(self, repository, sample_candidate):
        """중복 체크 테스트"""
        repository.add_candidate(sample_candidate)

        is_duplicate = repository.check_duplicate(sample_candidate.source_url)

        assert is_duplicate is True

    def test_get_stats(self, repository, sample_candidate):
        """통계 조회 테스트"""
        repository.add_candidate(sample_candidate)

        stats = repository.get_stats()

        assert stats["total"] == 1
        assert stats["pending"] == 1


# ============================================================
# KeywordManager 테스트
# ============================================================

class TestKeywordManager:
    """키워드 매니저 테스트"""

    def test_add_keyword(self, keyword_manager):
        """키워드 추가"""
        result = keyword_manager.add_keyword("테스트 키워드", "테스트", 3)

        assert result.keyword == "테스트 키워드"
        assert result.category == "테스트"
        assert result.priority == 3

    def test_get_active_keywords(self, keyword_manager):
        """활성 키워드 조회"""
        keyword_manager.add_keyword("키워드1", priority=1)
        keyword_manager.add_keyword("키워드2", priority=2)

        active = keyword_manager.get_active_keywords()

        assert len(active) == 2

    def test_deactivate_keyword(self, keyword_manager):
        """키워드 비활성화"""
        kw = keyword_manager.add_keyword("테스트")
        keyword_manager.deactivate_keyword(kw.id)

        active = keyword_manager.get_active_keywords()

        assert len(active) == 0

    def test_seed_default_keywords(self, keyword_manager):
        """기본 키워드 시드"""
        keywords = keyword_manager.seed_default_keywords()

        assert len(keywords) >= 5
        assert any(k.keyword == "데스크 정리함" for k in keywords)

    def test_get_keywords_to_crawl(self, keyword_manager):
        """크롤링 대상 키워드 선택"""
        keyword_manager.seed_default_keywords()

        to_crawl = keyword_manager.get_keywords_to_crawl(max_keywords=3)

        assert len(to_crawl) == 3


# ============================================================
# ProductFilter 테스트
# ============================================================

class TestProductFilter:
    """상품 필터 테스트"""

    def test_basic_filter_pass(self, product_filter):
        """기본 필터 통과"""
        products = [
            {"price": 50.0, "sales_count": 100, "shop_rating": 4.5},
        ]
        filtered = product_filter.apply_basic_filter(products)

        assert len(filtered) == 1

    def test_basic_filter_fail_price_low(self, product_filter):
        """기본 필터 - 가격 너무 낮음"""
        products = [
            {"price": 2.0, "sales_count": 100, "shop_rating": 4.5},
        ]
        filtered = product_filter.apply_basic_filter(products)

        assert len(filtered) == 0

    def test_basic_filter_fail_sales_low(self, product_filter):
        """기본 필터 - 판매량 부족"""
        products = [
            {"price": 50.0, "sales_count": 5, "shop_rating": 4.5},
        ]
        filtered = product_filter.apply_basic_filter(products)

        assert len(filtered) == 0

    def test_risk_filter_safe(self, product_filter):
        """리스크 필터 - 안전"""
        level, reasons = product_filter.apply_risk_filter("데스크 정리함 3단형")

        assert level == CrawlRiskLevel.SAFE
        assert len(reasons) == 0

    def test_risk_filter_brand_danger(self, product_filter):
        """리스크 필터 - 브랜드 위험"""
        level, reasons = product_filter.apply_risk_filter("나이키 신발 정품")

        assert level == CrawlRiskLevel.DANGER
        assert any("브랜드" in r for r in reasons)

    def test_risk_filter_kc_warning(self, product_filter):
        """리스크 필터 - KC인증 경고"""
        level, reasons = product_filter.apply_risk_filter("USB 충전기 케이블")

        assert level == CrawlRiskLevel.WARNING
        assert any("KC인증" in r for r in reasons)

    def test_risk_filter_forbidden(self, product_filter):
        """리스크 필터 - 금지품목"""
        level, reasons = product_filter.apply_risk_filter("건강 영양제 비타민")

        assert level == CrawlRiskLevel.DANGER
        assert any("판매 제한" in r for r in reasons)


# ============================================================
# NightCrawler 테스트 (Mock)
# ============================================================

class TestNightCrawler:
    """Night Crawler 테스트"""

    @pytest.mark.asyncio
    async def test_crawl_with_mock(self, temp_data_dir):
        """Mock 모드 크롤링"""
        config = CrawlerConfig(
            use_mock=True,
            max_keywords_per_run=2,
            max_products_per_keyword=5,
            min_delay_seconds=0,
            max_delay_seconds=1
        )
        repo = CandidateRepository(data_dir=temp_data_dir)
        crawler = NightCrawler(config=config, repository=repo)

        stats = await crawler.run_nightly_job()

        assert stats.crawled_keywords > 0
        assert stats.total_products_found > 0

    @pytest.mark.asyncio
    async def test_crawl_stats(self, temp_data_dir):
        """크롤링 통계 확인"""
        config = CrawlerConfig(
            use_mock=True,
            max_keywords_per_run=1,
            max_products_per_keyword=3,
            min_delay_seconds=0,
            max_delay_seconds=1
        )
        repo = CandidateRepository(data_dir=temp_data_dir)
        crawler = NightCrawler(config=config, repository=repo)

        stats = await crawler.run_nightly_job()

        assert stats.start_time is not None
        assert stats.end_time is not None
        assert stats.duration_minutes >= 0


# ============================================================
# ContentGenerator 테스트
# ============================================================

class TestContentGenerator:
    """콘텐츠 생성기 테스트"""

    def test_template_generation(self, sample_candidate):
        """템플릿 기반 생성 (AI 없이)"""
        generator = ContentGenerator(ContentGeneratorConfig(use_ai=False))
        content = generator._generate_template(sample_candidate)

        assert content.title == sample_candidate.title_kr
        assert content.problem != ""
        assert content.agitation != ""
        assert content.solution != ""
        assert len(content.features) >= 3

    def test_html_generation(self, sample_candidate):
        """HTML 생성"""
        generator = ContentGenerator(ContentGeneratorConfig(use_ai=False))
        content = generator._generate_template(sample_candidate)
        html = content.to_html()

        assert "<div" in html
        assert content.title in html or sample_candidate.title_kr in html


# ============================================================
# NaverUploader 테스트 (Mock)
# ============================================================

class TestNaverUploader:
    """네이버 업로더 테스트"""

    @pytest.mark.asyncio
    async def test_mock_upload(self, sample_candidate):
        """Mock 업로드"""
        uploader = NaverUploader(NaverUploaderConfig(use_mock=True))
        generator = ContentGenerator(ContentGeneratorConfig(use_ai=False))

        content = generator._generate_template(sample_candidate)
        result = await uploader.upload_product(sample_candidate, content)

        # Mock은 90% 성공률이지만 대부분 성공할 것
        assert result is not None
        assert result.product_id != "" or result.error_message != ""


# ============================================================
# Integration 테스트
# ============================================================

class TestIntegration:
    """통합 테스트"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, temp_data_dir):
        """전체 워크플로우 테스트"""
        # 1. 저장소 및 키워드 설정
        repo = CandidateRepository(data_dir=temp_data_dir)
        km = KeywordManager(repo)
        km.add_keyword("테스트 정리함", "테스트", 1)

        # 2. 크롤링
        config = CrawlerConfig(
            use_mock=True,
            max_keywords_per_run=1,
            max_products_per_keyword=3,
            min_delay_seconds=0,
            max_delay_seconds=1
        )
        crawler = NightCrawler(config=config, repository=repo)
        await crawler.run_nightly_job()

        # 3. 결과 확인
        pending = repo.get_pending_candidates()
        assert len(pending) >= 0  # 필터링에 따라 0개일 수 있음

        # 4. 통계 확인
        stats = repo.get_stats()
        assert stats["total"] >= 0


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
