"""
리뷰 분석 탭 (Nice to have)
"""
import streamlit as st
import os


def render():
    """리뷰 분석 탭 렌더링"""
    st.header("📝 경쟁사 리뷰 분석")
    st.markdown("리뷰를 분석하여 **결함**, **개선점**, **마케팅 포인트**를 도출합니다.")

    # API 키 상태
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        st.warning("⚠️ GOOGLE_API_KEY가 설정되지 않았습니다.")
        return

    st.success("✅ Gemini API 연결됨")

    # 카테고리 선택
    review_category = st.selectbox(
        "📦 상품 카테고리",
        options=["의류", "가구", "전자기기", "주방용품", "캠핑/레저", "화장품", "기타"],
        index=0
    )

    # 리뷰 입력
    reviews_text = st.text_area(
        "리뷰 텍스트 (줄바꿈으로 구분)",
        height=200,
        placeholder="""좋아요! 색감이 사진이랑 똑같아요.
근데 세탁하니까 좀 줄었어요...
실밥이 튀어나와 있어서 아쉬워요.""",
        key="review_text"
    )

    use_mock = st.checkbox("🧪 테스트 모드 (Mock)", value=False)

    if st.button("🔍 리뷰 분석", type="primary", key="review_btn"):
        if not reviews_text and not use_mock:
            st.error("리뷰 텍스트를 입력하세요.")
        else:
            with st.spinner("🧠 Gemini 분석 중..."):
                try:
                    from src.analyzers.review_analyzer import ReviewAnalyzer, MockReviewAnalyzer, Verdict

                    if use_mock:
                        analyzer = MockReviewAnalyzer()
                    else:
                        analyzer = ReviewAnalyzer(api_key=google_api_key)

                    result = analyzer.analyze_sync(reviews_text or "테스트 리뷰", category=review_category)

                    # 판정 결과
                    st.markdown("---")
                    if result.verdict == Verdict.GO:
                        st.success("🟢 **Go** - 소싱 진행 권장")
                    elif result.verdict == Verdict.HOLD:
                        st.warning("🟡 **Hold** - 샘플 확인 후 결정")
                    else:
                        st.error("🔴 **Drop** - 소싱 포기 권장")

                    # 요약
                    if result.summary_one_line:
                        st.info(f"📝 {result.summary_one_line}")

                    # 3단 컬럼
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.subheader("🚨 결함")
                        for d in result.critical_defects:
                            st.markdown(f"- [{d.frequency}] {d.issue}")

                    with col2:
                        st.subheader("🔧 개선 요청")
                        for item in result.improvement_requests:
                            st.markdown(f"- {item}")

                    with col3:
                        st.subheader("💡 마케팅 포인트")
                        for item in result.marketing_hooks:
                            st.markdown(f"- {item}")

                except ImportError as e:
                    st.error(f"패키지 오류: {e}")
                    st.code("pip install pydantic google-generativeai")
                except Exception as e:
                    if "quota" in str(e).lower() or "429" in str(e):
                        st.error("💡 API 쿼터 초과! 잠시 후 다시 시도하세요.")
                    else:
                        st.error(f"❌ 분석 실패: {e}")
