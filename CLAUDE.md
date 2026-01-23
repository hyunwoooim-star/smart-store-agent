# Smart Store Agent - Claude 프로젝트 컨텍스트

## 프로젝트 개요
AI 에이전트 기반 네이버 스마트스토어 자동화 시스템 (v3.5)

**GitHub**: https://github.com/hyunwoooim-star/smart-store-agent

## 핵심 목표
"틈새 시장 발굴 → 소싱 검증 → 콘텐츠 생성" 과정 자동화

## 현재 상태 (v3.5.2)
- **Phase 1**: 핵심 엔진 개발 ✅ 완료
- **Phase 2**: Streamlit 대시보드 ✅ 완료
- **Phase 3.5**: 1688 스크래핑 (Apify API) ✅ 완료
- **Phase 4**: Pre-Flight Check ✅ 완료
- **Phase 5.1**: 리뷰 분석 ✅ 완료
- **Phase 5.2**: Pydantic + Supabase 캐싱 ✅ 완료
- **Phase 6-1**: 엑셀 생성기 ✅ 완료
- **Phase 6-2**: 테스트 코드 보강 ← 다음
- **Phase 7**: 1688 실시간 연동 (Gemini CTO 권장 우선순위 격상)

## 기술 스택
- 오케스트레이션: Claude Code CLI
- AI 분석: Gemini 1.5 Flash
- 1688 스크래핑: **Apify API** (클라우드 스크래핑)
- 언어: Python 3.11+
- 데이터베이스: Supabase (PostgreSQL)
- UI: Streamlit

---

## Claude Code 개발 규칙

### 메모리 파일 계층
- 전역 설정: `~/.claude/CLAUDE.md`
- 프로젝트 설정: `./CLAUDE.md` (이 파일)
- 커스텀 명령어: `.claude/commands/` 폴더

### 코딩 원칙
1. **파일 먼저 읽기**: 수정 전 반드시 파일 내용 확인
2. **작은 단위 커밋**: 기능별로 커밋 분리
3. **테스트 우선**: 새 기능 추가 시 테스트 코드 함께 작성
4. **타입 힌트**: Python 타입 힌트 필수 사용

### 금지 사항
- ~~직접 크롤링/스크래핑~~ → **Apify API 사용**
- 하드코딩 상수 (MarginConfig 등 설정 클래스 사용)
- 무분별한 API 호출 (Python 사전 필터링 후 호출)

---

## 핵심 모듈 (v3.5)

### 1. alibaba_scraper.py (v3.5 - Apify API)
- 1688.com 상품 정보 자동 추출
- Apify 클라우드에서 스크래핑 (WSL 이슈 해결)
- 가격 범위 → 최대값 선택 (방어적 계산)
- Mock 스크래퍼 포함 (테스트용)

```python
from src.adapters.alibaba_scraper import scrape_1688

# 실제 스크래핑
product = await scrape_1688("https://detail.1688.com/offer/xxx.html")

# Mock 테스트
product = await scrape_1688("mock", use_mock=True)
```

### 2. preflight_check.py (v3.5 - Phase 4)
- 네이버 금지어/위험 표현 검사
- 의료/건강 효능 주장 탐지
- 최상급/과장 표현 탐지
- 안전한 대안 제시

```python
from src.analyzers.preflight_check import PreFlightChecker

checker = PreFlightChecker(strict_mode=True)
result = checker.check("최고의 다이어트 효과! 암 예방!")

if not result.passed:
    for v in result.violations:
        print(f"[{v.severity}] {v.type.value}: {v.matched_text}")
```

### 3. margin_calculator.py (프로젝트의 심장)
- 부피무게 계산: (가로×세로×높이) / 6000
- 관부가세 계산 (관세 8-13%, 부가세 10%)
- 반품 충당금 5%, 광고비 10% 포함
- 손익분기 판매가 자동 계산

### 4. gemini_analyzer.py
- 마스터 시스템 프롬프트 적용
- 불만 패턴 TOP 5 분석
- Semantic Gap 식별
- 개선 카피라이팅 생성

### 5. data_importer.py
- 아이템스카우트 엑셀 파일 파싱
- 키워드, 검색량, 경쟁강도 추출

### 6. gap_reporter.py
- opportunity_report.md 생성
- 종합 분석 리포트

