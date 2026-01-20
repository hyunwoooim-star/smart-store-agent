"""
alibaba_scraper.py - 1688 상품 정보 자동 추출기 (Phase 3.5 - Option B)

Playwright + Gemini 하이브리드 방식
- Playwright: 빠른 페이지 로딩 + HTML 추출
- Gemini: 텍스트에서 구조화된 데이터 파싱

이전 browser-use 방식 대비 장점:
- WSL 환경에서도 2-3초 내 로딩
- AI가 브라우저를 조작하지 않아 안정적
- Gemini API 비용 절감 (스크린샷 대신 텍스트)

환경변수: GOOGLE_API_KEY 또는 GEMINI_API_KEY
"""

import asyncio
import json
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
    """1688.com 상품 정보 추출기 (Playwright + Gemini 하이브리드)

    브라우징은 Playwright(기계)가 하고, 독해는 Gemini(AI)가 합니다.

    Example:
        scraper = AlibabaScraper()
        product = await scraper.scrape("https://detail.1688.com/offer/xxx.html")
        print(product.price_cny, product.weight_kg)
    """

    # Stealth User-Agent (봇 탐지 우회)
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, api_key: Optional[str] = None, headless: bool = True):
        """
        Args:
            api_key: Google API 키 (없으면 환경변수에서 로드)
            headless: True면 브라우저 창 안 보임 (백그라운드 실행)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY가 필요합니다. .env 파일을 확인하세요.")

        self.headless = headless
        self._llm = None

    def _get_llm(self):
        """Gemini LLM 인스턴스 (lazy loading)"""
        if self._llm is None:
            from langchain_google_genai import ChatGoogleGenerativeAI
            self._llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",  # 2.0보다 할당량 안정적
                google_api_key=self.api_key,
                temperature=0,  # 정확한 추출을 위해 0
            )
        return self._llm

    async def scrape(self, url: str) -> ScrapedProduct:
        """1688 상품 페이지에서 정보 추출

        Args:
            url: 1688 상품 상세페이지 URL

        Returns:
            ScrapedProduct: 추출된 상품 정보
        """
        try:
            from playwright.async_api import async_playwright
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError(
                "필수 패키지가 없습니다.\n"
                "설치: pip install playwright beautifulsoup4\n"
                "브라우저 설치: playwright install chromium"
            )

        text_content = ""
        image_url = None

        async with async_playwright() as p:
            # 1. 브라우저 실행 (Stealth 모드)
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ]
            )

            context = await browser.new_context(
                user_agent=self.USER_AGENT,
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
            )

            page = await context.new_page()

            # 2. 리소스 차단 (속도 향상) - 이미지/폰트/스타일시트 제외
            await page.route(
                "**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,eot}",
                lambda route: route.abort()
            )

            try:
                # 3. 페이지 이동 (30초 타임아웃)
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")

                # 잠시 대기 (동적 콘텐츠 로딩)
                await asyncio.sleep(2)

                # 4. 로그인 팝업 감지 및 처리
                try:
                    # 일반적인 닫기 버튼 클릭 시도
                    close_btn = page.locator("[class*='close'], [class*='Close'], .baxia-dialog-close")
                    if await close_btn.count() > 0:
                        await close_btn.first.click()
                        await asyncio.sleep(0.5)
                except Exception:
                    pass  # 팝업 없으면 무시

                # 5. 페이지 제목으로 로그인 페이지 감지
                title = await page.title()
                if "登录" in title or "login" in title.lower():
                    raise Exception("로그인 페이지로 리다이렉트됨. VPN이나 쿠키가 필요할 수 있습니다.")

                # 6. HTML 추출
                html_content = await page.content()

                # 7. 대표 이미지 URL 추출 시도
                try:
                    img_element = page.locator("img.detail-gallery-img, img[class*='main-image'], .detail-gallery img").first
                    if await img_element.count() > 0:
                        image_url = await img_element.get_attribute("src")
                except Exception:
                    pass

                # 8. BeautifulSoup으로 텍스트 추출
                soup = BeautifulSoup(html_content, "html.parser")

                # 스크립트/스타일 제거
                for tag in soup(["script", "style", "noscript", "iframe"]):
                    tag.decompose()

                # 주요 영역 텍스트 추출
                text_parts = []

                # 상품 제목
                title_elem = soup.select_one("h1, .d-title, .title-text, [class*='title']")
                if title_elem:
                    text_parts.append(f"[상품명] {title_elem.get_text(strip=True)}")

                # 가격 영역
                price_elem = soup.select_one(".price, [class*='price'], .d-price")
                if price_elem:
                    text_parts.append(f"[가격] {price_elem.get_text(strip=True)}")

                # 속성/스펙 영역
                attr_elems = soup.select(".offer-attr-list, .mod-detail-attributes, [class*='attribute'], [class*='spec']")
                for elem in attr_elems:
                    text_parts.append(f"[속성] {elem.get_text(separator=' | ', strip=True)}")

                # 전체 본문 (fallback)
                body_text = soup.get_text(separator="\n", strip=True)

                # 텍스트 조합 (앞부분 1만자 제한 - 토큰 절약)
                if text_parts:
                    text_content = "\n".join(text_parts) + "\n\n[본문 일부]\n" + body_text[:5000]
                else:
                    text_content = body_text[:10000]

            except Exception as e:
                await browser.close()
                return ScrapedProduct(
                    url=url,
                    name=f"페이지 로딩 실패: {str(e)}",
                    price_cny=0.0,
                )

            await browser.close()

        # 9. Gemini로 텍스트 파싱
        return await self._parse_with_ai(text_content, url, image_url)

    async def _parse_with_ai(self, text: str, url: str, image_url: Optional[str] = None) -> ScrapedProduct:
        """Gemini를 사용하여 텍스트에서 상품 정보 추출"""

        prompt = f"""당신은 1688.com 상품 데이터 추출 전문가입니다.
