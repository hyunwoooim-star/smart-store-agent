# Smart Store Agent - Phase 3 현황 보고서

## 📊 프로젝트 정보

| 항목 | 값 |
|------|-----|
| **GitHub** | https://github.com/hyunwoooim-star/smart-store-agent |
| **버전** | v3.3 |
| **현재 Phase** | Phase 3 - Browser-Use 자동화 |
| **작성일** | 2026-01-21 |

---

## ✅ 완료된 작업

### 1. browser-use 0.11.3 API 호환성 업데이트
- `GEMINI_API_KEY` → `GOOGLE_API_KEY` (2025-05 변경사항 반영)
- `langchain-google-genai` → `ChatGoogle` (browser-use 내장 클래스 사용)
- `browser_config` dict → `Browser` 클래스 직접 파라미터 전달
- `gemini-1.5-flash` → `gemini-2.0-flash` 업그레이드

### 2. 이전 Gemini 피드백 반영
- 가격 범위 → 최대값 선택 (방어적 계산)
- 무게/사이즈 없으면 `null` (임의 생성 금지)
- 팝업 대응 로직 추가

---

## ❌ 현재 문제점

### 1. WSL 환경에서 브라우저 시작 타임아웃 (30초)

**증상:**
```
WARNING  [bubus] ⏱️  TIMEOUT ERROR - Handling took more than 30.0s
TimeoutError: Event handler ... timed out after 30.0s
```

**원인 추정:**
- WSL에서 Playwright/Chromium 첫 실행 시 초기화가 느림
- 확장 프로그램(uBlock, ClearURLs 등) 다운로드/설치에 시간 소요
- Windows ↔ WSL 파일시스템 경계에서 성능 저하

**시도한 해결책:**
- `timeout=120` 파라미터 추가 → 효과 없음 (browser-use가 내부적으로 30초 고정?)

### 2. 클라우드 브라우저 인증 오류

**증상:**
```
CloudBrowserAuthError: Authentication failed for cloud browser service.
Set BROWSER_USE_API_KEY environment variable.
```

**해결:**
- `use_cloud=False` 추가로 로컬 브라우저 강제 사용
- 현재 이 설정이 제대로 적용되는지 재테스트 필요

---

## 🔍 현재 코드 상태

### alibaba_scraper.py 핵심 부분

```python
# browser-use 내장 ChatGoogle 사용
llm = ChatGoogle(model="gemini-2.0-flash")

# Browser 설정 (v0.11+ API)
browser = Browser(
    headless=self.headless,
    disable_security=True,  # CORS 등 우회
    use_cloud=False,  # 로컬 브라우저 사용
)

# Browser-Use 에이전트 실행
agent = Agent(
    task=extraction_prompt,
    llm=llm,
    browser=browser,
)
```

### 프롬프트 (Gemini 피드백 반영 v2)

```
당신은 1688.com 소싱 리스크 관리자입니다. **보수적으로** 데이터를 추출하세요.

[추출 규칙 - 매우 중요!]
- price_cny: 가격 범위(예: ¥25-35)가 있으면 **무조건 큰 값(35)** 선택
- weight_kg/size: '사양' 탭 먼저 찾고, 없으면 본문에서 단위 패턴 검색
- 정보 없음: null로 두세요 (임의로 지어내지 마세요!)
```

---

## ❓ Gemini에게 질문

### Q1. browser-use 0.11의 타임아웃 설정 방법

browser-use 0.11.3에서 브라우저 시작 타임아웃(기본 30초)을 늘리는 방법이 있나요?

```python
# 이렇게 해봤지만 효과 없음
browser = Browser(timeout=120, ...)
```

공식 문서에서는 `timeout` 파라미터가 있지만, 내부 이벤트 버스(bubus)의 타임아웃을 제어하지 못하는 것 같습니다.

### Q2. WSL 환경 vs Windows 네이티브 Python

현재 구조:
- Windows 프로젝트 폴더: `C:\Users\임현우\Desktop\현우 작업폴더\smart`
- WSL Python 환경: `~/smart-venv/.venv` (Linux home에 venv)
- browser-use가 Windows 경로(`/mnt/c/...`)에서 실행됨

이 구조가 브라우저 시작 지연의 원인일 수 있나요?
Windows 네이티브 Python 3.11로 전환하면 해결될까요?

### Q3. browser-use 대안

만약 browser-use가 WSL에서 안정적으로 작동하지 않는다면, 대안으로:
1. **Playwright 직접 사용** + Gemini API 호출 분리
2. **Selenium** + 기존 방식
3. **puppeteer (Node.js)**

어떤 것을 추천하시나요? browser-use의 "AI가 페이지를 탐색" 기능이 필요한 건 아니고,
특정 CSS 셀렉터로 데이터 추출하는 것도 가능합니다.

### Q4. 1688 스펙 테이블 구조

1688 상품 페이지에서 스펙 테이블의 일반적인 HTML 구조를 알려주실 수 있나요?
예: `div.detail-attributes`, `table.spec-table` 등

직접 파싱하는 방식으로 전환할 경우 참고하고 싶습니다.

---

## 📈 다음 단계 계획

### Option A: browser-use 계속 사용
1. Windows 네이티브 Python으로 환경 재구성
2. browser-use 타임아웃 이슈 해결
3. 실제 1688 URL 테스트 완료

### Option B: Playwright 직접 구현
1. Playwright로 1688 페이지 로드
2. 특정 셀렉터로 데이터 추출 (가격, 스펙 등)
3. 추출 실패 시에만 Gemini Vision API로 스크린샷 분석

### Option C: 하이브리드
1. 먼저 Playwright로 시도
2. 동적 콘텐츠나 복잡한 구조면 browser-use 사용

**현재 선호:** Option B (Playwright 직접 구현)
- 더 빠르고 안정적
- Gemini API 비용 절감 (스크린샷 분석은 fallback으로만)

---

## 📝 환경 정보

```yaml
Python: 3.11.11 (WSL)
browser-use: 0.11.3
playwright: 1.44.0
OS: Windows 11 + WSL2 (Ubuntu)
LLM: gemini-2.0-flash (Google AI)
```

---

## 🔗 관련 파일

| 파일 | 설명 |
|------|------|
| `src/adapters/alibaba_scraper.py` | 1688 스크래퍼 (browser-use) |
| `test_browser.py` | CLI 테스트 도구 |
| `docs/GEMINI_REPORT_PHASE3.md` | 이전 보고서 |
| `.env.example` | 환경변수 템플릿 |

---

*보고자: Claude Code CLI*
*검토 요청 대상: Gemini AI*
