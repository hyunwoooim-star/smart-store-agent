"""
morning_tab.py - 모닝 브리핑 탭 (v4.2)

틴더 스타일 UI로 소싱 후보 승인/반려
Gemini CTO 승인: "아침 5분 검토 시스템"

v4.2 UI Enhancement:
- Toss 스타일 카드 + Naver 그린 컬러
- 개선된 태그/배지 디자인
- Plotly 도넛 차트 (상태별 분포)
"""

import streamlit as st
from typing import Optional

from src.crawler.repository import CandidateRepository
from src.domain.crawler_models import SourcingCandidate, CandidateStatus, CrawlRiskLevel
from src.ui.styles import COLORS, SHADOWS, RADIUS


def render():
    """모닝 브리핑 탭 렌더링 (v4.1 - 키워드 관리는 설정 탭으로 이동)"""
    st.header("모닝 브리핑")
    st.markdown("밤새 AI가 찾아온 상품 후보들입니다. 승인/반려를 결정해주세요.")
    st.caption("💡 키워드 관리는 **설정 탭**에서 하세요.")

    # 저장소 초기화
    repo = CandidateRepository()

    # 탭 내부 구성 (v4.1 - 키워드 관리는 설정 탭으로 이동)
    sub_tab1, sub_tab2, sub_tab3 = st.tabs([
        "대기 중", "승인됨", "통계"
    ])

    with sub_tab1:
        _render_pending_tab(repo)

    with sub_tab2:
        _render_approved_tab(repo)

    with sub_tab3:
        _render_stats_tab(repo)


def _render_pending_tab(repo: CandidateRepository):
    """대기 중 후보 목록"""
    st.subheader("검토 대기 중")

    # 통계 표시
    stats = repo.get_stats()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("대기 중", f"{stats['pending']}개")
    col2.metric("승인됨", f"{stats['approved']}개")
    col3.metric("등록 완료", f"{stats['uploaded']}개")
    col4.metric("평균 마진율", f"{stats['avg_margin']:.1f}%")

    st.divider()

    # 대기 중인 후보 목록
    candidates = repo.get_pending_candidates()

    if not candidates:
        st.info("검토할 상품이 없습니다. 푹 쉬세요!")

        # 샘플 데이터 생성 버튼
        if st.button("샘플 데이터 생성 (테스트용)"):
            _generate_sample_candidates(repo)
            st.rerun()
        return

    # 일괄 처리 버튼
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        if st.button("마진 35%+ 전체 승인"):
            approved_count = 0
            for c in candidates:
                if c.estimated_margin_rate >= 0.35:
                    repo.approve_candidate(c.id)
                    approved_count += 1
            st.success(f"{approved_count}개 승인됨!")
            st.rerun()

    with col2:
        if st.button("위험 상품 전체 반려"):
            rejected_count = 0
            for c in candidates:
                if c.risk_level == CrawlRiskLevel.DANGER:
                    repo.reject_candidate(c.id, "위험 상품")
                    rejected_count += 1
            st.warning(f"{rejected_count}개 반려됨!")
            st.rerun()

    with col3:
        if st.button("📋 검토용 엑셀 다운로드"):
            try:
                from src.publisher.naver_excel_exporter import NaverExcelExporter
                exporter = NaverExcelExporter()
                file_path = exporter.export_for_review()
                if file_path:
                    with open(file_path, "rb") as f:
                        st.download_button(
                            label="💾 저장",
                            data=f.read(),
                            file_name=file_path.split("/")[-1].split("\\")[-1],
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_review_excel"
                        )
                    st.success("검토용 엑셀 생성 완료!")
            except Exception as e:
                st.error(f"오류: {e}")

    st.divider()

    # 후보 카드 목록
    for candidate in candidates:
        _render_candidate_card(candidate, repo, "pending")


