"""
config.py - Smart Store Agent 설정 (v3.1)

모든 상수와 설정값을 중앙 관리
"""

import os
from dataclasses import dataclass
from typing import Dict

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ============================================================
# 핵심 상수 (v3.1 확정값 - 변경 금지)
# ============================================================

@dataclass(frozen=True)
class MarginConstants:
    """마진 계산 상수"""
    EXCHANGE_RATE: float = 190          # CNY → KRW 환율
    VAT_RATE: float = 0.10              # 부가세율 10%
    NAVER_FEE_RATE: float = 0.055       # 네이버 수수료 5.5%
    RETURN_ALLOWANCE_RATE: float = 0.05 # 반품/CS 충당금 5%
    AD_COST_RATE: float = 0.10          # 광고비 10%
    VOLUME_WEIGHT_DIVISOR: int = 6000   # 부피무게 계수
    DOMESTIC_SHIPPING: int = 3000       # 국내 택배비 (원)
    MIN_VIABLE_MARGIN: float = 15.0     # 최소 수익성 마진율 (%)


@dataclass(frozen=True)
class TariffRates:
    """카테고리별 관세율"""
    FURNITURE: float = 0.08         # 가구/인테리어
    CAMPING: float = 0.08           # 캠핑/레저
    CLOTHING: float = 0.13          # 의류/패션
    ELECTRONICS: float = 0.08       # 전자기기
    HOUSEHOLD: float = 0.08         # 생활용품
    DEFAULT: float = 0.10           # 기타

    @classmethod
    def get_rate(cls, category: str) -> float:
        """카테고리별 관세율 반환"""
        rates = {
            "가구/인테리어": cls.FURNITURE,
            "캠핑/레저": cls.CAMPING,
            "의류/패션": cls.CLOTHING,
            "전자기기": cls.ELECTRONICS,
            "생활용품": cls.HOUSEHOLD,
        }
        return rates.get(category, cls.DEFAULT)


@dataclass(frozen=True)
class ShippingRates:
    """배대지 배송비 (kg당, 원)"""
    # 실제 배대지 업체별로 다름 - 예시값
    RATE_PER_KG: int = 4000         # 기본 kg당 요금
    FIRST_KG_RATE: int = 6000       # 첫 1kg 요금
    MINIMUM_CHARGE: int = 6000       # 최소 배송비

    @classmethod
    def calculate(cls, weight_kg: float) -> int:
        """청구무게 기준 배송비 계산"""
        if weight_kg <= 0:
            return cls.MINIMUM_CHARGE

        if weight_kg <= 1:
            return cls.FIRST_KG_RATE

        # 첫 1kg + 추가 kg
        additional_kg = weight_kg - 1
        total = cls.FIRST_KG_RATE + int(additional_kg * cls.RATE_PER_KG)
        return max(total, cls.MINIMUM_CHARGE)


# ============================================================
# 환경 설정
# ============================================================

class Config:
    """환경 설정"""

    # API Keys (환경변수에서 로드)
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")

    # Gemini 설정
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_MAX_TOKENS: int = 4096

    # 출력 설정
    OUTPUT_DIR: str = os.environ.get("OUTPUT_DIR", "output")
    REPORT_FORMAT: str = "markdown"  # "markdown" or "json"

    # 필터링 기본값
    MIN_SEARCH_VOLUME: int = 1000   # 최소 월간 검색량
    MAX_COMPETITION_RATE: float = 5.0  # 최대 경쟁강도

    # 분석 설정
    MAX_REVIEWS_FOR_ANALYSIS: int = 50  # Gemini에 전달할 최대 리뷰 수
    TOP_KEYWORDS_COUNT: int = 20        # 상위 키워드 수

    @classmethod
    def is_gemini_configured(cls) -> bool:
        """Gemini API 설정 여부"""
        return bool(cls.GEMINI_API_KEY)

    @classmethod
    def is_supabase_configured(cls) -> bool:
        """Supabase 설정 여부"""
        return bool(cls.SUPABASE_URL and cls.SUPABASE_KEY)

    @classmethod
    def get_status(cls) -> Dict[str, bool]:
        """설정 상태 반환"""
        return {
            "gemini_configured": cls.is_gemini_configured(),
            "supabase_configured": cls.is_supabase_configured(),
        }


