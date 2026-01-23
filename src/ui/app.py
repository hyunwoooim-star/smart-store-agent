"""
app.py - Streamlit 대시보드 (v3.7.0)

Gemini CTO 피드백 반영:
- 탭별 모듈 분리 (src/ui/tabs/)
- MVP 집중: 마진 분석 + Pre-Flight + 엑셀 생성
- 1688 스크래핑: 수동 입력 우선
- 가격 추적: 운영 단계 기능 (현재 우선순위 낮음)

실행: streamlit run src/ui/app.py
"""

import streamlit as st
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.domain.models import MarketType
from src.domain.logic import LandedCostCalculator
from src.core.config import AppConfig

# 탭 모듈 임포트
from src.ui.tabs import margin_tab, scraping_tab, preflight_tab, review_tab, price_tab

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="Smart Store Agent",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Smart Store Agent")
st.markdown("**v3.7.0** | AI 기반 스마트스토어 자동화")

# ============================================================
# 사이드바: 공통 설정
# ============================================================
st.sidebar.header("⚙️ 설정")

with st.sidebar.expander("💱 환율 및 요금", expanded=True):
    exchange_rate = st.number_input(
        "환율 (원/위안)",
        min_value=100.0,
        max_value=300.0,
        value=195.0,
        step=1.0
    )

    shipping_rate_air = st.number_input(
        "항공 배대지 요금 (원/kg)",
        min_value=1000,
        max_value=20000,
        value=8000,
        step=500
    )

    domestic_shipping = st.number_input(
        "국내 택배비 (원)",
        min_value=1000,
        max_value=10000,
        value=3000,
        step=500
    )

# 마켓 선택
st.sidebar.markdown("---")
market_options = {
    "네이버 스마트스토어 (5.5%)": MarketType.NAVER,
    "쿠팡 (10.8%)": MarketType.COUPANG,
    "아마존 (15%)": MarketType.AMAZON,
}
selected_market_name = st.sidebar.selectbox(
    "🏪 판매 마켓",
    options=list(market_options.keys()),
    index=0
)
selected_market = market_options[selected_market_name]

with st.sidebar.expander("📊 숨겨진 비용 설정"):
    return_allowance_rate = st.slider(
        "반품/CS 충당금 (%)",
        min_value=0.0,
        max_value=20.0,
        value=5.0,
        step=0.5
    ) / 100

    ad_cost_rate = st.slider(
        "광고비 (%)",
        min_value=0.0,
        max_value=30.0,
        value=10.0,
        step=1.0
    ) / 100

# 설정 적용
config = AppConfig(
    exchange_rate=exchange_rate,
    shipping_rate_air=shipping_rate_air,
    domestic_shipping=domestic_shipping,
    return_allowance_rate=return_allowance_rate,
    ad_cost_rate=ad_cost_rate,
)

calculator = LandedCostCalculator(config)

# ============================================================
# 탭 구성 (5개 탭)
# ============================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 마진 분석",      # MVP 필수
    "✅ Pre-Flight",     # MVP 필수
    "🇨🇳 1688 입력",     # 수동 입력 우선
    "📝 리뷰 분석",      # Nice to have
    "📈 가격 추적"       # 운영 단계
])

# ============================================================
# TAB 1: 마진 분석 (MVP 필수)
# ============================================================
with tab1:
    margin_tab.render(config, calculator, selected_market)

# ============================================================
# TAB 2: Pre-Flight Check (MVP 필수)
# ============================================================
with tab2:
    preflight_tab.render()

# ============================================================
# TAB 3: 1688 스크래핑 (수동 입력 우선)
# ============================================================
with tab3:
    scraping_tab.render()

# ============================================================
# TAB 4: 리뷰 분석 (Nice to have)
# ============================================================
with tab4:
    review_tab.render()

# ============================================================
# TAB 5: 가격 추적 (운영 단계)
# ============================================================
with tab5:
    price_tab.render()

# ============================================================
# 푸터
# ============================================================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        Smart Store Agent v3.7.0 | MVP: 마진 분석 + Pre-Flight + 엑셀<br>
        Gemini CTO: "준비는 끝났습니다. 이제 전장(시장)으로 나가세요."
    </div>
    """,
    unsafe_allow_html=True
)
