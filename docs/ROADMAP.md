# Smart Store Agent - 전체 로드맵 계획서

## 📊 현재 상태 (Phase 1 완료)

**GitHub**: https://github.com/hyunwoooim-star/smart-store-agent

### 완료된 작업
- [x] 핵심 모듈 6개 구현 (margin_calculator, data_importer, keyword_filter, gemini_analyzer, spec_validator, gap_reporter)
- [x] Supabase 연동 준비
- [x] 모니터링/알림 시스템
- [x] CLI 인터페이스
- [x] GitHub 저장소 생성

### Gemini 코드 리뷰 결과
- ✅ 마진 계산기: 부피무게, 숨겨진 비용, BEP 로직 정확
- ✅ Gemini 분석기: 구조화된 프롬프트, 안전장치 완비
- ✅ 오케스트레이션: 파이프라인 매끄러움, 확장성 좋음

---

## 🚀 전체 로드맵

### Phase 1.5: 통합 테스트 및 실전 검증 (즉시)
> Gemini가 권장한 "진짜 돌려보기"

| 순서 | 작업 | 설명 |
|------|------|------|
| 1 | 환경 설정 | `.env` 파일에 실제 API 키 입력 |
| 2 | 의존성 설치 | `pip install -r requirements.txt` |
| 3 | Mock 테스트 | `--mock` 플래그로 먼저 실행 |
| 4 | 실전 테스트 | Gemini API 연결 후 "캠핑의자" 시나리오 검증 |
| 5 | DB 연동 확인 | Supabase 테이블 데이터 확인 |

**검증 포인트:**
- 부피무게 4.0kg 적용 확인
- 마진율 음수(-XX%) 출력 확인
- output/ 폴더 리포트 생성 확인

---

### Phase 2: 사용자 인터페이스 (UI)
> "날개를 달자" - Flutter App 또는 웹 대시보드

#### Option A: Flutter 모바일 앱
- 장점: 모바일에서 실시간 알림, 어디서든 조회
- 단점: Flutter 학습 필요, 개발 기간 길음

#### Option B: Streamlit 웹 대시보드 (추천)
- 장점: Python만으로 빠르게 개발, 1-2일 완성 가능
- 단점: 모바일 최적화 약함

#### Option C: Notion/Slack 연동
- 장점: 개발 최소화, 익숙한 도구 사용
- 단점: 커스터마이징 한계

**예상 기능:**
- 실시간 마진 계산기 (입력 폼)
- 분석 히스토리 조회
- 리포트 다운로드
- 알림 설정

---

### Phase 3: 자동화 확장
> "눈을 달자" - 이미지 기반 소싱 자동화

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 이미지 OCR | 1688 상품 이미지에서 스펙 자동 추출 | 높음 |
| 가격 모니터링 | 경쟁사 가격 변동 추적 | 중간 |
| 리뷰 수집 자동화 | 네이버 리뷰 엑셀 자동 다운로드 | 중간 |
| 키워드 트렌드 | 검색량 변화 알림 | 낮음 |

---

### Phase 4: 비즈니스 확장
> 수익화 및 고도화

| 기능 | 설명 |
|------|------|
| 멀티 스토어 지원 | 여러 스마트스토어 계정 관리 |
| 자동 상품 등록 | 네이버 Commerce API 연동 |
| 재고 관리 | 1688 재고 ↔ 스마트스토어 연동 |
| 정산 리포트 | 월별 수익/비용 자동 집계 |

---

## 📅 권장 일정

```
Week 1: Phase 1.5 (통합 테스트) ← 지금 여기
Week 2-3: Phase 2 (Streamlit 대시보드)
Week 4-6: Phase 3 (이미지 OCR, 자동화)
Week 7+: Phase 4 (비즈니스 확장)
```

---

## ⚡ 즉시 실행 가능한 작업 (Phase 1.5)

### Step 1: .env 파일 생성
```bash
cp .env.example .env
# 편집기로 열어서 실제 키 입력
```

### Step 2: 의존성 설치
```bash
pip install -r requirements.txt
```

### Step 3: 테스트 실행
```bash
# Mock 테스트 (API 키 없이)
python src/main.py --demo

# 실전 테스트 (API 키 필요)
python src/main.py \
  --product "초경량 릴렉스 캠핑의자" \
  --category "캠핑/레저" \
  --price-cny 45 \
  --weight 2.5 \
  --dimensions "80x20x15" \
  --moq 50 \
  --target-price 45000
```

---

## 🔗 보고서용 링크

| 항목 | 링크 |
|------|------|
| **GitHub 저장소** | https://github.com/hyunwoooim-star/smart-store-agent |
| **이 계획서** | (GitHub에 업로드 예정) |

---

## ✅ 결정 사항

**Phase 2 UI: Streamlit 웹 대시보드 선택**

선택 이유:
- 나만 쓰는 용도로 적합
- Python만으로 빠르게 개발 (1-2일)
- 복잡하지 않고 간편함
- 추후 확장도 용이

---

## 📊 최종 로드맵 요약

```
[완료] Phase 1: 핵심 엔진 개발 ✅
[현재] Phase 1.5: 통합 테스트 및 실전 검증
[다음] Phase 2: Streamlit 대시보드 (1-2일)
[예정] Phase 3: 이미지 OCR 자동화
[예정] Phase 4: 비즈니스 확장
```

---

*작성일: 2026-01-20*
*버전: v3.1*
*상태: Phase 1 완료, Phase 1.5 진입 준비*
*UI 결정: Streamlit 웹 대시보드*
