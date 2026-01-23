# Smart Store Agent - Gemini CTO 컨설팅 요청서

**날짜**: 2026-01-22
**버전**: v3.5.1
**GitHub**: https://github.com/hyunwoooim-star/smart-store-agent
**브랜치**: `claude/add-pydantic-retry-logic-nICEw`

---

## 1. 프로젝트 개요

### 핵심 목표
"틈새 시장 발굴 → 소싱 검증 → 콘텐츠 생성" 과정을 AI로 자동화하는 네이버 스마트스토어 운영 도구

### 기술 스택
| 구분 | 기술 |
|------|------|
| 오케스트레이션 | Claude Code CLI |
| AI 분석 | Gemini 1.5 Flash |
| 1688 스크래핑 | Apify API (클라우드) |
| 데이터베이스 | Supabase (PostgreSQL) |
| UI | Streamlit |
| 데이터 검증 | Pydantic v2 |

---

## 2. 현재 진행 상태

### 완료된 Phase

| Phase | 내용 | 상태 |
|-------|------|------|
| 1.0 | 핵심 엔진 (마진 계산기, 키워드 필터) | ✅ 완료 |
| 1.5 | 통합 테스트 | ✅ 완료 |
| 2.0 | Streamlit 대시보드 | ✅ 완료 |
| 3.5 | 1688 스크래핑 (Apify 전환) | ⚠️ **문제 발생** |
| 4.0 | Pre-Flight Check (금지어 검사) | ✅ 완료 |
| 5.1 | 리뷰 분석 MVP | ✅ 완료 |
| 5.2 | Pydantic + Retry 로직 | ✅ 완료 |

### 구현된 모듈 (43개 파일)

```
src/
├── adapters/
│   └── alibaba_scraper.py    # 1688 Apify 스크래퍼
├── analyzers/
│   ├── gemini_analyzer.py    # Gemini AI 분석
│   ├── keyword_filter.py     # 키워드 필터링
│   ├── preflight_check.py    # 네이버 금지어 검사
│   ├── review_analyzer.py    # 리뷰 분석 (Phase 5.1)
│   └── spec_validator.py     # 스펙 검증
├── sourcing/
│   └── margin_calculator.py  # 마진 계산 (프로젝트 핵심)
├── ui/
│   └── app.py               # Streamlit 4개 탭
├── domain/
│   ├── models.py            # Pydantic 모델
│   └── logic.py             # 비즈니스 로직
└── ...
```

---

## 3. 현재 문제점 (Critical)

### 3.1 Apify Actor 유료화 문제

**상황**:
- 기존 사용하던 Actor: `ecomscrape/1688-product-details-page-scraper`
- 무료 트라이얼 종료 → **월 $20 유료** 전환됨

**에러 메시지**:
```
"You must rent a paid Actor in order to run it after its free trial has expired.
To rent this Actor, go to https://console.apify.com/actors/aXavqrEp6XpQAg7ox"
```

**영향**:
- Streamlit 앱의 "1688 스크래핑" 탭 사용 불가
- 실시간 상품 정보 추출 불가

### 3.2 대안 검토 현황

| 옵션 | 장점 | 단점 |
|------|------|------|
| **A. 유료 구독** ($20/월) | 즉시 사용 가능, 안정적 | 비용 발생 |
| **B. 다른 무료 Actor** | 무료 | 동작 보장 없음, 코드 수정 필요 |
| **C. 직접 스크래핑** | 무료, 커스터마이징 | Anti-bot 대응 어려움, 개발 시간 |
| **D. 수동 입력 유지** | 비용 0 | 자동화 의미 없음 |

### 3.3 발견된 무료 Actor 후보

1. `styleindexamerica/cn-1688-scraper`
2. `songd/1688-search-scraper`
3. `nice_dev/1688-product-scraper`

**문제**: 이 Actor들의 안정성/정확도가 검증되지 않음

---

## 4. 테스트 결과 요약

### 4.1 로컬 Windows 환경 테스트 (2026-01-22)

| 항목 | 결과 |
|------|------|
| Python 설치 | ✅ 3.14.2 |
| 의존성 설치 | ✅ 완료 |
| Streamlit 실행 | ✅ localhost:8501 |
| 마진 분석 탭 | ✅ 정상 동작 |
| Pre-Flight Check 탭 | ✅ 정상 동작 |
| 리뷰 분석 탭 | ✅ Gemini API 연결됨 |
| **1688 스크래핑 탭** | ❌ **Apify 유료화로 실패** |

### 4.2 pytest 결과 (서버 환경)

```
178 passed, 3 skipped (Supabase mock 관련)
```

---

## 5. 질문 사항

### Q1. Apify Actor 유료화 대응 전략

> 월 $20 구독 vs 무료 대안 Actor vs 직접 구현
> 어떤 방향이 비용 대비 효과적인가요?

**고려사항**:
- 현재 테스트 단계 (실제 운영 전)
- 예상 사용량: 월 100~500건
- 개발 리소스: 1인 개발

### Q2. 1688 스크래핑 장기 전략

> 1688 스크래핑이 비즈니스에 필수인가요?
> 아니면 수동 입력 + AI 분석에 집중하는 게 나은가요?

