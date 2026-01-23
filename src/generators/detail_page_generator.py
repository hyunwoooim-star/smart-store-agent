"""
detail_page_generator.py - 상세페이지 자동 생성 (Phase 10)

Gemini CTO 권장: "콘텐츠 생성이 병목. 상세페이지 초안 생성 기능 최우선"

사용법:
    generator = DetailPageGenerator(api_key="...")
    result = generator.generate(
        product_name="초경량 캠핑의자",
        specs={"무게": "2.5kg", "재질": "알루미늄"},
        target_audience="캠핑 초보자",
        key_benefits=["가벼움", "튼튼함", "휴대성"]
    )
    print(result.headline)
    print(result.body_sections)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import json
import os
import re


@dataclass
class DetailPageResult:
    """상세페이지 생성 결과"""
    headline: str                          # 대표 헤드라인
    sub_headlines: List[str]               # 서브 헤드라인 3-5개
    body_sections: List[Dict[str, str]]    # 본문 섹션 [{title, content}]
    bullet_points: List[str]               # 핵심 포인트 (불릿)
    seo_keywords: List[str]                # SEO 키워드
    call_to_action: str                    # CTA 문구
    cautions: List[str]                    # 주의사항/면책 문구
    raw_response: str = ""                 # 원본 응답 (디버깅용)


@dataclass
class ProductInput:
    """상품 정보 입력"""
    name: str                              # 상품명
    category: str = "기타"                 # 카테고리
    specs: Dict[str, str] = field(default_factory=dict)  # 스펙 (무게, 사이즈 등)
    target_audience: str = ""              # 타겟 고객
    key_benefits: List[str] = field(default_factory=list)  # 핵심 장점
    competitor_weaknesses: List[str] = field(default_factory=list)  # 경쟁사 약점
    price_positioning: str = "중간가"      # 가격 포지셔닝


class DetailPageGenerator:
    """Gemini 기반 상세페이지 생성기"""

    SYSTEM_PROMPT = """당신은 10년 차 스마트스토어 MD이자 카피라이터입니다.
상품 스펙을 받으면, 네이버 스마트스토어에 등록할 상세페이지 텍스트를 작성합니다.

[작성 원칙]
1. 고객의 "문제 해결" 관점으로 작성 (기능 나열 X)
2. 구체적인 숫자/스펙 활용 (막연한 표현 X)
3. 네이버 금지어 회피 (최고, 1위, 암 예방, 100% 효과 등 금지)
4. 모바일 가독성 고려 (짧은 문장, 줄바꿈)

[출력 형식]
반드시 아래 JSON 형식으로만 출력하세요. 마크다운/설명 금지.

{
    "headline": "대표 헤드라인 (1문장)",
    "sub_headlines": ["서브1", "서브2", "서브3"],
    "body_sections": [
        {"title": "섹션 제목", "content": "본문 내용 (2-3문장)"}
    ],
    "bullet_points": ["핵심 포인트1", "핵심 포인트2", "핵심 포인트3"],
    "seo_keywords": ["키워드1", "키워드2"],
    "call_to_action": "CTA 문구",
    "cautions": ["주의사항1"]
}
"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Google API 키 (없으면 환경변수에서 로드)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self._model = None

    def _get_model(self):
        """Gemini 모델 초기화 (lazy loading)"""
        if self._model is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel("gemini-1.5-flash")
        return self._model

    def generate(self, product: ProductInput) -> DetailPageResult:
        """상세페이지 생성

        Args:
            product: 상품 정보

        Returns:
            DetailPageResult: 생성된 상세페이지 콘텐츠
        """
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")

        prompt = self._build_prompt(product)
        model = self._get_model()

        response = model.generate_content(
            [self.SYSTEM_PROMPT, prompt],
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 2000,
            }
        )

        return self._parse_response(response.text)

    def generate_from_dict(
        self,
        product_name: str,
        specs: Dict[str, str] = None,
        target_audience: str = "",
        key_benefits: List[str] = None,
        category: str = "기타"
    ) -> DetailPageResult:
        """딕셔너리 인터페이스로 생성 (편의 메서드)"""
        product = ProductInput(
            name=product_name,
            category=category,
            specs=specs or {},
            target_audience=target_audience,
            key_benefits=key_benefits or []
        )
        return self.generate(product)

    def _build_prompt(self, product: ProductInput) -> str:
        """프롬프트 생성"""
        specs_text = "\n".join([f"- {k}: {v}" for k, v in product.specs.items()])
        benefits_text = ", ".join(product.key_benefits) if product.key_benefits else "미정"
        weaknesses_text = ", ".join(product.competitor_weaknesses) if product.competitor_weaknesses else "없음"

        return f"""
[상품 정보]
- 상품명: {product.name}
- 카테고리: {product.category}
- 가격대: {product.price_positioning}
- 타겟 고객: {product.target_audience or "일반 소비자"}

[스펙]
{specs_text or "- 스펙 정보 없음"}

[핵심 장점]
{benefits_text}

[경쟁사 약점 (차별화 포인트)]
{weaknesses_text}

위 정보를 바탕으로 네이버 스마트스토어 상세페이지 텍스트를 JSON 형식으로 작성해주세요.
"""

    def _parse_response(self, response_text: str) -> DetailPageResult:
        """응답 파싱"""
        # JSON 추출 (코드 블록 제거)
        clean_text = response_text.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r"```(?:json)?\n?", "", clean_text)
            clean_text = clean_text.strip()

        try:
            data = json.loads(clean_text)
            return DetailPageResult(
                headline=data.get("headline", ""),
                sub_headlines=data.get("sub_headlines", []),
                body_sections=data.get("body_sections", []),
                bullet_points=data.get("bullet_points", []),
                seo_keywords=data.get("seo_keywords", []),
                call_to_action=data.get("call_to_action", ""),
                cautions=data.get("cautions", []),
                raw_response=response_text
            )
        except json.JSONDecodeError:
            # 파싱 실패 시 원본 텍스트로 반환
            return DetailPageResult(
                headline="[파싱 실패] 원본 응답 확인 필요",
                sub_headlines=[],
                body_sections=[{"title": "원본 응답", "content": response_text}],
                bullet_points=[],
                seo_keywords=[],
                call_to_action="",
                cautions=[],
                raw_response=response_text
            )

    def format_for_naver(self, result: DetailPageResult) -> str:
        """네이버 스마트스토어 형식으로 포맷팅 (복사-붙여넣기용)"""
        lines = []

        # 헤드라인
        lines.append(f"# {result.headline}")
        lines.append("")

        # 서브 헤드라인
        for sub in result.sub_headlines:
            lines.append(f"## {sub}")
        lines.append("")

        # 본문 섹션
        for section in result.body_sections:
            lines.append(f"### {section.get('title', '')}")
            lines.append(section.get('content', ''))
            lines.append("")

        # 핵심 포인트
        if result.bullet_points:
            lines.append("### 핵심 포인트")
            for point in result.bullet_points:
                lines.append(f"✓ {point}")
            lines.append("")

        # CTA
        if result.call_to_action:
            lines.append(f"**{result.call_to_action}**")
            lines.append("")

        # 주의사항
        if result.cautions:
            lines.append("---")
            lines.append("※ 주의사항")
            for caution in result.cautions:
                lines.append(f"- {caution}")

        return "\n".join(lines)


