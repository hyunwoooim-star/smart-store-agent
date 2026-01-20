# Smart Store Agent - 현재 상태 (2026-01-21)

## 📍 현재 위치: Phase 3.5 테스트 중

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

### Phase 3.5: 1688 스크래퍼 (진행중)
- ✅ browser-use → Playwright + Gemini 하이브리드 전환
- ✅ `alibaba_scraper.py` 재작성
- ✅ WSL 브라우저 의존성 설치 완료
- ⏳ Playwright 페이지 로딩 테스트 중 (Page crashed 이슈)

---

## 🔴 현재 이슈

### 1. Playwright "Page crashed" 오류
WSL에서 Chromium 실행 시 메모리 이슈 발생 가능

**다음 시도:**
- 메모리 관련 Chromium 플래그 추가
- 또는 Windows 네이티브 Python으로 전환

### 2. Gemini API 할당량
- gemini-2.0-flash 할당량 초과 → gemini-1.5-flash로 변경 완료

---

## 📁 주요 파일 위치

| 파일 | 설명 |
|------|------|
| `src/adapters/alibaba_scraper.py` | 1688 스크래퍼 (Playwright + Gemini) |
| `test_browser.py` | 스크래퍼 테스트 CLI |
| `src/domain/logic.py` | LandedCostCalculator |
| `streamlit_app.py` | 대시보드 |
| `.env` | API 키 (GOOGLE_API_KEY, GEMINI_API_KEY) |

---

## 🛠️ 환경 설정

### WSL 환경 (현재)
```bash
# venv 위치
~/smart-venv/.venv

# 활성화
source ~/smart-venv/.venv/bin/activate

# 프로젝트 위치
cd /mnt/c/Users/임현우/Desktop/현우\ 작업폴더/smart

# 테스트 실행
python test_browser.py --url "https://detail.1688.com/offer/1010455960182.html"
```

### 필요한 의존성 (WSL)
```bash
sudo apt-get install -y libnss3 libnspr4 libasound2
pip install playwright beautifulsoup4 langchain-google-genai
playwright install chromium
```

---

## 📋 다음 할 일

1. **Page crashed 해결**
   - Chromium 메모리 플래그 추가 (`--disable-gpu`, `--single-process`)
   - 또는 Windows 네이티브 Python 환경 구성

2. **실제 1688 URL 테스트 성공 확인**

3. **마진 계산 통합 테스트**

---

## 💡 참고

- Gemini 피드백: Option B (Playwright + Gemini) 전략 채택
- browser-use 제거 이유: WSL 30초 타임아웃 이슈
- 전략: "브라우징은 Playwright(기계), 독해는 Gemini(AI)"

---

*마지막 업데이트: 2026-01-21*
