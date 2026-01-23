# Smart Store Agent - 전체 로드맵

**버전**: v3.5.2
**최종 업데이트**: 2026-01-23
**GitHub**: https://github.com/hyunwoooim-star/smart-store-agent

---

## 프로젝트 목표
"틈새 시장 발굴 → 소싱 검증 → 콘텐츠 생성" 과정 자동화

---

## 진행 현황

```
[완료] Phase 1   - 핵심 엔진 개발
[완료] Phase 2   - Streamlit 대시보드
[완료] Phase 3.5 - 1688 스크래핑 (Apify API)
[완료] Phase 4   - Pre-Flight Check (금지어 검사)
[완료] Phase 5.2 - Pydantic + Supabase 캐싱
[예정] Phase 6   - 비즈니스 확장
```

---

## Phase 1: 핵심 엔진 (완료)

### 구현 모듈
| 모듈 | 파일 | 기능 |
|------|------|------|
| 마진 계산기 | `margin_calculator.py` | 부피무게, 관부가세, 손익분기 |
| 데이터 임포터 | `data_importer.py` | 아이템스카우트 엑셀 파싱 |
| 키워드 필터 | `keyword_filter.py` | 부정 키워드 기반 필터링 |
| Gemini 분석기 | `gemini_analyzer.py` | AI 리뷰 분석 |
| 스펙 검증기 | `spec_validator.py` | 카피 vs 실제 스펙 검증 |
| 리포트 생성기 | `gap_reporter.py` | opportunity_report.md |

---

## Phase 2: Streamlit 대시보드 (완료)

### 3개 탭 구성
1. **마진 분석** - 상품 정보 입력 → 손익분기 계산
2. **1688 스크래핑** - URL 입력 → 상품 정보 추출
3. **Pre-Flight Check** - 금지어/위험 표현 검사

### 실행
```bash
streamlit run src/ui/app.py
```

---

## Phase 3.5: 1688 스크래핑 (완료)

### 전략 변경 이력
| 시도 | 결과 | 이유 |
|------|------|------|
| browser-use | X | WSL 30초 타임아웃 |
| Playwright + Gemini | X | Page crashed (메모리) |
| **Apify API** | O | 클라우드 스크래핑, 안정적 |

### 최종 구현
- `alibaba_scraper.py` - Apify Client 기반
- 로컬 브라우저 불필요, Anti-bot 우회는 Apify가 처리

---

## Phase 4: Pre-Flight Check (완료)

### 기능
- 네이버 금지어 검사
- 의료/건강 효능 주장 탐지
- 최상급/과장 표현 탐지
- 안전한 대안 제시

### 파일
- `preflight_check.py`

---

## Phase 5: 리뷰 분석 + 안정성 (완료)

### Phase 5.1: 리뷰 분석
- `review_analyzer.py`
- 불만 패턴 TOP 5 추출
- 개선 카피라이팅 제안
- 공장 요청 사항 도출

### Phase 5.2: 안정성 강화
- `validators.py` - Pydantic 모델 + Retry 로직
- `supabase_client.py` - 캐싱 레이어 (API 비용 절감)

---

## Phase 6: 비즈니스 확장 (예정)

### 우선순위
| 순위 | 기능 | 비즈니스 가치 |
|------|------|--------------|
| 1 | 경쟁사 가격 모니터링 | 높음 |
| 2 | Slack/Email 알림 | 중간 |
| 3 | 자동 상품 등록 | 높음 (리스크도 높음) |

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| 오케스트레이션 | Claude Code CLI |
| AI 분석 | Gemini 1.5 Flash |
| 1688 스크래핑 | Apify API |
| UI | Streamlit |
| 데이터베이스 | Supabase (PostgreSQL) |
| 언어 | Python 3.11+ |

---

## 환경 변수

```ini
# .env
APIFY_API_TOKEN=apify_api_xxx
GOOGLE_API_KEY=your_google_api_key
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_key
```

---

## 마진 계산 공식

```
총비용 = 상품원가 + 관세 + 부가세 + 배대지 + 국내택배 + 네이버수수료 + 반품충당금 + 광고비
손익분기 = 고정비용 / (1 - 변동비율)
변동비율 = 5.5%(네이버) + 5%(반품) + 10%(광고) = 20.5%
```

### 기본 상수
- 환율: 195원/CNY
- 네이버 수수료: 5.5%
- 반품/CS 충당금: 5%
- 광고비: 10%
- 부피무게 계수: 6000

---

## 주의사항

- 마진율 15% 미만 = 수익성 부족
- 부피무게 > 실무게 → 부피무게로 청구
- MOQ 50개 이상 → 구매대행 테스트 우선
