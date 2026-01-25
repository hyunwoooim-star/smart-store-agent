# v4.4 에러 보고서 - Gemini CTO 분석 요청

**작성일**: 2026-01-25
**버전**: v4.4 이미지 검색 + 경쟁사 UI
**상태**: 에러 발생 - 분석 요청

---

## 1. 에러 내용

### 1.1 첫 번째 에러
```
AttributeError: 'AppConfig' object has no attribute 'exchange_rate_usd_cny'

File "sourcing_tab.py", line 77, in render
    price_cny = price_usd * config.exchange_rate_usd_cny
```

### 1.2 두 번째 에러 (수정 후)
```
TypeError: AppConfig.__init__() got an unexpected keyword argument 'exchange_rate_usd'

File "settings_tab.py", line 545, in get_app_config
    return AppConfig(
```

---

## 2. 코드 현황

### 2.1 config.py (수정됨)
```python
@dataclass
class AppConfig:
    # 환율
    exchange_rate: float = 195              # 원/위안 (2026년 기준)
    exchange_rate_usd: float = 1400         # 원/달러 (v4.4) ← 추가됨
    exchange_rate_usd_cny: float = 7.2      # 달러/위안 (v4.4) ← 추가됨

    # ... 나머지 필드들 ...
```

### 2.2 settings_tab.py (수정됨)
```python
def get_app_config() -> AppConfig:
    settings = get_current_settings()
    return AppConfig(
        exchange_rate=settings["exchange_rate"],
        exchange_rate_usd=settings.get("exchange_rate_usd", 1400),  # v4.4 ← 추가됨
        exchange_rate_usd_cny=settings.get("exchange_rate_usd_cny", 7.2),  # v4.4 ← 추가됨
        shipping_rate_air=settings["shipping_rate_air"],
        # ...
    )
```

### 2.3 sourcing_tab.py (수정됨)
```python
# v4.4: 플랫폼별 가격 입력
if is_aliexpress_mode:
    price_usd = st.number_input("알리익스프레스 가격 (USD)", ...)
    price_cny = price_usd * config.exchange_rate_usd_cny  # ← 여기서 에러
```

---

## 3. 의심되는 원인

### 가설 1: Streamlit 모듈 캐싱 문제
- Streamlit이 Python 모듈을 메모리에 캐싱
- config.py 파일이 수정되었지만 이전 버전(필드 없는)을 계속 사용
- 서버 재시작해도 WSL ↔ Windows 파일 동기화 지연

### 가설 2: WSL 환경 문제
- 코드는 Windows 파일시스템에 존재 (`C:\Users\...`)
- 실행은 WSL에서 (`/mnt/c/Users/...`)
- 파일 변경이 WSL에 즉시 반영되지 않을 수 있음

### 가설 3: Python bytecode 캐시 (.pyc)
- `__pycache__/config.cpython-311.pyc` 파일이 오래된 버전 유지
- 새 코드가 컴파일되지 않음

---

## 4. 시도한 해결책

1. **Streamlit 서버 재시작** → 실패
2. **config.py에 필드 확인** → 정상적으로 추가되어 있음
3. **settings_tab.py 수정** → 정상적으로 추가되어 있음

---

## 5. CTO님께 질문

### Q1. 근본 원인
```
AppConfig에 필드가 분명히 추가되어 있는데,
왜 "unexpected keyword argument" 에러가 발생하는가?

가능한 원인:
A) WSL 파일 동기화 지연
B) Python __pycache__ 문제
C) Streamlit import 캐싱
D) 다른 문제
```

**CTO님 의견?**: A / B / C / D / 기타

### Q2. 해결 방법
```
권장 해결 순서?

옵션 A: __pycache__ 폴더 삭제 후 재시작
옵션 B: WSL 재시작
옵션 C: 코드를 WSL 네이티브 경로로 이동 (/home/user/smart)
옵션 D: 필드 접근 방식 변경 (config.필드 대신 상수 사용)
옵션 E: 기타
```

**CTO님 의견?**: A / B / C / D / E

### Q3. 아키텍처 개선
```
현재 구조:
- sourcing_tab.py → get_app_config() → AppConfig 인스턴스 생성

문제:
- AppConfig 변경 시 여러 파일 수정 필요
- 캐싱 문제에 취약

대안?

옵션 A: 환율을 config.py에서 직접 상수로 export
    USD_CNY_RATE = 7.2
    sourcing_tab에서: from src.core.config import USD_CNY_RATE

옵션 B: 환율을 settings dict에서만 관리 (AppConfig 수정 안 함)
    sourcing_tab에서: settings.get("exchange_rate_usd_cny", 7.2)

옵션 C: 현재 구조 유지, 캐시 문제만 해결

옵션 D: 기타
```

**CTO님 의견?**: A / B / C / D

---

## 6. 긴급 해결 (임시)

캐시 문제 해결 전까지 임시 방안:

```python
# sourcing_tab.py에서 직접 상수 사용
USD_CNY_RATE = 7.2  # 하드코딩 (임시)

if is_aliexpress_mode:
    price_cny = price_usd * USD_CNY_RATE
```

**이 임시 방안 괜찮은가?**: Yes / No (더 나은 방법 제시)

---

## 7. 파일 구조

```
C:\Users\임현우\Desktop\현우 작업폴더\smart\
├─ src/
│  ├─ core/
│  │  └─ config.py              ← AppConfig 정의 (수정됨)
│  ├─ ui/tabs/
│  │  ├─ settings_tab.py        ← get_app_config() (수정됨)
│  │  └─ sourcing_tab.py        ← config 사용 (에러 발생)
│  └─ domain/
│     └─ logic.py               ← LandedCostCalculator
└─ docs/
   └─ v44_error_report.md       ← 이 파일
```

---

## 8. 전체 코드 참조

### config.py 전체 (83줄)
- 환율 필드: 라인 35-37
- AppConfig 클래스: 라인 27-78

### settings_tab.py 관련 부분
- get_app_config(): 라인 542-554
- get_current_settings(): 라인 526-539

### sourcing_tab.py 관련 부분
- 모드 전환: 라인 41-48
- USD 입력 및 환산: 라인 66-87
- source_platform 전달: 라인 163-171

---

**피드백 요청**: Q1~Q3 답변 및 권장 해결책 부탁드립니다!
