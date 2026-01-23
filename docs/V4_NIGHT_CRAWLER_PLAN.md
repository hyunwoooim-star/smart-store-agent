# Smart Store Agent v4.0: Night Crawler 설계서

## Gemini CTO 검토 요청

**작성일**: 2026-01-24
**버전**: v4.0 설계안
**목표**: "AI가 밤새 소싱 → 사장님 아침 승인 → AI가 등록" 반자동 시스템

---

## 1. 시스템 개요

### 1.1 핵심 컨셉
```
"Human-in-the-loop" 자동화
- AI: 노동(Labor) 담당 - 밤새 상품 찾기
- 인간: 결정(Decision) 담당 - 아침에 승인/반려
- AI: 실행(Execution) 담당 - 상세페이지 생성 및 등록
```

### 1.2 일일 워크플로우
```
[새벽 01:00] Night Crawler 시작
     ↓ (6시간 동안 천천히)
[새벽 07:00] 소싱 완료, DB 저장
     ↓
[아침 08:00] 슬랙/카톡 알림 발송
     "주인님, 밤새 42개의 꿀템을 찾아뒀습니다"
     ↓
[아침 09:00] 사장님 대시보드 접속
     - 틴더 스타일 UI로 승인/반려
     - 5분 안에 검토 완료
     ↓
[자동] Publishing Bot 작동
     - 승인된 상품 상세페이지 생성
     - 네이버 스마트스토어 등록
     ↓
[완료] 슬랙 알림
     "5개 상품 등록 완료! [링크]"
```

---

## 2. 아키텍처 설계

### 2.1 시스템 구성도
```
┌─────────────────────────────────────────────────────────────┐
│                    Smart Store Agent v4.0                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Scheduler │───▶│Night Crawler│───▶│  Supabase   │     │
│  │  (01:00 AM) │    │   (소싱봇)   │    │    (DB)     │     │
│  └─────────────┘    └─────────────┘    └──────┬──────┘     │
│                                                │             │
│                                                ▼             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Slack/    │◀───│  Streamlit  │◀───│  Morning    │     │
│  │   KakaoTalk │    │  Dashboard  │    │  Briefing   │     │
│  └─────────────┘    └──────┬──────┘    └─────────────┘     │
│                            │                                 │
│                            ▼ (승인 시)                       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Naver     │◀───│ Publishing  │◀───│  Content    │     │
│  │    API      │    │    Bot      │    │  Generator  │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 모듈 구조
```
src/
├── crawler/
│   ├── __init__.py
│   ├── night_crawler.py      # 메인 소싱 봇
│   ├── keyword_manager.py    # 키워드 관리
│   ├── product_filter.py     # 1차/2차/3차 필터링
│   └── scheduler.py          # 스케줄러 (APScheduler)
│
├── approval/
│   ├── __init__.py
│   ├── candidate_manager.py  # 후보 상품 관리
│   └── approval_service.py   # 승인/반려 처리
│
├── publisher/
│   ├── __init__.py
│   ├── content_generator.py  # 상세페이지 생성 (PAS)
│   ├── image_processor.py    # 이미지 처리 (기본)
│   └── naver_uploader.py     # 네이버 API 등록
│
├── notifications/
│   ├── __init__.py
│   ├── slack_notifier.py     # 슬랙 알림
│   └── kakao_notifier.py     # 카카오톡 알림
│
└── ui/
    └── tabs/
        └── morning_tab.py    # 모닝 브리핑 탭
