"""
settings.py - 프로젝트 설정 파일 (v3.1)

환경변수 기반 설정 관리
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# 프로젝트 루트 디렉토리
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "output"
LOGS_DIR = ROOT_DIR / "logs"


@dataclass
class AppSettings:
    """애플리케이션 설정"""

    # --- API 키 (환경변수에서 로드) ---
    gemini_api_key: str = ""
    supabase_url: str = ""
    supabase_key: str = ""

    # --- 마진 계산 상수 (v3.1 확정값) ---
    exchange_rate: int = 190                    # CNY → KRW
    vat_rate: float = 0.10                      # 부가세 10%
    naver_fee_rate: float = 0.055               # 네이버 수수료 5.5%
    return_allowance_rate: float = 0.05         # 반품/CS 충당금 5%
    ad_cost_rate: float = 0.10                  # 광고비 10%
    volume_weight_divisor: int = 6000           # 부피무게 계수
    domestic_shipping: int = 3000               # 국내 택배비

    # --- 배대지 요금 (원/kg) ---
    shipping_rate_air: int = 8000               # 항공
    shipping_rate_sea: int = 3000               # 해운

    # --- 관세율 ---
    tariff_furniture: float = 0.08              # 가구/인테리어
    tariff_camping: float = 0.08                # 캠핑/레저
    tariff_fashion: float = 0.13                # 의류/패션
    tariff_electronics: float = 0.08            # 전자기기
    tariff_living: float = 0.08                 # 생활용품
    tariff_default: float = 0.10                # 기타

    # --- 필터링 기준 ---
    min_search_volume: int = 1000               # 최소 월간 검색량
    max_competition_rate: float = 5.0           # 최대 경쟁강도
    min_margin_percent: float = 15.0            # 최소 마진율

    # --- Gemini 설정 ---
    gemini_model: str = "gemini-1.5-flash"
    gemini_max_tokens: int = 8192
    gemini_temperature: float = 0.7

    # --- 기타 ---
    debug_mode: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "AppSettings":
        """환경변수에서 설정 로드"""
        return cls(
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            supabase_url=os.getenv("SUPABASE_URL", ""),
            supabase_key=os.getenv("SUPABASE_KEY", ""),
            debug_mode=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    def get_tariff_rate(self, category: str) -> float:
        """카테고리별 관세율 반환"""
        tariff_map = {
            "가구/인테리어": self.tariff_furniture,
            "캠핑/레저": self.tariff_camping,
            "의류/패션": self.tariff_fashion,
            "전자기기": self.tariff_electronics,
            "생활용품": self.tariff_living,
        }
        return tariff_map.get(category, self.tariff_default)

    def validate(self) -> list:
        """설정 유효성 검사"""
        errors = []

        if not self.gemini_api_key:
            errors.append("GEMINI_API_KEY가 설정되지 않았습니다.")

        if self.exchange_rate <= 0:
            errors.append("환율은 0보다 커야 합니다.")

        if not (0 <= self.vat_rate <= 1):
            errors.append("부가세율은 0~1 사이여야 합니다.")

        return errors


# 전역 설정 인스턴스
settings = AppSettings.from_env()


# --- 카테고리 목록 ---
CATEGORIES = [
    "가구/인테리어",
    "캠핑/레저",
    "의류/패션",
    "전자기기",
    "생활용품",
    "기타",
]


# --- 배송 방법 ---
SHIPPING_METHODS = ["항공", "해운"]


# --- 리스크 레벨 ---
RISK_LEVELS = {
    "LOW": {"min_margin": 30, "color": "green"},
    "MEDIUM": {"min_margin": 15, "color": "yellow"},
    "HIGH": {"min_margin": 0, "color": "red"},
}


def get_settings() -> AppSettings:
    """설정 인스턴스 반환"""
    return settings


def reload_settings() -> AppSettings:
    """설정 다시 로드"""
    global settings
    settings = AppSettings.from_env()
    return settings


# --- 테스트 ---
if __name__ == "__main__":
    print("="*50)
    print("⚙️ 설정 확인")
    print("="*50)

    s = get_settings()

    print(f"\n[API 키]")
    print(f"  Gemini: {'설정됨' if s.gemini_api_key else '미설정'}")
    print(f"  Supabase: {'설정됨' if s.supabase_url else '미설정'}")

    print(f"\n[마진 계산 상수]")
    print(f"  환율: {s.exchange_rate}원/CNY")
    print(f"  부가세: {s.vat_rate*100}%")
    print(f"  네이버 수수료: {s.naver_fee_rate*100}%")
    print(f"  반품 충당금: {s.return_allowance_rate*100}%")
    print(f"  광고비: {s.ad_cost_rate*100}%")

    print(f"\n[유효성 검사]")
    errors = s.validate()
    if errors:
        for e in errors:
            print(f"  ⚠️ {e}")
    else:
        print("  ✅ 모든 설정 유효")

    print("="*50)
