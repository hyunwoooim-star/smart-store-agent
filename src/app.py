"""
Smart Store Agent - Streamlit 대시보드 (v1.0)

Phase 2: 웹 기반 마진 계산 대시보드
- 변수 설정 패널 (환율, 배대지 요금 등)
- 마진 계산기 폼
- 결과 시각화
"""

import streamlit as st
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.sourcing import (
    MarginCalculator,
    MarginConfig,
    SourcingInput,
    ProductDimensions,
    DEFAULT_CONFIG
)

# 페이지 설정
st.set_page_config(
    page_title="Smart Store Agent",
    page_icon="📦",
    layout="wide"
)

st.title("📦 Smart Store Agent - 마진 계산기")
st.markdown("**v3.2** | AI 기반 스마트스토어 소싱 분석 도구")

# 사이드바: 설정 패널
st.sidebar.header("⚙️ 설정")

with st.sidebar.expander("💱 환율 및 요금 설정", expanded=True):
    exchange_rate = st.number_input(
        "환율 (원/위안)",
        min_value=100.0,
        max_value=300.0,
        value=float(DEFAULT_CONFIG.exchange_rate),
        step=1.0,
        help="현재 위안-원 환율"
    )

    shipping_rate_air = st.number_input(
        "항공 배대지 요금 (원/kg)",
        min_value=1000,
        max_value=20000,
        value=DEFAULT_CONFIG.shipping_rate_air,
        step=500,
        help="kg당 항공 배송료"
    )

    shipping_rate_sea = st.number_input(
        "해운 배대지 요금 (원/kg)",
        min_value=500,
        max_value=10000,
        value=DEFAULT_CONFIG.shipping_rate_sea,
        step=500,
        help="kg당 해운 배송료"
    )

    domestic_shipping = st.number_input(
        "국내 택배비 (원)",
        min_value=1000,
        max_value=10000,
        value=DEFAULT_CONFIG.domestic_shipping,
        step=500
    )

with st.sidebar.expander("📊 수수료 설정"):
    naver_fee_rate = st.slider(
        "네이버 수수료 (%)",
        min_value=0.0,
        max_value=15.0,
        value=DEFAULT_CONFIG.naver_fee_rate * 100,
        step=0.5
    ) / 100

    return_allowance_rate = st.slider(
        "반품/CS 충당금 (%)",
        min_value=0.0,
        max_value=20.0,
        value=DEFAULT_CONFIG.return_allowance_rate * 100,
        step=0.5
    ) / 100

    ad_cost_rate = st.slider(
        "광고비 (%)",
        min_value=0.0,
        max_value=30.0,
        value=DEFAULT_CONFIG.ad_cost_rate * 100,
        step=1.0
    ) / 100

# 설정 적용
config = MarginConfig(
    exchange_rate=exchange_rate,
    shipping_rate_air=shipping_rate_air,
    shipping_rate_sea=shipping_rate_sea,
    domestic_shipping=domestic_shipping,
    naver_fee_rate=naver_fee_rate,
    return_allowance_rate=return_allowance_rate,
    ad_cost_rate=ad_cost_rate
)

calculator = MarginCalculator(config)

# 메인 영역: 상품 입력 폼
st.header("📝 상품 정보 입력")

col1, col2 = st.columns(2)

with col1:
    product_name = st.text_input("상품명", value="초경량 캠핑 의자")

    category = st.selectbox(
        "카테고리",
        options=list(MarginCalculator.TARIFF_RATES.keys()),
        index=1  # 캠핑/레저
    )

    wholesale_price_cny = st.number_input(
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
    actual_weight = st.number_input(
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
shipping_method = st.radio(
    "배송 방법",
    options=["항공", "해운"],
    horizontal=True
)

include_ad_cost = st.checkbox("광고비 포함", value=True)

# 계산 버튼
if st.button("🧮 마진 계산", type="primary", use_container_width=True):
    # 입력 데이터 생성
    input_data = SourcingInput(
        product_name=product_name,
        wholesale_price_cny=wholesale_price_cny,
        actual_weight_kg=actual_weight,
        dimensions=ProductDimensions(length, width, height),
        moq=moq,
        target_price_krw=target_price,
        category=category
    )

    # 계산 실행
    result = calculator.calculate(input_data, shipping_method, include_ad_cost)

    # 결과 표시
    st.markdown("---")
    st.header("📊 분석 결과")

    # 마진율에 따른 색상
    if result.margin_percent >= 30:
        margin_color = "green"
        margin_emoji = "🟢"
    elif result.margin_percent >= 15:
        margin_color = "orange"
        margin_emoji = "🟡"
    else:
        margin_color = "red"
        margin_emoji = "🔴"

    # 핵심 지표 카드
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

    with metric_col1:
        st.metric(
            label="예상 마진율",
            value=f"{result.margin_percent}%",
            delta=f"{margin_emoji} {result.risk_level}"
        )

    with metric_col2:
        st.metric(
            label="예상 수익",
            value=f"{result.profit_krw:,}원"
        )

    with metric_col3:
        st.metric(
            label="손익분기 판매가",
            value=f"{result.breakeven_price_krw:,}원"
        )

    with metric_col4:
        st.metric(
            label="30% 마진 달성가",
            value=f"{result.target_margin_price_krw:,}원"
        )

    # AI 조언
    st.markdown("---")
    st.subheader("🤖 AI 조언")
    st.info(result.recommendation)

    # 비용 상세
    with st.expander("💰 비용 상세 내역", expanded=True):
        cost_col1, cost_col2 = st.columns(2)

        with cost_col1:
            st.markdown("**기본 비용**")
            st.write(f"- 상품 원가: {result.product_cost_krw:,}원")
            st.write(f"- 관세: {result.tariff_krw:,}원")
            st.write(f"- 부가세: {result.vat_krw:,}원")
            st.write(f"- 배대지 비용: {result.shipping_agency_fee_krw:,}원")
            st.write(f"- 국내 택배비: {result.domestic_shipping_krw:,}원")

        with cost_col2:
            st.markdown("**판매 비용**")
            st.write(f"- 네이버 수수료: {result.platform_fee_krw:,}원")
            st.write(f"- 반품 충당금: {result.return_allowance_krw:,}원")
            st.write(f"- 광고비: {result.ad_cost_krw:,}원")
            st.markdown("---")
            st.write(f"**총 비용: {result.total_cost_krw:,}원**")

    # 무게 분석
    with st.expander("⚖️ 무게 분석"):
        weight_col1, weight_col2, weight_col3 = st.columns(3)

        with weight_col1:
            st.metric("실제 무게", f"{result.actual_weight_kg} kg")

        with weight_col2:
            volume_applied = "⭐ 적용" if result.volume_weight_kg > result.actual_weight_kg else ""
            st.metric("부피 무게", f"{result.volume_weight_kg} kg {volume_applied}")

        with weight_col3:
            st.metric("청구 무게", f"{result.billable_weight_kg} kg")

        if result.volume_weight_kg > result.actual_weight_kg:
            st.warning("⚠️ 부피무게가 실무게보다 큽니다! 부피무게로 배송비가 계산됩니다.")

# 푸터
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        Smart Store Agent v3.2 | Phase 2: Streamlit Dashboard<br>
        Powered by Claude Code + Gemini AI
    </div>
    """,
    unsafe_allow_html=True
)
