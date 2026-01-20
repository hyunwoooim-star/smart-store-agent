# Smart Store Agent - Claude 프로젝트 컨텍스트

## 프로젝트 개요
AI 에이전트 기반 네이버 스마트스토어 자동화 시스템 (v3.2)

**GitHub**: https://github.com/hyunwoooim-star/smart-store-agent

## 핵심 목표
"틈새 시장 발굴 → 소싱 검증 → 콘텐츠 생성" 과정 자동화

## 현재 상태
- **Phase 1**: 핵심 엔진 개발 ✅ 완료
- **Phase 1.5**: 통합 테스트 ← 현재
- **Phase 2**: Streamlit 대시보드 (예정)
- **Phase 3**: Browser-Use + Gemini Vision 자동화 (예정)
- **Phase 4**: 비즈니스 확장 (예정)

## 기술 스택
- 오케스트레이션: Claude Code CLI
- AI 분석: Gemini 1.5 Flash (+ Vision for Phase 3)
- 브라우저 자동화: Browser-Use (Phase 3)
- 언어: Python 3.11+
- 데이터베이스: Supabase (PostgreSQL)
- UI: Streamlit (Phase 2)

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
- 크롤링/스크래핑 (엑셀 업로드 방식 사용)
- 하드코딩 상수 (MarginConfig 등 설정 클래스 사용)
- 무분별한 API 호출 (Python 사전 필터링 후 호출)

---

## Gemini 프롬프트 가이드 (v3.2)

### 마스터 시스템 프롬프트
gemini_analyzer.py에 적용된 기본 페르소나:
```
당신은 '10년 차 베테랑 MD'이자 '깐깐한 품질 관리자'입니다.
당신의 목표는 "사장님의 돈을 지키는 것"입니다.

[분석 원칙]
1. 비판적 사고: 판매자 상세페이지는 모두 "광고"로 가정
2. 보수적 마진: 배송비/관세/반품비는 최악의 상황 가정
3. 근거 중심: "좋아 보입니다" 금지, 숫자로 말하기
```

### 상황별 프롬프트 치트키

| 상황 | 프롬프트 예시 |
|------|---------------|
| **시장 분석** | "리뷰 50개에서 '단순 변심' 제외, '구조적 결함'만 3가지 뽑아. 공장에 뭐라고 요청해야 하는지 전문 용어로." |
| **카피라이팅** | "'최고예요' 같은 뻔한 말 빼. 고객이 '불안 해소됐다' 느낄 수 있는 문제 해결 중심 헤드카피 5개." |
| **이미지 생성** | "소구점 강조할 연출컷 아이디어 줘. Midjourney 영어 프롬프트로 변환해줘." |

### JSON 출력 강제 규칙
- 마크다운/잡담/인사말 금지
- 코드 블록(```) 사용 금지
- 순수 JSON만 출력

---

## 핵심 모듈

### 1. data_importer.py
- 아이템스카우트 엑셀 파일 파싱
- 키워드, 검색량, 경쟁강도 추출

### 2. margin_calculator.py (v3.2 - 프로젝트의 심장)
- 부피무게 계산: (가로×세로×높이) / 6000
- 관부가세 계산 (관세 8-13%, 부가세 10%)
- 반품 충당금 5%, 광고비 10% 포함
- 손익분기 판매가 자동 계산
- **v3.2**: MarginConfig 설정 주입 방식

### 3. keyword_filter.py
- 부정 키워드 기반 리뷰 필터링
- False positive 패턴 방어

### 4. gemini_analyzer.py (v3.2)
- **마스터 시스템 프롬프트 적용**
- 불만 패턴 TOP 5 분석
- Semantic Gap 식별
- 개선 카피라이팅 생성
- 스펙 체크리스트 추출

### 5. spec_validator.py
- AI 생성 카피 ↔ 실제 스펙 일치 검증
- 허위/과장 광고 방지
- **Phase 4 예정**: Pre-Flight Check (네이버 금지어 검사)

### 6. gap_reporter.py
- opportunity_report.md 생성
- 종합 분석 리포트

---

## 설정 주입 방식 (v3.2)
```python
from src.sourcing.margin_calculator import MarginCalculator, MarginConfig

# 커스텀 설정 (환율 변동, 배대지 요금 인상 대응)
config = MarginConfig(
    exchange_rate=195,        # 환율 변경
    shipping_rate_air=9000,   # 배대지 요금 인상
    ad_cost_rate=0.15         # 광고비 비율 조정
)
calculator = MarginCalculator(config=config)
```

## 기본 상수 (MarginConfig 기본값)
```python
exchange_rate = 190           # CNY → KRW
vat_rate = 0.10              # 부가세 10%
naver_fee_rate = 0.055       # 네이버 수수료 5.5%
return_allowance_rate = 0.05 # 반품/CS 충당금 5%
ad_cost_rate = 0.10          # 광고비 10%
volume_weight_divisor = 6000 # 부피무게 계수
domestic_shipping = 3000     # 국내 택배비
shipping_rate_air = 8000     # 항공 배대지 kg당
shipping_rate_sea = 3000     # 해운 배대지 kg당
```

## 관세율 테이블
- 가구/인테리어: 8%
- 캠핑/레저: 8%
- 의류/패션: 13%
- 전자기기: 8%
- 생활용품: 8%
- 기타: 10%

## 마진 계산 공식
```
총비용 = 상품원가 + 관세 + 부가세 + 배대지비용 + 국내택배 + 네이버수수료 + 반품충당금 + 광고비
손익분기 판매가 = 고정비용 / (1 - 변동비율)
변동비율 = 5.5% + 5% + 10% = 20.5%
```

---

## Browser-Use 자동화 (Phase 3 예정)

### 개요
- AI가 브라우저를 "보고(Vision)", "클릭"하고, "입력"하는 자동화
- API 없는 사이트(1688, 타오바오)도 자동화 가능
- Playwright 기반 + LLM 연동

### 사용 예시
```python
from browser_use import Agent

agent = Agent(
    task="1688에서 '캠핑의자' 검색하고 최저가 공장 3곳 찾아줘",
    llm=gemini_model
)
result = await agent.run()
```

### 주의사항
- 속도가 느림 (사람처럼 동작)
- API 호출 비용 발생 (화면 캡처 전송)
- 개발 시: Claude Code + Chrome MCP
- 운영 시: Browser-Use 라이브러리

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
| 2026-01-20 | Supabase RLS 정책 주의 | ✅ 문서화 |
| 2026-01-20 | Streamlit 선택 (신의 한 수) | ✅ 결정 |
| 2026-01-20 | Phase 2 변수 설정 UI 최우선 | ✅ 계획 |
| 2026-01-20 | Phase 3 Gemini Vision + Browser-Use | ✅ 계획 |
| 2026-01-20 | Phase 4 Pre-Flight Check | ✅ 계획 |
| 2026-01-20 | 마스터 시스템 프롬프트 적용 | ✅ 완료 |
| 2026-01-20 | 프롬프트 치트키 문서화 | ✅ 완료 |

---

## 로드맵 링크
- 전체 로드맵: `docs/ROADMAP.md`
- GitHub: https://github.com/hyunwoooim-star/smart-store-agent/blob/main/docs/ROADMAP.md
