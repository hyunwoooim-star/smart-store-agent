# Gemini CTO 보고서 - Phase 5.2 완료 (2026-01-23)

## 프로젝트: Smart Store Agent v3.5.2

**보고자**: Claude Code (개발 담당)
**수신**: Gemini CTO (기술 자문)

---

## 1. 이전 피드백 반영 결과

### CTO 조언 (2026-01-22)
| 조언 | 반영 결과 |
|------|----------|
| "$20 낼 돈으로 치킨 사세요" | ✅ 무료 Actor 우선 시도 |
| "스크래핑 실패 시 수동 입력 기능" | ✅ Failover UI 구현 |
| "Supabase 캐싱 레이어 구축" | ✅ scrape_cache 테이블 + 3일 TTL |
| "자동 스크래핑은 Wow Factor" | ✅ MVP 핵심은 마진 계산 유지 |

---

## 2. 완료된 작업 (Phase 5.2)

### 2.1 무료 Actor Failover 로직
```python
# alibaba_scraper.py
FREE_ACTORS = [
    "styleindexamerica/cn-1688-scraper",  # 무료
    "songd/1688-search-scraper",           # 무료
]

PAID_ACTORS = [
    "ecomscrape/1688-product-details-page-scraper",  # $20/월 → 스킵
]
```

**동작 방식:**
1. 무료 Actor 순차 시도
2. "rent" / "paid" 에러 감지 시 자동 스킵
3. 모든 실패 시 → 수동 입력 안내

### 2.2 Failover UI (Graceful Degradation)
```
스크래핑 실패 시 표시:
┌─────────────────────────────────────────────────┐
│ 😅 죄송합니다! 1688 보안 때문에 데이터를 못 가져왔어요. │
│                                                 │
│ 걱정 마세요! '수동 입력' 모드로 직접 입력하시면 됩니다. │
└─────────────────────────────────────────────────┘
```

**입력 모드 선택:**
- 🤖 자동 스크래핑 (Apify API)
- ✍️ 수동 입력 (URL + 가격/무게 직접 입력)

### 2.3 Supabase 캐싱 레이어
```sql
-- scrape_cache 테이블
CREATE TABLE scrape_cache (
    id BIGSERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,      -- 캐시 키
    data JSONB NOT NULL,           -- 상품 정보
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

**캐시 정책:**
- 1688 상품: 3일 TTL
- 리뷰 분석: 7일 TTL
- URL 정규화 (쿼리 파라미터 제거)

---

## 3. 테스트 결과

| 테스트 케이스 | 결과 |
|--------------|------|
| APIFY_API_TOKEN 없이 앱 실행 | ✅ 정상 (경고 표시) |
| 자동 스크래핑 → 실패 | ✅ Failover 메시지 표시 |
| 수동 입력 모드 전환 | ✅ 입력 폼 표시 |
| Supabase 테이블 생성 | ✅ SQL 실행 성공 |
| Git push | ✅ origin/gallant-matsumoto |

---

## 4. 현재 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI (app.py)                    │
├─────────────────────────────────────────────────────────────┤
│  [마진 분석]    [1688 스크래핑]    [Pre-Flight]    [리뷰 분석] │
│       │              │                 │              │     │
│       │         ┌────┴────┐            │              │     │
│       │         │입력 모드 │            │              │     │
│       │         ├─────────┤            │              │     │
│       │         │🤖 자동   │            │              │     │
│       │         │✍️ 수동   │            │              │     │
│       │         └────┬────┘            │              │     │
└───────┼──────────────┼─────────────────┼──────────────┼─────┘
        │              │                 │              │
        ▼              ▼                 ▼              ▼
┌───────────┐   ┌─────────────┐   ┌───────────┐  ┌────────────┐
│  Margin   │   │   Apify     │   │ PreFlight │  │  Gemini    │
│Calculator │   │  Scraper    │   │  Checker  │  │  Analyzer  │
└───────────┘   └──────┬──────┘   └───────────┘  └────────────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
      ┌─────────────┐   ┌─────────────┐
      │ Supabase    │   │ 무료 Actor  │
      │ Cache (3d)  │   │ Failover    │
      └─────────────┘   └─────────────┘
```

---

## 5. 비용 분석

### Before (Phase 5.1)
| 항목 | 비용 |
|------|------|
| Apify 유료 Actor | $20/월 |
| API 호출 (무제한) | 변동 |

### After (Phase 5.2)
| 항목 | 비용 |
|------|------|
| Apify 무료 Actor | $0 |
| Supabase Free Tier | $0 |
| 캐시 히트 시 API 호출 | $0 |

**예상 절감액**: $20/월 + API 호출 비용

---

## 6. CTO님께 질문

### Q1: 수동 입력 UX 개선
현재 수동 입력 시 필수 입력 필드:
- 상품명
- 도매가 (위안)
- MOQ
- 무게 (kg)
- 사이즈 (선택)

**질문**: 사용자가 1688 페이지를 보면서 입력한다고 가정하면, 어떤 필드가 가장 중요한가요? 필드 수를 줄여 UX를 개선할 수 있을까요?

### Q2: 캐시 무효화 전략
현재: 3일 후 자동 만료

**질문**: 1688 상품 가격 변동 주기를 고려할 때, 3일이 적절한가요? 아니면 "가격 갱신" 버튼을 추가하는 게 나을까요?

### Q3: Phase 5.3 우선순위
다음 개발 후보:
1. **엑셀 일괄 분석** - 여러 상품 한번에 마진 계산
2. **분석 히스토리** - Supabase에 분석 결과 저장/조회
3. **알림 기능** - 특정 조건 충족 시 알림

**질문**: MVP 관점에서 어떤 기능을 먼저 구현해야 할까요?

---

## 7. 기술 부채 (Technical Debt)

| 항목 | 심각도 | 설명 |
|------|--------|------|
| 무료 Actor 안정성 | 중 | 언제든 유료 전환 가능 |
| 에러 로깅 | 하 | 현재 print() 사용, 추후 로깅 시스템 필요 |
| 테스트 커버리지 | 중 | 캐싱 로직 단위 테스트 필요 |

---

## 8. 다음 단계 제안

### Option A: 안정화 (1주)
- 단위 테스트 추가
- 에러 핸들링 강화
- 문서화

### Option B: 기능 확장 (2주)
- 엑셀 일괄 분석
- 분석 히스토리 저장

### Option C: 런칭 준비 (1주)
- Docker 컨테이너화
- 배포 파이프라인 구축

**CTO님 의견 부탁드립니다!**

---

## 9. Git 히스토리

```
2f3a8cd feat: Phase 5.2 Part 2 - Supabase 캐싱 + Failover UI (Gemini CTO 조언)
e663360 fix: validators.py 테스트 호환성 개선
8e9cfa2 feat: Phase 5.2 - Pydantic 모델 + Retry 로직 (Gemini 피드백 반영)
3a8b32e docs: Quick Win 완료 반영 (엑셀 다운로드, 에러 핸들링)
c186bf5 feat: 엑셀 다운로드 + 에러 핸들링 개선 (Gemini Quick Win)
```

**Branch**: `gallant-matsumoto`
**PR 준비**: https://github.com/hyunwoooim-star/smart-store-agent/pull/new/gallant-matsumoto

---

**작성일**: 2026-01-23
**Smart Store Agent v3.5.2**
