"""
원클릭 소싱 분석 탭 (Phase 10.5)

Gemini CTO: "킬러 피처. 무조건 GO"

기능:
1. 1688 스크린샷 업로드 → 상품 정보 추출 (Claude Vision)
2. 이미지로 경쟁사 검색 (Google Lens)
3. 시장가 자동 조회 + 목표가 추천
4. 마진 분석까지 원클릭 완료
"""
import streamlit as st
from typing import Optional, Dict
import base64
import io


def render():
    """원클릭 소싱 탭 렌더링"""
    st.header("원클릭 소싱 분석")
    st.markdown("""
    **1688 스크린샷 한 장으로 모든 분석 완료!**
    - 상품 정보 자동 추출
    - 경쟁사 가격 자동 조회
    - 목표가 추천
    - 마진 분석
    """)

    # API 키 상태 표시
    _render_api_status()

    st.markdown("---")

    # 방법 선택
    method = st.radio(
        "분석 방법 선택",
        options=["텍스트 검색", "이미지 업로드"],
        horizontal=True,
        help="텍스트 검색: 키워드로 시장 조사 | 이미지 업로드: 1688 스크린샷으로 상품+시장 동시 분석"
    )

    if method == "텍스트 검색":
        _render_text_search()
    else:
        _render_image_upload()


def _render_api_status():
    """API 키 상태 표시"""
    import os

    col1, col2 = st.columns(2)

    with col1:
        naver_ok = os.getenv("NAVER_CLIENT_ID") and os.getenv("NAVER_CLIENT_SECRET")
        if naver_ok:
            st.success("네이버 API: 연결됨")
        else:
            st.warning("네이버 API: 미설정 (Mock 모드)")
            with st.expander("네이버 API 설정 방법"):
                st.markdown("""
                1. [네이버 개발자센터](https://developers.naver.com) 접속
                2. 애플리케이션 등록 → 쇼핑 검색 API 추가
                3. `.env` 파일에 추가:
                ```
                NAVER_CLIENT_ID=your_client_id
                NAVER_CLIENT_SECRET=your_client_secret
                ```
                """)

    with col2:
        serpapi_ok = os.getenv("SERPAPI_KEY")
        if serpapi_ok:
            st.success("SerpApi: 연결됨")
        else:
            st.warning("SerpApi: 미설정 (Mock 모드)")
            with st.expander("SerpApi 설정 방법"):
                st.markdown("""
                1. [SerpApi](https://serpapi.com) 가입 (무료 100회/월)
                2. API 키 발급
                3. `.env` 파일에 추가:
                ```
                SERPAPI_KEY=your_serpapi_key
                ```
                """)


