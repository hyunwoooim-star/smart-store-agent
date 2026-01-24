# Smart Store Agent - 전체 프로젝트 분석 보고서

**작성일**: 2026-01-24
**버전**: v4.2.0
**목적**: Gemini Deep Research 분석용

---

# Part 1: 프로젝트 개요

## 1.1 비전
"밤새 일하는 AI, 아침에 결재하는 사장님"

1인 스마트스토어 운영자를 위한 AI 기반 소싱-등록 자동화 시스템

## 1.2 핵심 가치
- **시간 절약**: 키워드 발굴 → 소싱 검증 → 등록까지 자동화
- **리스크 관리**: 마진 계산, 금지어 검사, 경쟁사 분석
- **의사결정 지원**: GO/NO-GO 판정으로 빠른 결정

## 1.3 기술 스택
| 영역 | 기술 |
|------|------|
| 언어 | Python 3.11+ |
| AI | Gemini 1.5 Flash (분석), Claude Code (개발) |
| UI | Streamlit v4.2 (Toss+Naver 스타일) |
| 차트 | Plotly (게이지, 도넛) |
| 크롤링 | Apify API (1688) |
| DB | 로컬 JSON (Supabase 예정) |

---

# Part 2: 아키텍처

## 2.1 폴더 구조
```
smart/
├── src/
│   ├── core/              # 핵심 설정
│   │   └── config.py      # AppConfig (환율, 수수료 등)
│   │
│   ├── domain/            # 도메인 모델 (DDD)
│   │   ├── models.py      # Product, CostResult, RiskLevel
│   │   ├── logic.py       # LandedCostCalculator (마진 계산)
│   │   └── crawler_models.py  # SourcingCandidate, CrawlStats
│   │
│   ├── analyzers/         # AI 분석 모듈
│   │   ├── market_researcher.py   # 네이버 시장조사
│   │   ├── gemini_analyzer.py     # Gemini 리뷰 분석
│   │   ├── review_analyzer.py     # 고급 리뷰 분석 (v3.5.2)
│   │   ├── keyword_filter.py      # 부정 키워드 필터
│   │   └── preflight_check.py     # 금지어 검사
│   │
│   ├── crawler/           # Night Crawler (야간 소싱봇)
│   │   ├── night_crawler.py       # 메인 크롤러
│   │   ├── repository.py          # JSON 저장소
│   │   ├── keyword_manager.py     # 키워드 스케줄링
│   │   └── product_filter.py      # 3단계 필터링
│   │
│   ├── publisher/         # 네이버 등록
│   │   ├── naver_excel_exporter.py  # 대량등록 엑셀
│   │   ├── naver_uploader.py        # API 업로더 (Mock)
│   │   └── content_generator.py     # PAS 상세페이지
│   │
│   └── ui/                # Streamlit UI
│       ├── app.py         # 메인 앱 (v4.2)
│       ├── styles.py      # Toss+Naver CSS
│       └── tabs/
│           ├── morning_tab.py    # 모닝 브리핑
│           ├── sourcing_tab.py   # 소싱 분석 (통합)
│           ├── review_tab.py     # 리뷰 분석
│           └── settings_tab.py   # 설정
│
├── tests/                 # 테스트
├── config/                # 설정 파일
└── docs/                  # 문서
```

## 2.2 데이터 흐름
```
[키워드 등록]
     ↓
[Night Crawler] ─── 1688 검색 (Apify) ───→ [상품 목록]
     ↓
[3단계 필터링]
  ├─ 1차: 가격/평점/판매량
  ├─ 2차: 마진율 30% 이상
  └─ 3차: 리스크 (브랜드/KC인증)
     ↓
[SourcingCandidate] ─── 저장 ───→ [repository.json]
     ↓
[모닝 브리핑] ─── 승인/반려 ───→ [APPROVED 상태]
     ↓
[NaverExcelExporter] ─── 엑셀 생성 ───→ [네이버 대량등록]
```

---

# Part 3: 핵심 모듈 상세

## 3.1 마진 계산기 (LandedCostCalculator)

### 설정 (AppConfig)
```python
@dataclass
class AppConfig:
    exchange_rate: float = 195        # 원/위안
    volume_weight_divisor: int = 5000 # 부피무게 계수
    vat_rate: float = 0.10            # 부가세 10%

    # 마켓별 수수료
    naver_fee_rate: float = 0.055     # 5.5%
    coupang_fee_rate: float = 0.108   # 10.8%

    # 배송비
    air_shipping_rate: int = 8000     # 항공 kg당
    sea_shipping_rate: int = 3000     # 해운 kg당
    domestic_shipping: int = 3500     # 국내 택배

    # 숨겨진 비용
    return_allowance_rate: float = 0.05  # 반품 충당 5%
    ad_cost_rate: float = 0.10           # 광고비 10%
    packaging_cost: int = 500            # 포장비
```

