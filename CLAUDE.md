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
- **Phase 3**: Gemini Vision 자동화 (예정)
- **Phase 4**: 비즈니스 확장 (예정)

## 기술 스택
- 오케스트레이션: Claude Code CLI
- AI 분석: Gemini 1.5 Flash (+ Vision for Phase 3)
- 언어: Python 3.11+
- 데이터베이스: Supabase (PostgreSQL)
- UI (예정): Streamlit

## 핵심 모듈

### 1. data_importer.py
- 아이템스카우트 엑셀 파일 파싱
- 키워드, 검색량, 경쟁강도 추출

### 2. margin_calculator.py (v3.2 - 프로젝트의 심장)
- 부피무게 계산: (가로×세로×높이) / 6000
- 관부가세 계산 (관세 8-13%, 부가세 10%)
- 반품 충당금 5%, 광고비 10% 포함
- 손익분기 판매가 자동 계산
- 2-Track 전략 추천
- **v3.2 신규**: MarginConfig 설정 주입 방식 (Streamlit UI 연동 대비)

### 3. keyword_filter.py
- 부정 키워드 기반 리뷰 필터링
- False positive 패턴 방어

### 4. gemini_analyzer.py
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

## 개발 원칙
1. 크롤링 금지 → 엑셀 업로드 방식
2. Gemini API 비용 최적화 → Python 사전 필터링
3. 허위광고 방지 → 스펙 검증 필수
4. 현실적 마진 계산 → 모든 숨겨진 비용 포함
5. **설정 유연성** → 하드코딩 대신 설정 주입 (v3.2)

## 주의사항
- 마진율 15% 미만은 수익성 부족으로 판정
- 부피무게가 실무게보다 큰 경우 청구무게로 적용
- MOQ 50개 이상은 구매대행 테스트 우선 권장
- **Supabase RLS 정책 확인 필수** (테스트 시 INSERT 권한)

## Gemini 피드백 반영 사항 (2026-01-20)
| 피드백 | 상태 |
|--------|------|
| 환율/배대지 요금 하드코딩 → 설정 주입 | ✅ 완료 |
| Supabase RLS 정책 주의 | ✅ 문서화 |
| Streamlit 선택 (신의 한 수) | ✅ 결정 |
| Phase 2 변수 설정 UI 최우선 | ✅ 계획 |
| Phase 3 Gemini Vision 활용 | ✅ 계획 |
| Phase 4 Pre-Flight Check | ✅ 계획 |

## 로드맵 링크
- 전체 로드맵: `docs/ROADMAP.md`
- GitHub: https://github.com/hyunwoooim-star/smart-store-agent/blob/main/docs/ROADMAP.md
