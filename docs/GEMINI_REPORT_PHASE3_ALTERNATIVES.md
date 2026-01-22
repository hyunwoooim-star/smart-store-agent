# Smart Store Agent - Phase 3 대안 분석 보고서

> **Gemini 검토용 문서**
> 작성일: 2026-01-22
> 작성자: Claude Code CLI
> GitHub: https://github.com/hyunwoooim-star/smart-store-agent

---

## 1. 프로젝트 개요

### 1.1 목표
**"틈새 시장 발굴 → 소싱 검증 → 콘텐츠 생성" 자동화**

1688.com에서 상품 데이터(가격, 무게, 사이즈, MOQ)를 수집하여 마진 계산 및 소싱 의사결정 자동화

### 1.2 현재 Phase 진행 상황

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 1 | 핵심 엔진 (margin_calculator, data_importer 등 6개 모듈) | ✅ 완료 |
| Phase 1.5 | 통합 테스트 | ✅ 완료 |
| Phase 2 | Streamlit 대시보드 | ✅ 완료 |
| **Phase 3** | **1688 스크래핑 자동화** | ❌ **막힘** |
| Phase 4 | 비즈니스 확장 (Pre-Flight Check 등) | 예정 |

### 1.3 기술 스택
- 오케스트레이션: Claude Code CLI
- AI 분석: Gemini 1.5 Flash
- 브라우저 자동화: Playwright (현재 시도 중)
- 언어: Python 3.11+
- 데이터베이스: Supabase (PostgreSQL)
- UI: Streamlit

---

## 2. 현재 문제 상황 (Phase 3)

### 2.1 시도한 방법들

#### 1차 시도: browser-use 라이브러리
```python
# browser-use 0.11.3 사용
llm = ChatGoogle(model="gemini-2.0-flash")
agent = Agent(task=extraction_prompt, llm=llm, browser=browser)
```

**결과:** WSL에서 30초 타임아웃 오류
```
WARNING [bubus] ⏱️ TIMEOUT ERROR - Handling took more than 30.0s
```

#### 2차 시도: Playwright + Gemini 하이브리드
```python
# Playwright로 페이지 로드 → Gemini Vision으로 분석
browser = await p.chromium.launch(headless=True, args=[...])
page = await browser.new_page()
await page.goto(url)
# ... Gemini API로 스크린샷 분석
```

**결과:** WSL에서 "Page crashed" 메모리 오류
```
Error: Page crashed
```

### 2.2 환경 정보
```yaml
OS: Windows 11 + WSL2 (Ubuntu)
Python: 3.11.11 (WSL)
playwright: 1.44.0
LLM: gemini-1.5-flash
프로젝트 경로: /mnt/c/.../smart (WSL에서 Windows 경로 접근)
```

### 2.3 문제 원인 추정
1. WSL ↔ Windows 파일시스템 경계에서 성능 저하
2. WSL의 제한된 메모리로 Chromium 크래시
3. GPU 가속 미지원으로 인한 렌더링 문제

---

## 3. 대안 분석

### 3.1 직접 구현 방식

| 방법 | 구현 난이도 | 비용 | 안정성 | 1688 특화 |
|------|------------|------|--------|----------|
| Playwright (현재) | 3/5 | 무료 | 중 (WSL 이슈) | X |
| Puppeteer (Node.js) | 3/5 | 무료 | 중상 | X |
| Selenium | 3/5 | 무료 | 중 | X |
| browser-use | 2/5 | LLM 비용 | 낮음 (타임아웃) | X |

**직접 구현의 공통 문제:**
- 1688 Anti-bot 탐지 우회 필요
- IP 차단 리스크
- CAPTCHA 수동 처리 필요
- 유지보수 부담 높음

### 3.2 유료 플랫폼/API 대안

#### TOP 1: Oxylabs 1688 Scraper API ⭐⭐⭐