### 비용 계산 공식
```python
# 1. 상품 원가
product_cost = price_cny * exchange_rate

# 2. 청구 무게 (실무게 vs 부피무게 중 큰 값)
volume_weight = (L × W × H) / 5000
chargeable_weight = max(actual_weight, volume_weight)

# 3. 관부가세 (간이통관 기준)
customs_base = product_cost + china_shipping + international_shipping
tariff = customs_base * tariff_rate[category]  # 8~13%
vat = (customs_base + tariff) * 0.10

# 4. 총 비용
total_cost = (
    product_cost +
    china_shipping +
    agency_fee +
    tariff +
    vat +
    international_shipping +
    domestic_shipping +
    platform_fee +
    ad_cost +
    return_allowance +
    packaging
)

# 5. 마진 계산
profit = target_price - total_cost
margin_percent = (profit / target_price) * 100
```

### 관세율 테이블
```python
TARIFF_RATES = {
    "가구/인테리어": 0.08,
    "캠핑/레저": 0.08,
    "의류/패션": 0.13,
    "전자기기": 0.08,
    "생활용품": 0.08,
    "기타": 0.10,
}
```

## 3.2 Night Crawler (야간 소싱봇)

### 설정
```python
@dataclass
class CrawlerConfig:
    min_delay_seconds: int = 60      # 안티봇 딜레이
    max_delay_seconds: int = 180
    max_products_per_keyword: int = 20
    max_total_candidates: int = 50
    min_margin_rate: float = 0.30    # 30% 이상만 저장
    use_mock: bool = True            # Mock/Apify 전환
```

### 3단계 필터링
```python
# 1차 필터 (기본)
FilterConfig(
    min_price_cny=5.0,
    max_price_cny=500.0,
    min_sales_count=10,
    min_shop_rating=4.0
)

# 2차 필터 (마진)
if margin_rate < 0.30:
    reject("마진 부족")

# 3차 필터 (리스크)
BRAND_KEYWORDS = ["nike", "adidas", "gucci", "apple", "samsung", ...]
KC_KEYWORDS = ["전자", "충전기", "유아", "장난감"]
BANNED_KEYWORDS = ["식품", "화장품", "담배", "무기"]
```

### 1688 검색 (Apify)
```python
async def _search_1688_apify(self, keyword: str):
    client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

    run = client.actor("songd/1688-search-scraper").call({
        "searches": [{"keyword": keyword}],
        "maxPagesPerSearch": 1,
        "proxySettings": {"useApifyProxy": True}
    })

    items = client.dataset(run["defaultDatasetId"]).iterate_items()
    return [self._normalize_item(item) for item in items]
```

## 3.3 시장 조사 (MarketResearcher)

### 네이버 쇼핑 API
```python
class MarketResearcher:
    def research_by_text(self, keyword: str, max_results: int = 10):
        # 네이버 검색 API 호출
        url = "https://openapi.naver.com/v1/search/shop.json"
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
        }
        params = {"query": keyword, "display": max_results}

        response = requests.get(url, headers=headers, params=params)
        items = response.json()["items"]

        # 가격 분석
        prices = [item["lprice"] for item in items]
        return MarketResearchResult(
            competitors=items,
            price_range=(min(prices), max(prices)),
            average_price=sum(prices) / len(prices),
            recommended_price=int(sum(prices) / len(prices) * 0.9)
        )
```

## 3.4 리뷰 분석 (Gemini)

