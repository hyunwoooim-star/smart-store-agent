"""
styles.py - UI 스타일 유틸리티 (v4.2)

Gemini CTO 승인:
- Toss UX + Naver Brand Color 하이브리드
- Plotly 차트 (게이지, 도넛)
- Pretendard 폰트 (숫자 가독성)
"""

import streamlit as st


# ============================================================
# 색상 팔레트 (Gemini CTO 제안)
# ============================================================
COLORS = {
    # Primary
    "primary": "#03C75A",        # Naver Green
    "primary_light": "#E8F5E9",  # Light Green
    "primary_dark": "#1B5E20",   # Dark Green

    # Status
    "success": "#4CAF50",
    "warning": "#FFC107",
    "danger": "#F44336",

    # Toss Gray Scale
    "bg_light": "#F5F6F8",       # Background
    "text_main": "#191F28",      # Main Text
    "text_sub": "#8B95A1",       # Sub Text
    "card_bg": "#FFFFFF",        # Card Background
    "border": "#E5E8EB",         # Border

    # Chart Colors (Green Scale)
    "chart_1": "#03C75A",
    "chart_2": "#4CAF50",
    "chart_3": "#81C784",
    "chart_4": "#A5D6A7",
    "chart_5": "#C8E6C9",
}

# 그림자 (Toss 스타일)
SHADOWS = {
    "sm": "0 1px 3px rgba(0, 0, 0, 0.08)",
    "md": "0 4px 20px rgba(0, 0, 0, 0.05)",  # CTO 추천
    "lg": "0 8px 30px rgba(0, 0, 0, 0.08)",
}

# 라운드 코너
RADIUS = {
    "sm": "8px",
    "md": "12px",
    "lg": "16px",
    "xl": "24px",
}


