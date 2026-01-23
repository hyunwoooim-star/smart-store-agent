"""
app.py - Streamlit 대시보드 (v3.6.2)

DDD 원칙: UI는 껍데기일 뿐, 로직은 domain에서 가져옴
- 로직 변경 시 이 파일은 수정 불필요
- Next.js로 전환해도 domain 코드 재사용 가능

v3.6.2 업데이트 (Phase 9):
- 자동 모니터링 스케줄러 UI 추가
- 스케줄러 상태 표시 및 제어 (시작/중지/일시정지)
- 최근 실행 결과 및 통계 대시보드

v3.6.1 업데이트 (Phase 8):
- 가격 추적 탭 추가 (경쟁사 모니터링)
- Tier 기반 경쟁력 분석 (Gemini CTO 피드백)
- 가격 변동 알림 대시보드

v3.5.1:
- 탭 기반 UI로 변경
- 1688 스크래핑 탭 추가 (Apify API)
- Pre-Flight Check 탭 추가 (금지어 검사 + 의료기기 패턴)
- 리뷰 분석 탭 추가 (Phase 5.1 MVP)
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
from src.monitors.price_tracker import (
    PriceTracker, CompetitorProduct, PriceAlert, PricingStrategy,
    AlertLevel, MarketPlatform, ExposureTier, PricingStrategyType
)
from src.monitors.scheduler import (
    PriceMonitorScheduler, SchedulerStatus, MonitoringResult,
    MockPriceFetcher, create_scheduler
)

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="Smart Store Agent",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Smart Store Agent")
st.markdown("**v3.6.2** | AI 기반 스마트스토어 자동화 시스템")

# ============================================================
# 탭 구성 (5개 탭)
# ============================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 마진 분석",
    "🇨🇳 1688 스크래핑",
    "✅ Pre-Flight Check",
    "📝 리뷰 분석",
    "📈 가격 추적"
])

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
            "domestic_shipping": domestic_shipping,
        }

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
    # 엑셀 다운로드 섹션 (항상 표시)
    # ============================================================
    st.markdown("---")
    st.subheader("📥 엑셀 내보내기")

    try:
        from src.generators.excel_generator import NaverExcelGenerator, NaverProductData

        # 현재 상품 추가 버튼 (분석 결과가 있을 때만)
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
                # 엑셀 파일 생성
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

    except ImportError as e:
        st.warning(f"⚠️ 엑셀 생성 기능을 사용하려면 openpyxl을 설치하세요: `pip install openpyxl`")

# ============================================================
# TAB 2: 1688 스크래핑 (Apify API + Failover UI)
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

    # 입력 모드 선택 (Gemini CTO 조언: Failover UI)
    input_mode = st.radio(
        "📥 입력 방식",
        options=["🤖 자동 스크래핑", "✍️ 수동 입력"],
        horizontal=True,
        index=0,
        help="스크래핑 실패 시 수동 입력으로 전환하세요"
    )

    if input_mode == "🤖 자동 스크래핑":
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
                with st.spinner("⏳ 상품 정보 추출 중... (무료 Actor 순차 시도)"):
                    try:
                        from src.adapters.alibaba_scraper import scrape_1688, AlibabaScraper, MockAlibabaScraper

                        # 비동기 함수 실행
                        if use_mock_checkbox:
                            scraped = asyncio.run(scrape_1688(url_input or "mock", use_mock=True))
                        else:
                            scraped = asyncio.run(scrape_1688(url_input, use_mock=False))

                        # 스크래핑 실패 감지 (Failover 트리거)
                        scrape_failed = (
                            scraped.price_cny == 0 or
                            "실패" in scraped.name or
                            "수동 입력" in scraped.name
                        )

                        if scrape_failed:
                            # Failover UI 표시 (Gemini CTO 조언)
                            st.markdown("---")
                            st.warning("""
                            😅 **죄송합니다! 1688 보안 때문에 데이터를 못 가져왔어요.**

                            걱정 마세요! **가격과 무게만 알려주시면** 마진 분석은 정상 진행됩니다.
                            """)

                            # 에러 상세 (접은 상태)
                            with st.expander("🔍 오류 상세 보기"):
                                if scraped.raw_specs and "error" in scraped.raw_specs:
                                    st.code(scraped.raw_specs["error"])

                            # 수동 입력 폼으로 유도
                            st.info("👆 위의 **'수동 입력'** 모드를 선택해서 직접 입력하세요!")

                            # 세션에 URL 저장 (수동 입력 시 참조용)
                            st.session_state['failed_url'] = url_input

                        else:
                            # 성공 - 결과 표시
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
                            st.markdown("---")
                            st.info("💡 위 데이터로 마진 분석을 하려면 '마진 분석' 탭에서 직접 입력하세요.")

                            # 세션에 데이터 저장 (추후 탭 간 연동용)
                            st.session_state['scraped_product'] = scraped

                    except ImportError as e:
                        st.error(f"패키지 오류: {e}")
                        st.code("pip install apify-client", language="bash")
                    except Exception as e:
                        # 예외 발생 시에도 Failover UI
                        st.markdown("---")
                        st.warning(f"""
                        😅 **스크래핑 중 오류가 발생했어요.**

                        오류: `{str(e)[:100]}`

                        걱정 마세요! **'수동 입력'** 모드로 직접 입력하시면 됩니다.
                        """)

    else:
        # 수동 입력 모드 (Failover UI)
        st.markdown("### ✍️ 수동 입력 모드")
        st.markdown("1688 페이지에서 직접 확인한 정보를 입력하세요.")

        # 이전 실패 URL 표시
        if 'failed_url' in st.session_state:
            st.caption(f"🔗 참조 URL: {st.session_state['failed_url']}")

        manual_col1, manual_col2 = st.columns(2)

        with manual_col1:
            manual_name = st.text_input("상품명 (중국어/한글)", value="", key="manual_name")
            manual_price = st.number_input(
                "💰 도매가 (위안, ¥)",
                min_value=0.1,
                max_value=100000.0,
                value=45.0,
                step=1.0,
                key="manual_price",
                help="1688 페이지에서 가격 확인"
            )
            manual_moq = st.number_input(
                "📦 MOQ (최소주문량)",
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
                key="manual_weight",
                help="모르면 대략적인 값 입력"
            )

            st.markdown("**📐 사이즈 (cm)** - 모르면 기본값 사용")
            size_col1, size_col2, size_col3 = st.columns(3)
            with size_col1:
                manual_length = st.number_input("가로", min_value=1, value=30, key="manual_length")
            with size_col2:
                manual_width = st.number_input("세로", min_value=1, value=20, key="manual_width")
            with size_col3:
                manual_height = st.number_input("높이", min_value=1, value=10, key="manual_height")

        # 저장 버튼
        if st.button("💾 정보 저장 → 마진 분석으로", type="primary", key="manual_save_btn"):
            from src.adapters.alibaba_scraper import ScrapedProduct

            manual_product = ScrapedProduct(
                url=st.session_state.get('failed_url', 'manual_input'),
                name=manual_name or "수동 입력 상품",
                price_cny=manual_price,
                weight_kg=manual_weight,
                length_cm=manual_length,
                width_cm=manual_width,
                height_cm=manual_height,
                moq=manual_moq,
            )

            st.session_state['scraped_product'] = manual_product

            st.success(f"""
            ✅ **저장 완료!**

            - 상품명: {manual_product.name}
            - 가격: ¥{manual_product.price_cny}
            - 무게: {manual_product.weight_kg}kg

            **'마진 분석' 탭**에서 계속 진행하세요!
            """)

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
    with st.expander("📋 금지어 가이드 (v3.5.1 업데이트)"):
        st.markdown("""
        ### 🔴 절대 금지 (HIGH)
        - **의료/건강 효능**: 암 예방, 당뇨 개선, 면역력 강화 등
        - **효과 보장**: 100% 효과, 무조건 성공, 효과 보장
        - **네이버 금지어**: 카카오톡, 쿠팡, 직거래, 계좌이체 등
        - **기능성화장품**: 미백, 주름개선, 자외선차단 (식약처 인증 필요)
        - **아동용제품**: 유아용 장난감, 아기 화장품 (KC인증 필요)
        - **지식재산권**: 디즈니, 카카오프렌즈 캐릭터 (라이선스 필요)
        - **의료기기 오인** ⭐NEW: 치료, 교정, 통증 완화, 혈액순환 등

        ### 🟡 주의 필요 (MEDIUM)
        - **최상급 표현**: 최고, 최초, 1위, 완벽, 기적
        - **비교 광고**: 타사 대비, 경쟁사보다 (증빙 필요)
        - **가격 표현**: 정가 대비 할인 (증빙 필요)
        - **상표권**: ~스타일, ~느낌, ~풍 (디자인 카피 암시)

        ### 💡 안전한 대안
        - "최고의" → "프리미엄", "고품질"
        - "암 예방" → "건강한 생활 도움"
        - "100% 효과" → "만족도 높은", "호평받는"
        - "미백 효과" → "피부 보습", "촉촉한 사용감"
        - "디즈니 캐릭터" → "오리지널 디자인", "자체 제작"
        - "통증 완화" → "편안한 사용감", "릴렉스"
        - "자세 교정" → "바른 자세 도움", "자세 습관 관리"
        """)

# ============================================================
# TAB 4: 리뷰 분석 (Phase 5.1 MVP - v3.5.1)
# ============================================================
with tab4:
    st.header("📝 경쟁사 리뷰 분석")
    st.markdown("리뷰를 분석하여 **치명적 결함**, **개선점**, **마케팅 소구점**, **샘플 체크리스트**를 도출합니다.")

    # API 키 상태 확인
    import os
    google_api_key = os.getenv("GOOGLE_API_KEY")

    if not google_api_key:
        st.warning("⚠️ GOOGLE_API_KEY가 설정되지 않았습니다. .env 파일에 키를 추가하세요.")
        st.code("GOOGLE_API_KEY=your_google_api_key", language="ini")
        use_mock_review = True
    else:
        st.success("✅ Gemini API 연결됨")
        use_mock_review = False

    # 카테고리 선택 (v3.5.1 추가)
    review_category = st.selectbox(
        "📦 상품 카테고리",
        options=["의류", "가구", "전자기기", "주방용품", "캠핑/레저", "화장품", "기타"],
        index=0,
        help="카테고리에 맞는 분석 포인트가 적용됩니다"
    )

    # 입력 방식 선택
    input_method = st.radio(
        "입력 방식",
        options=["텍스트 붙여넣기", "파일 업로드 (TXT)"],
        horizontal=True,
        help="MVP: 네이버 리뷰 페이지에서 텍스트를 복사하여 붙여넣으세요"
    )

    reviews_text = ""

    if input_method == "텍스트 붙여넣기":
        reviews_text = st.text_area(
            "리뷰 텍스트 (줄바꿈으로 구분)",
            height=200,
            placeholder="""좋아요! 색감이 사진이랑 똑같아요.
