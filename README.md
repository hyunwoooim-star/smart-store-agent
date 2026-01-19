# Smart Store Agent v3.1

AI 에이전트 기반 네이버 스마트스토어 자동화 시스템

## 핵심 목표

"틈새 시장 발굴 → 소싱 검증 → 콘텐츠 생성" 과정 자동화

## 주요 기능

### 1. 마진 계산기 (margin_calculator.py)
- 부피무게 자동 계산 및 청구무게 적용
- 숨겨진 비용 반영 (반품충당금 5%, 광고비 10%)
- 손익분기점(BEP) 및 목표 마진 판매가 자동 산출
- 2-Track 전략 추천 (셀플링 vs 사입)

### 2. 데이터 임포터 (data_importer.py)
- 아이템스카우트 엑셀 파일 파싱
- 키워드, 검색량, 경쟁강도 추출
- 기회 점수 자동 계산

### 3. 키워드 필터 (keyword_filter.py)
- 부정 키워드 기반 리뷰 필터링
- False positive 패턴 방어
- 불만 카테고리 분류

### 4. Gemini 분석기 (gemini_analyzer.py)
- 불만 패턴 TOP 5 분석
- Semantic Gap 식별
- 개선 카피라이팅 생성
- 스펙 체크리스트 추출

### 5. 스펙 검증기 (spec_validator.py)
- AI 생성 카피 ↔ 실제 스펙 일치 검증
- 허위/과장 광고 방지
- 검증 리포트 생성

### 6. 리포트 생성기 (gap_reporter.py)
- opportunity_report.md 생성
- 종합 분석 리포트 출력
- 마크다운/JSON 포맷 지원

## 기술 스택

- **오케스트레이션**: Claude Code CLI
- **AI 분석**: Gemini 1.5 Flash
- **언어**: Python 3.11+
- **데이터베이스**: Supabase (PostgreSQL) - 향후 확장

## 설치 방법

```bash
# 클론
git clone https://github.com/your-repo/smart-store-agent.git
cd smart-store-agent

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일에 API 키 입력
```

## 사용 방법

### 데모 실행
```bash
python src/main.py --demo
```

### 상품 분석
```bash
python src/main.py \
    --product "캠핑의자" \
    --category "캠핑/레저" \
    --price-cny 45 \
    --weight 2.5 \
    --dimensions "80x20x15" \
    --moq 50 \
    --target-price 45000
```

### 키워드 파일과 함께 분석
```bash
python src/main.py \
    --product "캠핑의자" \
    --excel data/keywords.xlsx \
    --target-price 45000
```

## 핵심 상수 (v3.1 확정값)

| 항목 | 값 | 설명 |
|------|-----|------|
| EXCHANGE_RATE | 190 | 위안/원 환율 |
| VAT_RATE | 10% | 부가세율 |
| NAVER_FEE_RATE | 5.5% | 네이버 수수료 |
| RETURN_ALLOWANCE_RATE | 5% | 반품/CS 충당금 |
| AD_COST_RATE | 10% | 광고비 |
| VOLUME_WEIGHT_DIVISOR | 6000 | 부피무게 계수 |
| DOMESTIC_SHIPPING | 3000원 | 국내 택배비 |

## 관세율 테이블

| 카테고리 | 관세율 |
|----------|--------|
| 가구/인테리어 | 8% |
| 캠핑/레저 | 8% |
| 의류/패션 | 13% |
| 전자기기 | 8% |
| 생활용품 | 8% |
| 기타 | 10% |

## 마진 계산 공식

```
총비용 = 상품원가 + 관세 + 부가세 + 배대지비용 + 국내택배 + 네이버수수료 + 반품충당금 + 광고비

손익분기 판매가 = 고정비용 / (1 - 변동비율)
변동비율 = 5.5% + 5% + 10% = 20.5%
```

## 프로젝트 구조

```
smart/
├── src/
│   ├── sourcing/
│   │   └── margin_calculator.py    # 마진 계산기
│   ├── importers/
│   │   └── data_importer.py        # 데이터 임포터
│   ├── analyzers/
│   │   ├── keyword_filter.py       # 키워드 필터
│   │   ├── gemini_analyzer.py      # Gemini AI 분석
│   │   └── spec_validator.py       # 스펙 검증
│   ├── generators/
│   │   └── gap_reporter.py         # 리포트 생성
│   └── main.py                     # 오케스트레이션
├── tests/                          # 테스트 파일
├── data/                           # 데이터 파일
├── output/                         # 출력 파일
├── .github/workflows/              # GitHub Actions
├── requirements.txt
├── .env.example
└── README.md
```

## 테스트 실행

```bash
# 전체 테스트
pytest tests/ -v

# 커버리지 포함
pytest tests/ -v --cov=src
```

## 주의사항

- 마진율 15% 미만은 수익성 부족으로 판정
- 부피무게가 실무게보다 큰 경우 청구무게로 적용
- MOQ 50개 이상은 구매대행 테스트 우선 권장
- 크롤링 금지 → 엑셀 업로드 방식
- Gemini API 비용 최적화 → Python 사전 필터링
- 허위광고 방지 → 스펙 검증 필수

## 라이선스

MIT License

## 기여

Pull Request 환영합니다!