def _render_approved_tab(repo: CandidateRepository):
    """승인된 후보 목록"""
    st.subheader("승인된 상품")

    candidates = repo.get_approved_candidates()

    if not candidates:
        st.info("승인된 상품이 없습니다.")
        return

    st.info(f"총 {len(candidates)}개 상품이 등록 대기 중입니다.")

    # 엑셀 다운로드 & 등록 버튼
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📥 네이버 대량등록용 엑셀 다운로드", type="primary"):
            try:
                from src.publisher.naver_excel_exporter import NaverExcelExporter

                exporter = NaverExcelExporter()
                file_path = exporter.export_approved()

                if file_path:
                    # 파일 읽어서 다운로드 제공
                    with open(file_path, "rb") as f:
                        st.download_button(
                            label="💾 엑셀 파일 저장",
                            data=f.read(),
                            file_name=file_path.split("/")[-1].split("\\")[-1],
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_excel"
                        )
                    st.success(f"✅ 엑셀 파일 생성 완료: {len(candidates)}개 상품")
                else:
                    st.warning("추출할 상품이 없습니다.")
            except Exception as e:
                st.error(f"엑셀 생성 오류: {e}")

    with col2:
        if st.button("🚀 네이버 자동 등록 (API 연동 후 활성화)", disabled=True):
            st.warning("네이버 커머스 API 연동 후 사용 가능합니다.")

    st.divider()

    for candidate in candidates:
        _render_candidate_card(candidate, repo, "approved")


def _render_candidate_card(
    candidate: SourcingCandidate,
    repo: CandidateRepository,
    mode: str = "pending"
):
    """상품 카드 렌더링 (v4.2 Toss 스타일)

    Args:
        candidate: 소싱 후보
        repo: 저장소
        mode: pending/approved
    """
    # 마진율에 따른 카드 테두리 색상
    if candidate.estimated_margin_rate >= 0.40:
        border_color = COLORS["success"]
    elif candidate.estimated_margin_rate >= 0.35:
        border_color = COLORS["primary"]
    elif candidate.estimated_margin_rate >= 0.25:
        border_color = COLORS["warning"]
    else:
        border_color = COLORS["danger"]

    # Toss 스타일 카드 컨테이너
    st.markdown(f"""
    <div style="
        background: {COLORS['card_bg']};
        border-radius: {RADIUS['md']};
        border-left: 4px solid {border_color};
        padding: 4px 0;
        margin: 8px 0;
        box-shadow: {SHADOWS['md']};
    "></div>
    """, unsafe_allow_html=True)

    with st.container():
        col1, col2 = st.columns([1, 3])

        with col1:
            # 이미지
            if candidate.source_images:
                st.image(candidate.source_images[0], width=150)
            else:
                st.image("https://via.placeholder.com/150x150?text=No+Image", width=150)

        with col2:
            # 제목
            st.subheader(candidate.title_kr)
            st.caption(f"원본: {candidate.source_title[:50]}...")

            # 추천 사유 태그 (Gemini CTO 피드백 반영)
            tags = []
            if candidate.estimated_margin_rate >= 0.40:
                tags.append("마진 우수")
            elif candidate.estimated_margin_rate >= 0.35:
                tags.append("마진 양호")
            if candidate.competitor_count <= 10:
                tags.append("경쟁 낮음")
            if candidate.risk_level == CrawlRiskLevel.SAFE:
                tags.append("리스크 없음")
            if candidate.source_sales_count >= 1000:
                tags.append("검증된 상품")

            if tags:
                tag_html = " ".join([
                    f'<span style="background:{COLORS["primary_light"]};color:{COLORS["primary_dark"]};padding:4px 10px;border-radius:12px;font-size:12px;margin-right:6px;font-weight:500;">{tag}</span>'
                    for tag in tags
                ])
                st.markdown(tag_html, unsafe_allow_html=True)

            # 핵심 지표
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("예상 마진", f"{candidate.estimated_margin_rate:.0%}")
            m2.metric("추천 판매가", f"{candidate.recommended_price:,}원")
            m3.metric("원가 (CNY)", f"¥{candidate.source_price_cny:.0f}")
            m4.metric("경쟁사", f"{candidate.competitor_count}개")

            # 네이버 시장가
            st.caption(
                f"네이버: 최저 {candidate.naver_min_price:,}원 | "
                f"평균 {candidate.naver_avg_price:,}원 | "
                f"손익분기 {candidate.breakeven_price:,}원"
            )

            # 리스크 표시
            if candidate.risk_level == CrawlRiskLevel.DANGER:
                st.error(f"위험: {', '.join(candidate.risk_reasons)}")
            elif candidate.risk_level == CrawlRiskLevel.WARNING:
                st.warning(f"주의: {', '.join(candidate.risk_reasons)}")
            else:
                st.success("리스크 없음")

            # 버튼
            btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

            if mode == "pending":
                with btn_col1:
                    if st.button("승인", key=f"approve_{candidate.id}", type="primary"):
                        repo.approve_candidate(candidate.id)
                        st.success("승인됨!")
                        st.rerun()

                with btn_col2:
                    if st.button("반려", key=f"reject_{candidate.id}"):
                        repo.reject_candidate(candidate.id, "수동 반려")
                        st.warning("반려됨!")
                        st.rerun()

            elif mode == "approved":
                with btn_col1:
                    if st.button("등록 취소", key=f"cancel_{candidate.id}"):
                        repo.reject_candidate(candidate.id, "승인 취소")
                        st.warning("승인 취소됨!")
                        st.rerun()

            with btn_col3:
                if st.button("1688에서 보기", key=f"view_{candidate.id}"):
                    st.markdown(f"[원본 링크]({candidate.source_url})")

            with btn_col4:
                # 상세 정보 expander
                pass

        # 상세 정보 (접이식)
        with st.expander("상세 정보"):
            detail_col1, detail_col2 = st.columns(2)
            with detail_col1:
                st.write("**소싱 정보**")
                st.write(f"- 키워드: {candidate.keyword}")
                st.write(f"- 샵명: {candidate.source_shop_name}")
                st.write(f"- 샵 평점: {candidate.source_shop_rating}")
                st.write(f"- 판매량: {candidate.source_sales_count:,}개")

            with detail_col2:
                st.write("**비용 정보**")
                st.write(f"- 예상 총원가: {candidate.estimated_cost_krw:,}원")
                st.write(f"- 손익분기 판매가: {candidate.breakeven_price:,}원")
                st.write(f"- 추천 판매가: {candidate.recommended_price:,}원")
                st.write(f"- 예상 마진율: {candidate.estimated_margin_rate:.1%}")

        st.divider()


