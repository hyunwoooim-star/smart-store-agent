# Smart Store Agent - 현재 상태 (2026-01-22)

## 📍 현재 위치: Phase 3.5 완료 (Apify 전환)

### GitHub
https://github.com/hyunwoooim-star/smart-store-agent

### 클론 명령어
```bash
git clone https://github.com/hyunwoooim-star/smart-store-agent.git
cd smart-store-agent
```

---

## ✅ 완료된 작업

### Phase 1: 핵심 엔진 (완료)
- margin_calculator, data_importer, keyword_filter 등 6개 모듈
- LandedCostCalculator (구매대행 수수료, 관부가세 포함)

### Phase 2: Streamlit 대시보드 (완료)
- `streamlit_app.py`

### Phase 3.5: 1688 스크래퍼 (전략 전환 완료)
- ❌ ~~browser-use~~ (WSL 30초 타임아웃)
- ❌ ~~Playwright + Gemini~~ (WSL Page crashed)
- ✅ **Apify API로 전환** (클라우드 스크래핑)

**변경사항:**
- `alibaba_scraper.py` → Apify Client 기반으로 전면 재작성
- `test_browser.py` → 브라우저 옵션 제거, API 전용으로 단순화
- `requirements.txt` → playwright/browser-use 제거, apify-client 추가
- `.env.example` → APIFY_API_TOKEN 추가

---

## 🟢 현재 상태

### WSL 브라우저 이슈 해결됨
- 로컬 브라우저 필요 없음
- Apify 클라우드에서 스크래핑 처리
- Anti-bot 우회는 Apify가 담당

### 남은 작업
1. **Apify 계정 설정**
   - https://console.apify.com/sign-up 가입
   - Settings > Integrations에서 API Token 복사
   - `.env` 파일에 `APIFY_API_TOKEN=apify_api_xxx` 추가

2. **실제 1688 URL 테스트**
   ```bash
   python test_browser.py --url "https://detail.1688.com/offer/xxx.html"
   ```

3. **마진 계산 통합 테스트**

---

## 📁 주요 파일 위치

| 파일 | 설명 |
|------|------|
| `src/adapters/alibaba_scraper.py` | 1688 스크래퍼 (**Apify API**) |
| `test_browser.py` | 스크래퍼 테스트 CLI |
| `src/domain/logic.py` | LandedCostCalculator |
| `streamlit_app.py` | 대시보드 |
| `.env` | API 키 (**APIFY_API_TOKEN** 필수) |

---

## 🛠️ 환경 설정

### 1. 의존성 설치
```bash
pip install apify-client python-dotenv
```

### 2. API Token 설정
```ini
# .env 파일
APIFY_API_TOKEN=apify_api_xxxxxxxxxxxx
```

### 3. 테스트 실행
```bash
# Mock 테스트 (API 키 없이)
python test_browser.py --mock

# 실제 테스트 (Apify API 키 필요)
python test_browser.py --url "https://detail.1688.com/offer/xxx.html"
```

---

## 📋 Phase 3.5 전략 변경 이력

| 날짜 | 시도 | 결과 |
|------|------|------|
| 01-20 | browser-use | ❌ WSL 30초 타임아웃 |
| 01-21 | Playwright + Gemini | ❌ Page crashed (메모리) |
| 01-22 | **Apify API** | ✅ **채택** |

### Apify 선택 이유
1. **안정성**: 클라우드 실행, 로컬 리소스 0%
2. **Anti-bot 우회**: Apify가 프록시/CAPTCHA 처리
3. **비용**: 무료 플랜으로 테스트 가능
4. **속도**: WSL 환경 제약 없음

---

## 💰 예상 비용 (Apify)

| 사용량 | 월 비용 |
|--------|---------|
| 테스트 (100건) | 무료 |
| 소규모 (500건) | ~$5 |
| 중규모 (1000건) | ~$10 |

---

## 💡 다음 단계 (Phase 4 예정)

1. Pre-Flight Check (네이버 금지어 검사)
2. 자동 상품 등록 파이프라인
3. Streamlit 대시보드에 1688 스크래핑 통합

---

*마지막 업데이트: 2026-01-22*
*전략 변경: Playwright → Apify API*
