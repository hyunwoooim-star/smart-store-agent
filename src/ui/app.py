"""
app.py - Streamlit 대시보드 (v3.3)

DDD 원칙: UI는 껍데기일 뿐, 로직은 domain에서 가져옴
- 로직 변경 시 이 파일은 수정 불필요
- Next.js로 전환해도 domain 코드 재사용 가능
"""

import streamlit as st
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.domain.models import Product, MarketType, RiskLevel
from src.domain.logic import LandedCostCalculator
from src.core.config import AppConfig, MARKET_FEES

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="Smart Store Risk Filter",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Smart Store Risk Filter")
st.markdown("**v3.3** | 망하는 상품을 걸러내는 AI 리스크 분석기")

# ============================================================
# 사이드바: 설정 패널
# ============================================================
st.sidebar.header("⚙️ 설정")

with st.sidebar.expander("💱 환율 및 요금", expanded=True):
    exchange_rate = st.number_input(
        "환율 (원/위안)",
        min_value=100.0,
        max_value=300.0,
        value=195.0,
        step=1.0,
        help="현재 위안-원 환율"
    )

    shipping_rate_air = st.number_input(
        "항공 배대지 요금 (원/kg)",
        min_value=1000,
        max_value=20000,
        value=8000,
        step=500,
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
# 메인 영역: 상품 입력 폼
# ============================================================
st.header("📝 상품 정보 입력")

col1, col2 = st.columns(2)

with col1:
    product_name = st.text_input("상품명", value="초경량 캠핑 의자")

    category = st.selectbox(
        "카테고리",
        options=list(config.tariff_rates.keys()),
        index=1  # 캠핑/레저
    )

    price_cny = st.number_input(
        "1688 도매가 (위안)",
        min_value=1.0,
        max_value=10000.0,
        value=45.0,
        step=1.0
    )

    moq = st.number_input(
        "MOQ (최소 주문 수량)",
        min_value=1,
        max_value=1000,
        value=50,
        step=1
    )

with col2:
    weight_kg = st.number_input(
        "실제 무게 (kg)",
        min_value=0.1,
        max_value=100.0,
        value=2.5,
        step=0.1
    )

    st.markdown("**📦 박스 사이즈 (cm)**")
    dim_col1, dim_col2, dim_col3 = st.columns(3)
    with dim_col1:
        length = st.number_input("가로", min_value=1, value=80, step=1)
    with dim_col2:
        width = st.number_input("세로", min_value=1, value=20, step=1)
    with dim_col3:
        height = st.number_input("높이", min_value=1, value=15, step=1)

    target_price = st.number_input(
        "목표 판매가 (원)",
        min_value=1000,
        max_value=10000000,
        value=45000,
        step=1000
    )

# 배송 방법 선택
col_ship1, col_ship2 = st.columns(2)
with col_ship1:
    shipping_method = st.radio(
        "배송 방법",
        options=["항공", "해운"],
        horizontal=True
    )
with col_ship2:
    include_ad_cost = st.checkbox("광고비 포함", value=True)

# ============================================================
# 계산 버튼 및 결과
# ============================================================
if st.button("🔍 리스크 분석", type="primary", use_container_width=True):
    # Product 객체 생성
    product = Product(
        name=product_name,
        price_cny=price_cny,
        weight_kg=weight_kg,
        length_cm=length,
        width_cm=width,
        height_cm=height,
        category=category,
        moq=moq
    )

    # 계산 실행 (도메인 로직 호출)
    result = calculator.calculate(
        product=product,
        target_price=target_price,
        market=selected_market,
        shipping_method=shipping_method,
        include_ad_cost=include_ad_cost
    )

    # 결과 표시
    st.markdown("---")
    st.header("📊 리스크 분석 결과")

    # 신호등 표시
    if result.risk_level == RiskLevel.SAFE:
        signal_emoji = "🟢"
        signal_text = "진입 추천"
        signal_color = "green"
    elif result.risk_level == RiskLevel.WARNING:
        signal_emoji = "🟡"
        signal_text = "주의 필요"
        signal_color = "orange"
    else:
        signal_emoji = "🔴"
        signal_text = "진입 금지"
        signal_color = "red"

    # 핵심 지표 카드
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

    with metric_col1:
        st.metric(
            label="예상 마진율",
            value=f"{result.margin_percent}%",
            delta=f"{signal_emoji} {signal_text}"
        )

    with metric_col2:
        st.metric(
            label="예상 수익",
            value=f"{result.profit:,}원"
        )

    with metric_col3:
        st.metric(
            label="손익분기 판매가",
            value=f"{result.breakeven_price:,}원"
        )

    with metric_col4:
        st.metric(
            label="30% 마진 달성가",
            value=f"{result.target_margin_price:,}원"
        )

    # AI 조언 (신호등 스타일)
    st.markdown("---")
    st.subheader("🤖 AI 판정")

    if result.risk_level == RiskLevel.DANGER:
        st.error(result.recommendation)
    elif result.risk_level == RiskLevel.WARNING:
        st.warning(result.recommendation)
    else:
        st.success(result.recommendation)

    # 비용 상세 내역
    with st.expander("💰 비용 상세 내역", expanded=True):
        cost_col1, cost_col2 = st.columns(2)

        bd = result.breakdown
        with cost_col1:
            st.markdown("**기본 비용**")
            st.write(f"- 상품 원가: {bd.product_cost:,}원")
            st.write(f"- 관세: {bd.tariff:,}원")
            st.write(f"- 부가세: {bd.vat:,}원")
            st.write(f"- 해외 배송비: {bd.shipping_international:,}원")
            st.write(f"- 국내 택배비: {bd.shipping_domestic:,}원")

        with cost_col2:
            st.markdown("**판매/운영 비용**")
            market_info = MARKET_FEES[selected_market.value]
            st.write(f"- {market_info.name} 수수료: {bd.platform_fee:,}원")
            st.write(f"- 반품 충당금: {bd.return_allowance:,}원")
            st.write(f"- 광고비: {bd.ad_cost:,}원")
            st.write(f"- 포장비: {bd.packaging:,}원")
            st.markdown("---")
            st.write(f"**총 비용: {result.total_cost:,}원**")

    # 무게 분석
    with st.expander("⚖️ 무게 분석"):
        w_col1, w_col2, w_col3 = st.columns(3)

        with w_col1:
            st.metric("실제 무게", f"{result.actual_weight_kg} kg")

        with w_col2:
            vol_note = "⭐ 적용" if result.volume_weight_kg > result.actual_weight_kg else ""
            st.metric("부피 무게", f"{result.volume_weight_kg} kg {vol_note}")

        with w_col3:
            st.metric("청구 무게", f"{result.billable_weight_kg} kg")

        if result.volume_weight_kg > result.actual_weight_kg:
            st.warning("⚠️ 부피무게가 실무게보다 큽니다! 부피무게로 배송비가 계산됩니다.")

# ============================================================
# 푸터
# ============================================================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        Smart Store Risk Filter v3.3 | DDD Architecture<br>
        "망하는 상품을 미리 걸러내는" 보수적 분석기<br>
        Powered by Claude Code + Gemini AI
    </div>
    """,
    unsafe_allow_html=True
)
