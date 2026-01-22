"""
app.py - Streamlit 대시보드 (v3.5)

DDD 원칙: UI는 껍데기일 뿐, 로직은 domain에서 가져옴
- 로직 변경 시 이 파일은 수정 불필요
- Next.js로 전환해도 domain 코드 재사용 가능

v3.5 업데이트:
- 탭 기반 UI로 변경
- 1688 스크래핑 탭 추가 (Apify API)
- Pre-Flight Check 탭 추가 (금지어 검사)
"""

import streamlit as st
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.domain.models import Product, MarketType, RiskLevel
from src.domain.logic import LandedCostCalculator
from src.core.config import AppConfig, MARKET_FEES
from src.analyzers.preflight_check import PreFlightChecker, ViolationType

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="Smart Store Agent",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Smart Store Agent")
st.markdown("**v3.5** | AI 기반 스마트스토어 자동화 시스템")

# ============================================================
# 탭 구성
# ============================================================
tab1, tab2, tab3 = st.tabs(["📊 마진 분석", "🇨🇳 1688 스크래핑", "✅ Pre-Flight Check"])

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
# TAB 1: 마진 분석 (기존 기능)
# ============================================================
with tab1:
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

        # 결과 표시
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

# ============================================================
# TAB 2: 1688 스크래핑 (Apify API)
# ============================================================
with tab2:
    st.header("🇨🇳 1688 상품 정보 추출")
    st.markdown("1688.com URL을 입력하면 상품 정보를 자동으로 추출합니다.")

    # API 토큰 상태 확인
    import os
    apify_token = os.getenv("APIFY_API_TOKEN")

    if not apify_token:
        st.warning("⚠️ APIFY_API_TOKEN이 설정되지 않았습니다. .env 파일에 토큰을 추가하세요.")
        st.code("APIFY_API_TOKEN=apify_api_xxxxxxxxx", language="ini")
        st.info("Apify 가입: https://console.apify.com/sign-up")
        use_mock = True
    else:
        st.success("✅ Apify API 연결됨")
        use_mock = False

    # URL 입력
    url_input = st.text_input(
        "1688 상품 URL",
        placeholder="https://detail.1688.com/offer/xxxxxxxxx.html",
        key="scrape_url"
    )

    # Mock 모드 체크박스
    use_mock_checkbox = st.checkbox("🧪 테스트 모드 (Mock 데이터 사용)", value=use_mock)

    if st.button("🔍 상품 정보 추출", type="primary", key="scrape_btn"):
        if not url_input and not use_mock_checkbox:
            st.error("URL을 입력하세요.")
        else:
            with st.spinner("⏳ 상품 정보 추출 중... (5~30초 소요)"):
                try:
                    from src.adapters.alibaba_scraper import scrape_1688, AlibabaScraper, MockAlibabaScraper

                    # 비동기 함수 실행
                    if use_mock_checkbox:
                        scraped = asyncio.run(scrape_1688(url_input or "mock", use_mock=True))
                    else:
                        scraped = asyncio.run(scrape_1688(url_input, use_mock=False))

                    # 결과 표시
                    st.markdown("---")
                    st.subheader("📦 추출 결과")

                    result_col1, result_col2 = st.columns(2)

                    with result_col1:
                        st.markdown("**기본 정보**")
                        st.write(f"- 상품명: {scraped.name}")
                        st.write(f"- 가격: ¥{scraped.price_cny}")
                        st.write(f"- MOQ: {scraped.moq}개")

                        if scraped.image_url:
                            st.image(scraped.image_url, width=200)

                    with result_col2:
                        st.markdown("**물류 정보**")
                        st.write(f"- 무게: {scraped.weight_kg or '추출 실패'} kg")
                        st.write(f"- 사이즈: {scraped.length_cm or '?'} x {scraped.width_cm or '?'} x {scraped.height_cm or '?'} cm")

                        if scraped.raw_specs:
                            st.markdown("**원본 스펙**")
                            for key, value in list(scraped.raw_specs.items())[:5]:
                                st.write(f"- {key}: {value}")

                    # 마진 분석 연동 버튼
                    if scraped.price_cny > 0:
                        st.markdown("---")
                        st.info("💡 위 데이터로 마진 분석을 하려면 '마진 분석' 탭에서 직접 입력하세요.")

                        # 세션에 데이터 저장 (추후 탭 간 연동용)
                        st.session_state['scraped_product'] = scraped

                except ImportError as e:
                    st.error(f"패키지 오류: {e}")
                    st.code("pip install apify-client", language="bash")
                except Exception as e:
                    st.error(f"추출 실패: {str(e)}")

