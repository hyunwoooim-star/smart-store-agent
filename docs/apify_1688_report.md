# Apify 1688 스크래퍼 가성비 분석 보고서

**작성일**: 2026-01-25
**버전**: v4.2 Night Crawler
**상태**: Gemini CTO 검토 요청

---

## Part 1: 현재 상황

### 1.1 문제 발생 경위

Night Crawler 테스트 중 Apify 1688 Actor 관련 이슈 발생:

```
🔄 Actor 시도: styleindexamerica/cn-1688-scraper
⚠️ Actor 오류: Actor with this name was not found

🔄 Actor 시도: ecomscrape/1688-product-search-scraper
💰 유료 Actor: ecomscrape/1688-product-search-scraper

🔄 Actor 시도: songd/1688-search-scraper
💰 유료 Actor: songd/1688-search-scraper

⚠️ 모든 Apify Actor 실패 - Mock 모드 사용
```

**결론**: 무료 1688 Actor가 존재하지 않음

---

## Part 2: Apify 1688 Actor 비교

### 2.1 발견된 Actor 목록

| Actor | 개발자 | 가격 | 특징 |
|-------|--------|------|------|
| [1688-search-scraper](https://apify.com/songd/1688-search-scraper) | songd | **$89.99/월** | 검색 기반, 1페이지=100개 상품 |
| [1688-product-search-scraper](https://apify.com/ecomscrape/1688-product-search-scraper) | ecomscrape | 유료 (금액 미확인) | 검색+상세 정보 |
| [1688-product-details-page-scraper](https://apify.com/ecomscrape/1688-product-details-page-scraper) | ecomscrape | 유료 (금액 미확인) | URL 기반 상세 스크래핑 |
| [cn-1688-scraper](https://apify.com/styleindexamerica/cn-1688-scraper) | styleindexamerica | - | **존재하지 않음** (삭제됨) |

### 2.2 가격 모델 분석

Apify Actor 가격 모델은 3가지:

1. **월정액 렌탈 (Rental)**
   - 고정 월 요금 + 플랫폼 사용료
   - 예: songd/1688-search-scraper = $89.99/월

2. **결과당 과금 (Pay Per Result)**
   - 추출된 데이터 건당 과금
   - 플랫폼 사용료 없음
   - 소량 사용시 유리

3. **이벤트당 과금 (Pay Per Event)**
   - 페이지 스크래핑, API 호출 등 액션당 과금
   - 가장 유연한 모델

### 2.3 songd/1688-search-scraper 상세

**확인된 정보:**
- 가격: $89.99/월
- 무료 체험: 2시간
- 성공률: 99%+
- 생성일: 2025년 1월
- 1페이지 = 약 100개 상품
- 최대 2000개 결과/쿼리

**기능:**
- 키워드 검색
- 가격대 필터 (min/max CNY)
- 페이지네이션 지원
- 프록시 지원

---

## Part 3: 비용 시뮬레이션

### 3.1 Night Crawler 예상 사용량

| 항목 | 일일 | 월간 |
|------|------|------|
| 키워드 수 | 10개 | 300개 |
| 키워드당 상품 | 30개 | 30개 |
| 총 상품 발굴 | 300개 | 9,000개 |

### 3.2 비용 비교

| 옵션 | 월 비용 | 상품당 비용 | 비고 |
|------|---------|-------------|------|
| **Apify songd** | $89.99 (~₩117,000) | ₩13/개 | 안정적, 즉시 사용 |
| **Apify PPR (추정)** | ~$50-100 | 변동 | 미확인 |
| **직접 개발** | ₩0 | ₩0 | 개발 시간 필요 |
| **Mock 모드** | ₩0 | - | 테스트 전용 |

---

## Part 4: 대안 분석

### 옵션 A: Apify 유료 결제 ($89.99/월)

**장점:**
- 즉시 사용 가능
- 99%+ 안정성
- 유지보수 불필요
- 프록시/IP 관리 자동

**단점:**
- 월 ₩117,000 고정 비용
- 외부 의존성
- Actor 삭제/가격 변동 리스크

### 옵션 B: 직접 스크래핑 개발 (Playwright)

**장점:**
- 무료 (개발 비용만)
- 완전한 제어권
- 커스터마이징 자유

**단점:**
- 개발 시간 필요 (추정 1-2주)
- 1688 안티봇 대응 필요
- 프록시 비용 별도
- IP 차단 리스크
- 유지보수 부담

### 옵션 C: 하이브리드 (권장?)

1. **단기**: Apify 2시간 무료 체험으로 데이터 품질 검증
2. **중기**: 결과 만족시 월정액 결제
3. **장기**: 사용량 증가시 직접 개발 검토

---

## Part 5: Gemini CTO 질문

### Q1. 1688 스크래핑 전략

```
현재 상황:
- 무료 Apify Actor 없음
- songd/1688-search-scraper = $89.99/월
- 직접 개발 = 1-2주 소요

질문:
A) Apify 유료 결제 (즉시 시작, 월 ₩117,000)
B) 직접 Playwright 개발 (무료, 시간 투자)
C) 하이브리드 (체험 후 결정)
D) 다른 대안 (예: 다른 중국 도매 플랫폼)
```

**CTO님 의견?**: A / B / C / D

---

### Q2. 비용 대비 가치

```
월 $89.99 (₩117,000) 투자 가치가 있는가?

예상 효과:
- 월 9,000개 상품 발굴
- 그 중 10% = 900개 잠재 후보
- 그 중 10% = 90개 실제 등록 가능
- 상품당 평균 마진 ₩5,000 가정
- 월 예상 추가 수익: 90 × ₩5,000 = ₩450,000

ROI: (₩450,000 - ₩117,000) / ₩117,000 = 284%
```

**CTO님 의견?**: 투자 가치 O / X / 계산 수정 필요

---

### Q3. 직접 개발시 기술 스택

```
만약 직접 개발한다면:

옵션 A: Playwright + Stealth Plugin
- 장점: 기존 Phase 3 경험 활용
- 단점: 1688 안티봇 강력

옵션 B: Scrapy + Splash
- 장점: 대량 처리 최적화
- 단점: 새로운 학습 필요

옵션 C: httpx + 역공학
- 장점: 가볍고 빠름
- 단점: API 변경시 깨짐

옵션 D: 외주 개발
- 장점: 시간 절약
- 단점: 비용 발생
```

**CTO님 의견?**: A / B / C / D / Apify 유지

---

### Q4. 플랫폼 다각화

```
1688 외에 고려할 플랫폼:

1. 타오바오 (Taobao) - 소매 중심
2. 알리익스프레스 - 해외 배송 지원
3. 핀둬둬 (Pinduoduo) - 초저가
4. Made-in-China.com - 영문 지원

질문: 1688 집중 vs 플랫폼 다각화?
```

**CTO님 의견?**: 1688 집중 / 다각화 / 기타

---

## Part 6: 현재 코드 상태

### 6.1 구현 완료

```python
# two_stage_crawler.py - 다중 Actor Fallback 전략

actors = [
    {"id": "styleindexamerica/cn-1688-scraper", ...},  # 1순위 (삭제됨)
    {"id": "ecomscrape/1688-product-search-scraper", ...},  # 2순위 (유료)
    {"id": "songd/1688-search-scraper", ...},  # 3순위 (유료)
]

# 모든 Actor 실패시 → Mock 모드 자동 전환
```

### 6.2 GitHub Actions

```yaml
# .github/workflows/night_crawler.yml
# 매일 새벽 1시 (KST) 자동 실행
# 현재: Mock 모드로 동작
```

---

## Part 7: 요약

| 항목 | 현재 상태 |
|------|----------|
| 무료 Actor | ❌ 없음 |
| 권장 유료 Actor | songd/1688-search-scraper ($89.99/월) |
| 현재 동작 | Mock 모드 (테스트용 가짜 데이터) |
| 결정 필요 | 유료 결제 vs 직접 개발 |

---

**피드백 요청**: Q1~Q4 답변 부탁드립니다!

---

## Sources

- [Apify Pricing](https://apify.com/pricing)
- [songd/1688-search-scraper](https://apify.com/songd/1688-search-scraper)
- [ecomscrape/1688-product-search-scraper](https://apify.com/ecomscrape/1688-product-search-scraper)
- [Apify Paid Actors](https://help.apify.com/en/articles/5139819-paid-actors)
- [Apify Pay Per Event](https://help.apify.com/en/articles/10700066-what-is-pay-per-event)