---

## Streamlit 대시보드 (v3.5)

### 3개 탭 구성
1. **마진 분석**: 상품 정보 입력 → 리스크 분석
2. **1688 스크래핑**: URL 입력 → Apify로 상품 정보 추출
3. **Pre-Flight Check**: 금지어/위험 표현 검사

### 실행 방법
```bash
streamlit run src/ui/app.py
```

---

## 환경 변수 (.env)

```ini
# Apify API (1688 스크래핑)
APIFY_API_TOKEN=apify_api_xxxxxxxxx

# Google API (Gemini 분석)
GOOGLE_API_KEY=your_google_api_key

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_key
```

---

## Gemini 프롬프트 가이드

### 마스터 시스템 프롬프트
```
당신은 '10년 차 베테랑 MD'이자 '깐깐한 품질 관리자'입니다.
당신의 목표는 "사장님의 돈을 지키는 것"입니다.

[분석 원칙]
1. 비판적 사고: 판매자 상세페이지는 모두 "광고"로 가정
2. 보수적 마진: 배송비/관세/반품비는 최악의 상황 가정
3. 근거 중심: "좋아 보입니다" 금지, 숫자로 말하기
```

### JSON 출력 강제 규칙
- 마크다운/잡담/인사말 금지
- 코드 블록(```) 사용 금지
- 순수 JSON만 출력

---

## 기본 상수 (v3.5.2)

```python
exchange_rate = 195           # CNY → KRW
vat_rate = 0.10              # 부가세 10%
naver_fee_rate = 0.055       # 네이버 수수료 5.5%
return_allowance_rate = 0.05 # 반품/CS 충당금 5%
ad_cost_rate = 0.10          # 광고비 10%
volume_weight_divisor = 5000 # 부피무게 계수 (Gemini CTO 권장: 보수적 계산)
domestic_shipping = 3500     # 국내 택배비
shipping_rate_air = 8000     # 항공 배대지 kg당
cbm_rate = 75000             # 해운 CBM당 (Gemini CTO 권장)
```

## 관세율 테이블
- 가구/인테리어: 8%
- 캠핑/레저: 8%
- 의류/패션: 13%
- 전자기기: 8%
- 생활용품: 8%
- 기타: 10%

---

## Phase 3.5 전략 변경 이력

| 시도 | 결과 | 이유 |
|------|------|------|
| browser-use | ❌ | WSL 30초 타임아웃 |
| Playwright + Gemini | ❌ | Page crashed (메모리) |
| **Apify API** | ✅ | 클라우드 스크래핑, 안정적 |

---

## 주의사항
- 마진율 15% 미만은 수익성 부족으로 판정
- 부피무게가 실무게보다 큰 경우 청구무게로 적용
- MOQ 50개 이상은 구매대행 테스트 우선 권장
- **Supabase RLS 정책 확인 필수** (테스트 시 INSERT 권한)

---

## Gemini 피드백 반영 사항

| 날짜 | 피드백 | 상태 |
|------|--------|------|
| 2026-01-20 | 환율/배대지 요금 하드코딩 → 설정 주입 | ✅ 완료 |
| 2026-01-20 | Streamlit 선택 | ✅ 완료 |
| 2026-01-20 | 마스터 시스템 프롬프트 적용 | ✅ 완료 |
| 2026-01-21 | browser-use → Playwright 전환 | ✅ 완료 |
| 2026-01-22 | Playwright → **Apify API 전환** | ✅ 완료 |
| 2026-01-22 | Phase 4 Pre-Flight Check 구현 | ✅ 완료 |
| 2026-01-22 | Streamlit 탭 UI 업데이트 | ✅ 완료 |
| 2026-01-23 | 부피무게 계수 6000→5000 (보수적 계산) | ✅ 완료 |
| 2026-01-23 | KC인증/전기제품 레드플래그 강화 | ✅ 완료 |
| 2026-01-23 | 손절매 룰 추천 메시지 반영 | ✅ 완료 |
| 2026-01-23 | 사용법 가이드/전략 문서 작성 | ✅ 완료 |

---

## 로드맵 링크
- 전체 로드맵: `docs/ROADMAP.md`
- 현재 상태: `docs/CURRENT_STATUS.md`
- GitHub: https://github.com/hyunwoooim-star/smart-store-agent
