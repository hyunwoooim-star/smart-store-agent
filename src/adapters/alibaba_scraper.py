"""
alibaba_scraper.py - 1688 상품 정보 추출기 (Apify API 버전)

Phase 3.5 Pivot: Playwright → Apify SaaS 전환
- WSL 브라우저 이슈 영구 해결
- Anti-bot 우회는 Apify가 처리
- 로컬 리소스 0% 사용

환경변수:
- APIFY_API_TOKEN: Apify 계정의 Personal API Token
- APIFY_ACTOR_ID: (선택) 사용할 Actor ID

Apify 가입: https://console.apify.com/sign-up
API Token: Settings > Integrations > Personal API tokens
"""

import asyncio
import os
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ScrapedProduct:
    """1688에서 추출한 상품 정보 (Raw Data)"""
    url: str
    name: str                           # 상품명 (중국어)
    price_cny: float                    # 가격 (위안)
    image_url: Optional[str] = None     # 대표 이미지
    weight_kg: Optional[float] = None   # 무게 (kg)
    length_cm: Optional[float] = None   # 가로
    width_cm: Optional[float] = None    # 세로
    height_cm: Optional[float] = None   # 높이
    moq: int = 1                        # 최소 주문량
    raw_specs: Optional[Dict[str, str]] = None  # 원본 스펙 테이블


