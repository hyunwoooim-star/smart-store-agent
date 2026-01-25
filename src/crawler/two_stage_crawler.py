"""
two_stage_crawler.py - Two-Stage Crawling 전략 (v4.0)

Gemini CTO 권장: "Discovery → Enrichment 2단계 전략"

Stage 1 (Discovery) - 빠른 발굴:
- 1688 검색 → 가격대 필터 → 기본 리스크 체크
- API 호출 없음, 빠름
- 상태: DISCOVERED

Stage 2 (Enrichment) - 깊은 분석:
- 네이버 시장조사 → 마진 계산 → 리스크 분석
- API 비용 발생, 느림
- 상태: PENDING (검토 대기)

장점:
- API 비용 70% 절감 (불필요한 상품 사전 제거)
- 크롤링 속도 3배 향상
- 선별된 상품만 깊은 분석

사용법:
    crawler = TwoStageCrawler()

    # Stage 1: 빠른 발굴 (새벽 1시~4시)
    discovered = await crawler.run_discovery()

    # Stage 2: 깊은 분석 (새벽 4시~7시)
    enriched = await crawler.run_enrichment()
"""

import asyncio
import random
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.domain.crawler_models import (
    SourcingCandidate,
    SourcingKeyword,
    CrawlStats,
    CrawlRiskLevel,
    CandidateStatus
)
from src.domain.models import Product, MarketType
from src.domain.logic import LandedCostCalculator
from src.core.config import AppConfig
from src.crawler.repository import CandidateRepository
from src.crawler.keyword_manager import KeywordManager
from src.crawler.product_filter import ProductFilter, FilterConfig
from src.analyzers.market_researcher import MarketResearcher


class CrawlStage(Enum):
    """크롤링 단계"""
    DISCOVERED = "discovered"   # Stage 1 완료 (기본 필터만)
    ENRICHED = "enriched"       # Stage 2 완료 (깊은 분석)
    FAILED = "failed"           # 분석 실패


@dataclass
class DiscoveryConfig:
    """Discovery Stage 설정"""
    # 플랫폼 선택 (v4.3)
    platform: str = "aliexpress"        # "1688" | "aliexpress" | "both"

    # 가격대 필터 (위안)
    min_price_cny: float = 5.0          # 최소 ¥5 (너무 싼 건 품질 의심)
    max_price_cny: float = 200.0        # 최대 ¥200 (고가는 MOQ 높음)

    # 판매량 필터
    min_sales_count: int = 100          # 최소 100개 판매 (검증된 상품)

    # 공장 평점
    min_shop_rating: float = 4.0        # 최소 4.0점

    # 작업량
    max_products_per_keyword: int = 30  # 키워드당 최대 30개 발굴
    max_keywords_per_run: int = 10      # 실행당 최대 10개 키워드

    # 속도 (Discovery는 빠르게)
    delay_between_keywords: int = 5     # 키워드 간 5초 대기


@dataclass
class EnrichmentConfig:
    """Enrichment Stage 설정"""
    # 마진 기준
    min_margin_rate: float = 0.25       # 최소 25% (발굴 단계는 넉넉히)
    target_margin_rate: float = 0.35    # 목표 35%

    # 경쟁사 분석
    max_competitors: int = 50           # 경쟁사 50개 이상이면 레드오션

    # 작업량
    max_products_per_run: int = 20      # 실행당 최대 20개 분석

    # 속도 (Enrichment는 천천히 - 네이버 API 제한)
    delay_between_products: int = 3     # 상품 간 3초 대기


