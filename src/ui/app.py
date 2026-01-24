"""
app.py - Streamlit 대시보드 (v4.2.0)

v4.2 UI/UX Enhancement:
- Toss UX + Naver Brand Color 하이브리드
- Plotly 차트 (마진 게이지, 비용 도넛)
- Pretendard 폰트 적용
- 커스텀 컴포넌트 (판정카드, 상품카드)

실행: streamlit run src/ui/app.py
"""

import streamlit as st
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# .env 파일 로딩 (환경변수)
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# 스타일 모듈 (v4.2)
from src.ui.styles import inject_custom_css

# 탭 모듈 임포트 (v4.1 - 4탭 구조)
from src.ui.tabs import morning_tab, sourcing_tab, review_tab, settings_tab

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="Smart Store Agent",
    page_icon="🛡️",
    layout="wide"
)

st.title("Smart Store Agent")
st.markdown("**v4.2.0** | AI 기반 스마트스토어 자동화")

# 커스텀 CSS 주입 (Toss + Naver 스타일)
inject_custom_css()

# ============================================================
# 사이드바: 빠른 설정 (축소)
# ============================================================
with st.sidebar:
    st.markdown("### 🛡️ Smart Store Agent")
    st.caption("v4.2 - Toss + Naver 스타일")

    st.divider()

    # 현재 설정 요약
    from src.ui.tabs.settings_tab import get_current_settings
    settings = get_current_settings()

    st.markdown("**📊 현재 설정**")
    st.write(f"환율: {settings['exchange_rate']}원/위안")
    st.write(f"목표 마진: {settings['target_margin'] * 100:.0f}%")
    st.write(f"마켓: {settings['market']}")

    st.divider()

    # 빠른 링크
    st.markdown("**🔗 빠른 링크**")
    st.markdown("[네이버 쇼핑](https://shopping.naver.com)")
    st.markdown("[1688](https://1688.com)")
    st.markdown("[판다랭크](https://pandarank.net)")

    st.divider()

    # 도움말
    with st.expander("❓ 도움말"):
        st.markdown("""
        **탭 설명:**
        - **모닝 브리핑**: 밤새 AI가 찾은 상품 검토
        - **소싱 분석**: 상품 마진 분석 (통합)
        - **리뷰 분석**: AI 리뷰 분석
        - **설정**: 환율, 키워드 관리

        **워크플로우:**
        1. 판다랭크에서 키워드 다운로드
        2. 설정 탭에서 키워드 업로드
        3. Night Crawler 실행 (CLI)
        4. 모닝 브리핑에서 승인/반려
        5. 엑셀 다운로드 → 네이버 등록
        """)

# ============================================================
# 탭 구성 (4개 탭) - v4.1 UI 통합
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🌅 모닝 브리핑",
    "🔍 소싱 분석",
    "💬 리뷰 분석",
    "⚙️ 설정"
])

# ============================================================
# TAB 1: 모닝 브리핑 (Night Crawler 결과)
# ============================================================
with tab1:
    morning_tab.render()

# ============================================================
# TAB 2: 소싱 분석 (시장조사 + 마진 + Pre-Flight 통합)
# ============================================================
with tab2:
    sourcing_tab.render()

# ============================================================
# TAB 3: 리뷰 분석
# ============================================================
with tab3:
    review_tab.render()

# ============================================================
# TAB 4: 설정 (환율, 비용, 키워드 관리)
# ============================================================
with tab4:
    settings_tab.render()

# ============================================================
# 푸터
# ============================================================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #8B95A1; font-size: 13px;'>
        Smart Store Agent v4.2.0 | Toss + Naver Style<br>
        "밤새 일하는 AI, 아침에 결재하는 사장님"
    </div>
    """,
    unsafe_allow_html=True
)
