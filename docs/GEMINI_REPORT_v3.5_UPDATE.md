# Smart Store Agent v3.5 - Gemini 피드백 반영 보고서

> **작성일**: 2026-01-22
> **작성자**: Claude Code CLI
> **GitHub**: https://github.com/hyunwoooim-star/smart-store-agent
> **브랜치**: claude/scrape-progress-data-oFba0

---

## 1. 이전 피드백 반영 완료

### 1.1 Apify 전환 ✅
| 항목 | 결과 |
|------|------|
| Playwright 제거 | ✅ 완료 |
| Apify Client 적용 | ✅ 완료 |
| Mock 스크래퍼 | ✅ 테스트용 포함 |

### 1.2 Pre-Flight Check 패턴 추가 ✅

Gemini 피드백대로 3가지 패턴 추가:

| 패턴 | 구현 | 예시 |
|------|------|------|
| **기능성화장품** | ✅ | 미백, 주름개선, SPF/PA, 탈모 |
| **아동용제품** | ✅ | 유아용 장난감, 아기 화장품, KC인증 |
| **지식재산권** | ✅ | 디즈니, 카카오프렌즈, 레플리카 |

**코드 위치**: `src/analyzers/preflight_check.py`

```python
# v3.5 추가 패턴
self.functional_cosmetic_patterns = [...]  # 7개 패턴
self.children_product_patterns = [...]      # 6개 패턴
self.ip_patterns = [...]                    # 8개 패턴
```

### 1.3 코드 개선 ✅

**`_extract_max_price` 개선:**
- 리스트/딕셔너리 형태 처리
- 통화 기호 제거 (¥, $, €, ₩)
- 천 단위 구분자 처리 (10,000)
- 중국어 "至" 범위 표현 지원

### 1.4 Phase 5 로드맵 ✅

Gemini 피드백 반영하여 우선순위 조정:

| 순위 | 기능 | 이유 |
|------|------|------|
| **1위** | 리뷰 분석 + 개선점 도출 | 안전하고 가치 높음 |
| 2위 | Supabase 캐싱 | 비용 최적화 |
| 3위 | 경쟁사 가격 모니터링 | 후순위 |
| ~~4위~~ | ~~자동 상품 등록~~ | 리스크 높음 (보류) |

---

## 2. 현재 프로젝트 상태

### 2.1 Phase 현황

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 1 | 핵심 엔진 | ✅ 완료 |
| Phase 2 | Streamlit 대시보드 | ✅ 완료 |
| Phase 3.5 | Apify API 전환 | ✅ 완료 |
| Phase 4 | Pre-Flight Check | ✅ 완료 |
| **Phase 5** | **리뷰 분석** | ⏳ **다음 단계** |

### 2.2 Streamlit 대시보드

3개 탭 구성 완료:
1. **마진 분석** - 상품 정보 → 리스크 분석
2. **1688 스크래핑** - Apify API 연동
3. **Pre-Flight Check** - 금지어/위험 표현 검사 (v3.5 업데이트)

### 2.3 파일 구조

```
smart-store-agent/
├── src/
│   ├── adapters/
│   │   └── alibaba_scraper.py    # Apify API (v3.5)
│   ├── analyzers/
│   │   └── preflight_check.py    # 금지어 검사 (v3.5 패턴 추가)
│   ├── ui/
│   │   └── app.py                # Streamlit 3탭 (v3.5)
│   └── domain/
│       └── logic.py              # 마진 계산
├── docs/
│   ├── PHASE5_ROADMAP.md         # Phase 5 상세 계획 ← NEW
│   └── GEMINI_REPORT_v3.5_UPDATE.md  # 이 문서
└── CLAUDE.md                     # 프로젝트 컨텍스트 (v3.5)
```

---

## 3. 다음 단계: Phase 5.1 리뷰 분석

### 3.1 구현 계획

```
[입력]
- 네이버 상품 리뷰 (URL 또는 직접 입력)
- 1688 상품 리뷰

[처리]
1. 리뷰 수집 (Apify 또는 수동)
2. Gemini 분석 (불만 패턴, Semantic Gap)
3. 개선안 생성

[출력]
- 불만 패턴 TOP 5
- 공장 요청 사항
- 개선 카피라이팅
```

### 3.2 예상 결과물

| 파일 | 역할 |
|------|------|
| `src/analyzers/review_analyzer.py` | 리뷰 분석 핵심 로직 |
| `src/ui/app.py` | 리뷰 분석 탭 추가 |

---

## 4. Gemini에게 질문

### Q1. Pre-Flight 패턴 추가 검토
추가한 3가지 패턴(기능성화장품, 아동용제품, 지식재산권)이 충분한가요?
더 추가해야 할 패턴이 있나요?

### Q2. 리뷰 분석 프롬프트
Phase 5.1 리뷰 분석용 Gemini 프롬프트 초안:

```
당신은 10년차 베테랑 MD입니다.
아래 리뷰 {N}개를 분석하여:

1. "단순 변심"은 제외, "구조적 결함"만 집중
2. 공장에 개선 요청할 수 있는 구체적 사항 도출
3. 상세페이지에서 미리 해소할 수 있는 불안 요소 파악

JSON으로만 출력:
{
  "complaint_patterns": [...],
  "copy_improvements": [...],
  "risk_summary": "..."
}
```

이 프롬프트가 적절한가요? 개선점이 있나요?

### Q3. Supabase 캐싱 전략
Apify API 비용 최적화를 위한 캐싱 계획:

```sql
CREATE TABLE scrape_cache (
  url_hash TEXT UNIQUE,
  data JSONB,
  expires_at TIMESTAMPTZ
);
```

- 1688 데이터: 7일 유효
- 네이버 리뷰: 1일 유효

이 캐싱 전략이 적절한가요?

### Q4. 네이버 리뷰 수집 방법
네이버 스마트스토어 리뷰 수집 방법 추천:
1. Apify Actor 사용
2. 네이버 Open API (있다면)
3. 수동 복사-붙여넣기 (MVP)

어떤 방법을 추천하시나요?

---

## 5. 커밋 히스토리

```
d78d47e feat: Phase 4 Pre-Flight Check + Streamlit 탭 UI 업데이트
52398fe refactor: Phase 3.5 Pivot - Playwright → Apify API 전환
4b955fa feat: Gemini 피드백 반영 - Pre-Flight 패턴 보완 + Phase 5 로드맵
```

---

## 6. 요약

### 완료된 작업
- ✅ Apify API 전환
- ✅ Pre-Flight Check 패턴 3종 추가
- ✅ `_extract_max_price` 코드 개선
- ✅ Phase 5 로드맵 작성
- ✅ Streamlit UI 업데이트

### 다음 작업 (Phase 5.1)
- ⏳ `review_analyzer.py` 구현
- ⏳ Gemini 프롬프트 튜닝
- ⏳ Streamlit 리뷰 분석 탭
- ⏳ Supabase 캐싱 (비용 최적화)

---

*보고자: Claude Code CLI*
*검토 요청: Gemini AI*
*다음 피드백 받고 Phase 5.1 진행 예정*
