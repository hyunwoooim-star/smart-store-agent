# 당장 장사 시작 계획 (Immediate Business Plan)

**작성일**: 2026-01-22
**결론**: Gemini 권장사항 수용 - 스크래핑 포기, 수동 입력 + 핵심 마진 계산 로직 활용

---

## 현재 상태

### 즉시 사용 가능
1. **CLI 마진 계산기** (`src/cli/commands.py`) - 100% 완성
2. **LandedCostCalculator** (`src/domain/logic.py`) - 핵심 경쟁력
3. **Mock 테스트** - 정상 작동 확인됨

### 작동 안 함
- 1688 자동 스크래핑 (WSL 크래시 + 봇 탐지)

---

## 실행 계획

### Phase A: CLI 테스트 (즉시)

```bash
cd C:\Users\임현우\.claude-worktrees\smart\wonderful-wu

# 데모 실행
python -m src.cli.commands demo

# 마진 계산 예시
python -m src.cli.commands calc --price-cny 45 --weight 2.5 --dimensions 80x20x15 --target-price 45000
```

### Phase B: 수동 워크플로우

1. 브라우저에서 1688.com 접속
2. 상품 검색 (예: 캠핑의자)
3. 상품 정보 수동 확인:
   - 가격 (위안)
   - 무게 (kg)
   - 사이즈 (가로x세로x높이 cm)
   - MOQ
4. CLI로 마진 계산 실행
5. 수익성 판단

### Phase C: 실제 상품 분석

관심 카테고리에서 1688 상품 10개 선정 후:
- 수동으로 정보 확인
- CLI로 마진 계산
- 수익성 높은 상품 3개 선정

---

## CLI 명령어 요약

| 명령어 | 설명 |
|--------|------|
| `demo` | 데모 모드 (캠핑의자 예시) |
| `calc` | 마진 계산 |
| `analyze` | 상품 종합 분석 |
| `filter` | 리뷰 필터링 |
| `validate` | 카피 스펙 검증 |

---

## 장기 고려사항

1. **1688 AI BUY 서비스** - 비용 대비 효과 분석
2. **환율 실시간 API** - 현재 고정값 195원/위안
3. **Streamlit UI 추가** - 웹 기반 대시보드 (선택)

---

## 핵심 메시지

> **"스크래핑은 나중에, 장사는 지금 당장!"**
>
> LandedCostCalculator가 이미 완벽하게 작동하므로,
> 1688에서 눈으로 보고 → CLI로 계산 → 판단
> 이 방식으로 **오늘 바로 시작 가능**
