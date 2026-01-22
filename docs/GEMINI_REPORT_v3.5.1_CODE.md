# Smart Store Agent v3.5.1 - Gemini 코드 리뷰 요청

> **작성일**: 2026-01-22
> **버전**: v3.5.1
> **목적**: Phase 5.1 MVP 코드 검토 요청

---

## 1. 이번 업데이트 요약

| 기능 | 파일 | 상태 |
|------|------|------|
| 의료기기 오인 패턴 | `preflight_check.py` | ✅ 완료 |
| 리뷰 분석 MVP | `review_analyzer.py` | ✅ 완료 |
| Streamlit 4탭 UI | `app.py` | ✅ 완료 |
| 캐싱 전략 문서화 | `PHASE5_ROADMAP.md` | ✅ 완료 |

---

## 2. 핵심 코드 리뷰 요청

### 2.1 의료기기 오인 패턴 (`preflight_check.py`)

**추가된 패턴:**

```python
# 11. 의료기기 오인 표현 (CRITICAL - 의료기기법 위반)
# 일반 공산품에 의학적 효능 암시 → 경찰서 가는 케이스
self.medical_device_patterns = [
    # 치료/교정 관련
    (r"(치료|치료용|치료기)", "치료 표현 (의료기기 인증 필요)"),
    (r"(교정|교정기|교정용)", "교정 표현 (의료기기)"),
    (r"(거북목|일자목).{0,5}(교정|개선|치료)", "거북목 교정 (의료기기)"),
    (r"(자세).{0,5}(교정|개선|치료)", "자세 교정 (의료기기)"),
    (r"(척추|허리|목).{0,5}(교정|치료)", "척추/허리 교정 (의료기기)"),

    # 통증 관련
    (r"(통증).{0,5}(완화|개선|치료|제거)", "통증 완화 (의료기기 효능)"),
    (r"(근육통|관절통|두통|어깨통증|허리통증).{0,5}(완화|해소)", "통증 완화 표현"),

    # 혈액/순환 관련
    (r"(혈액순환|혈행).{0,5}(개선|촉진|증진)", "혈액순환 개선 (의료기기)"),
    (r"(혈류|혈관).{0,5}(개선|확장)", "혈류 관련 (의료기기)"),

    # 척추/디스크 관련
    (r"(디스크|추간판).{0,5}(예방|치료|개선)", "디스크 관련 (의료기기)"),
    (r"(허리디스크|목디스크)", "디스크 언급 (의료적 표현)"),

    # 기타 의료적 표현
    (r"(재활|물리치료|테라피)", "재활/치료 표현"),
    (r"(의료용|의료기기|의료기)", "의료 관련 표현"),
    (r"(적외선|원적외선).{0,5}(치료|효과)", "적외선 치료 (의료기기)"),
]
```

**안전한 대안:**

```python
ViolationType.MEDICAL_DEVICE: [
    "자세 도움", "바른 자세 습관", "편안한 사용감",
    "일상 관리", "컨디션 케어", "릴렉스",
],
```

**Q1: 추가해야 할 의료기기 오인 패턴이 더 있을까요?**
- 예: EMS, 저주파, 마사지건 관련 표현?

---

### 2.2 리뷰 분석 프롬프트 (`review_analyzer.py`)

**Gemini 피드백 반영한 프롬프트:**

```python
REVIEW_ANALYSIS_PROMPT = """당신은 연 매출 100억 쇼핑몰의 수석 MD이자 상품 기획자입니다.
수집된 리뷰 데이터를 분석하여, 이 상품을 소싱할 때 '반드시 개선해야 할 점'과 '강조해야 할 점'을 도출하십시오.

[분석 지침]
1. **Noise Filtering**: "배송이 늦어요", "박스가 찌그러졌어요" 같은 단순 CS는 무시하십시오. 오직 '제품 자체'에 집중하십시오.
2. **Severity Scoring**: 같은 불만이 반복되면 가중치를 높이십시오.
3. **Sentiment Gap**: 고객이 기대했으나 실망한 포인트(Gap)를 찾으십시오.

[출력 형식 (JSON만 출력 - 마크다운/인사말 금지)]
{
  "critical_defects": [
    {"issue": "세탁 후 수축 심함", "frequency": "High", "quote": "한 번 빨았더니 아기 옷이 됐어요"}
  ],
  "improvement_requests": [
    "마감 실밥 처리 강화 요청",
    "매뉴얼에 한국어 설명 추가 필요"
  ],
  "marketing_hooks": [
    "예상보다 훨씬 가벼움 (무게 강조)",
    "색감이 화면과 똑같음 (실사 강조)"
  ],
  "verdict": "Go"
}

[verdict 기준]
- "Go": 치명적 결함 없음, 소싱 진행 권장
- "Hold": 일부 이슈 있으나 샘플 확인 후 결정
- "Drop": 치명적 결함으로 소싱 포기 권장

[리뷰 데이터]
{reviews}
"""
```

