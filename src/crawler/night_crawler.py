"""
night_crawler.py - 밤샘 소싱 봇 (v4.0)

Gemini CTO 승인 아키텍처:
- 새벽 1시~7시 천천히 크롤링
- 60~180초 랜덤 대기 (안티봇 회피)
- 키워드당 최대 20개 상품
- 마진 30% 이상만 저장

사용법:
    crawler = NightCrawler()
    await crawler.run_nightly_job()
"""

import asyncio
import random
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

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


@dataclass
class CrawlerConfig:
    """크롤러 설정"""
    # 속도 제한 (Gemini CTO 승인: 7분 간격)
    min_delay_seconds: int = 60         # 최소 대기 60초
    max_delay_seconds: int = 180        # 최대 대기 180초

    # 작업량 제한
    max_products_per_keyword: int = 20  # 키워드당 최대 20개
    max_total_candidates: int = 50      # 총 최대 50개
    max_keywords_per_run: int = 5       # 실행당 최대 키워드 5개

    # 마진 기준 (Gemini CTO 승인: 30%)
    min_margin_rate: float = 0.30       # 최소 마진율

    # Mock 모드 (Apify 미설정 시)
    use_mock: bool = True               # Mock 모드 사용


class NightCrawler:
    """밤샘 소싱 봇"""

    def __init__(
        self,
        config: CrawlerConfig = None,
        repository: CandidateRepository = None,
        keyword_manager: KeywordManager = None,
        product_filter: ProductFilter = None,
        market_researcher: MarketResearcher = None,
        margin_calculator: LandedCostCalculator = None
    ):
        self.config = config or CrawlerConfig()
        self.repository = repository or CandidateRepository()
        self.keyword_manager = keyword_manager or KeywordManager(self.repository)
        self.product_filter = product_filter or ProductFilter(FilterConfig(
            min_margin_rate=self.config.min_margin_rate
        ))
        self.market_researcher = market_researcher or MarketResearcher()
        self.margin_calculator = margin_calculator or LandedCostCalculator(AppConfig())

        self.stats = CrawlStats()
        self._should_stop = False

    async def run_nightly_job(self) -> CrawlStats:
        """메인 작업: 밤샘 소싱 실행

        Returns:
            CrawlStats: 크롤링 통계
        """
        print("[NightCrawler] 밤샘 소싱 시작!")
        self.stats = CrawlStats(start_time=datetime.now())
        self._should_stop = False

        try:
            # 1. 크롤링 대상 키워드 가져오기
            keywords = self.keyword_manager.get_keywords_to_crawl(
                max_keywords=self.config.max_keywords_per_run
            )
            self.stats.total_keywords = len(keywords)

            if not keywords:
                print("[NightCrawler] 활성 키워드가 없습니다. 기본 키워드를 추가합니다.")
                keywords = self.keyword_manager.seed_default_keywords()
                self.stats.total_keywords = len(keywords)

            print(f"[NightCrawler] 크롤링 대상 키워드: {len(keywords)}개")

            # 2. 키워드별 크롤링
            for i, keyword in enumerate(keywords, 1):
                if self._should_stop:
                    print("[NightCrawler] 중단 요청됨")
                    break

                if self.stats.saved_candidates >= self.config.max_total_candidates:
                    print(f"[NightCrawler] 최대 후보 수 도달 ({self.config.max_total_candidates}개)")
                    break

                print(f"\n[NightCrawler] [{i}/{len(keywords)}] 키워드: {keyword.keyword}")

                try:
                    await self._process_keyword(keyword)
                    self.stats.crawled_keywords += 1

                    # 키워드 처리 완료 표시
                    self.keyword_manager.mark_crawled(keyword.id)

                except Exception as e:
                    error_msg = f"키워드 '{keyword.keyword}' 처리 실패: {str(e)}"
                    print(f"[NightCrawler] ERROR: {error_msg}")
                    self.stats.errors.append(error_msg)

                # 다음 키워드 전 대기 (마지막 키워드 제외)
                if i < len(keywords) and not self._should_stop:
                    await self._random_delay("키워드 간 대기")

        except Exception as e:
            error_msg = f"크롤링 실패: {str(e)}"
            print(f"[NightCrawler] FATAL ERROR: {error_msg}")
            self.stats.errors.append(error_msg)

        finally:
            self.stats.end_time = datetime.now()
            self._print_summary()

        return self.stats

    async def _process_keyword(self, keyword: SourcingKeyword):
        """키워드 처리: 검색 → 필터링 → 저장

        Args:
            keyword: 소싱 키워드
        """
        # 1. 1688 검색 (현재는 Mock)
        print(f"  [검색] 1688에서 '{keyword.keyword}' 검색 중...")
        search_results = await self._search_1688(keyword.keyword)
        self.stats.total_products_found += len(search_results)
        print(f"  [검색] {len(search_results)}개 상품 발견")

        if not search_results:
            return

        # 2. 1차 필터링 (기본 조건)
        filtered = self.product_filter.apply_basic_filter(search_results)
        print(f"  [필터] 1차 필터 통과: {len(filtered)}개")

        if not filtered:
            return

        # 3. 상세 분석 및 저장 (천천히)
        saved_count = 0
        for j, product_data in enumerate(filtered[:self.config.max_products_per_keyword], 1):
            if self._should_stop:
                break

            if self.stats.saved_candidates >= self.config.max_total_candidates:
                break

            try:
                # 중복 체크
                source_url = product_data.get('url', '')
                if self.repository.check_duplicate(source_url):
                    print(f"    [{j}] 중복 상품 스킵")
                    continue

                # 상세 분석
                candidate = await self._analyze_product(product_data, keyword)

                if candidate:
                    # 저장
                    self.repository.add_candidate(candidate)
                    saved_count += 1
                    self.stats.saved_candidates += 1
                    print(f"    [{j}] 저장 완료: {candidate.title_kr[:30]}... (마진 {candidate.estimated_margin_rate:.0%})")

            except Exception as e:
                print(f"    [{j}] 분석 실패: {str(e)}")

            # 상품 간 대기 (마지막 상품 제외)
            if j < len(filtered) and not self._should_stop:
                await self._random_delay("상품 분석 간 대기", short=True)

        self.stats.filtered_products += saved_count
        print(f"  [완료] {saved_count}개 후보 저장")

    async def _search_1688(self, keyword: str) -> List[Dict[str, Any]]:
        """1688 검색 (Apify 또는 Mock)

        Args:
            keyword: 검색 키워드

        Returns:
            List[Dict]: 검색 결과 리스트
        """
        apify_token = os.getenv("APIFY_API_TOKEN")

        if apify_token and not self.config.use_mock:
            return await self._search_1688_apify(keyword, apify_token)
        else:
            return self._mock_1688_results(keyword)

    async def _search_1688_apify(self, keyword: str, api_token: str) -> List[Dict[str, Any]]:
        """Apify를 통한 1688 검색 (실제 구현)

        Args:
            keyword: 검색 키워드
            api_token: Apify API 토큰

        Returns:
            List[Dict]: 검색 결과
        """
        try:
            from apify_client import ApifyClient

            client = ApifyClient(api_token)

            run = client.actor("ecomscrape/1688-search-scraper").call(
                run_input={
                    "keyword": keyword,
                    "maxItems": 50,
                    "proxyConfiguration": {
                        "useApifyProxy": True,
                        "apifyProxyGroups": ["RESIDENTIAL"]
                    }
                },
                timeout_secs=300,
                memory_mbytes=512
            )

            results = client.dataset(run["defaultDatasetId"]).list_items().items

            # 결과 정규화
            normalized = []
            for item in results:
                normalized.append({
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "price": float(item.get("price", 0) or 0),
                    "sales_count": int(item.get("sales", 0) or 0),
                    "shop_name": item.get("shopName", ""),
                    "shop_rating": float(item.get("shopRating", 0) or 0),
                    "images": item.get("images", []),
                    "min_order": int(item.get("minOrder", 1) or 1),
                })

            return normalized

        except ImportError:
            print("[NightCrawler] apify_client 패키지 없음. Mock 모드로 전환")
            return self._mock_1688_results(keyword)
        except Exception as e:
            print(f"[NightCrawler] Apify 오류: {e}. Mock 모드로 전환")
            return self._mock_1688_results(keyword)

    def _mock_1688_results(self, keyword: str) -> List[Dict[str, Any]]:
        """1688 Mock 검색 결과

        Args:
            keyword: 검색 키워드

        Returns:
            List[Dict]: Mock 검색 결과
        """
        base_products = [
            {
                "title": f"{keyword} 고급형 A타입",
                "price": 35.0,
                "sales_count": 1250,
                "shop_rating": 4.8,
            },
            {
                "title": f"{keyword} 실용적 B타입",
                "price": 28.0,
                "sales_count": 2340,
                "shop_rating": 4.6,
            },
            {
                "title": f"{keyword} 미니멀 C타입",
                "price": 42.0,
                "sales_count": 856,
                "shop_rating": 4.9,
            },
            {
                "title": f"{keyword} 대용량 D타입",
                "price": 55.0,
                "sales_count": 567,
                "shop_rating": 4.5,
            },
            {
                "title": f"{keyword} 가성비 E타입",
                "price": 22.0,
                "sales_count": 3450,
                "shop_rating": 4.3,
            },
            {
                "title": f"{keyword} 프리미엄 F타입",
                "price": 68.0,
                "sales_count": 234,
                "shop_rating": 4.9,
            },
            {
                "title": f"{keyword} 스탠다드 G타입",
                "price": 30.0,
                "sales_count": 1890,
                "shop_rating": 4.7,
            },
            {
                "title": f"{keyword} 신상품 H타입",
                "price": 38.0,
                "sales_count": 120,
                "shop_rating": 4.8,
            },
        ]

        # 결과 정규화
        results = []
        for i, p in enumerate(base_products):
            results.append({
                "url": f"https://detail.1688.com/offer/{1000000 + i}.html",
                "title": p["title"],
                "price": p["price"],
                "sales_count": p["sales_count"],
                "shop_name": f"优质工厂{i+1}",
                "shop_rating": p["shop_rating"],
                "images": [
                    f"https://cbu01.alicdn.com/img/mock_{i}_1.jpg",
                    f"https://cbu01.alicdn.com/img/mock_{i}_2.jpg",
                ],
                "min_order": random.choice([2, 5, 10, 20]),
            })

        return results

    async def _analyze_product(
        self,
        product_data: Dict[str, Any],
        keyword: SourcingKeyword
    ) -> Optional[SourcingCandidate]:
        """상품 상세 분석

        Args:
            product_data: 1688 검색 결과 상품
            keyword: 소싱 키워드

        Returns:
            SourcingCandidate or None: 조건 충족 시 후보 반환
        """
        # 1. 기본 정보 추출
        source_url = product_data.get('url', '')
        source_title = product_data.get('title', '')
        source_price_cny = float(product_data.get('price', 0))
        source_images = product_data.get('images', [])
        shop_name = product_data.get('shop_name', '')
        shop_rating = float(product_data.get('shop_rating', 0))
        sales_count = int(product_data.get('sales_count', 0))

        # 2. 한국어 제목 생성 (간단히 키워드 + 특징)
        title_kr = self._generate_korean_title(source_title, keyword.keyword)

        # 3. 마진 계산
        # 가상의 상품 정보로 마진 계산 (평균적인 크기 가정)
        product = Product(
            name=title_kr,
            price_cny=source_price_cny,
            weight_kg=0.5,  # 기본 0.5kg
            length_cm=30,
            width_cm=20,
            height_cm=15,
            category=keyword.category or "기타",
        )

        # 4. 네이버 경쟁사 분석
        naver_result = self.market_researcher.research_by_text(keyword.keyword, max_results=10)
        naver_min_price = naver_result.price_range[0]
        naver_avg_price = naver_result.average_price
        naver_max_price = naver_result.price_range[1]
        competitor_count = len(naver_result.competitors)

        # 5. 추천 판매가로 마진 계산
        recommended_price = naver_result.recommended_price
        if recommended_price <= 0:
            # 네이버 데이터 없으면 원가의 3배로 가정
            recommended_price = int(source_price_cny * 195 * 3)

        margin_result = self.margin_calculator.calculate(
            product=product,
            target_price=recommended_price,
            market=MarketType.NAVER
        )

        estimated_margin_rate = margin_result.margin_percent / 100
        estimated_cost_krw = margin_result.total_cost
        breakeven_price = margin_result.breakeven_price

        # 6. 리스크 체크
        risk_level, risk_reasons = self.product_filter.apply_risk_filter(source_title)

        # 7. 마진 필터 적용
        if estimated_margin_rate < self.config.min_margin_rate:
            print(f"    마진 부족: {estimated_margin_rate:.0%} < {self.config.min_margin_rate:.0%}")
            return None

        if risk_level == CrawlRiskLevel.DANGER:
            print(f"    리스크 위험: {', '.join(risk_reasons)}")
            return None

        # 8. 후보 생성
        candidate = SourcingCandidate(
            source_url=source_url,
            source_title=source_title,
            source_price_cny=source_price_cny,
            source_images=source_images,
            source_shop_name=shop_name,
            source_shop_rating=shop_rating,
            source_sales_count=sales_count,
            title_kr=title_kr,
            estimated_cost_krw=estimated_cost_krw,
            estimated_margin_rate=estimated_margin_rate,
            recommended_price=recommended_price,
            breakeven_price=breakeven_price,
            risk_level=risk_level,
            risk_reasons=risk_reasons,
            naver_min_price=naver_min_price,
            naver_avg_price=naver_avg_price,
            naver_max_price=naver_max_price,
            competitor_count=competitor_count,
            keyword_id=keyword.id,
            keyword=keyword.keyword,
        )

        return candidate

    def _generate_korean_title(self, chinese_title: str, keyword: str) -> str:
        """중국어 제목을 한국어로 변환 (간단 버전)

        Args:
            chinese_title: 중국어 원본 제목
            keyword: 검색 키워드

        Returns:
            str: 한국어 제목
        """
        # 실제로는 Gemini API로 번역하면 좋지만
        # 지금은 키워드 기반으로 간단히 생성
        suffixes = ["프리미엄", "고급형", "대용량", "미니멀", "실용적", "인기", "베스트"]
        suffix = random.choice(suffixes)

        return f"{keyword} {suffix}"

    async def _random_delay(self, reason: str = "", short: bool = False):
        """랜덤 대기 (안티봇 회피)

        Args:
            reason: 대기 사유 (로그용)
            short: True면 짧은 대기 (10~30초)
        """
        if short:
            delay = random.uniform(10, 30)
        else:
            delay = random.uniform(
                self.config.min_delay_seconds,
                self.config.max_delay_seconds
            )

        if reason:
            print(f"  [{reason}] {delay:.0f}초 대기...")
        await asyncio.sleep(delay)

    def stop(self):
        """크롤링 중단 요청"""
        self._should_stop = True
        print("[NightCrawler] 중단 요청됨. 현재 작업 완료 후 종료합니다.")

    def _print_summary(self):
        """크롤링 결과 요약 출력"""
        print("\n" + "=" * 50)
        print("[NightCrawler] 밤샘 소싱 완료!")
        print("=" * 50)
        print(f"  키워드: {self.stats.crawled_keywords}/{self.stats.total_keywords}개 처리")
        print(f"  발견: {self.stats.total_products_found}개")
        print(f"  저장: {self.stats.saved_candidates}개")
        print(f"  소요 시간: {self.stats.duration_minutes:.1f}분")
        if self.stats.errors:
            print(f"  오류: {len(self.stats.errors)}개")
            for err in self.stats.errors[:3]:
                print(f"    - {err}")
        print("=" * 50)


# CLI 테스트용
async def main():
    """CLI 테스트"""
    crawler = NightCrawler()
    stats = await crawler.run_nightly_job()
    print(f"\n결과: {stats.to_dict()}")


if __name__ == "__main__":
    asyncio.run(main())