### 마스터 시스템 프롬프트
```python
SYSTEM_PROMPT = """
당신은 '10년 차 베테랑 MD'이자 '깐깐한 품질 관리자'입니다.
당신의 목표는 "사장님의 돈을 지키는 것"입니다.

[분석 원칙]
1. 비판적 사고: 판매자 상세페이지는 모두 "광고"로 가정
2. 보수적 마진: 배송비/관세/반품비는 최악의 상황 가정
3. 근거 중심: "좋아 보입니다" 금지, 숫자로 말하기

[출력 규칙]
- JSON만 출력 (마크다운/잡담 금지)
- 코드블록(```) 사용 금지
"""
```

### 카테고리별 분석 포인트
```python
CATEGORY_CONTEXT = {
    "의류": "핏, 마감, 세탁 후 변형, 사이즈 정확도",
    "가구": "조립 난이도, 냄새, 흔들림, 내구성",
    "전자기기": "발열, 배터리, 오작동, 소음",
    "캠핑/레저": "내구성, 무게, 방수, 조립 편의성",
    "생활용품": "소재 품질, 냄새, 실용성",
}
```

## 3.5 Pre-Flight 체크 (금지어 검사)

### 금지어 카테고리
```python
VIOLATION_TYPES = {
    "TRADEMARK": ["나이키", "아디다스", "애플", ...],
    "EXAGGERATION": ["최고", "1위", "100%", "완벽", ...],
    "MEDICAL_CLAIM": ["치료", "효능", "암예방", ...],
    "ILLEGAL": ["짝퉁", "레플리카", "이미테이션", ...],
}
```

---

# Part 4: UI/UX (v4.2)

## 4.1 4탭 구조
```
┌─────────────────────────────────────────────────────────┐
│  🌅 모닝 브리핑 │ 🔍 소싱 분석 │ 💬 리뷰 분석 │ ⚙️ 설정  │
└─────────────────────────────────────────────────────────┘
```

### 모닝 브리핑 탭
- 밤새 수집된 후보 상품 검토
- 틴더 스타일 승인/반려
- 일괄 승인 (마진 35%+)
- 엑셀 다운로드

### 소싱 분석 탭 (통합)
- Step 1: 상품 정보 입력
- Step 2: 시장 조사 (네이버)
- Step 3: 마진 분석 (게이지 차트)
- Step 4: Pre-Flight 체크
- Step 5: GO/NO-GO 판정

### 리뷰 분석 탭
- 네이버 리뷰 크롤링
- Gemini 불만 패턴 분석
- 개선 포인트 추출

### 설정 탭
- 환율 설정
- 비용 설정 (배송비, 수수료)
- 키워드 관리

## 4.2 디자인 시스템

### 색상 팔레트
```python
COLORS = {
    "primary": "#03C75A",       # Naver Green
    "primary_light": "#E8F5E9",
    "primary_dark": "#1B5E20",
    "success": "#4CAF50",
    "warning": "#FFC107",
    "danger": "#F44336",
    "bg_light": "#F5F6F8",      # Toss Gray
    "text_main": "#191F28",
    "text_sub": "#8B95A1",
}
```

### 그림자 (Toss 스타일)
```css
box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
```

### 커스텀 컴포넌트
- `render_verdict_card()` - GO/NO-GO 판정 카드
- `render_margin_gauge()` - Plotly 마진 게이지
- `render_cost_donut()` - Plotly 비용 도넛
- `render_product_card()` - 상품 카드

---

# Part 5: 현재 상태 및 한계점

## 5.1 완료된 기능
| 기능 | 상태 | 비고 |
|------|------|------|
| 마진 계산기 | ✅ 완료 | v3.3 LandedCostCalculator |
| 시장 조사 | ✅ 완료 | 네이버 API 연동 |
| Pre-Flight 체크 | ✅ 완료 | 금지어 검사 |
| Night Crawler | ✅ 완료 | Mock/Apify 전환 가능 |
| Streamlit UI | ✅ 완료 | v4.2 Toss+Naver 스타일 |
| 엑셀 내보내기 | ✅ 완료 | 대량등록 포맷 |

## 5.2 현재 한계점

### 크롤러
- 1688 상세페이지 스크래핑 미구현 (무게/크기 추정)
- 한국어 제목 자동 번역 미구현 (현재 수동)
- Supabase 연동 미완료 (로컬 JSON 사용)

### 마진 계산
- 실시간 환율 미적용 (고정 195원)
- 배대지별 요금 테이블 미구현
- HS코드 기반 관세율 미구현

### 리뷰 분석
- 네이버 리뷰 크롤링 불안정
- Gemini API 할당량 제한

### 네이버 등록
- API 자동등록 Mock 상태
- 카테고리 자동 매핑 미구현

## 5.3 기술 부채
```python
# gemini_analyzer.py - 패키지 지원 종료 경고
FutureWarning: All support for `google.generativeai` has ended.
# → google.genai로 마이그레이션 필요
```

---

# Part 6: 테스트 결과 (2026-01-24)

## 6.1 티슈 박스 케이스 테스트

### 상품 정보
- 1688 URL: https://detail.1688.com/offer/...
- 가격: ¥15.00
- 카테고리: 생활용품 (PU 가죽)

### 첫 번째 분석 (키워드: "티슈 케이스")
```
시장 평균가: ₩19,678
총 비용: ₩22,501
마진율: -13.1%
판정: 🔴 NO-GO
```

### 두 번째 분석 (키워드: "가죽 티슈케이스")
```
시장 평균가: ₩38,680
총 비용: ₩22,501
마진율: +41.8%
판정: 🟢 GO
```

### 실제 경쟁사 (MOME 스토어)
```
판매가: ₩46,500
예상 마진율: 51.6%
```

### 교훈
**키워드 선정이 수익성을 결정한다**
- 같은 상품도 "일반 키워드" vs "프리미엄 키워드"로 시장이 다름
- 포지셔닝 전략이 중요

---

# Part 7: Gemini CTO에게 질문

## 7.1 기술적 질문

1. **Apify vs 자체 크롤러**
   - Apify 비용 대비 자체 Playwright 크롤러 구축이 나을까요?
   - WSL 환경에서 Playwright 안정성 이슈가 있었습니다.

2. **Supabase vs 로컬 JSON**
   - 1인 사용자 기준, Supabase 연동이 필요할까요?
   - 로컬 JSON으로 충분하다면 언제 마이그레이션해야 할까요?

3. **google.generativeai → google.genai 마이그레이션**
   - 긴급도가 어느 정도인가요?
   - 마이그레이션 시 주의사항?

## 7.2 비즈니스 질문

1. **SaaS 상품화 가능성**
   - 현재 기능으로 다른 스마트스토어 운영자에게 판매 가능할까요?
   - 필요한 추가 기능은?

2. **경쟁 우위**
   - 판다랭크, 셀러마스터 등 기존 도구 대비 차별점은?
   - 어떤 점을 강화해야 할까요?

3. **수익 모델**
   - 구독 vs 건당 과금 vs 프리미엄 기능?
   - 적정 가격대는?

## 7.3 로드맵 질문

1. **우선순위**
   - 다음 중 뭘 먼저 해야 할까요?
     - A: 실시간 환율 API 연동
     - B: 1688 상세페이지 크롤링 (무게/크기)
     - C: 네이버 API 자동 등록
     - D: 리뷰 분석 고도화

2. **Phase 3: Browser-Use**
   - Gemini Vision + Browser-Use 자동화가 실용적일까요?
   - 투자 대비 효과는?

3. **AI 모델 선택**
   - Gemini Flash vs Pro vs Claude?
   - 비용 대비 성능 최적점은?

---

# Part 8: 코드 스니펫

## 8.1 마진 계산 핵심 로직
```python
# src/domain/logic.py - LandedCostCalculator.calculate()

def calculate(
    self,
    product: Product,
    target_price: int,
    market: MarketType = MarketType.NAVER,
    shipping_method: str = "항공",
    include_ad_cost: bool = True
) -> CostResult:
    # 1. 상품 원가 (원화)
    product_cost = int(product.price_cny * self.config.exchange_rate)

    # 2. 부피무게 계산
    volume_weight = (
        product.length_cm * product.width_cm * product.height_cm
    ) / self.config.volume_weight_divisor

    # 3. 청구무게 (실무게 vs 부피무게 중 큰 값)
    chargeable_weight = max(product.weight_kg, volume_weight)

    # 4. 배송비
    if shipping_method == "항공":
        shipping_international = int(chargeable_weight * self.config.air_shipping_rate)
    else:
        shipping_international = int(chargeable_weight * self.config.sea_shipping_rate)

    # 5. 관부가세
    customs_base = product_cost + self.config.china_domestic_shipping + shipping_international
    tariff_rate = self.config.tariff_rates.get(product.category, 0.10)
    tariff = int(customs_base * tariff_rate)
    vat = int((customs_base + tariff) * self.config.vat_rate)

    # 6. 플랫폼 수수료
    market_fee_rate = MARKET_FEES.get(market.value, 0.055)
    platform_fee = int(target_price * market_fee_rate)

    # 7. 숨겨진 비용
    ad_cost = int(target_price * self.config.ad_cost_rate) if include_ad_cost else 0
    return_allowance = int(target_price * self.config.return_allowance_rate)

    # 8. 총 비용
    total_cost = (
        product_cost +
        self.config.china_domestic_shipping +
        int(product_cost * self.config.agency_fee_rate) +
        tariff +
        vat +
        shipping_international +
        self.config.domestic_shipping +
        platform_fee +
        ad_cost +
        return_allowance +
        self.config.packaging_cost
    )

    # 9. 수익 및 마진
    profit = target_price - total_cost
    margin_percent = round((profit / target_price) * 100, 1) if target_price > 0 else 0

    # 10. 리스크 레벨
    if margin_percent >= 35:
        risk_level = RiskLevel.SAFE
    elif margin_percent >= 20:
        risk_level = RiskLevel.WARNING
    else:
        risk_level = RiskLevel.DANGER

    return CostResult(
        total_cost=total_cost,
        breakdown=breakdown,
        profit=profit,
        margin_percent=margin_percent,
        risk_level=risk_level,
        ...
    )
```

## 8.2 Night Crawler 메인 루프
```python
# src/crawler/night_crawler.py - run_nightly_job()

async def run_nightly_job(self) -> CrawlStats:
    stats = CrawlStats()

    # 1. 크롤링 대상 키워드 선택
    keywords = self.keyword_manager.get_keywords_to_crawl(max_keywords=5)

    if not keywords:
        self.keyword_manager.seed_default_keywords()
        keywords = self.keyword_manager.get_keywords_to_crawl()

    # 2. 키워드별 크롤링
    for keyword in keywords:
        if stats.candidates_found >= self.config.max_total_candidates:
            break

        # 1688 검색
        products = await self._search_1688(keyword.keyword)

        # 1차 필터링
        filtered = self.product_filter.apply_basic_filter(products)

        # 상품별 분석
        for product in filtered[:self.config.max_products_per_keyword]:
            # 중복 체크
            if self.repo.check_duplicate(product["url"]):
                continue

            # 마진 분석
            candidate = await self._analyze_product(product, keyword)

            if candidate and candidate.estimated_margin_rate >= self.config.min_margin_rate:
                self.repo.add_candidate(candidate)
                stats.candidates_found += 1

        # 키워드 크롤링 완료 표시
        self.keyword_manager.mark_crawled(keyword.id)

        # 안티봇 딜레이
        await asyncio.sleep(random.uniform(
            self.config.min_delay_seconds,
            self.config.max_delay_seconds
        ))

    return stats
```

## 8.3 Streamlit 소싱 탭
```python
# src/ui/tabs/sourcing_tab.py - render()

def render():
    st.header("🔍 소싱 분석")

    # Step 1: 상품 정보 입력
    product_name = st.text_input("상품명")
    price_cny = st.number_input("1688 도매가 (위안)", value=35.0)
    weight_kg = st.number_input("실제 무게 (kg)", value=1.0)
    # ... 박스 사이즈, MOQ, 배송방법

    if st.button("🚀 전체 분석 시작"):
        # Step 2: 시장 조사
        market_result = _run_market_research(product_name)

        # Step 3: 마진 분석
        product = Product(name=product_name, price_cny=price_cny, ...)
        margin_result = calculator.calculate(product, target_price, ...)

        # Step 4: Pre-Flight 체크
        preflight_result = checker.check_product(product_name, "")

        # Step 5: 결과 표시
        render_verdict_card(verdict, reason, status)
        render_margin_gauge(margin_result.margin_percent)
        render_cost_donut(breakdown, total_cost)
```

---

# Part 9: 환경 설정

## 9.1 필수 환경변수
```bash
# .env 파일
GEMINI_API_KEY=xxx           # Gemini 분석용
NAVER_CLIENT_ID=xxx          # 네이버 검색 API
NAVER_CLIENT_SECRET=xxx
APIFY_API_TOKEN=xxx          # 1688 크롤링 (선택)
```

## 9.2 의존성
```
# requirements.txt 핵심
streamlit>=1.30.0
plotly>=5.18.0
google-generativeai>=0.3.0
pandas>=2.0.0
openpyxl>=3.1.0
apify-client>=1.6.0
pydantic>=2.0.0
python-dotenv>=1.0.0
```

---

# Part 10: 결론

## 현재 상태 요약
- **완성도**: 70% (핵심 기능 완료, 고도화 필요)
- **실사용 가능**: Yes (수동 + 반자동 워크플로우)
- **상품화 가능**: 추가 개발 필요

## 강점
1. 마진 계산 로직 정교함 (숨겨진 비용 포함)
2. Pre-Flight 금지어 검사
3. Streamlit UI 완성도 높음
4. 모듈화 설계 (확장 용이)

## 약점
1. 1688 크롤링 불안정 (Apify 의존)
2. 실시간 환율 미적용
3. 네이버 자동 등록 미완성

## 다음 단계 제안
1. **즉시**: google.genai 마이그레이션
2. **단기**: 실시간 환율 API 연동
3. **중기**: 1688 상세페이지 크롤링
4. **장기**: SaaS 상품화 검토

---

**작성자**: Claude Code + 임현우
**검토 요청**: Gemini Deep Research

**질문/피드백은 Gemini CTO에게 전달해주세요!**
