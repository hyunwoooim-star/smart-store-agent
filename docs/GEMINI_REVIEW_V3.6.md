# Gemini CTO 피드백 요청 (v3.6.0)

## 프로젝트 현황
- **GitHub**: https://github.com/hyunwoooim-star/smart-store-agent
- **테스트**: 314개 통과 (pytest)
- **버전**: v3.6.0

## 이번 세션 완료 항목

### 1. Phase 6-3: 경쟁사 가격 추적 모듈
**파일**: `src/monitors/price_tracker.py`

```python
# 핵심 기능
- URL 기반 플랫폼 자동 감지 (네이버/쿠팡/G마켓/11번가/옥션)
- 가격 변동 감지 및 알림 (5%/15% 임계값)
- 경쟁력 분석 (내 가격 포지션)
- 가격 전략 제안 (목표 마진 + 경쟁력 균형)
```

**사용 예시**:
```python
tracker = PriceTracker()
tracker.add_product("캠핑의자", "https://smartstore.naver.com/...", 45000, my_price=42000)
alert = tracker.update_price("comp_0001", 48000)  # 자동 알림 생성
analysis = tracker.get_competitive_analysis(my_price=42000)
```

---

## 피드백 요청 사항

### Q1. 가격 변동 알림 임계값
현재 설정:
- **5% 이상**: WARNING (주의)
- **15% 이상**: CRITICAL (긴급)

**질문**: 스마트스토어 실무에서 이 임계값이 적절한가요?
- 경쟁이 치열한 카테고리는 3%도 큰 변동인지?
- 계절 상품은 30%까지도 정상 변동인지?
- 카테고리별로 다르게 설정해야 하는지?

### Q2. 가격 전략 알고리즘 검토
현재 로직:
```python
# 추천 가격 = min(경쟁사 평균 * 0.95, 목표마진 달성 최소가)
if avg_price >= min_price_for_margin:
    recommended = min(avg_price, int(avg_price * 0.95))
else:
    recommended = min_price_for_margin  # 마진 우선
```

**질문**:
- "경쟁사 평균보다 5% 저렴하게" 전략이 맞는지?
- 최저가 경쟁보다 "적정 마진 + 차별화"가 더 중요한지?
- 가격대별로 전략이 달라야 하는지? (1만원대 vs 10만원대)

### Q3. 경쟁력 분석 포지션 분류
현재 분류:
```
- 최저가: cheaper == 0
- 저가 그룹: cheaper <= 30%
- 중간 그룹: 30% < cheaper < 70%
- 고가 그룹: cheaper >= 70%
- 최고가: expensive == 0
```

**질문**: 이 분류가 의미있는 인사이트를 주는지?

### Q4. 다음 Phase 우선순위
현재 완료:
- [x] 마진 계산기 (LandedCostCalculator)
- [x] Pre-Flight Check (금지어/KC인증)
- [x] 1688 스크래핑 (Apify)
- [x] 경쟁사 가격 추적

다음 후보:
1. **Streamlit UI 개선** - 가격 추적 대시보드 추가
2. **자동 가격 모니터링** - 스케줄러로 주기적 체크
3. **알림 시스템** - 슬랙/텔레그램 연동
4. **AI 카피라이팅** - Gemini로 상세페이지 생성

**질문**: 어떤 순서로 진행하면 좋을까요?

### Q5. 테스트 커버리지
현재 314개 테스트:
- `test_landed_cost_calculator.py`: 29개 (마진 계산)
- `test_preflight_checker.py`: 48개 (금지어)
- `test_alibaba_scraper.py`: 27개 (1688 스크래핑)
- `test_price_tracker.py`: 39개 (가격 추적)
- 기타 레거시 테스트

**질문**:
- 누락된 중요 테스트 케이스가 있는지?
- 통합 테스트(E2E)가 필요한 시점인지?

---

## 코드 리뷰 요청

### price_tracker.py 핵심 로직

```python
class PriceTracker:
    ALERT_THRESHOLD_PERCENT = 5.0
    CRITICAL_THRESHOLD_PERCENT = 15.0

    def update_price(self, product_id: str, new_price: int) -> Optional[PriceAlert]:
        """가격 업데이트 및 변동 감지"""
        product = self.products[product_id]
        old_price = product.current_price

        change_percent = ((new_price - old_price) / old_price) * 100

        # 알림 레벨 결정
        if abs(change_percent) >= self.CRITICAL_THRESHOLD_PERCENT:
            alert_level = AlertLevel.CRITICAL
        elif abs(change_percent) >= self.ALERT_THRESHOLD_PERCENT:
            alert_level = AlertLevel.WARNING
        else:
            alert_level = AlertLevel.INFO

        return PriceAlert(...)

    def get_pricing_strategy(self, product_id: str, my_cost: int, target_margin: float = 30.0):
        """가격 전략 제안"""
        min_price_for_margin = int(my_cost / (1 - target_margin / 100))

        if avg_price >= min_price_for_margin:
            recommended = min(avg_price, int(avg_price * 0.95))
        else:
            recommended = min_price_for_margin

        return PricingStrategy(recommended_price=recommended, ...)
```

**리뷰 포인트**:
1. 알고리즘이 실무적으로 타당한지
2. 엣지 케이스 처리가 충분한지
3. 확장성 (멀티 마켓, 글로벌 등)

---

## 요약
- 테스트 314개 통과
- URL 기반 경쟁사 가격 추적 완료
- 다음 단계 방향성 피드백 필요

감사합니다!