# ============================================================
# TAB 3: Pre-Flight Check (금지어 검사)
# ============================================================
with tab3:
    st.header("✅ Pre-Flight Check")
    st.markdown("상품 등록 전 금지어/위험 표현을 검사합니다.")

    # 검사 모드
    check_mode = st.radio(
        "검사 모드",
        options=["엄격 모드 (경고도 실패)", "일반 모드 (오류만 실패)"],
        horizontal=True
    )
    strict_mode = check_mode == "엄격 모드 (경고도 실패)"

    # 입력 영역
    check_col1, check_col2 = st.columns([1, 1])

    with check_col1:
        check_name = st.text_input("상품명", key="check_name", placeholder="예: 최고급 다이어트 보조제")
        check_desc = st.text_area(
            "상품 설명",
            key="check_desc",
            height=150,
            placeholder="예: 암 예방에 탁월한 효과! 100% 체중 감량 보장!"
        )

    # 검사 버튼
    if st.button("🔍 검사 실행", type="primary", key="preflight_btn"):
        if not check_name and not check_desc:
            st.error("상품명 또는 설명을 입력하세요.")
        else:
            checker = PreFlightChecker(strict_mode=strict_mode)
            result = checker.check_product(check_name, check_desc)

            # 결과 표시
            st.markdown("---")

            if result.passed:
                st.success(f"✅ 검사 통과! 등록 가능합니다.")
            else:
                st.error(f"❌ 검사 실패 - 오류 {result.error_count}건, 경고 {result.warning_count}건")

            # 위반 사항 표시
            if result.violations:
                st.subheader("🚨 발견된 문제")

                for i, v in enumerate(result.violations, 1):
                    if v.severity == "high":
                        st.error(f"""
                        **{i}. 🔴 [오류] {v.type.value}**
                        - 매칭: `{v.matched_text}`
                        - 패턴: {v.pattern}
                        - 💡 제안: {v.suggestion}
                        """)
                    elif v.severity == "medium":
                        st.warning(f"""
                        **{i}. 🟡 [경고] {v.type.value}**
                        - 매칭: `{v.matched_text}`
                        - 패턴: {v.pattern}
                        - 💡 제안: {v.suggestion}
                        """)
                    else:
                        st.info(f"""
                        **{i}. 🟢 [정보] {v.type.value}**
                        - 매칭: `{v.matched_text}`
                        """)

                    # 대안 제시
                    alternatives = checker.get_safe_alternatives(v)
                    if alternatives:
                        st.markdown(f"  🔄 **대안:** {', '.join(alternatives[:3])}")

    # 금지어 가이드
    with st.expander("📋 금지어 가이드"):
        st.markdown("""
        ### 🔴 절대 금지 (HIGH)
        - **의료/건강 효능**: 암 예방, 당뇨 개선, 면역력 강화 등
        - **효과 보장**: 100% 효과, 무조건 성공, 효과 보장
        - **네이버 금지어**: 카카오톡, 쿠팡, 직거래, 계좌이체 등

        ### 🟡 주의 필요 (MEDIUM)
        - **최상급 표현**: 최고, 최초, 1위, 완벽, 기적
        - **비교 광고**: 타사 대비, 경쟁사보다 (증빙 필요)
        - **가격 표현**: 정가 대비 할인 (증빙 필요)

        ### 💡 안전한 대안
        - "최고의" → "프리미엄", "고품질"
        - "암 예방" → "건강한 생활 도움"
        - "100% 효과" → "만족도 높은", "호평받는"
        """)

# ============================================================
# 푸터
# ============================================================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        Smart Store Agent v3.5 | Phase 3.5 완료 (Apify 전환)<br>
        "망하는 상품을 미리 걸러내는" 보수적 분석기<br>
        Powered by Claude Code + Gemini AI + Apify
    </div>
    """,
    unsafe_allow_html=True
)
