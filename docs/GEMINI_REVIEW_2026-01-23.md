# Smart Store Agent - Gemini 리뷰 요청 (2026-01-23)

## 요청 목적
Phase 5.2 완료 후, Phase 6 방향성 및 우선순위 피드백 요청

---

## 1. 프로젝트 현황

### GitHub
https://github.com/hyunwoooim-star/smart-store-agent

### 전체 진행도
```
Phase 1   [##########] 100%  핵심 엔진 (마진 계산기 등 6개 모듈)
Phase 2   [##########] 100%  Streamlit 대시보드 (3탭)
Phase 3.5 [##########] 100%  1688 스크래핑 (Apify API)
Phase 4   [##########] 100%  Pre-Flight Check (금지어 검사)
Phase 5.2 [##########] 100%  Pydantic + Supabase 캐싱
Phase 6   [          ]   0%  비즈니스 확장 (피드백 요청)
```

### 완료 요약
| Phase | 핵심 기능 | 파일 |
|-------|----------|------|
| 1 | 마진 계산, 부피무게, 관부가세 | `margin_calculator.py` |
| 2 | 웹 대시보드 3탭 | `src/ui/app.py` |
| 3.5 | 1688 스크래핑 (WSL 이슈 → Apify로 해결) | `alibaba_scraper.py` |
| 4 | 네이버 금지어/위험 표현 검사 | `preflight_check.py` |
| 5.1 | 리뷰 분석 (불만 패턴 TOP 5) | `review_analyzer.py` |
| 5.2 | Pydantic 검증 + Retry 로직 + 캐싱 | `validators.py`, `supabase_client.py` |

---

## 2. Phase 6 후보 기능

### 우선순위 결정 요청

| 순위 | 기능 | 설명 | 예상 가치 | 리스크 |
|------|------|------|----------|--------|
| ? | 경쟁사 가격 모니터링 | 네이버 쇼핑 경쟁 상품 가격 추적 | 높음 | 낮음 |
| ? | Slack/Email 알림 | 가격 변동, 재고 알림 | 중간 | 낮음 |
| ? | 자동 상품 등록 | 네이버 Commerce API 연동 | 매우 높음 | 높음 |
| ? | 1688 MOQ/배송비 자동 분석 | 상품 상세 추가 정보 추출 | 중간 | 중간 |
| ? | 엑셀 내보내기 기능 | 분석 결과 엑셀 다운로드 | 낮음 | 낮음 |

**질문: 비즈니스 가치와 리스크를 고려할 때 권장 우선순위는?**

---

## 3. 기술적 질문

### Q1. 자동 상품 등록 - 진행해야 할까요?

네이버 Commerce API로 상품 자동 등록이 가능하지만:
- 이미지 호스팅 문제
- 카테고리 매핑 복잡도
- 검수 정책 리스크

**의견 요청**: "지금 하기엔 리스크가 높다"는 이전 피드백이 있었는데, Phase 6에서도 후순위로 유지해야 할까요?

### Q2. 가격 모니터링 범위

- A) 특정 상품 URL만 모니터링 (단순)
- B) 키워드 검색 결과 전체 모니터링 (복잡)

**질문**: 1인 운영 기준, 어느 방식이 더 실용적일까요?

### Q3. 테스트 코드 작성

현재 테스트 코드가 부족합니다.

- 핵심 로직 (마진 계산기) 유닛 테스트 추가 필요
- Pytest 기반으로 작성 예정

**질문**: Phase 6 기능 개발 전에 테스트 코드를 먼저 보강해야 할까요?

---

## 4. 코드 구조 피드백 요청

### 현재 디렉토리 구조
```
src/
├── adapters/          # 외부 API 연동 (Apify)
│   └── alibaba_scraper.py
├── analyzers/         # 분석 로직
│   ├── gemini_analyzer.py
│   ├── keyword_filter.py
│   ├── preflight_check.py
│   ├── review_analyzer.py
│   └── spec_validator.py
├── api/               # Supabase 클라이언트
│   └── supabase_client.py
├── cli/               # CLI 인터페이스
│   └── commands.py
├── domain/            # 도메인 모델
│   ├── logic.py       # LandedCostCalculator
│   └── models.py
├── generators/        # 리포트 생성
│   └── gap_reporter.py
├── importers/         # 데이터 임포트
│   └── data_importer.py
├── sourcing/          # 소싱 관련
│   └── margin_calculator.py
├── ui/                # Streamlit UI
│   └── app.py
└── utils/             # 유틸리티
    └── validators.py
```

**질문**: DDD 구조로 잘 분리되어 있을까요? 개선점이 있다면?

---

## 5. 요청 사항 요약

1. **Phase 6 우선순위** 추천
2. **자동 상품 등록** 진행 여부 조언
3. **가격 모니터링** 방식 선택 (A vs B)
4. **테스트 코드** 우선 작성 여부
5. **코드 구조** 피드백

---

## 6. 참고 링크

| 항목 | 링크 |
|------|------|
| GitHub 저장소 | https://github.com/hyunwoooim-star/smart-store-agent |
| 전체 로드맵 | https://github.com/hyunwoooim-star/smart-store-agent/blob/main/docs/ROADMAP.md |
| 현재 상태 | https://github.com/hyunwoooim-star/smart-store-agent/blob/main/docs/CURRENT_STATUS.md |

---

*작성일: 2026-01-23*
*작성자: Claude Code*
*버전: v3.5.2*