근데 세탁하니까 좀 줄었어요...
실밥이 튀어나와 있어서 아쉬워요.
배송은 빨랐는데 박스가 찌그러져서 왔어요.
원단이 생각보다 두껍고 고급스러워요!
사이즈가 좀 작게 나온 것 같아요. 한 사이즈 크게 주문하세요.""",
            key="review_text"
        )
    else:
        uploaded_file = st.file_uploader("리뷰 파일 업로드", type=["txt"], key="review_file")
        if uploaded_file:
            reviews_text = uploaded_file.read().decode("utf-8")
            st.text_area("업로드된 내용", reviews_text, height=150, disabled=True)

    # Mock 모드 체크박스
    use_mock_review_checkbox = st.checkbox("🧪 테스트 모드 (Mock 데이터)", value=use_mock_review, key="review_mock")

    # 분석 버튼
    if st.button("🔍 리뷰 분석", type="primary", key="review_btn"):
        if not reviews_text and not use_mock_review_checkbox:
            st.error("리뷰 텍스트를 입력하세요.")
        else:
            with st.spinner("🧠 Gemini가 리뷰를 분석 중..."):
                try:
                    from src.analyzers.review_analyzer import (
                        ReviewAnalyzer, MockReviewAnalyzer, Verdict
                    )

                    if use_mock_review_checkbox:
                        analyzer = MockReviewAnalyzer()
                    else:
                        analyzer = ReviewAnalyzer(api_key=google_api_key)

                    result = analyzer.analyze_sync(reviews_text or "테스트 리뷰", category=review_category)

                    # 결과 표시
                    st.markdown("---")

                    # 판정 결과 (신호등 스타일)
                    if result.verdict == Verdict.GO:
                        st.markdown("""
                        <div style="background-color: #d4edda; padding: 15px; border-radius: 10px; border-left: 5px solid #28a745;">
                            <h3 style="color: #155724; margin: 0;">🟢 판정: Go - 소싱 진행 권장</h3>
                        </div>
                        """, unsafe_allow_html=True)
                    elif result.verdict == Verdict.HOLD:
                        st.markdown("""
                        <div style="background-color: #fff3cd; padding: 15px; border-radius: 10px; border-left: 5px solid #ffc107;">
                            <h3 style="color: #856404; margin: 0;">🟡 판정: Hold - 샘플 확인 후 결정</h3>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div style="background-color: #f8d7da; padding: 15px; border-radius: 10px; border-left: 5px solid #dc3545;">
                            <h3 style="color: #721c24; margin: 0;">🔴 판정: Drop - 소싱 포기 권장</h3>
                        </div>
                        """, unsafe_allow_html=True)

                    # 한 줄 요약 (v3.5.1 추가)
                    if result.summary_one_line:
                        st.info(f"📝 **요약:** {result.summary_one_line}")

                    # 3단 컬럼 레이아웃
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.subheader("🚨 치명적 결함")
                        if result.critical_defects:
                            for d in result.critical_defects:
                                freq_icon = "🔴" if d.frequency == "High" else "🟡" if d.frequency == "Medium" else "🟢"
                                st.markdown(f"{freq_icon} **[{d.frequency}]** {d.issue}")
                                if d.quote:
                                    st.caption(f'💬 "{d.quote}"')
                        else:
                            st.success("치명적 결함 없음")

                    with col2:
                        st.subheader("🔧 공장 협의사항")
                        if result.improvement_requests:
                            for item in result.improvement_requests:
                                st.markdown(f"• {item}")
                        else:
                            st.info("특별 요청 없음")

                    with col3:
                        st.subheader("💡 마케팅 소구점")
                        if result.marketing_hooks:
                            for item in result.marketing_hooks:
                                st.markdown(f"• {item}")
                        else:
                            st.info("소구점 미발견")

                    # 샘플 체크리스트 (v3.5.1 추가)
                    if result.sample_check_points:
                        st.markdown("---")
                        st.subheader("✅ 샘플 수령 시 체크리스트")
                        for i, item in enumerate(result.sample_check_points, 1):
                            st.checkbox(f"{i}. {item}", key=f"check_{i}", value=False)

                    # 엑셀 다운로드 (v3.5.1 Quick Win - Gemini 피드백)
                    st.markdown("---")
                    try:
                        import pandas as pd
                        from io import BytesIO

                        # 데이터 준비
                        export_data = {
                            "항목": ["판정", "한줄요약", "치명적결함", "공장협의", "마케팅소구점", "샘플체크"],
                            "내용": [
                                result.verdict.value,
                                result.summary_one_line,
                                "\n".join([f"[{d.frequency}] {d.issue}" for d in result.critical_defects]),
                                "\n".join(result.improvement_requests),
                                "\n".join(result.marketing_hooks),
                                "\n".join(result.sample_check_points),
                            ]
                        }
                        df = pd.DataFrame(export_data)

                        # 엑셀 버퍼 생성
                        buffer = BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False, sheet_name='리뷰분석')
                        buffer.seek(0)

                        st.download_button(
                            label="📥 엑셀로 다운로드",
                            data=buffer,
                            file_name=f"review_analysis_{review_category}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    except ImportError:
                        st.info("💡 엑셀 다운로드를 위해 `pip install pandas openpyxl` 실행 필요")

                    # 상세 보기
                    with st.expander("📋 전체 분석 리포트"):
                        st.code(analyzer.format_report(result), language="text")

                except ImportError as e:
                    st.error(f"패키지 오류: {e}")
                    st.code("pip install google-generativeai", language="bash")
                except Exception as e:
                    # 에러 유형별 핸들링 (Gemini 피드백 반영)
                    msg = str(e).lower()
                    if "quota" in msg or "429" in msg or "rate" in msg:
                        st.error("💡 API 쿼터 초과! 잠시 후 또는 내일 다시 시도하세요.")
                    elif "timeout" in msg or "timed out" in msg:
                        st.warning("⏱️ 응답이 늦네요. 잠시 후 다시 시도해주세요.")
                    elif "api_key" in msg or "invalid" in msg:
                        st.error("🔑 API 키가 잘못되었습니다. .env 파일을 확인하세요.")
                    else:
                        st.error(f"❌ 분석 실패: {str(e)}")

    # 사용법 가이드
    with st.expander("💡 사용법 가이드"):
        st.markdown("""
        ### 리뷰 수집 방법 (MVP)
        1. 네이버 쇼핑에서 경쟁 상품 페이지 열기
        2. 리뷰 탭에서 **최신순** 또는 **별점낮은순** 정렬
        3. 리뷰 텍스트를 복사 (Ctrl+C)
        4. 위 입력창에 붙여넣기 (Ctrl+V)

        ### 분석 결과 해석
        - **🚨 치명적 결함**: 즉시 소싱 포기 사유 (품질 문제)
        - **🔧 공장 협의사항**: 1688 판매자에게 요청할 개선점
        - **💡 마케팅 소구점**: 상세페이지에 강조할 장점

        ### 판정 기준
        - **Go**: 심각한 결함 없음, 소싱 진행
        - **Hold**: 일부 이슈 있음, 샘플 확인 후 결정
        - **Drop**: 치명적 결함, 소싱 포기 권장
        """)

# ============================================================
# TAB 5: 가격 추적 (Phase 8 - Gemini CTO 권장)
# ============================================================
with tab5:
    st.header("📈 경쟁사 가격 추적")
    st.markdown("경쟁사 상품 가격을 모니터링하고 최적의 가격 전략을 제안합니다.")

    # 세션 상태 초기화
    if "price_tracker" not in st.session_state:
        st.session_state.price_tracker = PriceTracker()

    tracker = st.session_state.price_tracker

    # 스케줄러 초기화
    if "scheduler" not in st.session_state:
        st.session_state.scheduler = create_scheduler(tracker, use_mock=True)

    scheduler = st.session_state.scheduler
    # 트래커가 변경된 경우 동기화
    scheduler.tracker = tracker

    # 서브탭
    price_tab1, price_tab2, price_tab3, price_tab4 = st.tabs([
        "➕ 상품 등록",
        "📊 경쟁 분석",
        "🔔 가격 알림",
        "⚙️ 자동 모니터링"
    ])

    # ----------------------------------------------------------
    # 서브탭 1: 상품 등록
    # ----------------------------------------------------------
    with price_tab1:
        st.subheader("경쟁사 상품 등록")

        reg_col1, reg_col2 = st.columns(2)

        with reg_col1:
            comp_name = st.text_input(
                "상품명",
                placeholder="예: 초경량 캠핑의자 A사",
                key="comp_name"
            )
            comp_url = st.text_input(
                "상품 URL",
                placeholder="https://smartstore.naver.com/...",
                key="comp_url",
                help="네이버, 쿠팡, G마켓 등 URL 입력"
            )
            comp_price = st.number_input(
                "현재 가격 (원)",
                min_value=0,
                max_value=10000000,
                value=30000,
                step=1000,
                key="comp_price"
            )

        with reg_col2:
            my_price = st.number_input(
                "내 상품 가격 (원) - 비교용",
                min_value=0,
                max_value=10000000,
                value=32000,
                step=1000,
                key="my_price_input"
            )
            my_cost = st.number_input(
                "내 상품 원가 (원) - 전략 계산용",
                min_value=0,
                max_value=10000000,
                value=20000,
                step=1000,
                key="my_cost_input"
            )
            comp_tags = st.text_input(
                "태그 (쉼표 구분)",
                placeholder="캠핑의자, 경쟁사A",
                key="comp_tags"
            )

        # 등록 버튼
        if st.button("➕ 경쟁사 상품 등록", type="primary", key="add_comp_btn"):
            if not comp_name:
                st.error("상품명을 입력하세요.")
            elif comp_price <= 0:
                st.error("가격을 입력하세요.")
            else:
                tags = [t.strip() for t in comp_tags.split(",") if t.strip()] if comp_tags else []
                product = tracker.add_product(
                    name=comp_name,
                    url=comp_url or "manual_input",
                    current_price=comp_price,
                    my_price=my_price if my_price > 0 else None,
                    tags=tags
                )

                # 플랫폼 자동 감지 표시
                platform_emoji = {
                    MarketPlatform.NAVER: "🟢 네이버",
                    MarketPlatform.COUPANG: "🟠 쿠팡",
                    MarketPlatform.GMARKET: "🔵 G마켓",
                    MarketPlatform.ELEVEN: "🟣 11번가",
                    MarketPlatform.AUCTION: "🔴 옥션",
                    MarketPlatform.OTHER: "⚪ 기타",
                }
                st.success(f"✅ 등록 완료! [{platform_emoji.get(product.platform, '기타')}] {product.name}")

        # 등록된 상품 목록
        st.markdown("---")
        st.subheader(f"📋 등록된 경쟁사 ({len(tracker.products)}개)")

        if tracker.products:
            for pid, p in tracker.products.items():
                with st.expander(f"{p.name} | {p.current_price:,}원", expanded=False):
                    info_col1, info_col2, action_col = st.columns([2, 2, 1])

                    with info_col1:
                        st.write(f"**플랫폼:** {p.platform.value.upper()}")
                        st.write(f"**현재 가격:** {p.current_price:,}원")
                        if p.my_price:
                            diff = p.current_price - p.my_price
                            diff_text = f"+{diff:,}원" if diff > 0 else f"{diff:,}원"
                            st.write(f"**내 가격 대비:** {diff_text}")

                    with info_col2:
                        st.write(f"**URL:** {p.url[:50]}...")
                        st.write(f"**태그:** {', '.join(p.tags) if p.tags else '-'}")
                        st.write(f"**마지막 확인:** {p.last_checked[:10]}")

                    with action_col:
                        # 가격 업데이트
                        new_price = st.number_input(
                            "새 가격",
                            min_value=0,
                            value=p.current_price,
                            key=f"update_{pid}"
                        )
                        if st.button("🔄 업데이트", key=f"update_btn_{pid}"):
                            alert = tracker.update_price(pid, new_price)
                            if alert:
                                st.info(f"가격 변동: {alert.change_percent:+.1f}%")
                            else:
                                st.success("가격 업데이트됨")
        else:
            st.info("아직 등록된 경쟁사 상품이 없습니다.")

    # ----------------------------------------------------------
    # 서브탭 2: 경쟁 분석
    # ----------------------------------------------------------
    with price_tab2:
        st.subheader("📊 경쟁력 분석 대시보드")

        if not tracker.products:
            st.warning("먼저 경쟁사 상품을 등록하세요.")
        else:
            # 내 가격 입력
            analysis_my_price = st.number_input(
                "내 상품 가격 (원)",
                min_value=1000,
                value=35000,
                step=1000,
                key="analysis_price"
            )

            analysis_my_cost = st.number_input(
                "내 상품 원가 (원)",
                min_value=1000,
                value=20000,
                step=1000,
                key="analysis_cost"
            )

            if st.button("🔍 경쟁력 분석", type="primary", key="analyze_btn"):
                # 경쟁력 분석
                analysis = tracker.get_competitive_analysis(analysis_my_price)

                st.markdown("---")

                # Tier 표시 (핵심!)
                tier = analysis.get("exposure_tier", "tier3")
                tier_msg = analysis.get("tier_message", "")

                tier_colors = {
                    "tier1": ("#d4edda", "#155724", "🟢"),  # 녹색
                    "tier2": ("#fff3cd", "#856404", "🟡"),  # 노란색
                    "tier3": ("#f8d7da", "#721c24", "🔴"),  # 빨간색
                }
                bg, fg, emoji = tier_colors.get(tier, tier_colors["tier3"])

                st.markdown(f"""
                <div style="background-color: {bg}; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                    <h3 style="color: {fg}; margin: 0;">{emoji} {tier_msg}</h3>
                </div>
                """, unsafe_allow_html=True)

                # 메트릭 카드
                m_col1, m_col2, m_col3, m_col4 = st.columns(4)

                with m_col1:
                    st.metric("경쟁사 수", f"{analysis['total_competitors']}개")
                with m_col2:
                    st.metric("시장 최저가", f"{analysis.get('min_price', 0):,}원")
                with m_col3:
                    st.metric("시장 평균가", f"{analysis['avg_competitor_price']:,}원")
                with m_col4:
                    st.metric("내 포지션", analysis['position'])

                # 가격 분포 차트
                st.markdown("---")
                st.subheader("📊 가격 분포")

                prices = [p.current_price for p in tracker.products.values()]
                price_data = {
                    "상품": [p.name for p in tracker.products.values()],
                    "가격": prices
                }

                import pandas as pd
                df = pd.DataFrame(price_data)
                df = df.sort_values("가격")

                # 내 가격 추가
                my_df = pd.DataFrame({"상품": ["⭐ 내 상품"], "가격": [analysis_my_price]})
                df = pd.concat([df, my_df], ignore_index=True)

                st.bar_chart(df.set_index("상품"))

                # 가격 전략 제안
                st.markdown("---")
                st.subheader("💡 가격 전략 제안")

                # 첫 번째 상품에 대해 전략 계산 (my_price가 설정된 경우)
                strategy_product = None
                for pid, p in tracker.products.items():
                    if p.my_price:
                        strategy_product = pid
                        break

                if strategy_product:
                    strategy = tracker.get_pricing_strategy(
                        strategy_product,
                        my_cost=analysis_my_cost,
                        target_margin=30.0
                    )

                    if strategy:
                        # 전략 유형 표시
                        if strategy.strategy_type == PricingStrategyType.PRICE_LEADERSHIP:
                            st.success(f"""
                            **🟢 전략: 가격 리더십 (Price Leadership)**

                            - 추천 가격: **{strategy.recommended_price:,}원**
                            - 예상 마진율: {strategy.margin_at_recommended:.1f}%
                            - 시장 최저가: {strategy.min_competitor_price:,}원

                            {strategy.recommendation}
                            """)
                        else:
                            st.warning(f"""
                            **🔴 전략: 프리미엄 포지셔닝 (Premium Positioning)**

                            - 추천 가격: **{strategy.recommended_price:,}원**
                            - 예상 마진율: {strategy.margin_at_recommended:.1f}%
                            - 시장 최저가: {strategy.min_competitor_price:,}원

                            {strategy.recommendation}
                            """)

                        # Tier 표시
                        tier_labels = {
                            ExposureTier.TIER1_EXPOSURE: "🟢 Tier 1: 노출권",
                            ExposureTier.TIER2_DEFENSE: "🟡 Tier 2: 방어권",
                            ExposureTier.TIER3_OUT: "🔴 Tier 3: 이탈권",
                        }
                        st.info(f"추천가 노출 등급: {tier_labels.get(strategy.exposure_tier, 'Unknown')}")
                else:
                    st.info("💡 가격 전략을 보려면 상품 등록 시 '내 상품 가격'을 입력하세요.")

    # ----------------------------------------------------------
    # 서브탭 3: 가격 알림
    # ----------------------------------------------------------
    with price_tab3:
        st.subheader("🔔 가격 변동 알림")

        alerts = tracker.alerts
        unread = tracker.get_unread_alerts()

        if unread:
            st.error(f"📢 읽지 않은 알림 {len(unread)}건")

        if alerts:
            for alert in reversed(alerts[-20:]):  # 최근 20개만
                # 알림 레벨별 스타일
                if alert.alert_level == AlertLevel.CRITICAL:
                    container = st.error
                    icon = "🚨"
                elif alert.alert_level == AlertLevel.WARNING:
                    container = st.warning
                    icon = "⚠️"
                else:
                    container = st.info
                    icon = "ℹ️"

                # 읽음 여부
                read_mark = "" if alert.is_read else " 🆕"

                container(f"""
                {icon} **{alert.product_name}**{read_mark}

                {alert.message}

                📅 {alert.timestamp[:16]}
                """)

                # 읽음 처리 버튼
                if not alert.is_read:
                    if st.button("✓ 읽음", key=f"read_{alert.alert_id}"):
                        tracker.mark_alert_read(alert.alert_id)
                        st.rerun()
        else:
            st.info("아직 가격 변동 알림이 없습니다.")

        # 알림 기준 안내
        with st.expander("📋 알림 기준 (v3.6.1)"):
            st.markdown(f"""
            ### 하이브리드 임계값 (Gemini CTO 권장)
            - **% 조건 AND 금액 조건** 모두 충족해야 WARNING 이상

            | 레벨 | 변동률 | 변동 금액 |
            |------|--------|-----------|
            | 🚨 CRITICAL | ≥15% | ≥1,000원 |
            | ⚠️ WARNING | ≥5% | ≥1,000원 |
            | ℹ️ INFO | 그 외 | - |

            ### 노출 등급 (Tier)
            - **Tier 1 (노출권)**: 최저가 대비 +2% 이내
            - **Tier 2 (방어권)**: 최저가 대비 +10% 이내
            - **Tier 3 (이탈권)**: +10% 초과 (사실상 노출 X)
            """)

    # ----------------------------------------------------------
    # 서브탭 4: 자동 모니터링 (Phase 9)
    # ----------------------------------------------------------
    with price_tab4:
        st.subheader("⚙️ 자동 모니터링 스케줄러")
        st.markdown("경쟁사 가격을 자동으로 모니터링하고 변동 시 알림을 받습니다.")

        # 스케줄러 상태 표시
        status = scheduler.get_status()
        current_status = status["status"]

        # 상태 카드
        status_colors = {
            "running": ("#d4edda", "#155724", "🟢 실행 중"),
            "paused": ("#fff3cd", "#856404", "🟡 일시정지"),
            "stopped": ("#f8d7da", "#721c24", "🔴 중지됨"),
        }
        bg, fg, status_text = status_colors.get(current_status, status_colors["stopped"])

        st.markdown(f"""
        <div style="background-color: {bg}; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
            <h3 style="color: {fg}; margin: 0;">{status_text}</h3>
            <p style="color: {fg}; margin: 5px 0 0 0;">등록된 상품: {status['products_count']}개 | 활성 상품: {status['active_products']}개</p>
        </div>
        """, unsafe_allow_html=True)

        # 컨트롤 버튼
        st.markdown("### 📡 스케줄러 제어")
        ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns(4)

        with ctrl_col1:
            interval_hours = st.selectbox(
                "체크 간격",
                options=[0.5, 1, 6, 12, 24],
                index=2,  # 6시간
                format_func=lambda x: f"{x}시간" if x >= 1 else f"{int(x*60)}분",
                key="scheduler_interval"
            )

        with ctrl_col2:
            if current_status == "stopped":
                if st.button("▶️ 시작", type="primary", key="start_scheduler"):
                    if status['products_count'] == 0:
                        st.error("먼저 경쟁사 상품을 등록하세요.")
                    else:
                        scheduler.start(interval_hours=interval_hours, run_immediately=True)
                        st.success("스케줄러 시작됨!")
                        st.rerun()
            elif current_status == "running":
                if st.button("⏸️ 일시정지", key="pause_scheduler"):
                    scheduler.pause()
                    st.rerun()
            else:  # paused
                if st.button("▶️ 재개", type="primary", key="resume_scheduler"):
                    scheduler.resume()
                    st.rerun()

        with ctrl_col3:
            if current_status != "stopped":
                if st.button("⏹️ 중지", key="stop_scheduler"):
                    scheduler.stop()
                    st.rerun()
            else:
                st.button("⏹️ 중지", key="stop_disabled", disabled=True)

        with ctrl_col4:
            if st.button("🔄 즉시 실행", key="run_now"):
                if status['products_count'] == 0:
                    st.error("먼저 경쟁사 상품을 등록하세요.")
                else:
                    with st.spinner("가격 체크 중..."):
                        result = scheduler.run_now()
                    st.success(f"✅ 완료! {result.products_checked}개 체크, {result.alerts_generated}개 알림 생성")
                    st.rerun()

        # 스케줄 정보
        if status["job"]:
            job = status["job"]
            st.markdown("---")
            st.markdown("### 📅 스케줄 정보")

            job_col1, job_col2, job_col3 = st.columns(3)

            with job_col1:
                interval_display = job["interval_seconds"] // 3600
                st.metric("체크 간격", f"{interval_display}시간")
            with job_col2:
                st.metric("총 실행 횟수", f"{job['run_count']}회")
            with job_col3:
                st.metric("오류 횟수", f"{job['error_count']}건")

            if job["last_run"]:
                st.caption(f"마지막 실행: {job['last_run'][:19]}")
            if job["next_run"]:
                st.caption(f"다음 실행 예정: {job['next_run'][:19]}")

        # 최근 실행 결과
        st.markdown("---")
        st.markdown("### 📊 최근 실행 결과")

        recent_results = scheduler.get_recent_results(limit=10)

        if recent_results:
            # 요약 통계
            summary = scheduler.get_summary()

            sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)
            with sum_col1:
                st.metric("총 실행", f"{summary['total_runs']}회")
            with sum_col2:
                st.metric("총 알림", f"{summary['total_alerts']}건")
            with sum_col3:
                st.metric("평균 소요시간", f"{summary['avg_duration_ms']:.0f}ms")
            with sum_col4:
                st.metric("오류율", f"{summary['error_rate']:.1f}%")

            # 결과 테이블
            st.markdown("#### 실행 기록")
            import pandas as pd

            results_data = []
            for r in reversed(recent_results):
                results_data.append({
                    "시간": r.timestamp[:19],
                    "체크 상품": r.products_checked,
                    "알림 생성": r.alerts_generated,
                    "오류": len(r.errors),
                    "소요시간": f"{r.duration_ms:.0f}ms"
                })

            if results_data:
                df = pd.DataFrame(results_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("아직 실행 기록이 없습니다. '즉시 실행' 또는 스케줄러를 시작하세요.")

        # 알림 콜백 설정 안내
        with st.expander("🔔 알림 설정 (개발 예정)"):
            st.markdown("""
            ### 향후 지원 예정 기능

            **📱 알림 채널**
            - Slack 웹훅
            - Telegram 봇
            - 이메일 알림
            - 카카오톡 알림 (Phase 4)

            **⚙️ 현재 방식**
            - 대시보드 '가격 알림' 탭에서 확인
            - 브라우저 새로고침으로 최신 알림 확인

            **💡 개발자 API**
            ```python
            # 커스텀 콜백 등록
            def my_callback(alert):
                send_slack(alert.message)

            scheduler.add_alert_callback(my_callback)
            ```
            """)

# ============================================================
# 푸터
# ============================================================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        Smart Store Agent v3.6.2 | Phase 9 (자동 모니터링 스케줄러)<br>
        "망하는 상품을 미리 걸러내는" 보수적 분석기<br>
        Powered by Claude Code + Gemini AI + Apify
    </div>
    """,
    unsafe_allow_html=True
)
