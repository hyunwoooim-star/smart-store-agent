"""
마진 분석 탭 (MVP 필수)
"""
import streamlit as st
from src.domain.models import Product, MarketType, RiskLevel
from src.domain.logic import LandedCostCalculator
from src.core.config import AppConfig, MARKET_FEES


def render(config: AppConfig, calculator: LandedCostCalculator, selected_market: MarketType):
    """마진 분석 탭 렌더링"""
    st.header("📝 상품 정보 입력")

    col1, col2 = st.columns(2)

    with col1:
        product_name = st.text_input("상품명", value="초경량 캠핑 의자", key="margin_name")

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

    # 세션 초기화
    if "analyzed_products" not in st.session_state:
        st.session_state.analyzed_products = []
    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "last_product_info" not in st.session_state:
        st.session_state.last_product_info = None

    # 계산 버튼
    if st.button("🔍 리스크 분석", type="primary", use_container_width=True, key="margin_btn"):
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

        result = calculator.calculate(
            product=product,
            target_price=target_price,
            market=selected_market,
            shipping_method=shipping_method,
            include_ad_cost=include_ad_cost
        )

        # 결과를 session_state에 저장
        st.session_state.last_result = result
        st.session_state.last_product_info = {
            "name": product_name,
            "price_cny": price_cny,
            "target_price": target_price,
            "moq": moq,
            "domestic_shipping": config.domestic_shipping,
        }

        # 결과 표시
        _render_result(result, selected_market)

    # 엑셀 다운로드 섹션
    _render_excel_section(config)


def _render_result(result, selected_market: MarketType):
    """분석 결과 표시"""
    st.markdown("---")
    st.header("📊 리스크 분석 결과")

    if result.risk_level == RiskLevel.SAFE:
        signal_emoji = "🟢"
        signal_text = "진입 추천"
    elif result.risk_level == RiskLevel.WARNING:
        signal_emoji = "🟡"
        signal_text = "주의 필요"
    else:
        signal_emoji = "🔴"
        signal_text = "진입 금지"

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

    with metric_col1:
        st.metric(label="예상 마진율", value=f"{result.margin_percent}%", delta=f"{signal_emoji} {signal_text}")
    with metric_col2:
        st.metric(label="예상 수익", value=f"{result.profit:,}원")
    with metric_col3:
        st.metric(label="손익분기 판매가", value=f"{result.breakeven_price:,}원")
    with metric_col4:
        st.metric(label="30% 마진 달성가", value=f"{result.target_margin_price:,}원")

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
            st.markdown("**🇨🇳 중국 내 비용**")
            st.write(f"- 상품 원가: {bd.product_cost:,}원")
            st.write(f"- 중국 내 배송비: {bd.china_shipping:,}원")
            st.write(f"- 구매대행 수수료 (10%): {bd.agency_fee:,}원")
            st.markdown("**🚢 수입 비용**")
            st.write(f"- 관세: {bd.tariff:,}원")
            st.write(f"- 부가세: {bd.vat:,}원")
            st.write(f"- 해외 배송비: {bd.shipping_international:,}원")
            st.write(f"- 국내 택배비: {bd.shipping_domestic:,}원")

        with cost_col2:
            st.markdown("**🛒 판매/운영 비용**")
            market_info = MARKET_FEES[selected_market.value]
            st.write(f"- {market_info.name} 수수료: {bd.platform_fee:,}원")
            st.write(f"- 반품 충당금 (5%): {bd.return_allowance:,}원")
            st.write(f"- 광고비 (10%): {bd.ad_cost:,}원")
            st.write(f"- 포장/검수비: {bd.packaging:,}원")
            st.markdown("---")
            st.write(f"**💰 총 비용: {result.total_cost:,}원**")


def _render_excel_section(config: AppConfig):
    """엑셀 다운로드 섹션"""
    st.markdown("---")
    st.subheader("📥 엑셀 내보내기")

    try:
        from src.generators.excel_generator import NaverExcelGenerator, NaverProductData

        col_add, col_download, col_clear = st.columns([1, 1, 1])

        with col_add:
            if st.session_state.last_result:
                if st.button("➕ 목록에 추가", key="add_to_list"):
                    info = st.session_state.last_product_info
                    res = st.session_state.last_result
                    naver_product = NaverProductData(
                        product_name=info["name"],
                        sale_price=info["target_price"],
                        stock_quantity=999,
                        origin="중국",
                        shipping_fee=int(info["domestic_shipping"]),
                        cost_price=res.total_cost,
                        margin_rate=res.margin_percent,
                        breakeven_price=res.breakeven_price,
                        risk_level=res.risk_level.value,
                        source_price_cny=info["price_cny"],
                        moq=info["moq"],
                    )
                    st.session_state.analyzed_products.append(naver_product)
                    st.success(f"✅ '{info['name']}' 추가됨! (총 {len(st.session_state.analyzed_products)}개)")
            else:
                st.button("➕ 목록에 추가", key="add_to_list_disabled", disabled=True)

        with col_download:
            if st.session_state.analyzed_products:
                generator = NaverExcelGenerator()
                import tempfile
                import os as temp_os

                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    tmp_path = tmp.name

                generator.generate(st.session_state.analyzed_products, tmp_path)

                with open(tmp_path, "rb") as f:
                    excel_data = f.read()

                temp_os.unlink(tmp_path)

                st.download_button(
                    label=f"📥 엑셀 다운로드 ({len(st.session_state.analyzed_products)}개)",
                    data=excel_data,
                    file_name="naver_products.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel"
                )
            else:
                st.button("📥 엑셀 다운로드", key="download_disabled", disabled=True)

        with col_clear:
            if st.button("🗑️ 목록 초기화", key="clear_list"):
                st.session_state.analyzed_products = []
                st.session_state.last_result = None
                st.session_state.last_product_info = None
                st.rerun()

        # 현재 목록 표시
        if st.session_state.analyzed_products:
            with st.expander(f"📋 현재 목록 ({len(st.session_state.analyzed_products)}개)", expanded=True):
                for idx, p in enumerate(st.session_state.analyzed_products, 1):
                    risk_emoji = {"safe": "🟢", "warning": "🟡", "danger": "🔴"}.get(p.risk_level, "⚪")
                    st.write(f"{idx}. {p.product_name} | {p.sale_price:,}원 | {p.margin_rate:.1f}% {risk_emoji}")

    except ImportError:
        st.warning("⚠️ 엑셀 생성 기능을 사용하려면 openpyxl을 설치하세요: `pip install openpyxl`")
