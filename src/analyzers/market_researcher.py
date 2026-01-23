"""
market_researcher.py - 원클릭 소싱 분석 시스템 (Phase 10.5)

Gemini CTO 승인: "킬러 피처. 무조건 GO"

기능:
1. Google Lens API로 이미지 역검색 → 동일/유사 상품 찾기
2. 네이버 쇼핑 검색 → 경쟁사 가격대 파악
3. 목표가 자동 추천 (시장가 기반)

사용법:
    researcher = MarketResearcher()
    result = researcher.research_by_image(image_path)
    print(result.recommended_price)
    print(result.competitors)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import os
import json
import re
import requests
from urllib.parse import quote


@dataclass
class CompetitorProduct:
    """경쟁사 상품 정보"""
    title: str                          # 상품명
    price: int                          # 가격 (원)
    url: str                            # 상품 링크
    source: str                         # 출처 (네이버쇼핑, 쿠팡 등)
    review_count: int = 0               # 리뷰 수
    rating: float = 0.0                 # 평점
    thumbnail: str = ""                 # 썸네일 이미지


@dataclass
class MarketResearchResult:
    """시장 조사 결과"""
    query: str                          # 검색 키워드
    competitors: List[CompetitorProduct]  # 경쟁 상품 목록
    price_range: Tuple[int, int]        # 가격 범위 (최저, 최고)
    average_price: int                  # 평균 가격
    recommended_price: int              # 추천 목표가
    price_strategy: str                 # 가격 전략 설명
    search_method: str                  # 검색 방법 (image/text)
    raw_response: Dict = field(default_factory=dict)  # 원본 응답 (디버깅용)


class MarketResearcher:
    """시장 조사 클래스"""

    # 네이버 쇼핑 API 엔드포인트
    NAVER_SHOPPING_URL = "https://openapi.naver.com/v1/search/shop.json"

    # SerpApi Google Lens 엔드포인트
    SERPAPI_LENS_URL = "https://serpapi.com/search"

    def __init__(
        self,
        naver_client_id: Optional[str] = None,
        naver_client_secret: Optional[str] = None,
        serpapi_key: Optional[str] = None
    ):
        """
        Args:
            naver_client_id: 네이버 API 클라이언트 ID
            naver_client_secret: 네이버 API 클라이언트 시크릿
            serpapi_key: SerpApi API 키
        """
        self.naver_client_id = naver_client_id or os.getenv("NAVER_CLIENT_ID")
        self.naver_client_secret = naver_client_secret or os.getenv("NAVER_CLIENT_SECRET")
        self.serpapi_key = serpapi_key or os.getenv("SERPAPI_KEY")

    def research_by_text(
        self,
        keyword: str,
        max_results: int = 10
    ) -> MarketResearchResult:
        """텍스트 키워드로 시장 조사

        Args:
            keyword: 검색 키워드
            max_results: 최대 결과 수

        Returns:
            MarketResearchResult: 시장 조사 결과
        """
        competitors = self._search_naver_shopping(keyword, max_results)
        return self._build_result(keyword, competitors, "text")

    def research_by_image(
        self,
        image_url: str,
        max_results: int = 10
    ) -> MarketResearchResult:
        """이미지 URL로 시장 조사 (Google Lens)

        Args:
            image_url: 이미지 URL
            max_results: 최대 결과 수

        Returns:
            MarketResearchResult: 시장 조사 결과
        """
        # 1. Google Lens로 유사 상품 검색
        lens_results = self._search_google_lens(image_url)

        if not lens_results:
            # Lens 결과 없으면 빈 결과 반환
            return MarketResearchResult(
                query=image_url,
                competitors=[],
                price_range=(0, 0),
                average_price=0,
                recommended_price=0,
                price_strategy="이미지 검색 결과 없음. 키워드 검색을 시도해주세요.",
                search_method="image",
                raw_response={}
            )

        # 2. Lens에서 추출한 키워드로 네이버 쇼핑 검색
        search_keyword = self._extract_keyword_from_lens(lens_results)
        competitors = self._search_naver_shopping(search_keyword, max_results)

        # 3. Lens 결과도 경쟁사 목록에 추가
        competitors.extend(self._convert_lens_to_competitors(lens_results))

        return self._build_result(search_keyword, competitors, "image")

    def _search_naver_shopping(
        self,
        keyword: str,
        max_results: int = 10
    ) -> List[CompetitorProduct]:
        """네이버 쇼핑 API 검색

        Args:
            keyword: 검색 키워드
            max_results: 최대 결과 수

        Returns:
            List[CompetitorProduct]: 경쟁사 상품 목록
        """
        if not self.naver_client_id or not self.naver_client_secret:
            return self._mock_naver_results(keyword)

        try:
            headers = {
                "X-Naver-Client-Id": self.naver_client_id,
                "X-Naver-Client-Secret": self.naver_client_secret
            }

            params = {
                "query": keyword,
                "display": max_results,
                "sort": "sim"  # 정확도순
            }

            response = requests.get(
                self.NAVER_SHOPPING_URL,
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            items = data.get("items", [])

            return [
                CompetitorProduct(
                    title=self._clean_html(item.get("title", "")),
                    price=int(item.get("lprice", 0)),
                    url=item.get("link", ""),
                    source="네이버쇼핑",
                    thumbnail=item.get("image", "")
                )
                for item in items
            ]

        except Exception as e:
            print(f"[MarketResearcher] 네이버 API 오류: {e}")
            return self._mock_naver_results(keyword)

    def _search_google_lens(self, image_url: str) -> Dict:
        """Google Lens API로 이미지 검색

        Args:
            image_url: 이미지 URL

        Returns:
            Dict: Google Lens 검색 결과
        """
        if not self.serpapi_key:
            return self._mock_lens_results(image_url)

        try:
            params = {
                "engine": "google_lens",
                "url": image_url,
                "api_key": self.serpapi_key,
                "hl": "ko",  # 한국어 결과
                "country": "kr"  # 한국 결과 우선
            }

            response = requests.get(
                self.SERPAPI_LENS_URL,
                params=params,
                timeout=30
            )
            response.raise_for_status()

            return response.json()

        except Exception as e:
            print(f"[MarketResearcher] SerpApi 오류: {e}")
            return self._mock_lens_results(image_url)

    def _extract_keyword_from_lens(self, lens_results: Dict) -> str:
        """Google Lens 결과에서 검색 키워드 추출

        Args:
            lens_results: Google Lens 응답

        Returns:
            str: 추출된 키워드
        """
        # visual_matches에서 타이틀 추출
        visual_matches = lens_results.get("visual_matches", [])
        if visual_matches:
            # 첫 번째 결과의 타이틀 사용
            first_match = visual_matches[0]
            title = first_match.get("title", "")
            # 한글/영문 키워드만 추출 (특수문자 제거)
            keyword = re.sub(r'[^\w\s가-힣]', '', title)
            return keyword.strip()[:50]  # 최대 50자

        # knowledge_graph에서 추출 시도
        knowledge = lens_results.get("knowledge_graph", {})
        if knowledge:
            return knowledge.get("title", "상품")

        return "상품"

    def _convert_lens_to_competitors(
        self,
        lens_results: Dict
    ) -> List[CompetitorProduct]:
        """Google Lens 결과를 경쟁사 상품 형식으로 변환

        Args:
            lens_results: Google Lens 응답

        Returns:
            List[CompetitorProduct]: 경쟁사 상품 목록
        """
        competitors = []

        # shopping_results가 있으면 사용 (가격 정보 포함)
        shopping = lens_results.get("shopping_results", [])
        for item in shopping[:5]:  # 최대 5개
            price_str = item.get("price", "0")
            price = self._parse_price(price_str)

            competitors.append(CompetitorProduct(
                title=item.get("title", ""),
                price=price,
                url=item.get("link", ""),
                source=item.get("source", "Google Lens"),
                thumbnail=item.get("thumbnail", "")
            ))

        # visual_matches도 추가
        visual = lens_results.get("visual_matches", [])
        for item in visual[:3]:  # 최대 3개
            price_str = item.get("price", {}).get("value", "0")
            price = self._parse_price(str(price_str))

            competitors.append(CompetitorProduct(
                title=item.get("title", ""),
                price=price,
                url=item.get("link", ""),
                source=item.get("source", "Google Lens"),
                thumbnail=item.get("thumbnail", "")
            ))

        return competitors

    def _build_result(
        self,
        query: str,
        competitors: List[CompetitorProduct],
        search_method: str
    ) -> MarketResearchResult:
        """시장 조사 결과 객체 생성

        Args:
            query: 검색 쿼리
            competitors: 경쟁사 목록
            search_method: 검색 방법

        Returns:
            MarketResearchResult: 결과 객체
        """
        # 가격이 있는 상품만 필터링
        priced_competitors = [c for c in competitors if c.price > 0]

        if not priced_competitors:
            return MarketResearchResult(
                query=query,
                competitors=competitors,
                price_range=(0, 0),
                average_price=0,
                recommended_price=0,
                price_strategy="가격 정보가 있는 경쟁 상품을 찾지 못했습니다.",
                search_method=search_method
            )

        # 가격 통계 계산
        prices = [c.price for c in priced_competitors]
        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) // len(prices)

        # 목표가 추천: 평균가의 90% (가격 경쟁력 확보)
        # 단, 최저가보다는 높게
        recommended = max(int(avg_price * 0.9), min_price)

        # 가격 전략 설명
        strategy = self._generate_price_strategy(
            min_price, max_price, avg_price, recommended, len(priced_competitors)
        )

        return MarketResearchResult(
            query=query,
            competitors=priced_competitors,
            price_range=(min_price, max_price),
            average_price=avg_price,
            recommended_price=recommended,
            price_strategy=strategy,
            search_method=search_method
        )

    def _generate_price_strategy(
        self,
        min_price: int,
        max_price: int,
        avg_price: int,
        recommended: int,
        count: int
    ) -> str:
        """가격 전략 설명 생성

        Args:
            min_price: 최저가
            max_price: 최고가
            avg_price: 평균가
            recommended: 추천가
            count: 경쟁사 수

        Returns:
            str: 가격 전략 설명
        """
        lines = []
        lines.append(f"경쟁사 {count}개 분석 완료")
        lines.append(f"- 최저가: {min_price:,}원")
        lines.append(f"- 최고가: {max_price:,}원")
        lines.append(f"- 평균가: {avg_price:,}원")
        lines.append("")
        lines.append(f"추천 목표가: {recommended:,}원")
        lines.append(f"(평균가 대비 {100 - int(recommended/avg_price*100)}% 저렴)")
        lines.append("")

        # 진입 가능성 판단
        if max_price - min_price > avg_price * 0.5:
            lines.append("시장 가격 분산이 큼 → 차별화 가격 전략 가능")
        else:
            lines.append("시장 가격 수렴 → 가격 경쟁 치열, 품질/서비스 차별화 필요")

        return "\n".join(lines)

    def _parse_price(self, price_str: str) -> int:
        """가격 문자열을 숫자로 변환

        Args:
            price_str: 가격 문자열 (예: "₩45,000", "$45", "45000원")

        Returns:
            int: 가격 (원화)
        """
        if not price_str:
            return 0

        # 숫자만 추출
        numbers = re.findall(r'[\d,]+', str(price_str))
        if not numbers:
            return 0

        # 첫 번째 숫자 사용
        price = int(numbers[0].replace(',', ''))

        # USD인 경우 환율 적용 (대략 1300원)
        if '$' in str(price_str) or 'USD' in str(price_str).upper():
            price = int(price * 1300)

        # CNY인 경우 환율 적용 (대략 190원)
        if '¥' in str(price_str) or 'CNY' in str(price_str).upper():
            price = int(price * 190)

        return price

    def _clean_html(self, text: str) -> str:
        """HTML 태그 제거

        Args:
            text: HTML 포함 텍스트

        Returns:
            str: 클린 텍스트
        """
        return re.sub(r'<[^>]+>', '', text)

    # ========================================
    # Mock 함수들 (API 키 없을 때 테스트용)
    # ========================================

    def _mock_naver_results(self, keyword: str) -> List[CompetitorProduct]:
        """네이버 쇼핑 Mock 결과"""
        return [
            CompetitorProduct(
                title=f"{keyword} 인기상품 A",
                price=38500,
                url="https://smartstore.naver.com/example/1",
                source="네이버쇼핑 (Mock)",
                review_count=127,
                rating=4.5
            ),
            CompetitorProduct(
                title=f"{keyword} 프리미엄 B",
                price=45000,
                url="https://smartstore.naver.com/example/2",
                source="네이버쇼핑 (Mock)",
                review_count=89,
                rating=4.3
            ),
            CompetitorProduct(
                title=f"{keyword} 가성비 C",
                price=32000,
                url="https://smartstore.naver.com/example/3",
                source="네이버쇼핑 (Mock)",
                review_count=256,
                rating=4.1
            ),
            CompetitorProduct(
                title=f"{keyword} 베스트셀러 D",
                price=42000,
                url="https://smartstore.naver.com/example/4",
                source="네이버쇼핑 (Mock)",
                review_count=512,
                rating=4.7
            ),
            CompetitorProduct(
                title=f"{keyword} 신상품 E",
                price=35900,
                url="https://smartstore.naver.com/example/5",
                source="네이버쇼핑 (Mock)",
                review_count=45,
                rating=4.2
            ),
        ]

    def _mock_lens_results(self, image_url: str) -> Dict:
        """Google Lens Mock 결과"""
        return {
            "visual_matches": [
                {
                    "title": "유아 승용완구 애벌레카",
                    "link": "https://example.com/1",
                    "source": "쿠팡",
                    "price": {"value": "39000", "currency": "KRW"}
                }
            ],
            "shopping_results": [
                {
                    "title": "애벌레 붕붕카 유아 승용완구",
                    "price": "₩38,500",
                    "link": "https://shopping.naver.com/1",
                    "source": "네이버쇼핑"
                },
                {
                    "title": "아기 애벌레 자동차 붕붕카",
                    "price": "₩42,000",
                    "link": "https://shopping.naver.com/2",
                    "source": "11번가"
                }
            ]
        }


class MockMarketResearcher:
    """테스트용 Mock 클래스"""

    def research_by_text(self, keyword: str, max_results: int = 10) -> MarketResearchResult:
        return MarketResearchResult(
            query=keyword,
            competitors=[
                CompetitorProduct(
                    title=f"{keyword} 테스트 상품 1",
                    price=35000,
                    url="https://example.com/1",
                    source="Mock"
                ),
                CompetitorProduct(
                    title=f"{keyword} 테스트 상품 2",
                    price=42000,
                    url="https://example.com/2",
                    source="Mock"
                ),
            ],
            price_range=(35000, 42000),
            average_price=38500,
            recommended_price=34650,
            price_strategy="Mock 데이터 기반 분석",
            search_method="text"
        )

    def research_by_image(self, image_url: str, max_results: int = 10) -> MarketResearchResult:
        return self.research_by_text("테스트 이미지 상품", max_results)


# 팩토리 함수
def create_researcher(use_mock: bool = False) -> MarketResearcher:
    """MarketResearcher 팩토리

    Args:
        use_mock: Mock 모드 여부

    Returns:
        MarketResearcher: 연구자 인스턴스
    """
    if use_mock:
        return MockMarketResearcher()
    return MarketResearcher()


# CLI 테스트
if __name__ == "__main__":
    researcher = MarketResearcher()

    # 텍스트 검색 테스트
    print("=== 텍스트 검색 테스트 ===")
    result = researcher.research_by_text("유아 승용완구 애벌레카")

    print(f"검색어: {result.query}")
    print(f"경쟁사 수: {len(result.competitors)}")
    print(f"가격 범위: {result.price_range[0]:,}원 ~ {result.price_range[1]:,}원")
    print(f"평균가: {result.average_price:,}원")
    print(f"추천 목표가: {result.recommended_price:,}원")
    print(f"\n{result.price_strategy}")