class AlibabaScraper:
    """Apify Actor를 활용한 1688 스크래퍼

    브라우저 없이 Apify 클라우드에서 스크래핑.
    WSL 환경에서도 3초 내 응답.

    Example:
        scraper = AlibabaScraper()
        product = await scraper.scrape("https://detail.1688.com/offer/xxx.html")
        print(product.price_cny, product.weight_kg)
    """

    # 기본 Actor ID (1688 전용 스크래퍼들)
    # 실제 사용 시 Apify Store에서 검색하여 적합한 Actor 선택
    DEFAULT_ACTORS = [
        "ecomscrape/1688-product-details-page-scraper",
        "songd/1688-search-scraper",
        "nice_dev/1688-product-scraper",
    ]

    def __init__(self, api_token: Optional[str] = None, actor_id: Optional[str] = None):
        """
        Args:
            api_token: Apify API 토큰 (없으면 환경변수에서 로드)
            actor_id: 사용할 Actor ID (없으면 환경변수 또는 기본값)
        """
        self.api_token = api_token or os.getenv("APIFY_API_TOKEN")
        if not self.api_token:
            raise ValueError(
                "APIFY_API_TOKEN이 필요합니다.\n"
                "1. https://console.apify.com/sign-up 가입\n"
                "2. Settings > Integrations에서 API Token 복사\n"
                "3. .env 파일에 APIFY_API_TOKEN=apify_api_xxx 추가"
            )

        self.actor_id = actor_id or os.getenv("APIFY_ACTOR_ID", self.DEFAULT_ACTORS[0])
        self._client = None

    def _get_client(self):
        """Apify 클라이언트 (lazy loading)"""
        if self._client is None:
            try:
                from apify_client import ApifyClient
                self._client = ApifyClient(self.api_token)
            except ImportError:
                raise ImportError(
                    "apify-client 패키지가 필요합니다.\n"
                    "설치: pip install apify-client"
                )
        return self._client

    async def scrape(self, url: str) -> ScrapedProduct:
        """1688 상품 페이지에서 정보 추출

        Args:
            url: 1688 상품 상세페이지 URL

        Returns:
            ScrapedProduct: 추출된 상품 정보
        """
        print(f"🚀 [Apify] 스크래핑 시작: {url}")
        print(f"📦 Actor: {self.actor_id}")

        try:
            client = self._get_client()

            # Actor 입력 설정 (Actor마다 다를 수 있음)
            run_input = self._build_input(url)

            # Apify는 동기 라이브러리 → 비동기 래핑
            run = await asyncio.to_thread(
                client.actor(self.actor_id).call,
                run_input=run_input,
                timeout_secs=60,  # 최대 60초 대기
            )

            # 결과 데이터셋 가져오기
            dataset = await asyncio.to_thread(
                client.dataset(run["defaultDatasetId"]).list_items
            )
            items = dataset.items

            if not items:
                print("⚠️ [Apify] 반환 데이터 없음")
                return ScrapedProduct(
                    url=url,
                    name="데이터 없음: Actor 반환값 비어있음",
                    price_cny=0.0,
                )

            raw_data = items[0]  # 첫 번째 결과 사용
            print(f"✅ [Apify] 데이터 수신 완료")

            # 데이터 매핑
            return self._parse_result(url, raw_data)

        except Exception as e:
            print(f"❌ [Apify] 에러: {str(e)}")
            return ScrapedProduct(
                url=url,
                name=f"스크래핑 실패: {str(e)}",
                price_cny=0.0,
            )

    def _build_input(self, url: str) -> Dict[str, Any]:
        """Actor 입력 구성 (Actor마다 필드명이 다를 수 있음)"""
        # 일반적인 필드명들을 모두 포함
        return {
            "url": url,
            "urls": [url],
            "productUrl": url,
            "startUrls": [{"url": url}],
            "maxItems": 1,
        }

    def _parse_result(self, url: str, data: Dict[str, Any]) -> ScrapedProduct:
        """Apify JSON 결과를 도메인 모델로 변환

        [비즈니스 로직]
        1. 가격 범위 → 최대값 선택 (방어적 계산)
        2. 무게/사이즈 없으면 None (임의 생성 금지)
        3. 상품명 중국어 그대로
        """
        # 1. 상품명 (여러 필드명 시도)
        name = (
            data.get("subject") or
            data.get("title") or
            data.get("name") or
            data.get("productName") or
            data.get("product_name") or
            "Unknown Product"
        )

        # 2. 가격 파싱 (범위 → 최대값)
        raw_price = (
            data.get("price") or
            data.get("currentPrice") or
            data.get("priceRange") or
            data.get("unitPrice") or
            "0"
        )
        price_cny = self._extract_max_price(raw_price)

        # 3. 이미지 URL
        image_url = self._extract_image(data)

        # 4. 스펙 정보 (무게, 사이즈)
        raw_specs = self._extract_specs(data)
        weight_kg = self._parse_weight(data, raw_specs)
        dimensions = self._parse_dimensions(data, raw_specs)

        # 5. MOQ
        moq = self._extract_moq(data)

        return ScrapedProduct(
            url=url,
            name=name,
            price_cny=price_cny,
            image_url=image_url,
            weight_kg=weight_kg,
            length_cm=dimensions.get("length"),
            width_cm=dimensions.get("width"),
            height_cm=dimensions.get("height"),
            moq=moq,
            raw_specs=raw_specs,
        )

    def _extract_max_price(self, price_val: Any) -> float:
        """가격 값에서 최대값 추출 (방어적 계산)

        Examples:
            "10.00" → 10.0
            "10.00-20.00" → 20.0
            "¥10~¥20" → 20.0
            {"min": 10, "max": 20} → 20.0
        """
        if not price_val:
            return 0.0

        # dict 형태 (일부 Actor)
        if isinstance(price_val, dict):
            return float(price_val.get("max") or price_val.get("min") or 0)

        # 숫자 형태
        if isinstance(price_val, (int, float)):
            return float(price_val)

        # 문자열 파싱
        price_str = str(price_val)

        # 범위 패턴: "10-20", "10~20", "10 - 20"
        range_match = re.search(r'([\d.]+)\s*[-~]\s*([\d.]+)', price_str)
        if range_match:
            prices = [float(range_match.group(1)), float(range_match.group(2))]
            return max(prices)

        # 단일 숫자 추출
        nums = re.findall(r'[\d.]+', price_str)
        if nums:
            return max(float(n) for n in nums)

        return 0.0

    def _extract_image(self, data: Dict[str, Any]) -> Optional[str]:
        """대표 이미지 URL 추출"""
        # 단일 이미지 필드
        for key in ["mainImage", "image", "imageUrl", "img", "picture"]:
            if data.get(key):
                return data[key]

        # 이미지 배열
        images = data.get("images") or data.get("imageList") or data.get("pics") or []
        if images and isinstance(images, list) and len(images) > 0:
            return images[0] if isinstance(images[0], str) else images[0].get("url")

        return None

    def _extract_specs(self, data: Dict[str, Any]) -> Dict[str, str]:
        """스펙 테이블 추출"""
        specs = {}

        # dict 형태
        attrs = data.get("attributes") or data.get("specs") or data.get("properties") or {}
        if isinstance(attrs, dict):
            specs.update(attrs)
        elif isinstance(attrs, list):
            for item in attrs:
                if isinstance(item, dict):
                    key = item.get("name") or item.get("key") or item.get("attrName")
                    val = item.get("value") or item.get("attrValue")
                    if key and val:
                        specs[key] = str(val)

        return specs

    def _parse_weight(self, data: Dict[str, Any], specs: Dict[str, str]) -> Optional[float]:
        """무게 추출 (kg 단위 변환)"""
        # 1. 최상위 필드
        for key in ["weight", "grossWeight", "netWeight"]:
            if key in data:
                return self._convert_weight(data[key])

        # 2. 스펙 내 검색
        weight_keywords = ["重量", "weight", "净重", "毛重", "包装重量"]
        for spec_key, spec_val in specs.items():
            if any(kw in spec_key.lower() for kw in weight_keywords):
                return self._convert_weight(spec_val)

        return None

    def _convert_weight(self, val: Any) -> Optional[float]:
        """무게 값을 kg로 변환"""
        if not val:
            return None

        if isinstance(val, (int, float)):
            # 100 이상이면 g으로 간주
            return val / 1000 if val >= 100 else val

        val_str = str(val).lower()
        nums = re.findall(r'[\d.]+', val_str)
        if not nums:
            return None

        num = float(nums[0])

        # 단위 감지
        if 'g' in val_str and 'kg' not in val_str:
            return num / 1000
        return num

    def _parse_dimensions(self, data: Dict[str, Any], specs: Dict[str, str]) -> Dict[str, Optional[float]]:
        """치수 추출 (cm 단위)"""
        result = {"length": None, "width": None, "height": None}

        # 1. 최상위 필드
        for dim, keys in [
            ("length", ["length", "packingLength"]),
            ("width", ["width", "packingWidth"]),
            ("height", ["height", "packingHeight"]),
        ]:
            for key in keys:
                if key in data and data[key]:
                    result[dim] = self._convert_dimension(data[key])
                    break

        # 2. 스펙에서 "80*20*15cm" 같은 패턴 찾기
        if not any(result.values()):
            size_keywords = ["尺寸", "规格", "包装尺寸", "size", "dimension"]
            for spec_key, spec_val in specs.items():
                if any(kw in spec_key.lower() for kw in size_keywords):
                    dims = self._parse_dimension_string(spec_val)
                    if dims:
                        result.update(dims)
                        break

        return result

    def _convert_dimension(self, val: Any) -> Optional[float]:
        """치수 값을 cm로 변환"""
        if not val:
            return None

        if isinstance(val, (int, float)):
            return float(val)

        val_str = str(val).lower()
        nums = re.findall(r'[\d.]+', val_str)
        if not nums:
            return None

        num = float(nums[0])

        # mm → cm 변환
        if 'mm' in val_str:
            return num / 10
        return num

    def _parse_dimension_string(self, val: str) -> Optional[Dict[str, float]]:
        """'80*20*15cm' 같은 문자열 파싱"""
        # 패턴: 숫자*숫자*숫자
        match = re.search(r'([\d.]+)\s*[*xX×]\s*([\d.]+)\s*[*xX×]\s*([\d.]+)', val)
        if match:
            return {
                "length": float(match.group(1)),
                "width": float(match.group(2)),
                "height": float(match.group(3)),
            }
        return None

    def _extract_moq(self, data: Dict[str, Any]) -> int:
        """최소 주문 수량 추출"""
        for key in ["moq", "minOrder", "minOrderQuantity", "起批量"]:
            if key in data:
                try:
                    return int(data[key])
                except (ValueError, TypeError):
                    pass
        return 1

    def to_domain_product(self, scraped: ScrapedProduct, category: str = "기타") -> "Product":
        """ScrapedProduct를 도메인 모델 Product로 변환

        Args:
            scraped: 1688에서 추출한 Raw 데이터
            category: 상품 카테고리 (관세율 결정용)

        Returns:
            Product: 마진 계산에 사용할 도메인 모델
        """
        from ..domain.models import Product

        return Product(
            name=scraped.name,
            price_cny=scraped.price_cny,
            weight_kg=scraped.weight_kg or 1.0,  # 없으면 1kg 가정
            length_cm=scraped.length_cm or 30,    # 없으면 30cm 가정
            width_cm=scraped.width_cm or 20,
            height_cm=scraped.height_cm or 10,
            category=category,
            moq=scraped.moq,
        )