**현재 워크플로우**:
```
1688 URL 입력 → 자동 스크래핑 → 마진 계산 → 리스크 분석
```

**대안 워크플로우**:
```
수동 정보 입력 (가격, 무게) → 마진 계산 → 리스크 분석
```

### Q3. MVP 범위 재정의

> 현재 기능 중 "있으면 좋은 것" vs "반드시 필요한 것"을 구분해주세요.

**현재 기능 목록**:
1. 마진 계산기 (손익분기 분석)
2. Pre-Flight Check (네이버 금지어 검사)
3. 1688 자동 스크래핑
4. 리뷰 분석 (Gemini AI)
5. Supabase 데이터 저장

### Q4. 다음 우선순위

> Phase 5.2 Part 2 (Supabase 캐싱 레이어) vs 다른 작업
> 어떤 것을 먼저 진행해야 할까요?

**Phase 5.2 Part 2 계획**:
- 1688 URL → 상품 정보 캐싱 (3일 유효)
- 네이버 URL → 리뷰 캐싱 (7일 유효)
- 중복 API 호출 방지 → 비용 절감

---

## 6. 아키텍처 현황

### 6.1 데이터 흐름

```
[사용자 입력]
     │
     ▼
[Streamlit UI] ──────────────────────────────────┐
     │                                           │
     ├─── 마진 분석 탭 ───▶ MarginCalculator     │
     │                            │              │
     │                            ▼              │
     │                     손익분기 계산          │
     │                                           │
     ├─── 1688 스크래핑 탭 ───▶ Apify API ❌     │
     │                            │              │
     │                            ▼              │
     │                     상품 정보 추출        │
     │                                           │
     ├─── Pre-Flight 탭 ───▶ PreFlightChecker   │
     │                            │              │
     │                            ▼              │
     │                     금지어 탐지           │
     │                                           │
     └─── 리뷰 분석 탭 ───▶ Gemini API ✅       │
                                  │              │
                                  ▼              │
                           리뷰 인사이트 분석    │
                                                 │
                                  ▼              │
                          [Supabase 저장] ◀──────┘
```

### 6.2 비용 구조

| 서비스 | 현재 비용 | 예상 비용 (운영 시) |
|--------|----------|---------------------|
| Gemini API | 무료 (Flash) | ~$5/월 |
| Supabase | 무료 플랜 | 무료 |
| Apify | **$20/월** (유료화) | $20~50/월 |
| **합계** | $20/월 | $25~55/월 |

---

## 7. 코드 품질 지표

### 7.1 테스트 커버리지
- Unit Tests: 178 passed
- 주요 모듈 테스트 완료 (margin_calculator, preflight_check 등)

### 7.2 최근 커밋 이력 (10개)

```
e663360 fix: validators.py 테스트 호환성 개선
8e9cfa2 feat: Phase 5.2 - Pydantic 모델 + Retry 로직
3a8b32e docs: Quick Win 완료 반영
c186bf5 feat: 엑셀 다운로드 + 에러 핸들링 개선
12fcd50 docs: v3.5.1 종합 피드백 반영 보고서
73851be feat: Gemini 피드백 전체 반영 - v3.5.1 완성
b249820 docs: Gemini 코드 리뷰 요청 문서
a0471f4 feat: Gemini 피드백 반영 - Phase 5.1 리뷰 분석 MVP
2eef321 docs: Phase 4 완료 보고서
4b955fa feat: Gemini 피드백 반영 - Pre-Flight 패턴 보완
```

### 7.3 Pydantic 모델 적용 (Phase 5.2)

```python
class ReviewAnalysisResult(BaseModel):
    """리뷰 분석 결과 - Gemini 출력 검증"""
    pain_points: list[str]
    improvement_ideas: list[str]
    sample_checklist: list[str]
    fatal_flaws: list[str]
    marketing_angles: list[str]
```

---

## 8. 요청 사항

### 8.1 기술적 조언
1. Apify 유료화 대응 최적 전략
2. 1688 스크래핑 없이 MVP 운영 가능 여부
3. 비용 최적화 방안

### 8.2 비즈니스 조언
1. 현재 기능 중 핵심 vs 부가 기능 구분
2. MVP 출시 최소 요구사항
3. 수익화 전략 (있다면)

### 8.3 아키텍처 조언
1. 캐싱 레이어 필요성
2. 에러 복구 전략
3. 확장성 고려사항

---

## 9. 첨부 자료

### 9.1 스크린샷
- Streamlit 앱 실행 화면 (4개 탭)
- Apify 유료화 에러 메시지
- 1688 스크래핑 실패 화면

### 9.2 관련 문서
- `docs/ROADMAP.md` - 전체 로드맵
- `docs/CURRENT_STATUS.md` - 현재 상태
- `CLAUDE.md` - 프로젝트 컨텍스트

---

## 10. 기대 결과

1. **단기** (1주): Apify 문제 해결 방향 결정
2. **중기** (2주): MVP 기능 확정 및 테스트 완료
3. **장기** (1개월): 실제 운영 시작

---

*작성: Claude Code + 사용자*
*검토 요청 대상: Gemini CTO*
*문서 버전: 1.0*