아래 텍스트는 1688 상품 페이지에서 추출한 내용입니다.

[중요 규칙]
1. 가격(price_cny): 범위가 있으면 **최대값** 선택 (예: ¥25-35 → 35)
2. 무게(weight_kg): "重量", "净重", "毛重" 키워드 찾기. g단위면 kg로 변환(÷1000)
3. 사이즈: "尺寸", "包装尺寸", "规格" 키워드 찾기. mm단위면 cm로 변환(÷10)
4. 정보 없음: 찾을 수 없으면 null (임의 생성 금지!)
5. MOQ: "起批", "最小起订" 등에서 찾기. 없으면 1

[추출할 정보]
- product_name: 상품명 (중국어 그대로)
- price_cny: 가격 (숫자만, 범위면 최대값)
- moq: 최소 주문량
- weight_kg: 무게 (kg)
- length_cm: 포장 가로 (cm)
- width_cm: 포장 세로 (cm)
- height_cm: 포장 높이 (cm)
- raw_specs: 기타 스펙 (dict)

[페이지 텍스트]
{text}

[출력 형식]
JSON만 출력하세요 (설명 없이):
```json
{{
    "product_name": "...",
    "price_cny": 45.0,
    "moq": 50,
    "weight_kg": 2.5,
    "length_cm": 80,
    "width_cm": 20,
    "height_cm": 15,
    "raw_specs": {{"키": "값"}}
}}
```"""

        try:
            llm = self._get_llm()
            response = await asyncio.to_thread(llm.invoke, prompt)
            result_text = response.content

            # JSON 추출
            json_match = re.search(r'```json\s*(.*?)\s*```', result_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                # JSON 블록 없이 바로 반환된 경우
                data = json.loads(result_text)

            return ScrapedProduct(
                url=url,
                name=data.get("product_name", "Unknown"),
                price_cny=float(data.get("price_cny", 0)),
                image_url=image_url or data.get("image_url"),
                weight_kg=data.get("weight_kg"),
                length_cm=data.get("length_cm"),
                width_cm=data.get("width_cm"),
                height_cm=data.get("height_cm"),
                moq=int(data.get("moq", 1)),
                raw_specs=data.get("raw_specs"),
            )

        except Exception as e:
            return ScrapedProduct(
                url=url,
                name=f"AI 파싱 실패: {str(e)}",
                price_cny=0.0,
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