# ============================================================
# 부정 키워드 사전
# ============================================================

NEGATIVE_KEYWORDS = {
    "품질": ["품질이 별로", "품질 나쁨", "품질 떨어", "저렴한 느낌", "싸구려"],
    "내구성": ["금방 망가", "쉽게 부러", "내구성 약", "오래 못", "며칠 만에"],
    "마감": ["마감 별로", "마감 불량", "뜯어짐", "실밥", "접착 불량"],
    "배송": ["배송 느림", "배송 늦", "배송 지연", "안 와", "분실"],
    "포장": ["포장 엉망", "포장 불량", "찢어져", "박스 훼손"],
    "설명불일치": ["사진과 다름", "설명과 다름", "색상 다름", "사이즈 다름", "다른 제품"],
    "불편": ["불편", "사용하기 어려", "복잡", "설명서 없"],
    "소음": ["소음", "시끄러", "삐걱"],
    "냄새": ["냄새", "악취", "화학 냄새"],
    "가격": ["비싸", "가격 대비", "돈 아까", "환불"],
    "실망": ["실망", "후회", "다신 안", "비추", "별로"],
}

POSITIVE_KEYWORDS = [
    "좋아요", "만족", "추천", "최고", "훌륭", "완벽",
    "가성비", "빠른 배송", "친절", "재구매", "굿",
]

FALSE_POSITIVE_PATTERNS = [
    r"품질이?\s*(좋|훌륭|최고)",
    r"품질\s*대비\s*(좋|괜찮|만족)",
    r"생각보다\s*(좋|괜찮|만족)",
    r"배송\s*(빠름|빨라|좋)",
    r"가격\s*대비\s*(좋|만족|훌륭)",
]


# ============================================================
# 버전 정보
# ============================================================

VERSION = "3.1.0"
VERSION_NAME = "Smart Store Agent"
VERSION_FULL = f"{VERSION_NAME} v{VERSION}"


# --- 테스트 ---
if __name__ == "__main__":
    print("="*60)
    print(f"⚙️ {VERSION_FULL} 설정")
    print("="*60)

    print("\n[마진 계산 상수]")
    mc = MarginConstants()
    print(f"  - 환율: {mc.EXCHANGE_RATE} 원/CNY")
    print(f"  - 부가세율: {mc.VAT_RATE * 100}%")
    print(f"  - 네이버 수수료: {mc.NAVER_FEE_RATE * 100}%")
    print(f"  - 반품 충당금: {mc.RETURN_ALLOWANCE_RATE * 100}%")
    print(f"  - 광고비: {mc.AD_COST_RATE * 100}%")
    print(f"  - 부피무게 계수: {mc.VOLUME_WEIGHT_DIVISOR}")

    print("\n[관세율]")
    for cat in ["캠핑/레저", "의류/패션", "전자기기", "기타"]:
        rate = TariffRates.get_rate(cat)
        print(f"  - {cat}: {rate * 100}%")

    print("\n[배송비 예시]")
    for kg in [0.5, 1.0, 2.5, 4.0, 10.0]:
        cost = ShippingRates.calculate(kg)
        print(f"  - {kg}kg: {cost:,}원")

    print("\n[환경 설정]")
    status = Config.get_status()
    print(f"  - Gemini API: {'✅ 설정됨' if status['gemini_configured'] else '❌ 미설정'}")
    print(f"  - Supabase: {'✅ 설정됨' if status['supabase_configured'] else '❌ 미설정'}")

    print("\n" + "="*60)
    print("✅ 설정 파일 준비 완료")
    print("="*60 + "\n")
