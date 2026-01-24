"""
1688 스크래핑 탭 (Nice to have - 수동 입력 우선)
"""
import streamlit as st
import asyncio
import os


def render():
    """1688 스크래핑 탭 렌더링"""
    st.header("🇨🇳 1688 상품 정보 추출")

    # Gemini CTO 권장: 수동 입력 우선
    st.info("💡 **권장**: 1688 페이지에서 직접 확인한 정보를 '수동 입력'으로 입력하세요.")

    # 입력 모드 선택
    input_mode = st.radio(
        "📥 입력 방식",
        options=["✍️ 수동 입력 (권장)", "🤖 자동 스크래핑"],
        horizontal=True,
        index=0
    )

    if input_mode == "✍️ 수동 입력 (권장)":
        _render_manual_input()
    else:
        _render_auto_scraping()


def _render_manual_input():
    """수동 입력 모드"""
    st.markdown("### ✍️ 수동 입력 모드")
    st.markdown("1688 페이지에서 직접 확인한 정보를 입력하세요.")

    manual_col1, manual_col2 = st.columns(2)

    with manual_col1:
        manual_name = st.text_input("상품명", value="", key="manual_name")
        manual_price = st.number_input(
            "💰 도매가 (위안, ¥)",
            min_value=0.1,
            max_value=100000.0,
            value=45.0,
            step=1.0,
            key="manual_price"
        )
        manual_moq = st.number_input(
            "📦 MOQ",
            min_value=1,
            max_value=10000,
            value=50,
            step=1,
            key="manual_moq"
        )

    with manual_col2:
        manual_weight = st.number_input(
            "⚖️ 무게 (kg)",
            min_value=0.01,
            max_value=100.0,
            value=1.0,
            step=0.1,
            key="manual_weight"
        )

        st.markdown("**📐 사이즈 (cm)**")
        size_col1, size_col2, size_col3 = st.columns(3)
        with size_col1:
            manual_length = st.number_input("가로", min_value=1, value=30, key="manual_length")
        with size_col2:
            manual_width = st.number_input("세로", min_value=1, value=20, key="manual_width")
        with size_col3:
            manual_height = st.number_input("높이", min_value=1, value=10, key="manual_height")

    if st.button("💾 정보 저장 → 마진 분석으로", type="primary", key="manual_save_btn"):
        from src.adapters.alibaba_scraper import ScrapedProduct

        manual_product = ScrapedProduct(
            url="manual_input",
            name=manual_name or "수동 입력 상품",
            price_cny=manual_price,
            weight_kg=manual_weight,
            length_cm=manual_length,
            width_cm=manual_width,
            height_cm=manual_height,
            moq=manual_moq,
        )

        st.session_state['scraped_product'] = manual_product
        st.success(f"✅ 저장 완료! '마진 분석' 탭에서 계속 진행하세요.")


def _render_auto_scraping():
    """자동 스크래핑 모드"""
    apify_token = os.getenv("APIFY_API_TOKEN")

    if not apify_token:
        st.warning("⚠️ APIFY_API_TOKEN이 설정되지 않았습니다.")
        st.info("월 $50 비용 발생. 매출이 월 100만 원 넘으면 고려하세요.")
        return

    url_input = st.text_input(
        "1688 상품 URL",
        placeholder="https://detail.1688.com/offer/xxxxxxxxx.html",
        key="scrape_url"
    )

    use_mock = st.checkbox("🧪 테스트 모드 (Mock)", value=True)

    if st.button("🔍 상품 정보 추출", type="primary", key="scrape_btn"):
        if not url_input and not use_mock:
            st.error("URL을 입력하세요.")
        else:
            with st.spinner("⏳ 추출 중..."):
                try:
                    from src.adapters.alibaba_scraper import scrape_1688
                    scraped = asyncio.run(scrape_1688(url_input or "mock", use_mock=use_mock))

                    st.success(f"✅ 추출 완료!")
                    st.write(f"- 상품명: {scraped.name}")
                    st.write(f"- 가격: ¥{scraped.price_cny}")
                    st.write(f"- MOQ: {scraped.moq}개")

                    st.session_state['scraped_product'] = scraped

                except Exception as e:
                    st.error(f"❌ 오류: {e}")
                    st.info("👆 '수동 입력' 모드를 사용하세요.")
