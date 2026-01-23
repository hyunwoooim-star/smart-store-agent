# Smart Store Agent - Phase 5 로드맵

> **작성일**: 2026-01-22
> **작성자**: Claude Code CLI
> **Gemini 피드백 반영**: 리뷰 분석 우선

---

## 1. Phase 5 개요

### 1.1 목표
**"소싱 검증 → 콘텐츠 개선"** 자동화 파이프라인 완성

### 1.2 우선순위 (Gemini 피드백 반영)

| 순위 | 기능 | 비즈니스 가치 | 리스크 |
|------|------|--------------|--------|
| **1위** | 리뷰 분석 + 개선점 도출 | ⭐⭐⭐⭐⭐ | 낮음 |
| 2위 | 경쟁사 가격 모니터링 | ⭐⭐⭐⭐ | 중간 |
| 3위 | 재고 알림 시스템 | ⭐⭐⭐ | 낮음 |
| ~~4위~~ | ~~자동 상품 등록~~ | - | ~~높음~~ (후순위) |

> **Gemini 피드백**: "자동 업로드는 리스크가 높다. 리뷰 분석이 가장 안전하면서도 비즈니스 가치가 높다."

---

## 2. Phase 5.1: 리뷰 분석 + 개선점 도출 (최우선)

### 2.1 기능 설명
1688 또는 경쟁 스마트스토어의 리뷰를 분석하여:
- 고객 불만 패턴 TOP 5 추출
- 개선 가능한 포인트 도출
- 상세페이지 카피라이팅 개선안 제안

### 2.2 기술 설계

```
[입력]
- 네이버 스마트스토어 상품 URL
- 또는 1688 상품 URL
- 또는 직접 리뷰 텍스트 붙여넣기

[처리]
1. 리뷰 수집 (Apify 또는 수동 입력)
2. Gemini 분석 (불만 패턴, Semantic Gap)
3. 개선안 생성 (카피라이팅)

[출력]
- 불만 패턴 TOP 5 (빈도순)
- 구조적 결함 vs 단순 변심 분류
- 개선 카피라이팅 5개
- 공장 요청 사항 (전문 용어)
```

### 2.3 구현 파일

| 파일 | 역할 |
|------|------|
| `src/analyzers/review_analyzer.py` | 리뷰 분석 핵심 로직 |
| `src/adapters/naver_scraper.py` | 네이버 리뷰 수집 (Apify) |
| `src/ui/app.py` | Streamlit 탭 추가 |

### 2.4 Gemini 프롬프트 (v3.5)

```
당신은 10년차 베테랑 MD입니다.
아래 리뷰 {N}개를 분석하여 다음을 추출하세요:

[분석 원칙]
1. "단순 변심"은 제외, "구조적 결함"만 집중
2. 공장에 개선 요청할 수 있는 구체적 사항 도출
3. 상세페이지에서 미리 해소할 수 있는 불안 요소 파악

[출력 형식]
JSON으로만 출력. 마크다운/코드블록 금지.
{
  "complaint_patterns": [
    {"pattern": "...", "count": N, "severity": "high/medium/low", "factory_request": "..."},
    ...
  ],
  "copy_improvements": ["...", "...", "..."],
  "risk_summary": "..."
}
```

### 2.5 예상 결과

**입력**: 캠핑의자 리뷰 50개

**출력**:
```json
{
  "complaint_patterns": [
    {"pattern": "팔걸이 꺾임", "count": 8, "severity": "high", "factory_request": "팔걸이 연결부 보강 요청"},
    {"pattern": "등받이 천 늘어남", "count": 5, "severity": "medium", "factory_request": "600D 옥스포드 → 900D 업그레이드"},
    {"pattern": "무게 생각보다 무거움", "count": 4, "severity": "low", "factory_request": "상세페이지 무게 강조"}
  ],
  "copy_improvements": [
    "✅ 팔걸이 이중 보강 설계 (기존 대비 30% 내구성↑)",
    "✅ 900D 고밀도 옥스포드 원단 (늘어남 방지)",
    "✅ 2.5kg 초경량 설계 (백패킹 OK)"
  ],
  "risk_summary": "팔걸이 내구성이 주요 불만. 공장에 보강 요청 또는 상세페이지에 사용 주의사항 명시 필요."
}
```

---

## 3. Phase 5.2: Supabase 캐싱 (비용 최적화)

### 3.1 목적
Apify API 중복 호출 방지 → 비용 절감

### 3.2 캐싱 전략 (Gemini 피드백 반영)

```
[캐싱 대상 - v3.5.1 업데이트]
- 1688 URL → 상품 정보 (3일 유효) ← 가격/재고 변동 잦음
- 네이버 URL → 리뷰 목록 (7일 유효) ← 과거 데이터, 변화 적음

[흐름]
1. URL 해시 → Supabase 조회
2. 캐시 있으면 → 반환
3. 캐시 없으면 → Apify 호출 → 저장 → 반환
4. UI에 "강제 새로고침" 버튼 제공
```

**Gemini 피드백 요약:**
- 1688: 7일 → **3일** (재고/가격 변동이 잦아서 7일이면 품절 상품 볼 위험)
- 네이버 리뷰: 1일 → **7일** (리뷰는 과거 데이터, 매일 갱신 불필요)

### 3.3 Supabase 테이블

```sql
CREATE TABLE scrape_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  url_hash TEXT UNIQUE NOT NULL,
  source TEXT NOT NULL,  -- '1688', 'naver'
  data JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_cache_hash ON scrape_cache(url_hash);
CREATE INDEX idx_cache_expires ON scrape_cache(expires_at);
```

### 3.4 예상 비용 절감

| 시나리오 | 캐싱 없음 | 캐싱 있음 | 절감율 |
|----------|----------|----------|--------|
| 동일 URL 10회 조회 | 10 API 호출 | 1 API 호출 | 90% |
| 월 1000건 (30% 중복) | 1000건 | 700건 | 30% |

---

## 4. Phase 5.3: 경쟁사 가격 모니터링

### 4.1 기능 설명
- 네이버 쇼핑 검색 결과에서 경쟁 상품 가격 추적
- 가격 변동 알림 (Slack/Email)

### 4.2 구현 (후순위)
Apify의 네이버 쇼핑 스크래퍼 활용

---

## 5. 구현 일정 (예상)

| 단계 | 작업 | 예상 |
|------|------|------|
| **5.1.1** | review_analyzer.py 기본 구조 | 2-3시간 |
| **5.1.2** | Gemini 프롬프트 튜닝 | 1-2시간 |
| **5.1.3** | Streamlit 리뷰 분석 탭 | 1-2시간 |
| **5.2** | Supabase 캐싱 레이어 | 2-3시간 |
| **5.3** | 가격 모니터링 (후순위) | 추후 |

---

## 6. 다음 단계

1. **즉시**: Phase 5.1 (리뷰 분석) 기본 구조 설계
2. **이번 주**: Gemini 프롬프트 튜닝 + 테스트
3. **다음 주**: Supabase 캐싱 + Streamlit 통합

---

*작성자: Claude Code CLI*
*검토 대상: Gemini AI*