# ============================================================
# 전역 CSS 주입
# ============================================================
def inject_custom_css():
    """앱 시작 시 호출 - 전역 CSS 주입"""
    st.markdown(f"""
    <style>
    /* ========== 폰트 (Pretendard + Noto Sans KR) ========== */
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Pretendard', 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    /* ========== 메트릭 카드 스타일 ========== */
    [data-testid="stMetric"] {{
        background: {COLORS['card_bg']};
        border-radius: {RADIUS['md']};
        padding: 16px 20px;
        box-shadow: {SHADOWS['md']};
        border: 1px solid {COLORS['border']};
    }}

    [data-testid="stMetric"] label {{
        color: {COLORS['text_sub']};
        font-size: 13px;
        font-weight: 500;
    }}

    [data-testid="stMetric"] [data-testid="stMetricValue"] {{
        font-size: 28px;
        font-weight: 700;
        color: {COLORS['text_main']};
    }}

    /* ========== 버튼 스타일 ========== */
    .stButton > button {{
        border-radius: {RADIUS['sm']};
        font-weight: 600;
        transition: all 0.2s ease;
    }}

    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: {SHADOWS['sm']};
    }}

    .stButton > button[kind="primary"] {{
        background-color: {COLORS['primary']};
        border: none;
    }}

    /* ========== 탭 스타일 ========== */
    .stTabs [data-baseweb="tab"] {{
        font-weight: 600;
        color: {COLORS['text_sub']};
    }}

    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        color: {COLORS['primary']};
    }}

    /* ========== Expander 스타일 ========== */
    .streamlit-expanderHeader {{
        font-weight: 600;
        color: {COLORS['text_main']};
        background: {COLORS['card_bg']};
        border-radius: {RADIUS['sm']};
    }}

    /* ========== 모바일 반응형 (morning_tab 카드) ========== */
    @media (max-width: 768px) {{
        [data-testid="stHorizontalBlock"] {{
            flex-direction: column;
        }}

        .product-card {{
            margin: 8px 0;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# 커스텀 컴포넌트
# ============================================================
def render_verdict_card(verdict: str, reason: str, status: str = "go"):
    """Toss 스타일 판정 카드

    Args:
        verdict: 판정 결과 (예: "🟢 GO", "🔴 NO-GO")
        reason: 판정 사유
        status: go / warning / nogo
    """
    status_styles = {
        "go": {
            "bg": f"linear-gradient(135deg, {COLORS['primary_light']} 0%, #FFFFFF 100%)",
            "border": COLORS['success'],
            "text": COLORS['primary_dark'],
        },
        "warning": {
            "bg": f"linear-gradient(135deg, #FFF8E1 0%, #FFFFFF 100%)",
            "border": COLORS['warning'],
            "text": "#F57F17",
        },
        "nogo": {
            "bg": f"linear-gradient(135deg, #FFEBEE 0%, #FFFFFF 100%)",
            "border": COLORS['danger'],
            "text": "#B71C1C",
        },
    }

    style = status_styles.get(status, status_styles["warning"])

    st.markdown(f"""
    <div style="
        background: {style['bg']};
        border-left: 4px solid {style['border']};
        border-radius: {RADIUS['md']};
        padding: 24px;
        margin: 16px 0;
        box-shadow: {SHADOWS['md']};
    ">
        <div style="font-size: 32px; font-weight: 700; color: {style['text']};">
            {verdict}
        </div>
        <div style="font-size: 14px; color: {COLORS['text_sub']}; margin-top: 8px;">
            {reason}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_product_card(
    image_url: str,
    title: str,
    subtitle: str,
    margin_percent: float,
    price: int,
    card_id: str = ""
):
    """Naver 스타일 상품 카드

    Args:
        image_url: 상품 이미지 URL
        title: 상품명
        subtitle: 부제목 (키워드 · 경쟁사 수)
        margin_percent: 마진율 (%)
        price: 추천 판매가
        card_id: 고유 ID (버튼용)
    """
    margin_color = COLORS['primary'] if margin_percent >= 35 else COLORS['danger']

    st.markdown(f"""
    <div class="product-card" style="
        background: {COLORS['card_bg']};
        border-radius: {RADIUS['md']};
        padding: 16px;
        margin: 8px 0;
        box-shadow: {SHADOWS['md']};
        border: 1px solid {COLORS['border']};
        display: flex;
        align-items: center;
        gap: 16px;
    ">
        <img src="{image_url}" style="
            width: 72px;
            height: 72px;
            border-radius: {RADIUS['sm']};
            object-fit: cover;
            flex-shrink: 0;
        " onerror="this.src='https://via.placeholder.com/72x72?text=No+Image'">

        <div style="flex: 1; min-width: 0;">
            <div style="
                font-weight: 600;
                font-size: 15px;
                color: {COLORS['text_main']};
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            ">
                {title}
            </div>
            <div style="
                color: {COLORS['text_sub']};
                font-size: 13px;
                margin-top: 4px;
            ">
                {subtitle}
            </div>
        </div>

        <div style="text-align: right; flex-shrink: 0;">
            <div style="
                font-size: 22px;
                font-weight: 700;
                color: {margin_color};
                font-family: 'Pretendard', sans-serif;
            ">
                {margin_percent:.0f}%
            </div>
            <div style="
                font-size: 13px;
                color: {COLORS['text_sub']};
            ">
                ₩{price:,}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_margin_gauge(margin_percent: float, target: float = 35):
    """마진율 게이지 차트 (Plotly)

    Args:
        margin_percent: 현재 마진율 (%)
        target: 목표 마진율 (%)
    """
    try:
        import plotly.graph_objects as go

        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=margin_percent,
            number={"suffix": "%", "font": {"size": 40, "family": "Pretendard"}},
            delta={"reference": target, "relative": False, "suffix": "%"},
            gauge={
                "axis": {"range": [0, 60], "tickwidth": 1},
                "bar": {"color": COLORS['primary'] if margin_percent >= target else COLORS['danger']},
                "bgcolor": "white",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 15], "color": "#FFEBEE"},
                    {"range": [15, 30], "color": "#FFF8E1"},
                    {"range": [30, 60], "color": COLORS['primary_light']},
                ],
                "threshold": {
                    "line": {"color": COLORS['primary_dark'], "width": 2},
                    "thickness": 0.8,
                    "value": target,
                },
            },
            title={"text": "예상 마진율", "font": {"size": 14, "color": COLORS['text_sub']}},
        ))

        fig.update_layout(
            height=220,
            margin=dict(t=40, b=0, l=30, r=30),
            paper_bgcolor="rgba(0,0,0,0)",
            font={"family": "Pretendard, Noto Sans KR, sans-serif"},
        )

        st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        st.warning("Plotly가 설치되지 않았습니다. `pip install plotly` 실행 필요")
        st.metric("예상 마진율", f"{margin_percent:.1f}%")


def render_cost_donut(breakdown: dict, total_cost: int):
    """비용 분석 도넛 차트 (Plotly)

    Args:
        breakdown: 비용 breakdown dict
        total_cost: 총 비용
    """
    try:
        import plotly.graph_objects as go

        labels = ["상품원가", "관세/부가세", "배송비", "수수료/광고", "기타"]
        values = [
            breakdown.get("product_cost", 0) + breakdown.get("china_shipping", 0),
            breakdown.get("tariff", 0) + breakdown.get("vat", 0),
            breakdown.get("shipping_international", 0) + breakdown.get("shipping_domestic", 0),
            breakdown.get("platform_fee", 0) + breakdown.get("ad_cost", 0),
            breakdown.get("return_allowance", 0) + breakdown.get("packaging", 0) + breakdown.get("agency_fee", 0),
        ]

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.5,
            marker=dict(colors=[
                COLORS['chart_1'],
                COLORS['chart_2'],
                COLORS['chart_3'],
                COLORS['chart_4'],
                COLORS['chart_5'],
            ]),
            textinfo="percent",
            textfont=dict(size=12, family="Pretendard"),
            hovertemplate="<b>%{label}</b><br>₩%{value:,.0f}<br>%{percent}<extra></extra>",
        )])

        # 중앙에 총 비용 표시
        fig.add_annotation(
            text=f"<b>₩{total_cost:,}</b><br><span style='font-size:11px'>총 비용</span>",
            x=0.5, y=0.5,
            font=dict(size=18, family="Pretendard", color=COLORS['text_main']),
            showarrow=False,
        )

        fig.update_layout(
            height=280,
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

    except ImportError:
        st.warning("Plotly가 설치되지 않았습니다.")


def render_stat_card(label: str, value: str, delta: str = None, icon: str = None):
    """통계 카드 (작은 버전)

    Args:
        label: 레이블
        value: 값
        delta: 변화량 (선택)
        icon: 이모지 아이콘 (선택)
    """
    icon_html = f'<span style="font-size: 20px; margin-right: 8px;">{icon}</span>' if icon else ""
    delta_html = f'<span style="color: {COLORS["primary"]}; font-size: 12px;">▲ {delta}</span>' if delta else ""

    st.markdown(f"""
    <div style="
        background: {COLORS['card_bg']};
        border-radius: {RADIUS['md']};
        padding: 16px;
        box-shadow: {SHADOWS['sm']};
        border: 1px solid {COLORS['border']};
        text-align: center;
    ">
        <div style="color: {COLORS['text_sub']}; font-size: 12px; margin-bottom: 4px;">
            {icon_html}{label}
        </div>
        <div style="font-size: 24px; font-weight: 700; color: {COLORS['text_main']};">
            {value}
        </div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)
