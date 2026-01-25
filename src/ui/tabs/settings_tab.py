"""
settings_tab.py - 설정 탭 (v4.1)

Gemini CTO 승인 사항:
- 환율 (CNY)
- 관세율 / 부가세율
- 배대지 요금 (기본/kg당)
- 목표 마진율
- 나이트 크롤러 키워드 관리

모든 탭이 이 설정을 참조하므로 Foundation으로 먼저 구현
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Any

from src.core.config import AppConfig, MARKET_FEES
from src.crawler.repository import CandidateRepository
from src.crawler.keyword_manager import KeywordManager


def render() -> Dict[str, Any]:
    """설정 탭 렌더링

    Returns:
        Dict: 현재 설정값들 (다른 탭에서 사용)
    """
    st.header("⚙️ 설정")
    st.markdown("소싱 분석에 사용되는 설정값들을 관리합니다.")

    # 서브탭 구성
    sub_tab1, sub_tab2, sub_tab3 = st.tabs([
        "💱 비용 설정", "📋 키워드 관리", "📊 시스템 설정"
    ])

    with sub_tab1:
        settings = _render_cost_settings()

    with sub_tab2:
        _render_keyword_management()

    with sub_tab3:
        _render_system_settings()

    return settings


def _render_cost_settings() -> Dict[str, Any]:
    """비용 설정 (환율, 배대지, 마진 기준)"""
    st.subheader("비용 설정")
    st.caption("이 설정은 모든 마진 계산에 적용됩니다.")

    # 기본 설정값 로드 (세션 스테이트)
    if "settings" not in st.session_state:
        st.session_state.settings = {
            "exchange_rate": 195.0,
            "shipping_rate_air": 8000,
            "shipping_rate_sea": 3000,
            "domestic_shipping": 3500,
            "return_allowance_rate": 0.05,
            "ad_cost_rate": 0.10,
            "target_margin": 0.35,
            "market": "naver",
        }

    settings = st.session_state.settings

    # ========== 환율 섹션 ==========
    st.markdown("### 💱 환율")
    col1, col2 = st.columns(2)

    with col1:
        settings["exchange_rate"] = st.number_input(
            "환율 (원/위안)",
            min_value=100.0,
            max_value=300.0,
            value=float(settings["exchange_rate"]),
            step=1.0,
            help="CNY → KRW 환율. 약간 보수적으로 설정하세요."
        )

    with col2:
        st.metric(
            "예시: 100위안",
            f"₩{int(100 * settings['exchange_rate']):,}원"
        )

    st.divider()

    # ========== 배대지 비용 ==========
    st.markdown("### 📦 배대지 비용")
    col1, col2, col3 = st.columns(3)

    with col1:
        settings["shipping_rate_air"] = st.number_input(
            "항공 배대지 (원/kg)",
            min_value=1000,
            max_value=20000,
            value=int(settings["shipping_rate_air"]),
            step=500,
            help="항공 배송 kg당 요금"
        )

    with col2:
        settings["shipping_rate_sea"] = st.number_input(
            "해운 배대지 (원/kg)",
            min_value=1000,
            max_value=10000,
            value=int(settings["shipping_rate_sea"]),
            step=500,
            help="해운 배송 kg당 요금"
        )

    with col3:
        settings["domestic_shipping"] = st.number_input(
            "국내 택배비 (원)",
            min_value=1000,
            max_value=10000,
            value=int(settings["domestic_shipping"]),
            step=500,
            help="국내 배송비"
        )

    st.divider()

    # ========== 관세/부가세 ==========
    st.markdown("### 🏛️ 관세 및 수수료")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**카테고리별 관세율**")
        tariff_info = """
        | 카테고리 | 관세율 |
        |---------|--------|
        | 가구/인테리어 | 8% |
        | 캠핑/레저 | 8% |
        | 의류/패션 | 13% |
        | 전자기기 | 8% |
        | 생활용품 | 8% |
        | 기타 | 10% |
        """
        st.markdown(tariff_info)

    with col2:
        st.markdown("**마켓별 수수료**")
        market_options = {
            "네이버 스마트스토어 (5.5%)": "naver",
            "쿠팡 (10.8%)": "coupang",
            "아마존 (15%)": "amazon",
        }
        selected_market_name = st.selectbox(
            "판매 마켓",
            options=list(market_options.keys()),
            index=0 if settings["market"] == "naver" else
                  1 if settings["market"] == "coupang" else 2
        )
        settings["market"] = market_options[selected_market_name]

        market_config = MARKET_FEES[settings["market"]]
        st.info(f"수수료: {market_config.fee_rate * 100:.1f}%")

    st.divider()

    # ========== 숨겨진 비용 ==========
    st.markdown("### 💸 숨겨진 비용")
    col1, col2, col3 = st.columns(3)

    with col1:
        settings["return_allowance_rate"] = st.slider(
            "반품/CS 충당금 (%)",
            min_value=0.0,
            max_value=15.0,
            value=float(settings["return_allowance_rate"] * 100),
            step=0.5,
            help="반품, 교환, CS 비용 대비용"
        ) / 100

    with col2:
        settings["ad_cost_rate"] = st.slider(
            "광고비 (%)",
            min_value=0.0,
            max_value=30.0,
            value=float(settings["ad_cost_rate"] * 100),
            step=1.0,
            help="네이버 쇼핑 광고비 등"
        ) / 100

    with col3:
        settings["target_margin"] = st.slider(
            "목표 마진율 (%)",
            min_value=15.0,
            max_value=60.0,
            value=float(settings["target_margin"] * 100),
            step=5.0,
            help="최소 목표 마진율"
        ) / 100

    # 설정 적용 버튼
    st.divider()
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 설정 저장", type="primary"):
            st.session_state.settings = settings
            st.success("설정이 저장되었습니다!")

    # 현재 설정 요약
    with st.expander("📋 현재 설정 요약"):
        st.json({
            "환율": f"{settings['exchange_rate']}원/위안",
            "항공배대지": f"{settings['shipping_rate_air']}원/kg",
            "해운배대지": f"{settings['shipping_rate_sea']}원/kg",
            "국내택배": f"{settings['domestic_shipping']}원",
            "반품충당금": f"{settings['return_allowance_rate'] * 100:.1f}%",
            "광고비": f"{settings['ad_cost_rate'] * 100:.1f}%",
            "목표마진": f"{settings['target_margin'] * 100:.0f}%",
            "판매마켓": settings['market'],
        })

    return settings


def _render_keyword_management():
    """키워드 관리 (Night Crawler용)"""
    st.subheader("소싱 키워드 관리")
    st.caption("Night Crawler가 이 키워드로 1688에서 상품을 자동 검색합니다.")

    # 저장소 초기화
    repo = CandidateRepository()
    km = KeywordManager(repo)

    # ========== 판다랭크 엑셀 업로드 ==========
    st.markdown("### 📥 판다랭크/아이템스카우트 엑셀 가져오기")
    st.caption("외부 툴에서 다운받은 키워드 엑셀을 업로드하면 Night Crawler 큐에 자동 추가됩니다.")

    uploaded_file = st.file_uploader(
        "키워드 엑셀 파일 업로드",
        type=["xlsx", "xls"],
        help="판다랭크, 아이템스카우트 등에서 다운로드한 키워드 엑셀",
        key="keyword_excel_upload"
    )

    if uploaded_file:
        try:
            from src.importers.pandarank_importer import PandarankImporter, add_keywords_to_crawler

            importer = PandarankImporter()
            keywords, stats = importer.import_from_bytes(
                uploaded_file.read(),
                uploaded_file.name
            )

            st.success(f"✅ {stats['total']}개 키워드 감지됨!")

            col1, col2, col3 = st.columns(3)
            col1.metric("총 키워드", f"{stats['total']}개")
            col2.metric("평균 검색량", f"{stats['avg_search_volume']:,}")
            col3.metric("고우선순위", f"{stats['high_priority_count']}개")

            # 미리보기
            with st.expander("상위 10개 키워드 미리보기"):
                for kw in sorted(keywords, key=lambda x: x.priority, reverse=True)[:10]:
                    st.write(f"[{kw.priority}] **{kw.keyword}** (검색량: {kw.search_volume:,})")

            if st.button("🚀 Night Crawler 큐에 추가", type="primary"):
                added = add_keywords_to_crawler(keywords, km)
                st.success(f"✅ {added}개 키워드가 Night Crawler 큐에 추가되었습니다!")
                st.balloons()
                st.rerun()

        except Exception as e:
            st.error(f"엑셀 파싱 오류: {e}")

    st.divider()

    # ========== 키워드 추가 폼 ==========
    with st.form("add_keyword_form"):
        st.markdown("**새 키워드 추가**")
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            new_keyword = st.text_input("키워드", placeholder="데스크 정리함")

        with col2:
            new_category = st.selectbox("카테고리", [
                "홈인테리어", "사무용품", "생활용품", "자동차", "기타"
            ])

        with col3:
            new_priority = st.number_input("우선순위", min_value=1, max_value=10, value=5)

        if st.form_submit_button("➕ 추가"):
            if new_keyword:
                km.add_keyword(new_keyword, new_category, new_priority)
                st.success(f"'{new_keyword}' 추가됨!")
                st.rerun()
            else:
                st.error("키워드를 입력해주세요.")

    st.divider()

    # ========== 기본 키워드 시드 ==========
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📌 기본 키워드 추가 (홈인테리어/수납)"):
            keywords = km.seed_default_keywords()
            st.success(f"{len(keywords)}개 키워드 추가됨!")
            st.rerun()

    with col2:
        if st.button("🗑️ 모든 키워드 삭제", type="secondary"):
            # 모든 키워드 삭제
            all_keywords = km.repository.get_keywords(active_only=False)
            for kw in all_keywords:
                km.repository.delete_keyword(kw.id)
            st.warning("모든 키워드 삭제됨!")
            st.rerun()

    st.divider()

    # ========== 현재 키워드 목록 ==========
    st.markdown("**현재 키워드 목록**")
    keywords = km.repository.get_keywords(active_only=False)

    if not keywords:
        st.info("등록된 키워드가 없습니다. 판다랭크 엑셀을 업로드하거나 수동으로 추가하세요.")
        return

    # 통계
    active_count = len([k for k in keywords if k.is_active])
    st.caption(f"총 {len(keywords)}개 (활성: {active_count}개)")

    for kw in keywords:
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

        with col1:
            status = "🟢" if kw.is_active else "⚪"
            st.write(f"{status} **{kw.keyword}** ({kw.category})")

        with col2:
            st.write(f"우선순위: {kw.priority}")

        with col3:
            if kw.last_crawled_at:
                time_diff = datetime.now() - kw.last_crawled_at
                if time_diff < timedelta(hours=1):
                    st.write("방금 전")
                elif time_diff < timedelta(hours=24):
                    st.write(f"{time_diff.seconds // 3600}시간 전")
                else:
                    st.write(f"{time_diff.days}일 전")
            else:
                st.write("미크롤링")

        with col4:
            if kw.is_active:
                if st.button("비활성화", key=f"deactivate_{kw.id}"):
                    km.deactivate_keyword(kw.id)
                    st.rerun()
            else:
                if st.button("활성화", key=f"activate_{kw.id}"):
                    km.activate_keyword(kw.id)
                    st.rerun()


def _render_system_settings():
    """시스템 설정 (데이터 관리 등)"""
    st.subheader("시스템 설정")

    repo = CandidateRepository()
    stats = repo.get_stats()

    # ========== 데이터 현황 ==========
    st.markdown("### 📊 데이터 현황")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("전체 후보", f"{stats['total']}개")
    col2.metric("대기 중", f"{stats['pending']}개")
    col3.metric("승인됨", f"{stats['approved']}개")
    col4.metric("등록 완료", f"{stats['uploaded']}개")

    st.divider()

    # ========== 데이터 관리 ==========
    st.markdown("### 🗄️ 데이터 관리")
    st.warning("아래 작업은 되돌릴 수 없습니다. 신중히 사용하세요.")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📝 샘플 데이터 생성"):
            _generate_sample_candidates(repo)
            st.success("샘플 데이터 생성 완료!")
            st.rerun()

    with col2:
        if st.button("🗑️ 대기 중 데이터만 삭제"):
            # 대기 중 데이터만 삭제
            from src.domain.crawler_models import CandidateStatus
            pending = repo.get_candidates(status=CandidateStatus.PENDING)
            for c in pending:
                repo.reject_candidate(c.id, "수동 삭제")
            st.warning(f"{len(pending)}개 데이터 삭제됨!")
            st.rerun()

    with col3:
        if st.button("⚠️ 모든 데이터 삭제", type="secondary"):
            repo.clear_all()
            st.warning("모든 데이터 삭제됨!")
            st.rerun()

    st.divider()

    # ========== Night Crawler 설정 ==========
    st.markdown("### 🌙 Night Crawler 설정")

    if "crawler_mock_mode" not in st.session_state:
        st.session_state.crawler_mock_mode = True

    mock_mode = st.checkbox(
        "Mock 모드 (테스트용)",
        value=st.session_state.crawler_mock_mode,
        help="실제 1688 크롤링 대신 목업 데이터 사용"
    )
    st.session_state.crawler_mock_mode = mock_mode

    if not mock_mode:
        st.info("실제 모드에서는 Apify API 토큰이 필요합니다. (유료 구독 $30/월)")

    # Apify 상태 확인
    import os
    apify_token = os.getenv("APIFY_API_TOKEN", "")
    if apify_token:
        st.success(f"✅ Apify API 토큰 설정됨: {apify_token[:20]}...")
    else:
        st.warning("⚠️ Apify API 토큰이 설정되지 않았습니다. .env 파일에 APIFY_API_TOKEN을 추가하세요.")


def _generate_sample_candidates(repo: CandidateRepository):
    """샘플 후보 데이터 생성 (테스트용)"""
    from src.domain.crawler_models import SourcingCandidate, CrawlRiskLevel
    import random

    sample_data = [
        {
            "title_kr": "미니멀 데스크 정리함 3단 서랍형",
            "source_title": "桌面收纳盒三层抽屉式",
            "price_cny": 35.0,
            "margin_rate": 0.42,
            "recommended_price": 24900,
            "naver_min": 19800,
            "naver_avg": 28500,
            "keyword": "데스크 정리함",
        },
        {
            "title_kr": "모니터 받침대 USB 허브 내장형",
            "source_title": "显示器支架带USB集线器",
            "price_cny": 68.0,
            "margin_rate": 0.38,
            "recommended_price": 32900,
            "naver_min": 25000,
            "naver_avg": 35000,
            "keyword": "모니터 받침대",
            "risk": CrawlRiskLevel.WARNING,
            "risk_reasons": ["KC인증 필요 가능성: 전자"],
        },
        {
            "title_kr": "틈새 수납장 슬림형 4단",
            "source_title": "缝隙收纳柜超窄四层",
            "price_cny": 42.0,
            "margin_rate": 0.45,
            "recommended_price": 29900,
            "naver_min": 22000,
            "naver_avg": 32000,
            "keyword": "틈새 수납장",
        },
        {
            "title_kr": "케이블 정리함 대용량",
            "source_title": "电线收纳盒大容量",
            "price_cny": 28.0,
            "margin_rate": 0.48,
            "recommended_price": 18900,
            "naver_min": 12000,
            "naver_avg": 19000,
            "keyword": "케이블 정리함",
        },
        {
            "title_kr": "화장품 정리함 회전식",
            "source_title": "化妆品收纳架旋转式",
            "price_cny": 55.0,
            "margin_rate": 0.35,
            "recommended_price": 34900,
            "naver_min": 28000,
            "naver_avg": 38000,
            "keyword": "화장품 정리함",
        },
    ]

    for data in sample_data:
        candidate = SourcingCandidate(
            source_url=f"https://detail.1688.com/offer/{random.randint(100000, 999999)}.html",
            source_title=data["source_title"],
            source_price_cny=data["price_cny"],
            source_images=[
                f"https://cbu01.alicdn.com/img/sample_{random.randint(1, 100)}.jpg"
            ],
            source_shop_name=f"优质工厂{random.randint(1, 10)}",
            source_shop_rating=round(random.uniform(4.5, 5.0), 1),
            source_sales_count=random.randint(100, 5000),
            title_kr=data["title_kr"],
            estimated_cost_krw=int(data["price_cny"] * 195 * 1.5),
            estimated_margin_rate=data["margin_rate"],
            recommended_price=data["recommended_price"],
            breakeven_price=int(data["recommended_price"] * 0.7),
            risk_level=data.get("risk", CrawlRiskLevel.SAFE),
            risk_reasons=data.get("risk_reasons", []),
            naver_min_price=data["naver_min"],
            naver_avg_price=data["naver_avg"],
            naver_max_price=int(data["naver_avg"] * 1.5),
            competitor_count=random.randint(5, 20),
            keyword=data["keyword"],
        )
        repo.add_candidate(candidate)


def get_current_settings() -> Dict[str, Any]:
    """현재 설정값 반환 (다른 탭에서 호출용)"""
    if "settings" not in st.session_state:
        st.session_state.settings = {
            "exchange_rate": 195.0,
            "shipping_rate_air": 8000,
            "shipping_rate_sea": 3000,
            "domestic_shipping": 3500,
            "return_allowance_rate": 0.05,
            "ad_cost_rate": 0.10,
            "target_margin": 0.35,
            "market": "naver",
        }
    return st.session_state.settings


def get_app_config() -> AppConfig:
    """설정값을 AppConfig로 변환 (다른 탭에서 호출용)"""
    settings = get_current_settings()
    return AppConfig(
        exchange_rate=settings["exchange_rate"],
        exchange_rate_usd=settings.get("exchange_rate_usd", 1400),  # v4.4
        exchange_rate_usd_cny=settings.get("exchange_rate_usd_cny", 7.2),  # v4.4
        shipping_rate_air=settings["shipping_rate_air"],
        shipping_rate_sea=settings["shipping_rate_sea"],
        domestic_shipping=settings["domestic_shipping"],
        return_allowance_rate=settings["return_allowance_rate"],
        ad_cost_rate=settings["ad_cost_rate"],
    )
