"""
sourcing_tab.py - 통합 소싱 분석 탭 (v4.2)

Gemini CTO 승인:
- 원클릭 소싱 + 마진 분석 + Pre-Flight 통합
- 워터폴 흐름: 입력 → 시장조사 → 마진계산 → 리스크체크 → 결정
- v4.2: Toss 스타일 판정카드, Plotly 게이지/도넛 차트
"""

import streamlit as st
from typing import Optional, Dict, Any
import os

from src.domain.models import Product, MarketType, RiskLevel
from src.domain.logic import LandedCostCalculator
from src.core.config import AppConfig, MARKET_FEES
from src.ui.tabs.settings_tab import get_current_settings, get_app_config
from src.ui.styles import render_verdict_card, render_margin_gauge, render_cost_donut, COLORS
from src.analyzers.preflight_check import PreFlightChecker


def render():
    """소싱 분석 탭 렌더링 (통합)"""
    st.header("🔍 소싱 분석")
    st.markdown("상품 정보 입력 → 시장조사 → 마진분석 → 리스크체크 → 최종 판정")

    # 설정 로드
    settings = get_current_settings()
    config = get_app_config()
    calculator = LandedCostCalculator(config)
    market = MarketType(settings["market"])

    # API 상태 표시
    _render_api_status()

    st.divider()

    # ========== Step 1: 상품 정보 입력 ==========
    st.subheader("📦 Step 1: 상품 정보")

    # v4.4: 소싱 플랫폼 모드 전환
    source_mode = st.radio(
        "소싱 플랫폼",
        options=["🇨🇳 1688 (위안)", "🛒 알리익스프레스 (달러)"],
        horizontal=True,
        key="source_platform_mode"
    )
    is_aliexpress_mode = "알리익스프레스" in source_mode

    col1, col2 = st.columns(2)

    with col1:
        product_name = st.text_input(
            "상품명",
            value="",
            placeholder="예: 미니멀 데스크 정리함",
            help="네이버 검색에 사용될 상품명"
        )

        category = st.selectbox(
            "카테고리",
            options=list(config.tariff_rates.keys()),
            index=4  # 생활용품
        )

        # v4.4: 플랫폼별 가격 입력
        if is_aliexpress_mode:
            price_usd = st.number_input(
                "알리익스프레스 가격 (USD)",
                min_value=0.1,
                max_value=1000.0,
                value=10.0,
                step=0.5,
                help="알리익스프레스 달러 가격 (배송비 포함 가정)"
            )
            # USD → CNY 변환
            price_cny = price_usd * config.exchange_rate_usd_cny
            st.caption(f"💱 환산: {price_cny:.1f} 위안 (1 USD = {config.exchange_rate_usd_cny} CNY)")
        else:
            price_cny = st.number_input(
                "1688 도매가 (위안)",
                min_value=1.0,
                max_value=10000.0,
                value=35.0,
                step=1.0,
                help="1688에서 확인한 단가"
            )

    with col2:
        weight_kg = st.number_input(
            "실제 무게 (kg)",
            min_value=0.1,
            max_value=100.0,
            value=1.0,
            step=0.1
        )

        st.markdown("**📦 박스 사이즈 (cm)**")
        dim_col1, dim_col2, dim_col3 = st.columns(3)
        with dim_col1:
            length = st.number_input("가로", min_value=1, value=30, step=1)
        with dim_col2:
            width = st.number_input("세로", min_value=1, value=20, step=1)
        with dim_col3:
            height = st.number_input("높이", min_value=1, value=15, step=1)

    col3, col4 = st.columns(2)
    with col3:
        moq = st.number_input(
            "MOQ (최소 주문 수량)",
            min_value=1,
            max_value=1000,
            value=10,
            step=1
        )
    with col4:
        shipping_method = st.radio(
            "배송 방법",
            options=["항공", "해운"],
            horizontal=True
        )

    # ========== 상세 정보 직접 입력 (선택) ==========
    with st.expander("📋 상세 정보 직접 입력 (선택)", expanded=False):
        manual_data = _render_manual_input_section()
        if manual_data:
            st.session_state.manual_input = manual_data

    st.divider()

    # ========== 분석 시작 버튼 ==========
    if st.button("🚀 전체 분석 시작", type="primary", use_container_width=True, disabled=not product_name):
        # v4.4: 새 분석 시작 시 session state 초기화
        st.session_state.sourcing_result = {}
        st.session_state.excluded_competitors = set()  # 경쟁사 제외 목록 초기화
        st.session_state.image_search_result = None    # 이미지 검색 결과 초기화

        # ========== Step 2: 시장 조사 ==========
        with st.spinner("📊 Step 2: 시장 조사 중..."):
            market_result = _run_market_research(product_name)
            st.session_state.sourcing_result["market"] = market_result

        # ========== Step 3: 마진 분석 ==========
        with st.spinner("💰 Step 3: 마진 분석 중..."):
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

            # 목표가 설정 (시장 조사 결과 또는 기본값)
            if market_result and market_result.get("recommended_price"):
                target_price = market_result["recommended_price"]
            else:
                # 원가의 2.5배를 기본 목표가로
                target_price = int(price_cny * settings["exchange_rate"] * 2.5)

            # v4.4: source_platform 전달 (알리는 중국 내 배송비 0)
            margin_result = calculator.calculate(
                product=product,
                target_price=target_price,
                market=market,
                shipping_method=shipping_method,
                include_ad_cost=True,
                source_platform="aliexpress" if is_aliexpress_mode else "1688"
            )
            st.session_state.sourcing_result["margin"] = margin_result
            st.session_state.sourcing_result["target_price"] = target_price

        # ========== Step 4: Pre-Flight 체크 ==========
        with st.spinner("✅ Step 4: 리스크 체크 중..."):
            checker = PreFlightChecker(strict_mode=False)
            preflight_result = checker.check_product(product_name, "")
            st.session_state.sourcing_result["preflight"] = preflight_result

        st.session_state.sourcing_result["product_name"] = product_name
        st.session_state.sourcing_result["price_cny"] = price_cny
        st.session_state.sourcing_result["category"] = category

        st.success("✅ 분석 완료!")
        st.rerun()

    # ========== 결과 표시 ==========
    if "sourcing_result" in st.session_state and st.session_state.sourcing_result:
        _render_results(st.session_state.sourcing_result, settings)


