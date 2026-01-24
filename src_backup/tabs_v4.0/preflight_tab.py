"""
Pre-Flight Check 탭 (MVP 필수)
"""
import streamlit as st
from src.analyzers.preflight_check import PreFlightChecker


def render():
    """Pre-Flight Check 탭 렌더링"""
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
                st.success("✅ 검사 통과! 등록 가능합니다.")
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
        - **의료기기 오인**: 치료, 교정, 통증 완화

        ### 🟡 주의 필요 (MEDIUM)
        - **최상급 표현**: 최고, 최초, 1위, 완벽, 기적

        ### 💡 안전한 대안
        - "최고의" → "프리미엄", "고품질"
        - "암 예방" → "건강한 생활 도움"
        - "통증 완화" → "편안한 사용감"
        """)
