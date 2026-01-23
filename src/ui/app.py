"""
app.py - Streamlit 대시보드 (v4.0.0)

v4.0 Night Crawler 업데이트:
- 모닝 브리핑: AI가 밤새 찾은 상품 검토
- 키워드 관리: 소싱 키워드 설정
- 자동화 준비: GitHub Actions 스케줄러 연동

실행: streamlit run src/ui/app.py
"""

import streamlit as st
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# .env 파일 로딩 (환경변수)
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.domain.models import MarketType
from src.domain.logic import LandedCostCalculator
from src.core.config import AppConfig

# 탭 모듈 임포트
from src.ui.tabs import margin_tab, scraping_tab, preflight_tab, review_tab, price_tab, oneclick_tab, morning_tab

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="Smart Store Agent",
    page_icon="🛡️",
    layout="wide"
)

st.title("Smart Store Agent")
st.markdown("**v4.0.0** | AI 기반 스마트스토어 자동화 + Night Crawler")

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
# 탭 구성 (7개 탭) - v4.0 Night Crawler
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "모닝 브리핑",       # v4.0 NEW! Night Crawler 결과 검토
    "원클릭 소싱",       # 킬러 피처
    "마진 분석",         # MVP 필수
    "Pre-Flight",        # MVP 필수
    "1688 입력",         # 수동 입력 우선
    "리뷰 분석",         # Nice to have
    "가격 추적"          # 운영 단계
])

# ============================================================
# TAB 1: 모닝 브리핑 (v4.0 Night Crawler)
# ============================================================
with tab1:
    morning_tab.render()

# ============================================================
# TAB 2: 원클릭 소싱 (킬러 피처)
# ============================================================
with tab2:
    oneclick_tab.render()

# ============================================================
# TAB 3: 마진 분석 (MVP 필수)
# ============================================================
with tab3:
    margin_tab.render(config, calculator, selected_market)

# ============================================================
# TAB 4: Pre-Flight Check (MVP 필수)
# ============================================================
with tab4:
    preflight_tab.render()

# ============================================================
# TAB 5: 1688 스크래핑 (수동 입력 우선)
# ============================================================
with tab5:
    scraping_tab.render()

# ============================================================
# TAB 6: 리뷰 분석 (Nice to have)
# ============================================================
with tab6:
    review_tab.render()

# ============================================================
# TAB 7: 가격 추적 (운영 단계)
# ============================================================
with tab7:
    price_tab.render()

# ============================================================
# 푸터
# ============================================================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        Smart Store Agent v4.0.0 | Night Crawler: AI가 밤새 소싱<br>
        "밤새 일하는 AI, 아침에 결재하는 사장님"
    </div>
    """,
    unsafe_allow_html=True
)