def _render_api_status():
    """API 상태 표시"""
    col1, col2 = st.columns(2)

    with col1:
        naver_ok = os.getenv("NAVER_CLIENT_ID") and os.getenv("NAVER_CLIENT_SECRET")
        if naver_ok:
            st.success("네이버 API: 연결됨")
        else:
            st.warning("네이버 API: 미설정 (Mock 모드)")

    with col2:
        serpapi_ok = os.getenv("SERPAPI_KEY")
        if serpapi_ok:
            st.success("SerpApi: 연결됨")
        else:
            st.info("SerpApi: 미설정 (선택)")


def _run_market_research(keyword: str) -> Optional[Dict[str, Any]]:
    """시장 조사 실행"""
    try:
        from src.analyzers.market_researcher import MarketResearcher

        researcher = MarketResearcher()
        result = researcher.research_by_text(keyword, max_results=10)

        return {
            "query": result.query,
            "competitor_count": len(result.competitors),
            "min_price": result.price_range[0],
            "max_price": result.price_range[1],
            "avg_price": result.average_price,
            "recommended_price": result.recommended_price,
            "price_strategy": result.price_strategy,
            "competitors": result.competitors[:5],  # 상위 5개만
        }

    except Exception as e:
        st.warning(f"시장 조사 오류: {e}")
        return None


