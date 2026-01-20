# Smart Store Agent v3.3 - Phase 3 개발 보고서

**작성일**: 2026-01-21
**작성자**: Claude Code (Opus 4.5)
**대상**: Gemini AI 코드 리뷰어
**GitHub**: https://github.com/hyunwoooim-star/smart-store-agent

---

## 1. 프로젝트 개요

### 1.1 목표
"1688 URL만 던지면 마진 계산 끝나는" AI 자동화 시스템 구축

### 1.2 전략: 창과 방패
```
1단계: 창 (유료 플랫폼) → 키워드/아이템 발굴 (판다랭크, 아이템스카우트)
2단계: 발품 (1688) → 후보 URL 수집
3단계: 방패 (우리 프로젝트) → 수익성/리스크 검증 ← 핵심!
4단계: 실행 → 2-Track 전략으로 판매
```

### 1.3 사용자 상황
- 알리페이/중국 은행 계좌 **없음** → 구매대행 필수
- 개인 사용 목적 (SaaS 아님)
- "방어형" 전략: 좋은 상품 찾기보다 **나쁜 상품 걸러내기**

---

## 2. Phase 3에서 구현한 내용

### 2.1 Browser-Use 기반 1688 스크래퍼

**파일**: `src/adapters/alibaba_scraper.py`

```python
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
    """1688.com 상품 정보 추출기"""

    def __init__(self, api_key: Optional[str] = None, headless: bool = True):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY가 필요합니다.")
        self.headless = headless

    async def scrape(self, url: str) -> ScrapedProduct:
        """1688 상품 페이지에서 정보 추출"""
        from browser_use import Agent
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=self.api_key,
            temperature=0.1,
        )

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
- 단위 변환: g → kg (÷1000), mm → cm (÷10)

[출력 형식]
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

        result = await agent.run()
        return self._parse_result(url, result)

    def to_domain_product(self, scraped: ScrapedProduct, category: str = "기타"):
        """ScrapedProduct → 도메인 모델 Product 변환"""
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
```

### 2.2 테스트 스크립트

**파일**: `test_browser.py`

```python
#!/usr/bin/env python3
"""
test_browser.py - 1688 스크래퍼 테스트 스크립트

사용법:
    python test_browser.py --mock                      # Mock 테스트
    python test_browser.py --url "https://..."         # 실제 URL 테스트
    python test_browser.py --url "https://..." --show  # 브라우저 창 보기
"""

import asyncio
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

async def test_mock_scraper():
    """Mock 스크래퍼 테스트"""
    from src.adapters.alibaba_scraper import scrape_1688
    from src.domain.logic import LandedCostCalculator
    from src.domain.models import MarketType

    # 1. Mock 데이터 추출
    scraped = await scrape_1688("https://detail.1688.com/offer/mock.html", use_mock=True)

    # 2. 마진 계산
    calculator = LandedCostCalculator()
    result = calculator.calculate(
        product=mock_scraper.to_domain_product(scraped, category="캠핑/레저"),
        target_price=45000,
        market=MarketType.NAVER,
        shipping_method="항공",
        include_ad_cost=True,
    )

    # 3. 결과 출력
    console.print(Panel(result.recommendation, title="🤖 AI 판정"))
```

### 2.3 Mock 테스트 결과

```
╭────────────────────────╮
│ Smart Store Agent v3.3 │
│ 1688 스크래퍼 테스트   │
╰────────────────────────╯

🧪 Mock 스크래퍼 테스트 시작

📦 URL: https://detail.1688.com/offer/mock-test.html
             🇨🇳 1688 추출 결과
┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 항목   ┃ 값                              ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 상품명 │ 超轻便携式折叠椅 户外露营钓鱼椅 │
│ 가격   │ ¥45.0                           │
│ 무게   │ 2.5 kg                          │
│ 사이즈 │ 80 x 20 x 15 cm                 │
│ MOQ    │ 50개                            │
│ 이미지 │ https://example.com/chair.jpg   │
└────────┴─────────────────────────────────┘

📋 원본 스펙 테이블:
  - 材质: 铝合金+牛津布
  - 承重: 150kg
  - 颜色: 黑色/灰色/蓝色
  - 净重: 2.5kg
  - 包装尺寸: 80*20*15cm

💰 마진 계산 테스트

       📊 마진 분석 결과
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ 항목            ┃ 값        ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ 목표 판매가     │ 45,000원  │
│ 총 비용         │ 66,932원  │
│ 예상 수익       │ -21,932원 │
│ 마진율          │ 🔴 -48.7% │
│ 손익분기점      │ 73,000원  │
│ 30% 마진 달성가 │ 117,000원 │
└─────────────────┴───────────┘
╭───────────────────────────────── 🤖 AI 판정 ─────────────────────────────────╮
│ 🔴 진입 금지! 예상 마진 -48.7%로 수익 불가. 최소 73,000원 이상 필요          │
╰──────────────────────────────────────────────────────────────────────────────╯

✅ Mock 테스트 완료!
```