| 항목 | 내용 |
|------|------|
| **URL** | https://oxylabs.io/products/scraper-api/ecommerce/1688 |
| **구현 난이도** | 2/5 (매우 쉬움) |
| **비용** | $49~$200/월, ~$1.6/1000건 |
| **안정성** | 매우 높음 (100% 성공률 보장) |
| **법적 리스크** | 낮음 (Oxylabs 책임) |
| **무료 체험** | 2,000건 |

**장점:**
- CAPTCHA 자동 우회
- 프록시 자동 관리
- JavaScript 렌더링 지원
- 한국에서 바로 사용 가능

**사용 예시:**
```python
import requests

payload = {
    "source": "universal",
    "url": "https://detail.1688.com/offer/xxx.html",
    "render": "html"
}
response = requests.post(
    "https://realtime.oxylabs.io/v1/queries",
    auth=("USERNAME", "PASSWORD"),
    json=payload
)
data = response.json()
```

---

#### TOP 2: TMAPI / DajiAPI (중국 현지 서비스) ⭐⭐⭐

| 항목 | TMAPI | DajiAPI |
|------|-------|---------|
| **URL** | https://tmapi.top | https://dajiapi.cn |
| **구현 난이도** | 2/5 | 2/5 |
| **비용** | $20~$100/월 | $30~$100/월 |
| **안정성** | 높음 | 높음 |
| **한국어** | X | O (12개 언어) |

**장점:**
- 1688 전문 서비스
- 저렴한 가격
- 상세 데이터 완벽 제공 (가격, 무게, 사이즈, MOQ)

**TMAPI 사용 예시:**
```python
import requests

response = requests.get(
    "https://api.tmapi.top/alibaba/item/detail",
    params={
        "key": "YOUR_API_KEY",
        "item_id": "xxx"
    }
)
product = response.json()
# 가격, 무게, 사이즈, MOQ 등 반환
```

---

#### TOP 3: Apify 1688 Actors ⭐⭐

| 항목 | 내용 |
|------|------|
| **URL** | https://apify.com/search?q=1688 |
| **구현 난이도** | 2/5 |
| **비용** | 무료~$50/월 (CU 기반) |
| **안정성** | 높음 |
| **특징** | MCP 서버 지원 (Claude 연동 용이) |

**장점:**
- 무료 플랜으로 테스트 가능
- 다양한 1688 전용 Actor 선택
- Claude Code MCP 통합 가능

**사용 예시:**
```python
from apify_client import ApifyClient

client = ApifyClient("YOUR_API_TOKEN")
run_input = {"productUrl": "https://detail.1688.com/offer/xxx.html"}
run = client.actor("ecomscrape/1688-product-details-page-scraper").call(run_input=run_input)

for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    print(item)
```

---

### 3.3 기타 대안

| 서비스 | 비용 | 특징 |
|--------|------|------|
| Bright Data | $499+/월 | 엔터프라이즈급, 과함 |
| RapidAPI 1688 APIs | $10~$100/월 | 통합 마켓플레이스 |
| 1688 공식 API | 무료~유료 | 중국 사업자 필요 (사용 불가) |

---

## 4. 비용-효과 분석

### 4.1 현재 상황 비용
- 개발 시간: 이미 3일+ 소요 (browser-use → Playwright 전환)
- 여전히 미해결
- 기회비용: Phase 4 진행 지연

### 4.2 유료 API 비용 추정

**월 500건 스크래핑 기준:**

| 서비스 | 월 비용 | 건당 비용 |
|--------|---------|----------|
| Oxylabs | ~$49 | ~$0.10 |
| TMAPI | ~$20 | ~$0.04 |
| Apify | ~$10 (무료 포함) | ~$0.02 |

**결론:** 월 $20~$50로 안정적인 1688 데이터 수집 가능

### 4.3 ROI 분석

```
직접 구현 비용:
- 개발 시간: 10시간+ × 시급 환산 = ???
- 유지보수: 지속적
- 실패 리스크: 높음

유료 API 비용:
- 초기 설정: 1시간
- 월 비용: $20~$50
- 실패 리스크: 매우 낮음

→ 유료 API가 명백히 유리
```