def _render_text_search():
    """텍스트 키워드 검색"""
    st.subheader("키워드로 시장 조사")

    keyword = st.text_input(
        "검색 키워드",
        value="",
        placeholder="예: 캠핑의자, 유아 승용완구",
        help="네이버 쇼핑에서 경쟁 상품을 검색합니다"
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        max_results = st.slider("최대 검색 결과", 5, 20, 10)
    with col2:
        st.write("")  # 간격 맞추기

    if st.button("시장 조사", type="primary", use_container_width=True, disabled=not keyword):
        with st.spinner("시장 조사 중..."):
            _run_market_research(keyword, max_results)


def _render_image_upload():
    """이미지 업로드로 분석"""
    st.subheader("1688 스크린샷 분석")

    st.info("""
    **사용법:**
    1. 1688에서 관심 상품 페이지 스크린샷 촬영
    2. 아래에 이미지 업로드
    3. AI가 자동으로 상품 정보 추출 + 경쟁사 분석
    """)

    uploaded_file = st.file_uploader(
        "1688 스크린샷 업로드",
        type=["png", "jpg", "jpeg"],
        help="상품 정보가 잘 보이는 스크린샷을 올려주세요"
    )

    # 또는 이미지 URL 입력
    image_url = st.text_input(
        "또는 이미지 URL 입력",
        placeholder="https://example.com/product.jpg",
        help="직접 이미지 URL을 입력할 수도 있습니다"
    )

    if uploaded_file:
        # 이미지 미리보기
        st.image(uploaded_file, caption="업로드된 이미지", use_container_width=True)

        if st.button("분석 시작", type="primary", use_container_width=True):
            with st.spinner("이미지 분석 중..."):
                # 이미지를 base64로 변환 (나중에 Claude Vision 연동용)
                image_bytes = uploaded_file.read()
                image_base64 = base64.b64encode(image_bytes).decode()

                # 현재는 Mock 모드로 시장 조사만 실행
                st.warning("이미지에서 상품 정보 추출 기능은 Claude Vision 연동 후 활성화됩니다.")
                st.info("현재는 아래에서 수동으로 키워드를 입력해 시장 조사를 진행해주세요.")

                # 키워드 입력 받기
                keyword = st.text_input("상품 키워드 (이미지에서 읽은 상품명)", key="image_keyword")
                if keyword and st.button("시장 조사 실행", key="run_research_btn"):
                    _run_market_research(keyword, 10)

    elif image_url:
        # URL로 이미지 표시
        st.image(image_url, caption="입력된 이미지 URL", use_container_width=True)

        if st.button("이미지로 시장 조사", type="primary", use_container_width=True):
            with st.spinner("Google Lens로 유사 상품 검색 중..."):
                _run_image_research(image_url)


def _run_market_research(keyword: str, max_results: int = 10):
    """시장 조사 실행"""
    try:
        from src.analyzers.market_researcher import MarketResearcher

        researcher = MarketResearcher()
        result = researcher.research_by_text(keyword, max_results)

        # 결과를 session_state에 저장
        st.session_state.market_research_result = result

        _render_research_result(result)

    except Exception as e:
        st.error(f"시장 조사 오류: {e}")


def _run_image_research(image_url: str, max_results: int = 10):
    """이미지로 시장 조사"""
    try:
        from src.analyzers.market_researcher import MarketResearcher

        researcher = MarketResearcher()
        result = researcher.research_by_image(image_url, max_results)

        # 결과를 session_state에 저장
        st.session_state.market_research_result = result

        _render_research_result(result)

    except Exception as e:
        st.error(f"이미지 시장 조사 오류: {e}")


def _render_research_result(result):
    """시장 조사 결과 표시"""
    from src.analyzers.market_researcher import MarketResearchResult

    st.markdown("---")
    st.header("시장 조사 결과")

    # 핵심 지표
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("경쟁사 수", f"{len(result.competitors)}개")
    with col2:
        st.metric("최저가", f"{result.price_range[0]:,}원")
    with col3:
        st.metric("평균가", f"{result.average_price:,}원")
    with col4:
        st.metric("추천 목표가", f"{result.recommended_price:,}원", delta=f"-{100-int(result.recommended_price/result.average_price*100)}%")

    # 가격 전략 설명
    st.markdown("---")
    st.subheader("가격 전략")
    st.code(result.price_strategy, language=None)

    # 경쟁사 목록
    st.markdown("---")
    st.subheader("경쟁사 상품 목록")

    if result.competitors:
        for idx, comp in enumerate(result.competitors, 1):
            with st.expander(f"{idx}. {comp.title[:50]}... | {comp.price:,}원", expanded=(idx <= 3)):
                col_info, col_link = st.columns([3, 1])

                with col_info:
                    st.write(f"**가격:** {comp.price:,}원")
                    st.write(f"**출처:** {comp.source}")
                    if comp.review_count:
                        st.write(f"**리뷰:** {comp.review_count}개 | 평점: {comp.rating}")

                with col_link:
                    if comp.url:
                        st.link_button("상품 보기", comp.url)
    else:
        st.warning("경쟁사 상품을 찾지 못했습니다.")

    # 마진 분석으로 연결
    st.markdown("---")
    st.subheader("마진 분석으로 이동")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**추천 목표가:** {result.recommended_price:,}원")
    with col2:
        if st.button("이 목표가로 마진 분석", type="primary"):
            # 마진 분석 탭으로 값 전달
            st.session_state.suggested_target_price = result.recommended_price
            st.session_state.suggested_keyword = result.query
            st.success("마진 분석 탭으로 이동해주세요!")
    with col3:
        custom_price = st.number_input(
            "직접 목표가 설정",
            min_value=1000,
            max_value=10000000,
            value=result.recommended_price,
            step=1000,
            key="custom_target"
        )
        if st.button("직접 설정한 목표가로 분석"):
            st.session_state.suggested_target_price = custom_price
            st.session_state.suggested_keyword = result.query
            st.success("마진 분석 탭으로 이동해주세요!")