class MockDetailPageGenerator:
    """테스트용 Mock 생성기"""

    def generate(self, product: ProductInput) -> DetailPageResult:
        return DetailPageResult(
            headline=f"{product.name} - 당신의 아웃도어를 업그레이드하세요",
            sub_headlines=[
                "가벼움의 새로운 기준",
                "튼튼함과 휴대성의 완벽한 조화",
                "캠핑 초보자도 쉽게 사용"
            ],
            body_sections=[
                {
                    "title": "왜 이 제품인가요?",
                    "content": "캠핑장에서 무거운 의자 때문에 고생하셨나요? "
                               f"이 {product.name}은(는) 단 2.5kg의 무게로 어디든 쉽게 들고 다닐 수 있습니다."
                },
                {
                    "title": "실사용 후기",
                    "content": "100명의 캠핑 초보자가 선택한 이유, 직접 확인해보세요."
                }
            ],
            bullet_points=[
                "무게 2.5kg - 한 손으로 들 수 있는 가벼움",
                "알루미늄 프레임 - 150kg 하중 지지",
                "전용 파우치 포함 - 깔끔한 수납"
            ],
            seo_keywords=["캠핑의자", "경량 캠핑의자", "접이식 의자", "야외 의자"],
            call_to_action="지금 주문하시면 내일 도착! 🚀",
            cautions=[
                "이미지와 실제 색상이 다소 다를 수 있습니다.",
                "150kg 이상 하중은 권장하지 않습니다."
            ]
        )

    def generate_from_dict(self, **kwargs) -> DetailPageResult:
        product = ProductInput(
            name=kwargs.get("product_name", "테스트 상품"),
            specs=kwargs.get("specs", {}),
            target_audience=kwargs.get("target_audience", ""),
            key_benefits=kwargs.get("key_benefits", [])
        )
        return self.generate(product)


# 편의 함수
def create_generator(use_mock: bool = False) -> DetailPageGenerator:
    """생성기 팩토리"""
    if use_mock:
        return MockDetailPageGenerator()
    return DetailPageGenerator()


# CLI 테스트
if __name__ == "__main__":
    # Mock 테스트
    generator = create_generator(use_mock=True)
    product = ProductInput(
        name="초경량 캠핑의자",
        category="캠핑/레저",
        specs={"무게": "2.5kg", "재질": "알루미늄", "최대 하중": "150kg"},
        target_audience="캠핑 초보자",
        key_benefits=["가벼움", "튼튼함", "휴대성"]
    )

    result = generator.generate(product)
    print("=== 상세페이지 생성 결과 ===")
    print(f"헤드라인: {result.headline}")
    print(f"서브: {result.sub_headlines}")
    print(f"핵심 포인트: {result.bullet_points}")
    print(f"CTA: {result.call_to_action}")