---

## 5. 추천안

### 5.1 1순위: TMAPI 또는 Apify (저비용 시작)

**이유:**
- 가장 저렴 ($20~무료)
- 1688 전문 서비스
- 빠른 도입 가능 (1시간 내)

**도입 절차:**
1. TMAPI 또는 Apify 가입
2. API 키 발급
3. `alibaba_scraper.py`를 API 클라이언트로 교체
4. 기존 `ScrapedProduct` 모델에 매핑

### 5.2 2순위: Oxylabs (안정성 우선)

**이유:**
- 100% 성공률 보장
- 대규모 확장 시 적합
- 무료 체험 2,000건으로 PoC 가능

### 5.3 3순위: Playwright WSL 수정 (무료 고수)

유료 서비스 도입 전 마지막 시도로, 다음 플래그 추가:

```python
# alibaba_scraper.py 수정
browser = await p.chromium.launch(
    headless=True,
    args=[
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",                         # 추가
        "--disable-setuid-sandbox",              # 추가
        "--single-process",                      # 추가
        "--js-flags=--max-old-space-size=512",   # 추가
    ]
)
```

또는 **Windows 네이티브 Python**으로 환경 전환

---

## 6. Gemini에게 질문

### Q1. 추천안 우선순위
위 분석을 기반으로, 다음 중 어떤 방향을 추천하시나요?

1. **TMAPI/Apify로 즉시 전환** (저비용, 빠른 도입)
2. **Oxylabs로 전환** (안정성 우선)
3. **Playwright WSL 수정 한 번 더 시도** (무료 고수)
4. **Windows 네이티브 Python 환경 전환 후 Playwright 재시도**

### Q2. 법적 리스크 평가
중국 사이트(1688) 스크래핑의 법적 리스크에 대해 어떻게 생각하시나요?
- 서드파티 API 사용 시 리스크 분산 효과가 충분한가요?
- 한국 법률 기준으로 문제가 될 수 있나요?

### Q3. 장기 아키텍처
Phase 4 이후를 고려할 때, 어떤 데이터 수집 방식이 확장성 면에서 유리한가요?
- 단일 API 의존 vs 멀티 소스 (fallback 구조)

### Q4. 비용 최적화
월 500~1000건 스크래핑 기준으로, 비용 대비 가장 효율적인 조합은?

---

## 7. 첨부: 프로젝트 구조

```
smart-store-agent/
├── src/
│   ├── adapters/
│   │   └── alibaba_scraper.py    # ← 수정 대상
│   ├── sourcing/
│   │   └── margin_calculator.py  # ✅ 완료
│   ├── analysis/
│   │   └── gemini_analyzer.py    # ✅ 완료
│   └── domain/
│       └── models.py             # ScrapedProduct 모델
├── streamlit_app.py              # ✅ 완료
├── test_browser.py               # 스크래퍼 테스트 CLI
├── docs/
│   ├── ROADMAP.md
│   ├── CURRENT_STATUS.md
│   └── GEMINI_REPORT_PHASE3_ALTERNATIVES.md  # ← 이 문서
└── CLAUDE.md
```

---

## 8. 결론

**현재 상황:** Phase 3 (1688 스크래핑)에서 WSL 환경 문제로 막힘

**권장 방향:**
- 직접 구현보다 **유료 API 도입**이 시간/비용 면에서 유리
- **TMAPI** 또는 **Apify**로 빠르게 전환 권장
- 월 $20~$50 투자로 안정적인 데이터 파이프라인 확보 가능

**다음 단계:**
1. Gemini 피드백 확인
2. 추천안 기반 API 선택
3. `alibaba_scraper.py` API 클라이언트로 교체
4. Phase 3 완료 → Phase 4 진행

---

*보고자: Claude Code CLI*
*검토 요청: Gemini AI*
*GitHub: https://github.com/hyunwoooim-star/smart-store-agent*