class MockAlibabaScraper:
    """테스트용 Mock 스크래퍼 (API 키 없이 테스트)"""

    async def scrape(self, url: str) -> ScrapedProduct:
        """가짜 데이터 반환"""
        await asyncio.sleep(0.5)  # 네트워크 지연 시뮬레이션

        return ScrapedProduct(
            url=url,
            name="超轻便携式折叠椅 户外露营钓鱼椅",
            price_cny=45.0,
            image_url="https://example.com/chair.jpg",
            weight_kg=2.5,
            length_cm=80,
            width_cm=20,
            height_cm=15,
            moq=50,
            raw_specs={
                "材质": "铝合金+牛津布",
                "承重": "150kg",
                "颜色": "黑色/灰色/蓝色",
                "净重": "2.5kg",
                "包装尺寸": "80*20*15cm",
            }
        )

    def to_domain_product(self, scraped: ScrapedProduct, category: str = "캠핑/레저") -> "Product":
        """Mock 데이터를 도메인 모델로 변환"""
        from ..domain.models import Product

        return Product(
            name=scraped.name,
            price_cny=scraped.price_cny,
            weight_kg=scraped.weight_kg or 1.0,
            length_cm=scraped.length_cm or 30,
            width_cm=scraped.width_cm or 20,
            height_cm=scraped.height_cm or 10,
            category=category,
            moq=scraped.moq,
        )


# 간편 사용 함수
async def scrape_1688(url: str, use_mock: bool = False) -> ScrapedProduct:
    """1688 URL에서 상품 정보 추출

    Args:
        url: 1688 상품 URL
        use_mock: True면 테스트용 가짜 데이터 반환

    Returns:
        ScrapedProduct: 추출된 상품 정보
    """
    if use_mock:
        scraper = MockAlibabaScraper()
    else:
        scraper = AlibabaScraper()

    return await scraper.scrape(url)
