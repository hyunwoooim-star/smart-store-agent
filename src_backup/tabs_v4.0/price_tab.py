"""
가격 추적 탭 (운영 단계용 - 현재는 Nice to have)
"""
import streamlit as st
from src.monitors.price_tracker import (
    PriceTracker, AlertLevel, MarketPlatform,
    ExposureTier, PricingStrategyType
)
from src.monitors.scheduler import (
    PriceMonitorScheduler, SchedulerStatus, create_scheduler
)


def render():
    """가격 추적 탭 렌더링"""
    st.header("📈 경쟁사 가격 추적")

    # Gemini CTO 권장: 현재는 우선순위 낮음
    st.info("💡 **참고**: 이 기능은 상품 등록 후 '운영 단계'에서 사용하세요. 지금은 마진 분석과 Pre-Flight에 집중!")

    # 세션 초기화
    if "price_tracker" not in st.session_state:
        st.session_state.price_tracker = PriceTracker()
    if "scheduler" not in st.session_state:
        st.session_state.scheduler = create_scheduler(st.session_state.price_tracker, use_mock=True)

    tracker = st.session_state.price_tracker
    scheduler = st.session_state.scheduler
    scheduler.tracker = tracker

    # 서브탭
    price_tab1, price_tab2, price_tab3 = st.tabs([
        "➕ 상품 등록",
        "📊 경쟁 분석",
        "⚙️ 자동 모니터링"
    ])

    with price_tab1:
        _render_register(tracker)

    with price_tab2:
        _render_analysis(tracker)

    with price_tab3:
        _render_scheduler(scheduler)


def _render_register(tracker: PriceTracker):
    """상품 등록"""
    st.subheader("경쟁사 상품 등록")

    col1, col2 = st.columns(2)

    with col1:
        comp_name = st.text_input("상품명", key="comp_name")
        comp_url = st.text_input("URL", key="comp_url")
        comp_price = st.number_input("가격 (원)", min_value=0, value=30000, key="comp_price")

    with col2:
        my_price = st.number_input("내 상품 가격", min_value=0, value=32000, key="my_price_input")
        comp_tags = st.text_input("태그 (쉼표 구분)", key="comp_tags")

    if st.button("➕ 등록", type="primary", key="add_comp_btn"):
        if comp_name and comp_price > 0:
            tags = [t.strip() for t in comp_tags.split(",") if t.strip()] if comp_tags else []
            product = tracker.add_product(
                name=comp_name,
                url=comp_url or "manual",
                current_price=comp_price,
                my_price=my_price if my_price > 0 else None,
                tags=tags
            )
            st.success(f"✅ 등록: {product.name}")
        else:
            st.error("상품명과 가격을 입력하세요.")

    # 목록
    st.markdown("---")
    st.subheader(f"📋 등록된 상품 ({len(tracker.products)}개)")
    for pid, p in tracker.products.items():
        st.write(f"- {p.name}: {p.current_price:,}원")


def _render_analysis(tracker: PriceTracker):
    """경쟁 분석"""
    st.subheader("📊 경쟁력 분석")

    if not tracker.products:
        st.warning("먼저 경쟁사 상품을 등록하세요.")
        return

    my_price = st.number_input("내 상품 가격", min_value=1000, value=35000, key="analysis_price")

    if st.button("🔍 분석", type="primary", key="analyze_btn"):
        analysis = tracker.get_competitive_analysis(my_price)

        # Tier 표시
        tier = analysis.get("exposure_tier", "tier3")
        tier_msg = analysis.get("tier_message", "")

        if tier == "tier1":
            st.success(f"🟢 {tier_msg}")
        elif tier == "tier2":
            st.warning(f"🟡 {tier_msg}")
        else:
            st.error(f"🔴 {tier_msg}")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("경쟁사 수", f"{analysis['total_competitors']}개")
        with col2:
            st.metric("최저가", f"{analysis.get('min_price', 0):,}원")
        with col3:
            st.metric("평균가", f"{analysis['avg_competitor_price']:,}원")


def _render_scheduler(scheduler: PriceMonitorScheduler):
    """스케줄러 제어"""
    st.subheader("⚙️ 자동 모니터링")

    status = scheduler.get_status()
    current_status = status["status"]

    # 상태 표시
    status_text = {"running": "🟢 실행 중", "paused": "🟡 일시정지", "stopped": "🔴 중지됨"}
    st.write(f"**상태**: {status_text.get(current_status, '알 수 없음')}")
    st.write(f"**상품 수**: {status['products_count']}개")

    # 제어 버튼
    col1, col2, col3 = st.columns(3)

    with col1:
        if current_status == "stopped":
            if st.button("▶️ 시작", key="start_scheduler"):
                scheduler.start(interval_hours=6, run_immediately=True)
                st.rerun()
        else:
            if st.button("⏹️ 중지", key="stop_scheduler"):
                scheduler.stop()
                st.rerun()

    with col2:
        if st.button("🔄 즉시 실행", key="run_now"):
            result = scheduler.run_now()
            st.success(f"✅ {result.products_checked}개 체크, {result.alerts_generated}개 알림")

    # 최근 결과
    results = scheduler.get_recent_results(limit=5)
    if results:
        st.markdown("---")
        st.subheader("최근 실행")
        for r in reversed(results):
            st.write(f"- {r.timestamp[:16]}: {r.products_checked}개 체크, {r.alerts_generated}개 알림")