---

## 3. 환경 설정 상세

### 3.1 Python 3.11 설치 (WSL)

```bash
# deadsnakes PPA 추가
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

# Python 3.11 설치
sudo apt install python3.11 python3.11-venv python3.11-dev

# 버전 확인
python3.11 --version  # Python 3.11.14
```

### 3.2 가상환경 생성 (Linux 경로 필수!)

```bash
# 중요: Windows 파일시스템(/mnt/c/)이 아닌 Linux 홈에 생성
cd ~
mkdir -p smart-venv
python3.11 -m venv ~/smart-venv/.venv

# 활성화
source ~/smart-venv/.venv/bin/activate

# 패키지 설치
pip install --upgrade pip
pip install browser-use langchain-google-genai playwright rich python-dotenv
```

### 3.3 Playwright 브라우저 설치

```bash
# Playwright 1.44.0 설치 (최신 버전은 WSL에서 node 호환 문제 있음)
pip install playwright==1.44.0

# Chromium 설치
playwright install chromium

# 브라우저 종속성 설치
sudo apt-get install libnss3 libnspr4 libasound2
```

### 3.4 requirements.txt 업데이트

```txt
# Browser Automation - AI 브라우저 제어 (Phase 3)
playwright>=1.40.0    # 브라우저 엔진
browser-use>=0.1.0    # AI 브라우저 자동화 (Python 3.11+ 필수)
langchain-google-genai>=2.0.0  # Gemini + LangChain 연동
```

---

## 4. 기존 v3.3 핵심 로직 (복습)

### 4.1 LandedCostCalculator 비용 계산 흐름

```python
# src/domain/logic.py

def calculate(self, product, target_price, market, shipping_method, include_ad_cost):
    cfg = self.config

    # 1. 상품 원가
    product_cost = int(product.price_cny * cfg.exchange_rate)  # 195원/위안

    # 2. 중국 내 비용 (구매대행 필수)
    china_shipping = cfg.china_domestic_shipping  # 3,000원
    china_total = product_cost + china_shipping
    agency_fee = int(china_total * cfg.agency_fee_rate)  # 10%

    # 3. 무게 계산 (부피무게 vs 실무게)
    volume_weight = (L * W * H) / 6000
    billable_weight = max(actual_weight, volume_weight)

    # 4. 해외 배송비
    if shipping_method == "항공":
        shipping = billable_weight * 8000  # kg당
    else:
        cbm = (L * W * H) / 1,000,000
        shipping = max(cbm * 75000, 6000)  # CBM당, 최소 6000원

    # 5. 관부가세 (간이통관 20%)
    taxable = china_total + shipping
    tariff_and_vat = taxable * 0.20

    # 6. 마켓 수수료
    platform_fee = target_price * market_fee_rate  # 네이버 5.5%, 쿠팡 10.8%

    # 7. 숨겨진 비용 (강제)
    return_allowance = target_price * 0.05  # 반품 충당금
    ad_cost = target_price * 0.10           # 광고비
    packaging = 500                          # 포장비

    # 8. 총 비용 및 마진 계산
    total_cost = sum([product_cost, china_shipping, agency_fee, ...])
    profit = target_price - total_cost
    margin_percent = profit / target_price * 100
```

### 4.2 위험도 판정 기준

| 마진율 | 레벨 | 판정 |
|--------|------|------|
| 30% 이상 | 🟢 SAFE | 진입 추천 |
| 15~30% | 🟡 WARNING | 주의 필요 |
| 15% 미만 | 🔴 DANGER | 진입 금지 |

### 4.3 마켓별 수수료

```python
MARKET_FEES = {
    "naver": MarketConfig("네이버 스마트스토어", 0.055),   # 5.5%
    "coupang": MarketConfig("쿠팡", 0.108),               # 10.8%
    "amazon": MarketConfig("아마존", 0.15),               # 15%
}
```

---

## 5. 파일 구조

```
smart/
├── src/
│   ├── core/
│   │   ├── config.py          # AppConfig (환율, 수수료, 관세율 등)
│   │   └── __init__.py
│   ├── domain/
│   │   ├── models.py          # Product, CostResult, CostBreakdown
│   │   ├── logic.py           # LandedCostCalculator
│   │   └── __init__.py
│   ├── adapters/
│   │   ├── alibaba_scraper.py # 🆕 Phase 3: 1688 스크래퍼
│   │   └── __init__.py
│   └── ui/
│       └── app.py             # Streamlit 대시보드
├── test_browser.py            # 🆕 Phase 3: 테스트 스크립트
├── requirements.txt           # 🔄 browser-use 추가
├── .env.example
└── docs/
    └── GEMINI_REPORT_PHASE3.md  # 🆕 이 보고서
```