**Q2: 프롬프트 개선점이 있을까요?**
- 카테고리별 특화 프롬프트 필요? (의류 vs 전자제품 vs 가구)
- `frequency` 계산 기준 명확화 필요?

---

### 2.3 리뷰 분석 결과 데이터 구조

```python
@dataclass
class CriticalDefect:
    """치명적 결함"""
    issue: str              # 문제 설명
    frequency: str          # "High", "Medium", "Low"
    quote: Optional[str] = None  # 실제 리뷰 인용


@dataclass
class ReviewAnalysisResult:
    """리뷰 분석 결과"""
    critical_defects: List[CriticalDefect] = field(default_factory=list)
    improvement_requests: List[str] = field(default_factory=list)
    marketing_hooks: List[str] = field(default_factory=list)
    verdict: Verdict = Verdict.HOLD
    raw_response: Optional[str] = None

    @property
    def has_critical_issues(self) -> bool:
        return any(d.frequency == "High" for d in self.critical_defects)
```

**Q3: 데이터 구조에 추가할 필드가 있을까요?**
- `confidence_score`: 분석 신뢰도?
- `category_specific_risks`: 카테고리별 특수 위험?

---

### 2.4 Streamlit UI 구조

```python
# 4탭 구성
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 마진 분석",
    "🇨🇳 1688 스크래핑",
    "✅ Pre-Flight Check",
    "📝 리뷰 분석"  # NEW
])

# 리뷰 분석 탭 - 3단 컬럼 레이아웃
col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("🚨 치명적 결함")
with col2:
    st.subheader("🔧 공장 협의사항")
with col3:
    st.subheader("💡 마케팅 소구점")
```

**Q4: UI/UX 개선 포인트가 있을까요?**
- 리뷰 개수 표시 필요?
- 분석 소요 시간 표시?

---

## 3. 캐싱 전략 확정 (Gemini 피드백 반영)

```
[캐싱 대상 - v3.5.1]
- 1688 URL → 상품 정보 (3일 유효) ← 가격/재고 변동 잦음
- 네이버 URL → 리뷰 목록 (7일 유효) ← 과거 데이터, 변화 적음
- UI에 "강제 새로고침" 버튼 제공
```

**Q5: 추가 캐싱 대상이 있을까요?**
- Gemini 분석 결과도 캐싱?
- Pre-Flight 검사 결과 캐싱?

---

## 4. 다음 단계 질문

### Q6: Phase 5.2 (Supabase 캐싱) 우선순위

현재 선택지:
1. **캐싱 먼저** → 비용 절감 후 기능 확장
2. **리뷰 분석 튜닝 먼저** → 기능 완성도 높인 후 캐싱

**권장 순서가 있을까요?**

---

### Q7: 네이버 리뷰 자동 수집

현재 MVP: 수동 복사/붙여넣기

다음 단계 옵션:
1. Apify Actor (`naver-shopping-scraper`)
2. 네이버 쇼핑 API (제한적)
3. 현재 MVP 유지 (수동)

**추천 방향이 있을까요?**

---

## 5. 전체 파일 구조 (v3.5.1)

```
smart-store-agent/
├── src/
│   ├── adapters/
│   │   └── alibaba_scraper.py    # Apify API (1688)
│   ├── analyzers/
│   │   ├── preflight_check.py    # 금지어 검사 (12개 패턴)
│   │   ├── review_analyzer.py    # 리뷰 분석 (NEW)
│   │   └── gemini_analyzer.py    # Gemini 분석
│   ├── domain/
│   │   ├── models.py             # 도메인 모델
│   │   └── logic.py              # 마진 계산 로직
│   ├── core/
│   │   └── config.py             # 설정
│   └── ui/
│       └── app.py                # Streamlit (4탭)
├── docs/
│   ├── PHASE5_ROADMAP.md         # 로드맵
│   └── GEMINI_REPORT_*.md        # 보고서들
└── CLAUDE.md                     # 프로젝트 컨텍스트
```

---

## 6. GitHub 링크

**브랜치**: https://github.com/hyunwoooim-star/smart-store-agent/tree/claude/scrape-progress-data-oFba0

**주요 커밋**:
- `a0471f4` feat: Gemini 피드백 반영 - Phase 5.1 리뷰 분석 MVP

---

## 7. 요약: Gemini에게 묻는 질문

| # | 질문 | 카테고리 |
|---|------|----------|
| Q1 | 의료기기 패턴 추가 (EMS, 저주파 등)? | Pre-Flight |
| Q2 | 리뷰 분석 프롬프트 개선점? | 프롬프트 |
| Q3 | 데이터 구조 추가 필드? | 설계 |
| Q4 | UI/UX 개선 포인트? | Streamlit |
| Q5 | 추가 캐싱 대상? | 캐싱 |
| Q6 | 캐싱 vs 리뷰 튜닝 우선순위? | 로드맵 |
| Q7 | 네이버 리뷰 자동 수집 방향? | 기능 |

---

*작성자: Claude Code CLI*
*검토 대상: Gemini AI*