def _render_results(result: Dict[str, Any], settings: Dict[str, Any]):
    """분석 결과 표시"""
    st.divider()
    st.header("📋 분석 결과")

    # ========== 최종 판정 ==========
    margin_result = result.get("margin")
    preflight_result = result.get("preflight")

    # 종합 판정
    if margin_result:
        if margin_result.risk_level == RiskLevel.DANGER:
            final_verdict = "🔴 NO-GO"
            verdict_status = "nogo"
            verdict_reason = f"마진율 {margin_result.margin_percent}% - 수익성 부족"
        elif margin_result.risk_level == RiskLevel.WARNING:
            final_verdict = "🟡 주의"
            verdict_status = "warning"
            verdict_reason = f"마진율 {margin_result.margin_percent}% - 신중한 검토 필요"
        else:
            final_verdict = "🟢 GO"
            verdict_status = "go"
            verdict_reason = f"마진율 {margin_result.margin_percent}% - 진입 추천"

        # Pre-Flight 위반 시 경고 추가
        if preflight_result and not preflight_result.passed:
            final_verdict = "🟡 주의"
            verdict_status = "warning"
            verdict_reason += f" (금지어 {preflight_result.error_count}건 발견)"
    else:
        final_verdict = "⚪ 분석 불가"
        verdict_status = "warning"
        verdict_reason = "마진 계산 실패"

    # Toss 스타일 판정 카드 (v4.2)
    render_verdict_card(final_verdict, verdict_reason, verdict_status)

    # ========== Step 2: 시장 조사 결과 ==========
    st.subheader("📊 시장 조사")

    # v4.4: 이미지 검색 결과가 있으면 우선 표시
    image_result = st.session_state.get("image_search_result")
    if image_result:
        st.info("🔍 이미지 검색 결과 (Google Lens)")
        market_result = image_result
    else:
        market_result = result.get("market")

    if market_result:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("경쟁사 수", f"{market_result['competitor_count']}개")
        col2.metric("최저가", f"{market_result['min_price']:,}원")
        col3.metric("평균가", f"{market_result['avg_price']:,}원")
        col4.metric("추천가", f"{market_result['recommended_price']:,}원")

        # v4.4: 경쟁사 목록 UI 개선 (썸네일 + 체크박스)
        with st.expander("경쟁사 목록 (제외 가능)", expanded=True):
            # session state 초기화
            if "excluded_competitors" not in st.session_state:
                st.session_state.excluded_competitors = set()

            competitors = market_result.get("competitors", [])

            if competitors:
                # 3열 그리드
                cols = st.columns(3)
                for i, comp in enumerate(competitors):
                    with cols[i % 3]:
                        # 체크박스 상태
                        is_excluded = i in st.session_state.excluded_competitors

                        # 썸네일 (있으면 표시)
                        if hasattr(comp, 'thumbnail') and comp.thumbnail:
                            try:
                                if is_excluded:
                                    st.image(comp.thumbnail, width=80, caption="제외됨")
                                else:
                                    st.image(comp.thumbnail, width=100)
                            except Exception:
                                pass

                        # 상품 정보 (제외 시 흐리게)
                        title_display = comp.title[:25] + "..." if len(comp.title) > 25 else comp.title
                        if is_excluded:
                            st.markdown(f"<span style='opacity:0.4; text-decoration:line-through;'>{title_display}</span>", unsafe_allow_html=True)
                            st.markdown(f"<span style='opacity:0.4'>💰 ~~{comp.price:,}원~~</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"**{title_display}**")
                            st.markdown(f"💰 **{comp.price:,}원**")

                        # 출처
                        source = getattr(comp, 'source', '네이버쇼핑')
                        st.caption(f"출처: {source}")

                        # 제외 체크박스
                        excluded = st.checkbox(
                            "제외",
                            key=f"exclude_{i}",
                            value=is_excluded
                        )
                        if excluded:
                            st.session_state.excluded_competitors.add(i)
                        else:
                            st.session_state.excluded_competitors.discard(i)

                        st.markdown("---")

                # v4.4: 제외 반영 재계산 버튼
                if st.session_state.excluded_competitors:
                    st.warning(f"⚠️ {len(st.session_state.excluded_competitors)}개 상품 제외됨")

                    if st.button("🔄 제외 반영하여 추천가 재계산", key="recalc_price_btn"):
                        # 제외되지 않은 경쟁사만 필터링
                        filtered_comps = [
                            c for i, c in enumerate(competitors)
                            if i not in st.session_state.excluded_competitors
                        ]

                        if filtered_comps:
                            prices = [c.price for c in filtered_comps if c.price > 0]
                            if prices:
                                new_min = min(prices)
                                new_max = max(prices)
                                new_avg = sum(prices) // len(prices)
                                new_recommended = max(int(new_avg * 0.9), new_min)

                                # session state 업데이트
                                st.session_state.sourcing_result["market"]["min_price"] = new_min
                                st.session_state.sourcing_result["market"]["max_price"] = new_max
                                st.session_state.sourcing_result["market"]["avg_price"] = new_avg
                                st.session_state.sourcing_result["market"]["recommended_price"] = new_recommended
                                st.session_state.sourcing_result["market"]["competitor_count"] = len(filtered_comps)

                                st.success(f"✅ 새 추천가: {new_recommended:,}원 ({len(filtered_comps)}개 기준)")
                                st.rerun()
                        else:
                            st.error("모든 경쟁사를 제외할 수 없습니다.")
            else:
                st.info("경쟁사 데이터 없음")
    else:
        st.info("시장 조사 데이터 없음 (API 미설정)")

    st.divider()

    # ========== Step 3: 마진 분석 결과 ==========
    st.subheader("💰 마진 분석")

    if margin_result:
        # 게이지 차트 + 메트릭 (v4.2)
        col_gauge, col_metrics = st.columns([1, 1])

        with col_gauge:
            # Plotly 마진 게이지 차트
            render_margin_gauge(
                margin_result.margin_percent,
                target=settings["target_margin"] * 100
            )

        with col_metrics:
            # 핵심 메트릭
            st.metric("예상 수익", f"₩{margin_result.profit:,}")
            st.metric("손익분기 판매가", f"₩{margin_result.breakeven_price:,}")
            st.metric("추천 판매가", f"₩{result.get('target_price', 0):,}")

        # 비용 구조 차트 (v4.2)
        st.markdown("##### 💸 비용 구조")
        col_donut, col_detail = st.columns([1, 1])

        with col_donut:
            # Plotly 도넛 차트
            bd = margin_result.breakdown
            breakdown_dict = {
                "product_cost": bd.product_cost,
                "china_shipping": bd.china_shipping,
                "agency_fee": bd.agency_fee,
                "tariff": bd.tariff,
                "vat": bd.vat,
                "shipping_international": bd.shipping_international,
                "shipping_domestic": bd.shipping_domestic,
                "platform_fee": bd.platform_fee,
                "ad_cost": bd.ad_cost,
                "return_allowance": bd.return_allowance,
                "packaging": bd.packaging,
            }
            render_cost_donut(breakdown_dict, margin_result.total_cost)

        with col_detail:
            # 비용 상세 (텍스트)
            with st.expander("상세 내역", expanded=True):
                st.markdown(f"""
                **🇨🇳 중국 내**
                - 상품 원가: ₩{bd.product_cost:,}
                - 중국 배송: ₩{bd.china_shipping:,}
                - 구매대행: ₩{bd.agency_fee:,}

                **🚢 수입**
                - 관세: ₩{bd.tariff:,}
                - 부가세: ₩{bd.vat:,}
                - 해외 배송: ₩{bd.shipping_international:,}

                **🛒 판매**
                - 수수료: ₩{bd.platform_fee:,}
                - 광고비: ₩{bd.ad_cost:,}
                - 국내 배송: ₩{bd.shipping_domestic:,}
                """)
    else:
        st.error("마진 분석 실패")

    st.divider()

    # ========== Step 4: Pre-Flight 결과 ==========
    st.subheader("✅ 리스크 체크")

    if preflight_result:
        if preflight_result.passed:
            st.success("✅ 금지어 검사 통과!")
        else:
            st.warning(f"⚠️ 오류 {preflight_result.error_count}건, 경고 {preflight_result.warning_count}건 발견")

            for v in preflight_result.violations[:3]:
                severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(v.severity, "⚪")
                st.write(f"{severity_emoji} **{v.type.value}**: `{v.matched_text}` → {v.suggestion}")
    else:
        st.info("Pre-Flight 검사 데이터 없음")

    st.divider()

    # ========== 액션 버튼 ==========
    st.subheader("🎯 다음 단계")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📥 엑셀에 추가", use_container_width=True):
            # 승인된 상품 저장 로직
            st.info("모닝 브리핑의 승인된 상품 목록에 추가하세요.")

    with col2:
        if st.button("📝 리뷰 분석으로", use_container_width=True):
            st.session_state.review_keyword = result.get("product_name", "")
            st.info("리뷰 분석 탭으로 이동하세요.")

    with col3:
        if st.button("🔄 새 분석", use_container_width=True, type="secondary"):
            st.session_state.sourcing_result = {}
            st.rerun()


def _render_manual_input_section() -> Optional[Dict]:
    """수동 입력 섹션 (1688/알리익스프레스 대체) - v4.3"""
    st.caption("1688 또는 알리익스프레스 상품 페이지에서 복사한 정보를 입력하세요.")

    col1, col2 = st.columns(2)

    with col1:
        source_url = st.text_input(
            "상품 URL",
            placeholder="https://detail.1688.com/... 또는 https://aliexpress.com/...",
            key="manual_source_url"
        )

        # URL 플랫폼 자동 감지
        platform = None
        if source_url:
            if "1688.com" in source_url:
                st.caption("🇨🇳 1688 상품 감지됨")
                platform = "1688"
            elif "aliexpress" in source_url.lower():
                st.caption("🛒 알리익스프레스 상품 감지됨")
                platform = "aliexpress"
            elif "taobao" in source_url.lower():
                st.caption("🛍️ 타오바오 상품 감지됨")
                platform = "taobao"

        chinese_name = st.text_input(
            "중국어 상품명",
            placeholder="桌面收纳盒三层抽屉式",
            key="manual_chinese_name"
        )
        factory_name = st.text_input(
            "공장/판매자명",
            placeholder="优质工厂",
            key="manual_factory"
        )

    with col2:
        image_url = st.text_input(
            "이미지 URL",
            placeholder="https://cbu01.alicdn.com/img/...",
            key="manual_image_url"
        )

        # 이미지 URL 프리뷰 (try-except로 안전하게)
        if image_url:
            try:
                st.image(image_url, width=150)
            except Exception:
                st.warning("이미지 로드 실패 - URL을 확인하세요")

            # v4.4: 이미지 검색 버튼 (SerpApi Google Lens)
            serpapi_key = os.getenv("SERPAPI_KEY")
            if not serpapi_key:
                st.warning("⚠️ SerpApi 키 미설정")
                st.button("🔍 이미지로 경쟁사 검색", disabled=True, key="image_search_disabled")
            else:
                if st.button("🔍 이미지로 경쟁사 검색 (Credit 소모)", key="image_search_btn"):
                    with st.spinner("Google Lens로 검색 중..."):
                        try:
                            from src.analyzers.market_researcher import MarketResearcher
                            researcher = MarketResearcher()
                            result = researcher.research_by_image(image_url, max_results=10)

                            if result.competitors:
                                st.session_state.image_search_result = {
                                    "query": result.query,
                                    "competitor_count": len(result.competitors),
                                    "min_price": result.price_range[0],
                                    "max_price": result.price_range[1],
                                    "avg_price": result.average_price,
                                    "recommended_price": result.recommended_price,
                                    "price_strategy": result.price_strategy,
                                    "competitors": result.competitors,
                                }
                                st.success(f"✅ {len(result.competitors)}개 유사 상품 발견!")
                            else:
                                st.warning("유사 상품을 찾지 못했습니다.")
                        except Exception as e:
                            st.error(f"검색 오류: {e}")

        sales_count = st.number_input(
            "판매량",
            min_value=0,
            value=100,
            key="manual_sales"
        )
        shop_rating = st.number_input(
            "판매자 평점",
            min_value=0.0,
            max_value=5.0,
            value=4.8,
            step=0.1,
            key="manual_rating"
        )

    # ========== 이미지 파일 업로드 ==========
    st.markdown("---")
    st.markdown("**📷 이미지 업로드** (선택)")

    uploaded_images = st.file_uploader(
        "상품 이미지 (최대 5장)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="manual_images",
        help="1688/알리익스프레스에서 저장한 상품 이미지"
    )

    if uploaded_images:
        img_cols = st.columns(min(len(uploaded_images), 5))
        for i, img in enumerate(uploaded_images[:5]):
            try:
                img_cols[i].image(img, use_container_width=True)
            except Exception:
                img_cols[i].warning("로드 실패")

    # 데이터 반환
    if source_url or chinese_name or uploaded_images:
        return {
            "source_url": source_url,
            "platform": platform,
            "chinese_name": chinese_name,
            "factory_name": factory_name,
            "image_url": image_url,
            "sales_count": sales_count,
            "shop_rating": shop_rating,
            "uploaded_images": uploaded_images,
        }
    return None