def _render_stats_tab(repo: CandidateRepository):
    """통계 대시보드 (v4.2 Plotly)"""
    st.subheader("소싱 통계")

    stats = repo.get_stats()

    # 전체 통계
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("전체 후보", f"{stats['total']}개")
    col2.metric("활성 키워드", f"{stats['keywords']}개")
    col3.metric("등록 완료", f"{stats['uploaded']}개")
    col4.metric("반려됨", f"{stats['rejected']}개")

    st.divider()

    # 상태별 분포 (Plotly 도넛 차트)
    st.write("**상태별 분포**")

    try:
        import plotly.graph_objects as go

        labels = ["대기 중", "승인됨", "등록 완료", "반려됨"]
        values = [stats['pending'], stats['approved'], stats['uploaded'], stats['rejected']]

        # 값이 모두 0인지 확인
        if sum(values) > 0:
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.5,
                marker=dict(colors=[
                    COLORS['warning'],   # 대기 중 - 노랑
                    COLORS['primary'],   # 승인됨 - 그린
                    COLORS['chart_3'],   # 등록 완료 - 연그린
                    COLORS['danger'],    # 반려됨 - 빨강
                ]),
                textinfo="label+value",
                textfont=dict(size=12, family="Pretendard"),
                hovertemplate="<b>%{label}</b><br>%{value}개<br>%{percent}<extra></extra>",
            )])

            # 중앙에 총 개수 표시
            fig.add_annotation(
                text=f"<b>{stats['total']}</b><br><span style='font-size:11px'>전체</span>",
                x=0.5, y=0.5,
                font=dict(size=18, family="Pretendard", color=COLORS['text_main']),
                showarrow=False,
            )

            fig.update_layout(
                height=300,
                margin=dict(t=20, b=20, l=20, r=20),
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.15,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=11),
                ),
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("데이터가 없습니다.")

    except ImportError:
        # Plotly 없을 경우 기본 차트
        status_data = {
            "대기 중": stats['pending'],
            "승인됨": stats['approved'],
            "등록 완료": stats['uploaded'],
            "반려됨": stats['rejected'],
        }
        st.bar_chart(status_data)

    st.divider()

    # 최근 활동
    st.write("**데이터 관리**")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("샘플 데이터 생성"):
            _generate_sample_candidates(repo)
            st.success("샘플 데이터 생성 완료!")
            st.rerun()

    with col2:
        if st.button("모든 데이터 삭제", type="secondary"):
            repo.clear_all()
            st.warning("모든 데이터 삭제됨!")
            st.rerun()


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