---

## 6. Gemini에게 질문/검토 요청

### 6.1 Browser-Use 프롬프트 개선

현재 프롬프트:
```
당신은 1688.com 상품 정보 추출 전문가입니다.
1. 주어진 URL로 이동하세요
2. 로그인 팝업이 뜨면 "X" 버튼을 눌러 닫으세요
3. 다음 정보를 찾아서 JSON 형식으로 반환하세요...
```

**질문**:
- 1688 페이지 구조가 다양한데, 스펙 테이블을 못 찾는 경우 fallback 로직이 필요할까요?
- 로그인 팝업 외에 다른 방해 요소(광고, 쿠폰 팝업 등)도 처리해야 할까요?
- 가격이 "¥25.00 - ¥35.00" 범위로 표시될 때 최저가를 쓰는 게 맞을까요?

### 6.2 부피무게 계산 정확성

현재 로직:
```python
volume_weight = (length * width * height) / 6000  # 항공 표준
billable_weight = max(actual_weight, volume_weight)
```

**질문**:
- 6000 divisor가 모든 배대지에서 동일한가요? 배대지마다 다를 수 있나요?
- 해운 CBM 계산(75,000원/m³)이 현실적인 가격인가요?

### 6.3 관부가세 계산

현재 로직:
```python
simple_tariff_rate = 0.20  # 간이통관 관부가세 약 20%
tariff = tariff_and_vat * 0.4  # 관세 40%
vat = tariff_and_vat * 0.6     # 부가세 60%
```

**질문**:
- 간이통관(목록통관) 기준 150달러 이하에서 이 계산이 맞나요?
- 카테고리별 관세율(의류 13%, 캠핑 8%)은 어디서 적용되어야 하나요?

### 6.4 구매대행 수수료

현재 로직:
```python
agency_fee_rate = 0.10  # 10%
china_domestic_shipping = 3000  # 중국 내 배송비
```

**질문**:
- 구매대행 수수료 10%가 업계 평균인가요? (5%~15% 범위로 알고 있음)
- 중국 내 배송비 3,000원이 적절한가요?

### 6.5 안티봇 대응

**질문**:
- 1688이 봇 탐지를 강화하면 어떤 대응책이 있을까요?
- Playwright의 stealth mode나 fingerprint 조작이 필요할까요?
- 너무 빠른 요청 시 rate limiting이 필요할까요?

---

## 7. 다음 단계 (Phase 3.5)

### 7.1 실제 1688 URL 테스트
- .env에 GEMINI_API_KEY 설정
- 실제 1688 상품 URL로 테스트
- 추출 성공률 측정

### 7.2 Streamlit 대시보드 통합
- URL 입력 필드 추가
- "자동 분석" 버튼으로 1688 → 마진 계산 원클릭

### 7.3 배치 처리
- 여러 URL 한 번에 분석
- 결과를 엑셀로 내보내기

---

## 8. 실행 방법 요약

```bash
# 1. WSL 터미널 열기
wsl

# 2. 가상환경 활성화
source ~/smart-venv/.venv/bin/activate

# 3. 프로젝트 폴더로 이동
cd /mnt/c/Users/임현우/Desktop/현우\ 작업폴더/smart

# 4. Mock 테스트 (API 키 없이)
python test_browser.py --mock

# 5. 실제 테스트 (API 키 필요)
# 먼저 .env 파일에 GEMINI_API_KEY=your_key 추가
python test_browser.py --url "https://detail.1688.com/offer/xxx.html"

# 6. 브라우저 창 보면서 테스트
python test_browser.py --url "..." --show
```

---

## 9. 첨부: 핵심 설정값

```python
# src/core/config.py - AppConfig

exchange_rate = 195              # 원/위안
vat_rate = 0.10                  # 부가세 10%
simple_tariff_rate = 0.20        # 간이통관 관부가세 20%

agency_fee_rate = 0.10           # 구매대행 수수료 10%
china_domestic_shipping = 3000   # 중국 내 배송비

shipping_rate_air = 8000         # 항공 kg당
cbm_rate = 75000                 # 해운 CBM당
min_shipping_fee = 6000          # 최소 해운비
domestic_shipping = 3500         # 국내 택배비

volume_weight_divisor = 6000     # 부피무게 계수

return_allowance_rate = 0.05     # 반품 충당금 5%
ad_cost_rate = 0.10              # 광고비 10%
packaging_cost = 500             # 포장비

danger_margin = 0.15             # 15% 미만 = 위험
warning_margin = 0.30            # 30% 미만 = 주의
```

---

**보고서 끝**

*이 보고서를 Gemini에게 전달하여 코드 리뷰 및 개선점을 받아주세요.*
