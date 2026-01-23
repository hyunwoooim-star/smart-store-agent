# Smart Store Agent - Gemini 리뷰 요청 (2026-01-23)

## 요청 목적
Phase 3.5 진행 상황 점검 및 블로커 해결 방향 피드백 요청

---

## 1. 프로젝트 현황

### GitHub
https://github.com/hyunwoooim-star/smart-store-agent

### 전체 진행도
```
Phase 1   [██████████] 100% ✅ 핵심 엔진 개발 (margin_calculator 등 6개 모듈)
Phase 2   [██████████] 100% ✅ Streamlit 대시보드 (streamlit_app.py)
Phase 3.5 [██████░░░░]  60% 🔄 Playwright + Gemini 하이브리드 (현재)
Phase 4   [░░░░░░░░░░]   0% ⏳ Pre-Flight Check, 비즈니스 확장
```

---

## 2. Phase 3.5 상세 진행 현황

### 완료된 작업
| 작업 | 상태 | 비고 |
|------|------|------|
| browser-use 0.11.3 호환성 테스트 | ✅ | 30초 타임아웃 이슈 발생 |
| Option B 전략 채택 (Playwright + Gemini) | ✅ | Gemini 피드백 반영 |
| `alibaba_scraper.py` 재작성 | ✅ | 하이브리드 방식 |
| WSL 브라우저 의존성 설치 | ✅ | libnss3, libnspr4, libasound2 |
| gemini-2.0-flash → 1.5-flash 변경 | ✅ | 할당량 안정성 |

### 현재 블로커
| 이슈 | 상태 | 시도한 해결책 |
|------|------|---------------|
| Playwright "Page crashed" (WSL) | 🔴 미해결 | Chromium 플래그 추가 예정 |

---

## 3. 기술적 질문 (피드백 요청)

### Q1. WSL vs Windows 네이티브 - 어느 쪽이 나을까요?

**현재 상황:**
- WSL Ubuntu에서 Playwright + Chromium 실행 시 "Page crashed" 발생
- 추정 원인: WSL의 메모리 제한 또는 GPU 접근 문제

**선택지:**
| 옵션 | 장점 | 단점 |
|------|------|------|
| A. WSL 유지 + Chromium 플래그 | 현재 환경 유지 | 추가 디버깅 필요 |
| B. Windows 네이티브 Python | 안정성 높음 | 환경 재구성 필요 |
| C. Docker 컨테이너 | 일관된 환경 | 복잡도 증가 |

**질문:** 1인 개발 환경에서 가장 실용적인 선택은?

---

### Q2. Playwright headless vs headed 모드

**현재 코드 (alibaba_scraper.py):**
```python
browser = await playwright.chromium.launch(
    headless=True,
    args=[
        '--disable-gpu',
        '--no-sandbox',
        '--disable-dev-shm-usage'
    ]
)
```

**질문:** 1688처럼 봇 탐지가 있는 사이트에서 headless 모드가 블로킹될 가능성은? headed 모드가 더 안전할까요?

---

### Q3. Gemini Vision 활용 전략

**현재 계획:**
1. Playwright로 페이지 스크린샷 캡처
2. Gemini Vision에 이미지 전송
3. 상품 정보(가격, MOQ, 스펙) 추출

**질문:**
- 스크린샷 해상도/크기 권장 설정은?
- 한 페이지를 여러 섹션으로 나눠서 보내는 게 나을까요, 전체 페이지 한 장이 나을까요?

---

## 4. 코드 리뷰 요청

### alibaba_scraper.py 핵심 로직
```python
class Alibaba1688Scraper:
    async def scrape_product(self, url: str) -> dict:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until='networkidle')

            # HTML 가져오기
            html = await page.content()

            # BeautifulSoup으로 1차 파싱
            soup = BeautifulSoup(html, 'html.parser')

            # Gemini로 2차 분석 (구조화된 데이터 추출)
            result = await self._analyze_with_gemini(html)

            return result
```

**리뷰 포인트:**
1. `wait_until='networkidle'` - 적절한가요?
2. HTML 전체를 Gemini에 보내는 것 vs 스크린샷 - 어느 쪽이 효율적?
3. 에러 핸들링/재시도 로직 추가 필요?

---

## 5. 다음 단계 계획

### 즉시 (이번 주)
1. Page crashed 해결 (옵션 결정 후)
2. 1688 실제 URL 테스트 성공
3. 추출 데이터 → MarginCalculator 연동

### 다음 (다음 주)
4. Streamlit에 1688 스크래퍼 통합
5. Phase 4 Pre-Flight Check 설계

---

## 6. 요청 사항 요약

1. **WSL vs Windows 네이티브** 환경 선택 조언
2. **headless vs headed** 모드 권장
3. **Gemini Vision** 최적 활용법
4. **alibaba_scraper.py** 코드 리뷰
5. 전체 진행 방향에 대한 피드백

---

## 7. 참고 링크

| 항목 | 링크 |
|------|------|
| GitHub 저장소 | https://github.com/hyunwoooim-star/smart-store-agent |
| 전체 로드맵 | https://github.com/hyunwoooim-star/smart-store-agent/blob/main/docs/ROADMAP.md |
| 현재 상태 문서 | https://github.com/hyunwoooim-star/smart-store-agent/blob/main/docs/CURRENT_STATUS.md |
| alibaba_scraper.py | https://github.com/hyunwoooim-star/smart-store-agent/blob/main/src/adapters/alibaba_scraper.py |

---

*작성일: 2026-01-23*
*작성자: Claude Code*
*버전: v3.2*
