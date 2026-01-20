"""
alibaba_scraper.py - 1688 상품 정보 자동 추출기 (Phase 3)

Browser-Use + Gemini를 이용한 AI 기반 스크래핑
- 1688 상품 URL에서 가격, 무게, 사이즈 자동 추출
- 안티봇 우회를 위한 User-Agent 조작
- 로그인 팝업 자동 닫기

주의: Python 3.11+ 필수
"""

import asyncio
import os
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# 환경변수 로드
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
    """1688.com 상품 정보 추출기

    Browser-Use 라이브러리를 사용하여 AI 에이전트가
    웹페이지를 탐색하고 정보를 추출합니다.

    Example:
        scraper = AlibabaScraper()
        product = await scraper.scrape("https://detail.1688.com/offer/xxx.html")
        print(product.price_cny, product.weight_kg)
    """

    def __init__(self, api_key: Optional[str] = None, headless: bool = True):
        """
        Args:
            api_key: Gemini API 키 (없으면 환경변수에서 로드)
            headless: True면 브라우저 창 안 보임 (백그라운드 실행)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY가 필요합니다. .env 파일을 확인하세요.")

        self.headless = headless
        self._browser = None
        self._agent = None

    async def scrape(self, url: str) -> ScrapedProduct:
        """1688 상품 페이지에서 정보 추출

        Args:
            url: 1688 상품 상세페이지 URL

        Returns:
            ScrapedProduct: 추출된 상품 정보
        """
        try:
            from browser_use import Agent
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError(
                "browser-use와 langchain-google-genai 패키지가 필요합니다.\n"
                "설치: pip install browser-use langchain-google-genai\n"
                "주의: Python 3.11+ 필수"
            )

        # Gemini LLM 설정
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=self.api_key,
            temperature=0.1,  # 정확한 추출을 위해 낮게
        )

        # 추출 지시문 (프롬프트)
        extraction_prompt = f"""
당신은 1688.com 상품 정보 추출 전문가입니다.

[작업]
1. 주어진 URL로 이동하세요: {url}
2. 로그인 팝업이 뜨면 "X" 버튼을 눌러 닫으세요. 로그인하지 마세요.
3. 다음 정보를 찾아서 JSON 형식으로 반환하세요:

[추출할 정보]
- product_name: 상품명 (중국어 그대로)
- price_cny: 가격 (위안, 숫자만. 범위면 최저가)
- image_url: 대표 이미지 URL
- moq: 최소 주문량 (기본 1)
- weight_kg: 무게 (kg 단위로 변환. 없으면 null)
- length_cm: 포장 가로 (cm. 없으면 null)
- width_cm: 포장 세로 (cm. 없으면 null)
- height_cm: 포장 높이 (cm. 없으면 null)
- raw_specs: 스펙 테이블 전체 (key-value 딕셔너리)

[힌트]
- 무게는 "重量", "净重", "毛重" 등으로 표시됨
- 사이즈는 "尺寸", "包装尺寸", "规格" 등으로 표시됨
- 스펙 테이블은 상품 설명 아래쪽에 있음
- 단위 변환: g → kg (÷1000), mm → cm (÷10)

[출력 형식]
반드시 아래 JSON 형식으로만 응답하세요:
```json
{{
    "product_name": "...",
    "price_cny": 45.0,
    "image_url": "...",
    "moq": 50,
    "weight_kg": 2.5,
    "length_cm": 80,
    "width_cm": 20,
    "height_cm": 15,
    "raw_specs": {{"key": "value", ...}}
}}
```
"""

        # Browser-Use 에이전트 실행
        agent = Agent(
            task=extraction_prompt,
            llm=llm,
            browser_config={
                "headless": self.headless,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            }
        )

        try:
            result = await agent.run()
            return self._parse_result(url, result)
        except Exception as e:
            # 실패 시 기본값 반환
            return ScrapedProduct(
                url=url,
                name=f"추출 실패: {str(e)}",
                price_cny=0.0,
            )

    def _parse_result(self, url: str, result: Any) -> ScrapedProduct:
        """에이전트 결과를 ScrapedProduct로 변환"""
        import json

        # 결과에서 JSON 추출
        result_str = str(result)
        json_match = re.search(r'```json\s*(.*?)\s*```', result_str, re.DOTALL)

        if json_match:
            try:
                data = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                data = {}
        else:
            # JSON 블록 없이 바로 반환된 경우
            try:
                data = json.loads(result_str)
            except json.JSONDecodeError:
                data = {}

        return ScrapedProduct(
            url=url,
            name=data.get("product_name", "Unknown"),
            price_cny=float(data.get("price_cny", 0)),
            image_url=data.get("image_url"),
            weight_kg=data.get("weight_kg"),
            length_cm=data.get("length_cm"),
            width_cm=data.get("width_cm"),
            height_cm=data.get("height_cm"),
            moq=int(data.get("moq", 1)),
            raw_specs=data.get("raw_specs"),
        )

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