```

---

## 3. 데이터베이스 설계 (Supabase)

### 3.1 테이블: `sourcing_keywords`
```sql
CREATE TABLE sourcing_keywords (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    keyword TEXT NOT NULL,
    category TEXT,
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 5,  -- 1(높음) ~ 10(낮음)
    last_crawled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 예시 데이터
INSERT INTO sourcing_keywords (keyword, category, priority) VALUES
('데스크 정리함', '홈인테리어', 1),
('틈새 수납장', '홈인테리어', 2),
('모니터 받침대', '사무용품', 3),
('차량용 수납', '자동차', 5);
```

### 3.2 테이블: `sourcing_candidates`
```sql
CREATE TABLE sourcing_candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 원본 정보
    source_url TEXT NOT NULL,           -- 1688 URL
    source_title TEXT,                  -- 원본 제목 (중국어)
    source_price_cny DECIMAL(10,2),     -- 원가 (위안)
    source_images TEXT[],               -- 이미지 URL 배열

    -- AI 분석 결과
    title_kr TEXT,                      -- AI 번역 제목
    estimated_cost_krw INTEGER,         -- 예상 총원가 (원)
    estimated_margin_rate DECIMAL(5,2), -- 예상 마진율 (%)
    recommended_price INTEGER,          -- 추천 판매가
    risk_level TEXT,                    -- safe/warning/danger
    risk_reasons TEXT[],                -- 리스크 사유 배열

    -- 경쟁사 분석
    naver_min_price INTEGER,            -- 네이버 최저가
    naver_avg_price INTEGER,            -- 네이버 평균가
    competitor_count INTEGER,           -- 경쟁사 수

    -- 상태 관리
    status TEXT DEFAULT 'PENDING',      -- PENDING/APPROVED/REJECTED/UPLOADED/FAILED
    approved_at TIMESTAMP,
    rejected_reason TEXT,

    -- 등록 정보
    naver_product_id TEXT,              -- 등록된 상품 ID
    naver_product_url TEXT,             -- 등록된 상품 URL
    uploaded_at TIMESTAMP,

    -- 메타
    keyword_id UUID REFERENCES sourcing_keywords(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_candidates_status ON sourcing_candidates(status);
CREATE INDEX idx_candidates_margin ON sourcing_candidates(estimated_margin_rate DESC);
CREATE INDEX idx_candidates_created ON sourcing_candidates(created_at DESC);
```

### 3.3 테이블: `upload_history`
```sql
CREATE TABLE upload_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID REFERENCES sourcing_candidates(id),
    platform TEXT NOT NULL,             -- naver/coupang
    status TEXT NOT NULL,               -- success/failed
    response_data JSONB,                -- API 응답 저장
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 4. Night Crawler 상세 설계

### 4.1 크롤링 전략
```python
# src/crawler/night_crawler.py

class NightCrawler:
    """밤샘 소싱 봇"""

    # 안티봇 회피 설정
    MIN_DELAY = 60      # 최소 대기 60초
    MAX_DELAY = 180     # 최대 대기 180초
    MAX_CONCURRENCY = 1 # 동시 요청 1개만

    # 작업량 제한
    MAX_PRODUCTS_PER_KEYWORD = 20   # 키워드당 최대 20개
    MAX_TOTAL_CANDIDATES = 50       # 총 최대 50개

    async def run_nightly_job(self):
        """메인 작업"""
        keywords = await self.get_active_keywords()

        for keyword in keywords:
            # 1단계: 검색 결과 수집
            search_results = await self.search_1688(keyword)

            # 2단계: 1차 필터링 (가격/판매량)
            filtered = self.apply_basic_filter(search_results)

            # 3단계: 상세 정보 수집 (천천히)
            for product in filtered[:self.MAX_PRODUCTS_PER_KEYWORD]:
                await self.random_delay()  # 랜덤 대기
                detail = await self.get_product_detail(product.url)

                # 4단계: 마진 분석
                analysis = await self.analyze_margin(detail)

                # 5단계: 네이버 경쟁사 조회
                competition = await self.check_naver_competition(detail.title)

                # 6단계: 최종 필터링 및 저장
                if analysis.margin_rate >= 0.30:  # 30% 이상만
                    await self.save_candidate(detail, analysis, competition)

        # 7단계: 알림 발송
        await self.send_morning_notification()
```

### 4.2 필터링 로직
```python
# src/crawler/product_filter.py

class ProductFilter:
    """3단계 필터링"""

    def apply_basic_filter(self, products: List[Product]) -> List[Product]:
        """1차 필터: 기본 조건"""
        return [p for p in products if (
            p.price_cny >= 5 and           # 5위안 이상
            p.price_cny <= 500 and         # 500위안 이하
            p.sales_count >= 10 and        # 판매량 10개 이상
            p.shop_rating >= 4.0           # 샵 평점 4.0 이상
        )]

    def apply_margin_filter(self, product: Product, analysis: MarginAnalysis) -> bool:
        """2차 필터: 마진 조건"""
        return (
            analysis.margin_rate >= 0.30 and      # 마진 30% 이상
            analysis.risk_level != 'danger' and   # 위험 등급 제외
            analysis.breakeven_price < analysis.naver_avg_price  # 손익분기 < 평균가
        )

    def apply_risk_filter(self, product: Product) -> Tuple[bool, List[str]]:
        """3차 필터: 리스크 체크"""
        risks = []

        # 지재권 체크 (브랜드명 포함 여부)
        brand_keywords = ['nike', 'adidas', 'gucci', '나이키', '아디다스',
                         'disney', '디즈니', 'marvel', '마블', 'kakao', '카카오']
        title_lower = product.title.lower()
        for brand in brand_keywords:
            if brand in title_lower:
                risks.append(f"브랜드명 포함: {brand}")

        # KC인증 필요 품목 체크
        kc_keywords = ['전자', '충전', '배터리', '유아', '아동', '장난감']
        for kc in kc_keywords:
            if kc in product.title:
                risks.append(f"KC인증 필요 가능성: {kc}")

        # 식품/의약품 체크
        forbidden = ['식품', '건강', '영양제', '의약', '화장품']
        for word in forbidden:
            if word in product.title:
                risks.append(f"판매 제한 품목: {word}")

        is_safe = len(risks) == 0
        return is_safe, risks
```

### 4.3 속도 제한 (Anti-Bot)
```python
# src/crawler/night_crawler.py

import asyncio
import random

class NightCrawler:
    async def random_delay(self):
        """랜덤 대기 (사람처럼 보이게)"""
        delay = random.uniform(self.MIN_DELAY, self.MAX_DELAY)
        print(f"[NightCrawler] 다음 요청까지 {delay:.1f}초 대기...")
        await asyncio.sleep(delay)

    async def search_1688(self, keyword: str) -> List[SearchResult]:
        """1688 검색 (Apify 사용)"""
        from apify_client import ApifyClient

        client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

        run = client.actor("ecomscrape/1688-search-scraper").call(
            run_input={
                "keyword": keyword,
                "maxItems": 50,
                "proxyConfiguration": {
                    "useApifyProxy": True,
                    "apifyProxyGroups": ["RESIDENTIAL"]  # 주거용 프록시
                }
            },
            timeout_secs=300,
            memory_mbytes=512
        )

        results = client.dataset(run["defaultDatasetId"]).list_items().items
        return [SearchResult.from_dict(r) for r in results]
```

---

## 5. Morning Briefing UI 설계

### 5.1 Streamlit 탭: `morning_tab.py`
```python
# src/ui/tabs/morning_tab.py

def render():
    """모닝 브리핑 탭"""
    st.header("🌞 모닝 브리핑")
    st.markdown("밤새 AI가 찾아온 상품 후보들입니다. 승인/반려를 결정해주세요.")

    # 통계 표시
    stats = get_candidate_stats()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("대기 중", f"{stats['pending']}개")
    col2.metric("승인됨", f"{stats['approved']}개")
    col3.metric("등록 완료", f"{stats['uploaded']}개")
    col4.metric("평균 마진율", f"{stats['avg_margin']:.1f}%")

    st.divider()

    # 대기 중인 후보 목록
    candidates = get_pending_candidates()

    if not candidates:
        st.info("🎉 검토할 상품이 없습니다. 푹 쉬세요!")
        return

    for candidate in candidates:
        render_candidate_card(candidate)

def render_candidate_card(candidate):
    """상품 카드 (틴더 스타일)"""
    with st.container():
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image(candidate.source_images[0], width=200)

        with col2:
            st.subheader(candidate.title_kr)

            # 핵심 지표
            m1, m2, m3 = st.columns(3)
            m1.metric("예상 마진", f"{candidate.estimated_margin_rate:.0%}")
            m2.metric("추천 판매가", f"{candidate.recommended_price:,}원")
            m3.metric("경쟁사", f"{candidate.competitor_count}개")

            # 네이버 시장가
            st.caption(f"네이버 최저가: {candidate.naver_min_price:,}원 | 평균가: {candidate.naver_avg_price:,}원")

            # 리스크 표시
            if candidate.risk_reasons:
                st.warning(f"⚠️ 주의: {', '.join(candidate.risk_reasons)}")

            # 승인/반려 버튼
            btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])

            with btn_col1:
                if st.button("✅ 승인", key=f"approve_{candidate.id}"):
                    approve_candidate(candidate.id)
                    st.rerun()

            with btn_col2:
                if st.button("❌ 반려", key=f"reject_{candidate.id}"):
                    reject_candidate(candidate.id)
                    st.rerun()

            with btn_col3:
                if st.button("🔍 1688에서 보기", key=f"view_{candidate.id}"):
                    st.markdown(f"[원본 링크]({candidate.source_url})")

        st.divider()
```

### 5.2 UI 미리보기
```
┌─────────────────────────────────────────────────────────────────┐
│ 🌞 모닝 브리핑                                                   │
│ 밤새 AI가 찾아온 상품 후보들입니다. 승인/반려를 결정해주세요.      │
├─────────────────────────────────────────────────────────────────┤
│ [대기 중: 12개] [승인됨: 3개] [등록완료: 45개] [평균마진: 42%]    │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────┬───────────────────────────────────────────────────┐ │
│ │         │ 미니멀 데스크 정리함 3단 서랍형                     │ │
│ │  [IMG]  │                                                   │ │
│ │         │ 예상마진: 45%  추천가: 24,900원  경쟁사: 8개       │ │
│ │         │ 네이버 최저가: 19,800원 | 평균가: 28,500원         │ │
│ │         │                                                   │ │
│ │         │ [✅ 승인]  [❌ 반려]  [🔍 1688에서 보기]           │ │
│ └─────────┴───────────────────────────────────────────────────┘ │
│ ─────────────────────────────────────────────────────────────── │
│ ┌─────────┬───────────────────────────────────────────────────┐ │
│ │         │ 모니터 받침대 USB 허브 내장형                       │ │
│ │  [IMG]  │                                                   │ │
│ │         │ 예상마진: 38%  추천가: 32,900원  경쟁사: 15개      │ │
│ │         │ ⚠️ 주의: KC인증 필요 가능성                        │ │
│ │         │                                                   │ │
│ │         │ [✅ 승인]  [❌ 반려]  [🔍 1688에서 보기]           │ │
│ └─────────┴───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Publishing Bot 설계

### 6.1 상세페이지 생성 (PAS 프레임워크)
```python
# src/publisher/content_generator.py

class ContentGenerator:
    """상세페이지 콘텐츠 생성기 (PAS 프레임워크)"""

    SYSTEM_PROMPT = """당신은 네이버 스마트스토어 판매 1위 상세페이지 기획자입니다.

[PAS 프레임워크]
- Problem: 고객이 겪는 문제/불편함을 짚어주세요
- Agitation: 그 문제를 방치하면 어떻게 되는지 경각심을 주세요
- Solution: 이 상품이 어떻게 해결해주는지 설명하세요

[작성 규칙]
1. 해요체 사용
2. 이모지 적절히 사용
3. 짧은 문장 (모바일 가독성)
4. 구체적인 숫자 사용
5. 네이버 금지어 회피 (최고, 1위, 100% 등)

[출력 형식]
JSON 형식으로 출력하세요.
"""

    async def generate(self, candidate: Candidate) -> DetailPageContent:
        """상세페이지 콘텐츠 생성"""
        prompt = f"""
상품명: {candidate.title_kr}
카테고리: {candidate.category}
주요 특징: {candidate.features}
타겟 고객: {candidate.target_audience}
경쟁사 대비 강점: {candidate.competitive_edge}

위 정보를 바탕으로 상세페이지 콘텐츠를 작성해주세요.
"""

        response = await self.gemini.generate(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt
        )

        return DetailPageContent.from_json(response)
```

### 6.2 네이버 등록 API
```python
# src/publisher/naver_uploader.py

class NaverUploader:
    """네이버 커머스 API 업로더"""

    BASE_URL = "https://api.commerce.naver.com/external/v1"

    async def upload_product(self, candidate: Candidate, content: DetailPageContent) -> UploadResult:
        """상품 등록"""

        # 1. 이미지 업로드
        image_urls = await self.upload_images(candidate.source_images)

        # 2. 상품 등록 요청
        payload = {
            "originProduct": {
                "statusType": "SALE",
                "saleType": "NEW",
                "name": content.title,
                "detailContent": content.to_html(),
                "images": {
                    "representativeImage": {"url": image_urls[0]},
                    "optionalImages": [{"url": url} for url in image_urls[1:5]]
                },
                "salePrice": candidate.recommended_price,
                "stockQuantity": 999,
                "deliveryInfo": {
                    "deliveryType": "DELIVERY",
                    "deliveryFee": {
                        "deliveryFeeType": "FREE"
                    }
                },
                "detailAttribute": {
                    "naverShoppingSearchInfo": {
                        "manufacturerName": "해외",
                        "brandName": "자체제작",
                        "modelName": content.title[:50]
                    }
                }
            }
        }

        response = await self._post("/products", payload)

        return UploadResult(
            success=response.status == 200,
            product_id=response.data.get("productId"),
            product_url=f"https://smartstore.naver.com/{self.store_id}/products/{response.data.get('productId')}"
        )
```

---

## 7. 스케줄러 설계

### 7.1 APScheduler 설정
```python
# src/crawler/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class CrawlerScheduler:
    """크롤링 스케줄러"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.crawler = NightCrawler()
        self.publisher = PublishingBot()

    def setup(self):
        """스케줄 설정"""

        # 1. 밤샘 소싱: 매일 새벽 1시
        self.scheduler.add_job(
            self.crawler.run_nightly_job,
            CronTrigger(hour=1, minute=0),
            id="night_crawl",
            name="밤샘 소싱"
        )

        # 2. 모닝 알림: 매일 아침 8시
        self.scheduler.add_job(
            self.send_morning_notification,
            CronTrigger(hour=8, minute=0),
            id="morning_notify",
            name="모닝 알림"
        )

        # 3. 자동 등록: 매시간 (승인된 것만)
        self.scheduler.add_job(
            self.publisher.process_approved,
            CronTrigger(minute=0),
            id="auto_publish",
            name="승인 상품 등록"
        )

    def start(self):
        """스케줄러 시작"""
        self.scheduler.start()
        print("[Scheduler] 스케줄러 시작됨")
        print("[Scheduler] 다음 소싱: 새벽 01:00")
```

### 7.2 GitHub Actions (대안)
```yaml
# .github/workflows/night_crawler.yml

name: Night Crawler

on:
  schedule:
    - cron: '0 16 * * *'  # UTC 16:00 = KST 01:00
  workflow_dispatch:  # 수동 실행 가능

jobs:
  crawl:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run Night Crawler
        env:
          APIFY_API_TOKEN: ${{ secrets.APIFY_API_TOKEN }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
        run: python -m src.crawler.night_crawler

      - name: Send Notification
        run: python -m src.notifications.slack_notifier
```

---

## 8. 개발 로드맵

### Phase 1: 기반 구축 (3일)
```
Day 1:
- [ ] Supabase 테이블 생성 (keywords, candidates, history)
- [ ] 기본 모델 클래스 정의
- [ ] DB 연결 테스트

Day 2:
- [ ] NightCrawler 기본 구조 작성
- [ ] Apify 1688 검색 연동
- [ ] 필터링 로직 구현

Day 3:
- [ ] 마진 계산 연동 (기존 모듈 활용)
- [ ] 네이버 경쟁사 조회 연동 (기존 모듈 활용)
- [ ] DB 저장 로직 완성
```

### Phase 2: UI 구축 (2일)
```
Day 4:
- [ ] morning_tab.py 생성
- [ ] 후보 목록 표시 UI
- [ ] 승인/반려 기능 구현

Day 5:
- [ ] 통계 대시보드
- [ ] 필터링/정렬 기능
- [ ] UI 테스트 및 개선
```

### Phase 3: 자동화 연결 (2일)
```
Day 6:
- [ ] 상세페이지 생성기 PAS 업그레이드
- [ ] 네이버 API 등록 연동
- [ ] 에러 핸들링

Day 7:
- [ ] 스케줄러 설정
- [ ] 알림 시스템 (슬랙)
- [ ] 전체 통합 테스트
```

### Phase 4: 안정화 (1일)
```
Day 8:
- [ ] 로깅 강화
- [ ] 모니터링 대시보드
- [ ] 문서화
- [ ] 실전 테스트
```

---

## 9. 비용 추정

### 9.1 월간 운영 비용
| 항목 | 서비스 | 예상 비용 |
|------|--------|----------|
| 1688 스크래핑 | Apify | $30 (약 4만원) |
| 프록시 | Apify Residential | 포함 |
| AI 분석/생성 | Gemini | $10 (약 1.3만원) |
| 데이터베이스 | Supabase | $0 (무료 티어) |
| 스케줄러 | GitHub Actions | $0 (무료) |
| **합계** | | **월 약 5~6만원** |

### 9.2 개발 비용
| 항목 | 예상 소요 |
|------|----------|
| 개발 기간 | 8일 (1인 기준) |
| 외주 시 | 300~500만원 |
| 직접 개발 | 0원 (본인 노동력) |

---

## 10. 질문 사항 (Gemini CTO 검토 요청)

### Q1. 크롤링 전략
```
현재 계획: 새벽 1시~7시, 7분 간격, 키워드 5개
```
- A) 계획대로 진행
- B) 더 느리게 (10분 간격)
- C) 더 빠르게 (5분 간격)
- D) 시간대 변경 제안

### Q2. 필터링 기준
```
현재 계획: 마진 30% 이상만 저장
```
- A) 30% 적절함
- B) 25%로 낮추기 (더 많은 후보)
- C) 35%로 높이기 (더 엄격하게)
- D) 가변적 (카테고리별 다르게)

### Q3. 스케줄러 선택
```
옵션 A: APScheduler (서버에서 24시간 실행)
옵션 B: GitHub Actions (서버리스, 무료)
```
- A) APScheduler
- B) GitHub Actions
- C) 둘 다 (백업용)
- D) 다른 제안

### Q4. 알림 채널
```
현재 계획: 슬랙
대안: 카카오톡, 이메일, 텔레그램
```
- A) 슬랙만
- B) 카카오톡 추가
- C) 텔레그램 추가
- D) 복수 선택

### Q5. 지재권 체크 강화
```
현재: 브랜드명 키워드 매칭
강화안: AI 이미지 분석 (로고 검출)
```
- A) 키워드 매칭만 (현재)
- B) AI 이미지 분석 추가 (비용 증가)
- C) 외부 서비스 연동 (검증된 DB)
- D) 나중에 검토

### Q6. MVP 범위
```
전체 기능 중 MVP로 먼저 만들 것:
```
- A) 소싱 봇 + UI (등록은 수동)
- B) 소싱 봇 + UI + 자동 등록
- C) 소싱 봇만 (UI는 나중에)
- D) 전체 다 한번에

### Q7. 개발 시작 시점
```
CTO 지시: Code Freeze 중
```
- A) 지금 바로 시작
- B) 첫 상품 등록 후 시작
- C) 첫 판매 발생 후 시작
- D) 1주일 후 시작

### Q8. 리스크 관리
```
가장 큰 리스크: 1688 차단
```
- A) 프록시 풀 확대
- B) 백업 소스 준비 (알리바바)
- C) 크롤링 포기, 수동 입력 병행
- D) 기타 제안

---

## 11. 기대 효과

### Before (현재)
```
소싱: 수동으로 1688 검색 (2시간/일)
분석: 수동으로 마진 계산 (30분/상품)
등록: 수동으로 상세페이지 작성 (1시간/상품)

→ 하루 2~3개 상품 등록 가능
```

### After (v4.0)
```
소싱: AI가 밤새 자동 (0분)
분석: AI가 자동 분석 (0분)
검토: 아침에 5분 승인
등록: AI가 자동 등록 (0분)

→ 하루 10~20개 상품 등록 가능
→ 작업 시간 90% 절감
```

---

**Gemini CTO님의 Q1~Q8 검토를 요청드립니다!**
