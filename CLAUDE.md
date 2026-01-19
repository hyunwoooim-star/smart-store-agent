# Smart Store Agent - Claude 프로젝트 컨텍스트

## 프로젝트 개요
AI 에이전트 기반 네이버 스마트스토어 자동화 시스템 (v3.1)

## 핵심 목표
"틈새 시장 발굴 → 소싱 검증 → 콘텐츠 생성" 과정 자동화

## 기술 스택
- 오케스트레이션: Claude Code CLI
- AI 분석: Gemini 1.5 Flash
- 언어: Python 3.11+
- 데이터베이스: Supabase (PostgreSQL)

## 핵심 모듈

### 1. data_importer.py
- 아이템스카우트 엑셀 파일 파싱
- 키워드, 검색량, 경쟁강도 추출

### 2. margin_calculator.py (v3.1 - 프로젝트의 심장)
- 부피무게 계산: (가로×세로×높이) / 6000
- 관부가세 계산 (관세 8-13%, 부가세 10%)
- 반품 충당금 5%, 광고비 10% 포함
- 손익분기 판매가 자동 계산
- 2-Track 전략 추천

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

### 6. gap_reporter.py
- opportunity_report.md 생성
- 종합 분석 리포트

## 중요 상수
```python
EXCHANGE_RATE = 190  # CNY → KRW
VAT_RATE = 0.10
NAVER_FEE_RATE = 0.055
RETURN_ALLOWANCE_RATE = 0.05
AD_COST_RATE = 0.10
VOLUME_WEIGHT_DIVISOR = 6000
```

## 관세율 테이블
- 가구/인테리어: 8%
- 캠핑/레저: 8%
- 의류/패션: 13%
- 전자기기: 8%
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

## 주의사항
- 마진율 15% 미만은 수익성 부족으로 판정
- 부피무게가 실무게보다 큰 경우 청구무게로 적용
- MOQ 50개 이상은 구매대행 테스트 우선 권장
