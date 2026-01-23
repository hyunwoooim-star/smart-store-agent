"""
test_detail_page_generator.py - 상세페이지 생성기 테스트
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.generators.detail_page_generator import (
    DetailPageGenerator,
    MockDetailPageGenerator,
    DetailPageResult,
    ProductInput,
    create_generator,
)


class TestProductInput:
    """ProductInput 테스트"""

    def test_basic_input(self):
        """기본 입력"""
        product = ProductInput(name="테스트 상품")
        assert product.name == "테스트 상품"
        assert product.category == "기타"
        assert product.specs == {}

    def test_full_input(self):
        """전체 입력"""
        product = ProductInput(
            name="캠핑의자",
            category="캠핑/레저",
            specs={"무게": "2.5kg", "재질": "알루미늄"},
            target_audience="캠핑 초보자",
            key_benefits=["가벼움", "튼튼함"],
            price_positioning="중간가"
        )
        assert product.name == "캠핑의자"
        assert product.specs["무게"] == "2.5kg"
        assert len(product.key_benefits) == 2


class TestDetailPageResult:
    """DetailPageResult 테스트"""

    def test_basic_result(self):
        """기본 결과"""
        result = DetailPageResult(
            headline="테스트 헤드라인",
            sub_headlines=["서브1", "서브2"],
            body_sections=[{"title": "제목", "content": "내용"}],
            bullet_points=["포인트1"],
            seo_keywords=["키워드1"],
            call_to_action="지금 구매",
            cautions=["주의사항"]
        )
        assert result.headline == "테스트 헤드라인"
        assert len(result.sub_headlines) == 2
        assert len(result.body_sections) == 1


class TestMockDetailPageGenerator:
    """Mock 생성기 테스트"""

    def test_generate(self):
        """기본 생성"""
        generator = MockDetailPageGenerator()
        product = ProductInput(
            name="초경량 캠핑의자",
            category="캠핑/레저",
            specs={"무게": "2.5kg"},
            key_benefits=["가벼움"]
        )

        result = generator.generate(product)

        assert isinstance(result, DetailPageResult)
        assert "캠핑의자" in result.headline
        assert len(result.sub_headlines) >= 3
        assert len(result.bullet_points) >= 3
        assert result.call_to_action != ""

    def test_generate_from_dict(self):
        """딕셔너리로 생성"""
        generator = MockDetailPageGenerator()
        result = generator.generate_from_dict(
            product_name="테스트 의자",
            specs={"무게": "3kg"},
            key_benefits=["편안함"]
        )

        assert isinstance(result, DetailPageResult)
        assert result.headline != ""


class TestCreateGenerator:
    """팩토리 함수 테스트"""

    def test_create_mock(self):
        """Mock 모드"""
        generator = create_generator(use_mock=True)
        assert isinstance(generator, MockDetailPageGenerator)

    def test_create_real(self):
        """실제 모드"""
        generator = create_generator(use_mock=False)
        assert isinstance(generator, DetailPageGenerator)


class TestDetailPageGenerator:
    """실제 생성기 테스트 (API 키 필요)"""

    def test_no_api_key(self):
        """API 키 없을 때"""
        import os
        original_key = os.environ.get("GOOGLE_API_KEY")

        try:
            os.environ.pop("GOOGLE_API_KEY", None)
            generator = DetailPageGenerator(api_key=None)

            product = ProductInput(name="테스트")

            with pytest.raises(ValueError) as exc_info:
                generator.generate(product)

            assert "GOOGLE_API_KEY" in str(exc_info.value)

        finally:
            if original_key:
                os.environ["GOOGLE_API_KEY"] = original_key

    def test_build_prompt(self):
        """프롬프트 빌드"""
        generator = DetailPageGenerator(api_key="test")
        product = ProductInput(
            name="캠핑의자",
            category="캠핑/레저",
            specs={"무게": "2.5kg", "재질": "알루미늄"},
            target_audience="초보 캠퍼",
            key_benefits=["가벼움", "튼튼함"]
        )

        prompt = generator._build_prompt(product)

        assert "캠핑의자" in prompt
        assert "캠핑/레저" in prompt
        assert "2.5kg" in prompt
        assert "초보 캠퍼" in prompt
        assert "가벼움" in prompt

    def test_parse_response_valid_json(self):
        """유효한 JSON 파싱"""
        generator = DetailPageGenerator(api_key="test")
        response = '''
        {
            "headline": "테스트 헤드라인",
            "sub_headlines": ["서브1", "서브2"],
            "body_sections": [{"title": "제목", "content": "내용"}],
            "bullet_points": ["포인트1"],
            "seo_keywords": ["키워드1"],
            "call_to_action": "CTA",
            "cautions": ["주의"]
        }
        '''

        result = generator._parse_response(response)

        assert result.headline == "테스트 헤드라인"
        assert len(result.sub_headlines) == 2
        assert result.call_to_action == "CTA"

    def test_parse_response_with_code_block(self):
        """코드 블록 포함 JSON 파싱"""
        generator = DetailPageGenerator(api_key="test")
        response = '''```json
        {
            "headline": "테스트",
            "sub_headlines": [],
            "body_sections": [],
            "bullet_points": [],
            "seo_keywords": [],
            "call_to_action": "",
            "cautions": []
        }
        ```'''

        result = generator._parse_response(response)

        assert result.headline == "테스트"

    def test_parse_response_invalid(self):
        """잘못된 응답 처리"""
        generator = DetailPageGenerator(api_key="test")
        response = "이건 JSON이 아닙니다."

        result = generator._parse_response(response)

        assert "파싱 실패" in result.headline
        assert response in result.raw_response


class TestFormatForNaver:
    """네이버 포맷 테스트"""

    def test_format(self):
        """포맷팅"""
        generator = DetailPageGenerator(api_key="test")
        result = DetailPageResult(
            headline="대표 헤드라인",
            sub_headlines=["서브1", "서브2"],
            body_sections=[{"title": "섹션 제목", "content": "본문 내용"}],
            bullet_points=["포인트1", "포인트2"],
            seo_keywords=["키워드"],
            call_to_action="지금 구매!",
            cautions=["주의사항"]
        )

        formatted = generator.format_for_naver(result)

        assert "# 대표 헤드라인" in formatted
        assert "## 서브1" in formatted
        assert "### 섹션 제목" in formatted
        assert "✓ 포인트1" in formatted
        assert "**지금 구매!**" in formatted
        assert "※ 주의사항" in formatted


# pytest 실행용
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