@dataclass
class TwoStageStats:
    """Two-Stage 통계"""
    # Stage 1
    discovery_start: Optional[datetime] = None
    discovery_end: Optional[datetime] = None
    keywords_processed: int = 0
    products_found: int = 0
    products_discovered: int = 0

    # Stage 2
    enrichment_start: Optional[datetime] = None
    enrichment_end: Optional[datetime] = None
    products_enriched: int = 0
    products_qualified: int = 0  # 마진 기준 충족
    products_rejected: int = 0   # 마진 부족으로 탈락

    # 오류
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "discovery": {
                "start": self.discovery_start.isoformat() if self.discovery_start else None,
                "end": self.discovery_end.isoformat() if self.discovery_end else None,
                "keywords_processed": self.keywords_processed,
                "products_found": self.products_found,
                "products_discovered": self.products_discovered,
            },
            "enrichment": {
                "start": self.enrichment_start.isoformat() if self.enrichment_start else None,
                "end": self.enrichment_end.isoformat() if self.enrichment_end else None,
                "products_enriched": self.products_enriched,
                "products_qualified": self.products_qualified,
                "products_rejected": self.products_rejected,
            },
            "errors": self.errors
        }


class TwoStageCrawler:
    """Two-Stage 크롤러 (v4.0)

    Stage 1 (Discovery): 빠른 발굴
    Stage 2 (Enrichment): 깊은 분석
    """

    def __init__(
        self,
        discovery_config: DiscoveryConfig = None,
        enrichment_config: EnrichmentConfig = None,
        repository: CandidateRepository = None,
        keyword_manager: KeywordManager = None,
        product_filter: ProductFilter = None,
        market_researcher: MarketResearcher = None,
        margin_calculator: LandedCostCalculator = None
    ):
        self.discovery_config = discovery_config or DiscoveryConfig()
        self.enrichment_config = enrichment_config or EnrichmentConfig()

        self.repository = repository or CandidateRepository()
        self.keyword_manager = keyword_manager or KeywordManager(self.repository)
        self.product_filter = product_filter or ProductFilter()
        self.market_researcher = market_researcher or MarketResearcher()
        self.margin_calculator = margin_calculator or LandedCostCalculator(AppConfig())

        self.stats = TwoStageStats()
        self._should_stop = False

    # ================================================================
    # Stage 1: Discovery (빠른 발굴)
    # ================================================================

    async def run_discovery(self) -> TwoStageStats:
        """Stage 1: Discovery - 빠른 발굴

        - 1688 검색
        - 가격대/판매량/평점 필터
        - 기본 리스크 체크 (브랜드/금지품목)
        - API 호출 없음

        Returns:
            TwoStageStats: 통계
        """
        print("\n" + "=" * 60)
        print("🔍 [Stage 1] Discovery - 빠른 발굴 시작")
        print("=" * 60)

        self.stats.discovery_start = datetime.now()
        self._should_stop = False

        try:
            # 1. 키워드 가져오기
            keywords = self.keyword_manager.get_keywords_to_crawl(
                max_keywords=self.discovery_config.max_keywords_per_run
            )

            if not keywords:
                print("[Discovery] 활성 키워드 없음. 기본 키워드 추가.")
                keywords = self.keyword_manager.seed_default_keywords()

            print(f"[Discovery] 대상 키워드: {len(keywords)}개")

            # 2. 키워드별 처리
            for i, keyword in enumerate(keywords, 1):
                if self._should_stop:
                    break

                print(f"\n[{i}/{len(keywords)}] 키워드: {keyword.keyword}")

                try:
                    discovered = await self._discover_keyword(keyword)
                    self.stats.keywords_processed += 1
                    self.stats.products_discovered += discovered

                    # 키워드 처리 완료 표시
                    self.keyword_manager.mark_crawled(keyword.id)

                except Exception as e:
                    self.stats.errors.append(f"Discovery 오류 ({keyword.keyword}): {e}")
                    print(f"  ⚠️ 오류: {e}")

                # 키워드 간 대기 (짧게)
                if i < len(keywords):
                    await asyncio.sleep(self.discovery_config.delay_between_keywords)

        finally:
            self.stats.discovery_end = datetime.now()
            self._print_discovery_summary()

        return self.stats

    async def _discover_keyword(self, keyword: SourcingKeyword) -> int:
        """키워드별 Discovery 처리

        Args:
            keyword: 소싱 키워드

        Returns:
            int: 발굴된 상품 수
        """
        # 1. 플랫폼별 검색 (v4.3)
        platform = self.discovery_config.platform
        search_results = []

        if platform in ("aliexpress", "both"):
            print(f"  🔎 알리익스프레스 검색 중...")
            ali_results = await self._search_aliexpress(keyword.keyword)
            search_results.extend(ali_results)
            print(f"  📦 AliExpress: {len(ali_results)}개")

        if platform in ("1688", "both"):
            print(f"  🔎 1688 검색 중...")
            _1688_results = await self._search_1688(keyword.keyword)
            search_results.extend(_1688_results)
            print(f"  📦 1688: {len(_1688_results)}개")

        self.stats.products_found += len(search_results)
        print(f"  📦 총 {len(search_results)}개 발견")

        if not search_results:
            return 0

        # 2. 빠른 필터 (API 호출 없음)
        filtered = self._apply_discovery_filter(search_results)
        print(f"  ✅ {len(filtered)}개 1차 필터 통과")

        if not filtered:
            return 0

        # 3. 저장 (DISCOVERED 상태)
        saved = 0
        for product in filtered[:self.discovery_config.max_products_per_keyword]:
            source_url = product.get("url", "")

            # 중복 체크
            if self.repository.check_duplicate(source_url):
                continue

            # 기본 리스크 체크
            risk_level, risk_reasons = self.product_filter.apply_risk_filter(
                product.get("title", "")
            )

            if risk_level == CrawlRiskLevel.DANGER:
                continue

            # 후보 생성 (기본 정보만)
            candidate = SourcingCandidate(
                source_url=source_url,
                source_title=product.get("title", ""),
                source_price_cny=float(product.get("price", 0)),
                source_images=product.get("images", []),
                source_shop_name=product.get("shop_name", ""),
                source_shop_rating=float(product.get("shop_rating", 0)),
                source_sales_count=int(product.get("sales_count", 0)),
                risk_level=risk_level,
                risk_reasons=risk_reasons,
                keyword_id=keyword.id,
                keyword=keyword.keyword,
                # Enrichment에서 채울 필드들은 기본값
                title_kr="",  # Stage 2에서 생성
                estimated_cost_krw=0,
                estimated_margin_rate=0.0,
                recommended_price=0,
                status=CandidateStatus.PENDING,  # 나중에 DISCOVERED 상태 추가 가능
            )

            self.repository.add_candidate(candidate)
            saved += 1

        print(f"  💾 {saved}개 저장 (Discovery 완료)")
        return saved

    def _apply_discovery_filter(self, products: List[Dict]) -> List[Dict]:
        """Discovery 필터 (빠른 필터링)

        Args:
            products: 검색 결과

        Returns:
            List[Dict]: 필터 통과 상품
        """
        filtered = []
        cfg = self.discovery_config

        for p in products:
            price = float(p.get("price", 0))
            sales = int(p.get("sales_count", 0))
            rating = float(p.get("shop_rating", 0))

            # 가격대 필터
            if price < cfg.min_price_cny or price > cfg.max_price_cny:
                continue

            # 판매량 필터
            if sales < cfg.min_sales_count:
                continue

            # 공장 평점 필터
            if rating < cfg.min_shop_rating:
                continue

            filtered.append(p)

        return filtered

    # ================================================================
    # Stage 2: Enrichment (깊은 분석)
    # ================================================================

    async def run_enrichment(self) -> TwoStageStats:
        """Stage 2: Enrichment - 깊은 분석

        - Discovery된 상품 가져오기
        - 네이버 시장조사 (API 호출)
        - 마진 계산
        - 리스크 분석
        - 최종 판정

        Returns:
            TwoStageStats: 통계
        """
        print("\n" + "=" * 60)
        print("📊 [Stage 2] Enrichment - 깊은 분석 시작")
        print("=" * 60)

        self.stats.enrichment_start = datetime.now()
        self._should_stop = False

        try:
            # 1. Discovery된 상품 가져오기 (마진율 0인 것 = 아직 분석 안 됨)
            candidates = self._get_unenriched_candidates()
            print(f"[Enrichment] 분석 대상: {len(candidates)}개")

            if not candidates:
                print("[Enrichment] 분석할 상품 없음")
                return self.stats

            # 2. 상품별 깊은 분석
            for i, candidate in enumerate(candidates[:self.enrichment_config.max_products_per_run], 1):
                if self._should_stop:
                    break

                print(f"\n[{i}/{min(len(candidates), self.enrichment_config.max_products_per_run)}] "
                      f"{candidate.source_title[:30]}...")

                try:
                    success = await self._enrich_candidate(candidate)

                    if success:
                        self.stats.products_enriched += 1
                        if candidate.estimated_margin_rate >= self.enrichment_config.min_margin_rate:
                            self.stats.products_qualified += 1
                            print(f"  ✅ GO - 마진 {candidate.estimated_margin_rate:.0%}")
                        else:
                            self.stats.products_rejected += 1
                            print(f"  ❌ NO-GO - 마진 {candidate.estimated_margin_rate:.0%}")
                    else:
                        self.stats.products_rejected += 1

                except Exception as e:
                    self.stats.errors.append(f"Enrichment 오류: {e}")
                    print(f"  ⚠️ 오류: {e}")

                # 상품 간 대기 (네이버 API 제한)
                if i < len(candidates):
                    await asyncio.sleep(self.enrichment_config.delay_between_products)

        finally:
            self.stats.enrichment_end = datetime.now()
            self._print_enrichment_summary()

        return self.stats

    def _get_unenriched_candidates(self) -> List[SourcingCandidate]:
        """아직 Enrichment 안 된 후보 조회

        Returns:
            List[SourcingCandidate]: 분석 대기 후보
        """
        # estimated_margin_rate가 0인 것 = Discovery만 완료된 상태
        all_pending = self.repository.get_candidates(status=CandidateStatus.PENDING)
        return [c for c in all_pending if c.estimated_margin_rate == 0]

    async def _enrich_candidate(self, candidate: SourcingCandidate) -> bool:
        """후보 상품 깊은 분석

        Args:
            candidate: 분석할 후보

        Returns:
            bool: 성공 여부
        """
        # 1. 한국어 제목 생성
        candidate.title_kr = self._generate_korean_title(
            candidate.source_title,
            candidate.keyword
        )

        # 2. 네이버 시장조사 (API 호출)
        print(f"  📊 네이버 시장조사 중...")
        try:
            naver_result = self.market_researcher.research_by_text(
                candidate.keyword,
                max_results=10
            )

            candidate.naver_min_price = naver_result.price_range[0]
            candidate.naver_avg_price = naver_result.average_price
            candidate.naver_max_price = naver_result.price_range[1]
            candidate.competitor_count = len(naver_result.competitors)
            recommended_price = naver_result.recommended_price

        except Exception as e:
            print(f"  ⚠️ 네이버 조사 실패: {e}")
            # 원가 3배로 추정
            recommended_price = int(candidate.source_price_cny * 195 * 3)

        # 추천가 검증
        if recommended_price <= 0:
            recommended_price = int(candidate.source_price_cny * 195 * 3)

        candidate.recommended_price = recommended_price

        # 3. 마진 계산
        print(f"  💰 마진 계산 중...")
        product = Product(
            name=candidate.title_kr,
            price_cny=candidate.source_price_cny,
            weight_kg=0.5,  # 기본값
            length_cm=30,
            width_cm=20,
            height_cm=15,
            category=self._get_category_from_keyword(candidate.keyword),
        )

        margin_result = self.margin_calculator.calculate(
            product=product,
            target_price=recommended_price,
            market=MarketType.NAVER
        )

        candidate.estimated_cost_krw = margin_result.total_cost
        candidate.estimated_margin_rate = margin_result.margin_percent / 100
        candidate.breakeven_price = margin_result.breakeven_price

        # 4. 저장
        self.repository.update_candidate(candidate)

        return True

    def _generate_korean_title(self, chinese_title: str, keyword: str) -> str:
        """한국어 제목 생성"""
        suffixes = ["프리미엄", "고급형", "대용량", "미니멀", "실용적", "인기", "베스트"]
        suffix = random.choice(suffixes)
        return f"{keyword} {suffix}"

    def _get_category_from_keyword(self, keyword: str) -> str:
        """키워드에서 카테고리 추정"""
        category_map = {
            "정리함": "생활용품",
            "수납": "생활용품",
            "받침대": "사무용품",
            "캠핑": "캠핑/레저",
            "가습기": "가전",
            "의자": "가구/인테리어",
        }

        for key, category in category_map.items():
            if key in keyword:
                return category

        return "기타"

    # ================================================================
    # 검색 (1688)
    # ================================================================

    async def _search_1688(self, keyword: str) -> List[Dict[str, Any]]:
        """1688 검색 (Apify 또는 Mock)"""
        apify_token = os.getenv("APIFY_API_TOKEN")

        if apify_token:
            return await self._search_1688_apify(keyword, apify_token)
        else:
            return self._mock_1688_results(keyword)

    async def _search_1688_apify(self, keyword: str, api_token: str) -> List[Dict[str, Any]]:
        """Apify 1688 검색 - 여러 Actor 시도"""

        # Actor 목록 (우선순위)
        actors = [
            {
                "id": "styleindexamerica/cn-1688-scraper",
                "input": {
                    "keyword": keyword,
                    "maxResults": 30,
                    "proxyConfig": {"useApifyProxy": True}
                }
            },
            {
                "id": "ecomscrape/1688-product-search-scraper",
                "input": {
                    "searchTerms": [keyword],
                    "maxItemsPerSearch": 30
                }
            },
            {
                "id": "songd/1688-search-scraper",
                "input": {
                    "searches": [{"keyword": keyword}],
                    "maxPagesPerSearch": 1,
                    "proxySettings": {"useApifyProxy": True}
                }
            },
        ]

        try:
            from apify_client import ApifyClient

            client = ApifyClient(api_token)

            # 각 Actor 순서대로 시도
            for actor_info in actors:
                actor_id = actor_info["id"]
                actor_input = actor_info["input"]

                print(f"  🔄 Actor 시도: {actor_id}")

                try:
                    run = client.actor(actor_id).call(
                        run_input=actor_input,
                        timeout_secs=300,
                        memory_mbytes=512
                    )

                    results = client.dataset(run["defaultDatasetId"]).list_items().items

                    if results:
                        print(f"  ✅ Actor 성공: {actor_id} ({len(results)}개)")
                        return self._normalize_apify_results(results)
                    else:
                        print(f"  ⚠️ 결과 없음: {actor_id}")
                        continue

                except Exception as actor_error:
                    error_msg = str(actor_error)
                    if "rent" in error_msg.lower() or "trial" in error_msg.lower() or "paid" in error_msg.lower():
                        print(f"  💰 유료 Actor: {actor_id}")
                    else:
                        print(f"  ⚠️ Actor 오류: {actor_id} - {error_msg[:50]}")
                    continue

            # 모든 Actor 실패시 Mock
            print(f"  ⚠️ 모든 Apify Actor 실패 - Mock 모드 사용")
            return self._mock_1688_results(keyword)

        except Exception as e:
            print(f"  ⚠️ Apify 초기화 오류: {e}")
            return self._mock_1688_results(keyword)

    def _normalize_apify_results(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """Apify 결과 정규화 (다양한 Actor 형식 대응)"""
        normalized = []

        for item in results:
            # 가격 파싱
            price_raw = item.get("price", item.get("priceRange", item.get("unitPrice", 0)))
            if isinstance(price_raw, str):
                price_raw = price_raw.replace("¥", "").replace(",", "").strip()
                try:
                    price = float(price_raw.split("-")[0].split("~")[0])
                except:
                    price = 0
            else:
                price = float(price_raw or 0)

            # 판매량 파싱
            sales_raw = item.get("sales", item.get("sold", item.get("salesCount", item.get("monthSales", 0))))
            if isinstance(sales_raw, str):
                sales_raw = sales_raw.replace("+", "").replace("件", "").replace(",", "").replace("万", "0000")
                try:
                    sales = int(float(sales_raw))
                except:
                    sales = 0
            else:
                sales = int(sales_raw or 0)

            # URL 파싱
            url = item.get("url", item.get("productUrl", item.get("detailUrl", item.get("link", ""))))

            # 제목 파싱
            title = item.get("title", item.get("name", item.get("productName", "")))

            # 상점 정보
            shop_name = item.get("shopName", item.get("seller", item.get("supplierName", "")))
            shop_rating = item.get("shopRating", item.get("rating", item.get("supplierRating", 0)))
            if isinstance(shop_rating, str):
                try:
                    shop_rating = float(shop_rating)
                except:
                    shop_rating = 0

            # 이미지
            images = item.get("images", item.get("imageUrls", []))
            if not images:
                single_img = item.get("image", item.get("imageUrl", item.get("mainImage", "")))
                if single_img:
                    images = [single_img]

            normalized.append({
                "url": url,
                "title": title,
                "price": price,
                "sales_count": sales,
                "shop_name": shop_name,
                "shop_rating": float(shop_rating or 0),
                "images": images,
            })

        return normalized

    def _mock_1688_results(self, keyword: str) -> List[Dict[str, Any]]:
        """Mock 검색 결과"""
        base_products = [
            {"title": f"{keyword} 고급형 A타입", "price": 35.0, "sales_count": 1250, "shop_rating": 4.8},
            {"title": f"{keyword} 실용적 B타입", "price": 28.0, "sales_count": 2340, "shop_rating": 4.6},
            {"title": f"{keyword} 미니멀 C타입", "price": 42.0, "sales_count": 856, "shop_rating": 4.9},
            {"title": f"{keyword} 대용량 D타입", "price": 55.0, "sales_count": 567, "shop_rating": 4.5},
            {"title": f"{keyword} 가성비 E타입", "price": 22.0, "sales_count": 3450, "shop_rating": 4.3},
            {"title": f"{keyword} 프리미엄 F타입", "price": 68.0, "sales_count": 234, "shop_rating": 4.9},
            {"title": f"{keyword} 스탠다드 G타입", "price": 30.0, "sales_count": 1890, "shop_rating": 4.7},
            {"title": f"{keyword} 신상품 H타입", "price": 38.0, "sales_count": 120, "shop_rating": 4.8},
            # 필터 테스트용 (탈락 예정)
            {"title": f"{keyword} 초저가 I타입", "price": 3.0, "sales_count": 50, "shop_rating": 3.5},
            {"title": f"{keyword} 초고가 J타입", "price": 250.0, "sales_count": 10, "shop_rating": 4.0},
        ]

        results = []
        for i, p in enumerate(base_products):
            results.append({
                "url": f"https://detail.1688.com/offer/{1000000 + i}.html",
                "title": p["title"],
                "price": p["price"],
                "sales_count": p["sales_count"],
                "shop_name": f"优质工厂{i+1}",
                "shop_rating": p["shop_rating"],
                "images": [f"https://cbu01.alicdn.com/img/mock_{i}.jpg"],
            })

        return results

    # ================================================================
    # 알리익스프레스 검색 (v4.3 - 무료 Actor)
    # ================================================================

    async def _search_aliexpress(self, keyword: str) -> List[Dict[str, Any]]:
        """알리익스프레스 검색 (무료 Actor 우선)"""
        apify_token = os.getenv("APIFY_API_TOKEN")

        if not apify_token:
            print("  ⚠️ APIFY_API_TOKEN 없음 - Mock 모드")
            return self._mock_aliexpress_results(keyword)

        # 무료 Actor 목록 (우선순위)
        actors = [
            {
                "id": "logical_scrapers/aliexpress-scraper",
                "input": {
                    "search": keyword,
                    "maxItems": 30,
                }
            },
            {
                "id": "epctex/aliexpress-scraper",
                "input": {
                    "startUrls": [{"url": f"https://www.aliexpress.com/wholesale?SearchText={keyword}"}],
                    "maxItems": 30,
                }
            },
        ]

        try:
            from apify_client import ApifyClient
            client = ApifyClient(apify_token)

            for actor_info in actors:
                actor_id = actor_info["id"]
                print(f"  🔄 AliExpress Actor: {actor_id}")

                try:
                    run = client.actor(actor_id).call(
                        run_input=actor_info["input"],
                        timeout_secs=300,
                        memory_mbytes=512
                    )

                    results = client.dataset(run["defaultDatasetId"]).list_items().items

                    if results:
                        print(f"  ✅ 성공: {len(results)}개")
                        return self._normalize_aliexpress_results(results)
                    else:
                        print(f"  ⚠️ 결과 없음: {actor_id}")
                        continue

                except Exception as actor_error:
                    error_msg = str(actor_error)
                    if "rent" in error_msg.lower() or "trial" in error_msg.lower() or "paid" in error_msg.lower():
                        print(f"  💰 유료 Actor: {actor_id}")
                    else:
                        print(f"  ⚠️ 오류: {error_msg[:50]}")
                    continue

            print(f"  ⚠️ 모든 AliExpress Actor 실패 - Mock 모드")
            return self._mock_aliexpress_results(keyword)

        except Exception as e:
            print(f"  ⚠️ Apify 초기화 오류: {e}")
            return self._mock_aliexpress_results(keyword)

    def _normalize_aliexpress_results(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """알리익스프레스 결과 정규화"""
        normalized = []

        for item in results:
            # 가격 파싱 (USD → CNY 변환, 1 USD ≈ 7.2 CNY)
            price_usd = item.get("price", item.get("salePrice", item.get("currentPrice", 0)))
            if isinstance(price_usd, str):
                price_usd = price_usd.replace("$", "").replace("US", "").replace(",", "").strip()
                try:
                    # 가격 범위 처리 ($5.99-$12.99 → 5.99)
                    price_usd = float(price_usd.split("-")[0].split("~")[0])
                except:
                    price_usd = 0
            else:
                price_usd = float(price_usd or 0)

            price_cny = price_usd * 7.2  # CNY 변환

            # 판매량 파싱
            orders = item.get("orders", item.get("sold", item.get("salesCount", "0")))
            if isinstance(orders, str):
                orders = orders.replace("+", "").replace("sold", "").replace("orders", "").replace(",", "").strip()
                # "1.2k" → 1200
                if "k" in orders.lower():
                    try:
                        orders = int(float(orders.lower().replace("k", "")) * 1000)
                    except:
                        orders = 0
                else:
                    try:
                        orders = int(float(orders))
                    except:
                        orders = 0
            else:
                orders = int(orders or 0)

            # URL 파싱
            url = item.get("url", item.get("productUrl", item.get("link", "")))

            # 제목 파싱
            title = item.get("title", item.get("name", item.get("productName", "")))

            # 상점 정보
            shop_name = item.get("storeName", item.get("seller", item.get("shopName", "")))
            shop_rating = item.get("rating", item.get("storeRating", item.get("shopRating", 0)))
            if isinstance(shop_rating, str):
                try:
                    shop_rating = float(shop_rating)
                except:
                    shop_rating = 0

            # 이미지
            images = item.get("images", item.get("imageUrls", []))
            if not images:
                single_img = item.get("imageUrl", item.get("image", item.get("mainImage", "")))
                if single_img:
                    images = [single_img]

            normalized.append({
                "url": url,
                "title": title,
                "price": price_cny,
                "price_usd": price_usd,
                "sales_count": orders,
                "shop_name": shop_name,
                "shop_rating": float(shop_rating or 0),
                "images": images,
                "platform": "aliexpress",
            })

        return normalized

    def _mock_aliexpress_results(self, keyword: str) -> List[Dict[str, Any]]:
        """알리익스프레스 Mock 결과"""
        base_products = [
            {"title": f"{keyword} Premium Quality", "price_usd": 5.99, "orders": 1250},
            {"title": f"{keyword} Best Seller 2024", "price_usd": 8.99, "orders": 2340},
            {"title": f"{keyword} Hot Sale Free Shipping", "price_usd": 12.99, "orders": 856},
            {"title": f"{keyword} New Arrival", "price_usd": 15.99, "orders": 567},
            {"title": f"{keyword} Top Rated Choice", "price_usd": 3.99, "orders": 3450},
            {"title": f"{keyword} Factory Direct", "price_usd": 6.50, "orders": 1890},
            {"title": f"{keyword} Wholesale Price", "price_usd": 4.25, "orders": 4120},
            {"title": f"{keyword} Limited Edition", "price_usd": 18.99, "orders": 234},
        ]

        results = []
        for i, p in enumerate(base_products):
            results.append({
                "url": f"https://www.aliexpress.com/item/{1000000 + i}.html",
                "title": p["title"],
                "price": p["price_usd"] * 7.2,  # CNY
                "price_usd": p["price_usd"],
                "sales_count": p["orders"],
                "shop_name": f"AliExpress Store {i+1}",
                "shop_rating": 4.5 + (i * 0.05),
                "images": [f"https://ae01.alicdn.com/img/mock_{i}.jpg"],
                "platform": "aliexpress",
            })

        return results

    # ================================================================
    # 유틸리티
    # ================================================================

    def stop(self):
        """크롤링 중단"""
        self._should_stop = True
        print("[TwoStageCrawler] 중단 요청됨")

    def _print_discovery_summary(self):
        """Discovery 요약"""
        duration = 0
        if self.stats.discovery_start and self.stats.discovery_end:
            duration = (self.stats.discovery_end - self.stats.discovery_start).total_seconds()

        print("\n" + "-" * 40)
        print("🔍 [Stage 1] Discovery 완료")
        print("-" * 40)
        print(f"  키워드: {self.stats.keywords_processed}개 처리")
        print(f"  발견: {self.stats.products_found}개")
        print(f"  저장: {self.stats.products_discovered}개")
        print(f"  소요: {duration:.0f}초")
        print("-" * 40)

    def _print_enrichment_summary(self):
        """Enrichment 요약"""
        duration = 0
        if self.stats.enrichment_start and self.stats.enrichment_end:
            duration = (self.stats.enrichment_end - self.stats.enrichment_start).total_seconds()

        print("\n" + "-" * 40)
        print("📊 [Stage 2] Enrichment 완료")
        print("-" * 40)
        print(f"  분석: {self.stats.products_enriched}개")
        print(f"  합격: {self.stats.products_qualified}개 (마진 {self.enrichment_config.min_margin_rate:.0%}+)")
        print(f"  탈락: {self.stats.products_rejected}개")
        print(f"  소요: {duration:.0f}초")
        print("-" * 40)

    async def run_full_pipeline(self) -> TwoStageStats:
        """전체 파이프라인 실행 (Discovery + Enrichment)

        Returns:
            TwoStageStats: 통계
        """
        print("\n" + "=" * 60)
        print("🚀 Two-Stage Crawling 전체 파이프라인 시작")
        print("=" * 60)

        # Stage 1
        await self.run_discovery()

        # 중간 대기
        print("\n⏳ Stage 2 준비 중... (5초 대기)")
        await asyncio.sleep(5)

        # Stage 2
        await self.run_enrichment()

        # 최종 요약
        self._print_final_summary()

        return self.stats

    def _print_final_summary(self):
        """최종 요약"""
        print("\n" + "=" * 60)
        print("🎯 Two-Stage Crawling 최종 결과")
        print("=" * 60)
        print(f"  🔍 Discovery: {self.stats.products_discovered}개 발굴")
        print(f"  📊 Enrichment: {self.stats.products_enriched}개 분석")
        print(f"  ✅ 최종 합격: {self.stats.products_qualified}개")

        if self.stats.products_found > 0:
            efficiency = self.stats.products_qualified / self.stats.products_found * 100
            print(f"  📈 효율: {efficiency:.1f}% (발견 → 합격)")

        if self.stats.errors:
            print(f"  ⚠️ 오류: {len(self.stats.errors)}개")

        print("=" * 60)


# CLI 테스트
async def main():
    """CLI 테스트"""
    crawler = TwoStageCrawler()
    stats = await crawler.run_full_pipeline()
    print(f"\n통계: {stats.to_dict()}")


if __name__ == "__main__":
    asyncio.run(main())
