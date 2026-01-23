"""
content_generator.py - 상세페이지 콘텐츠 생성기 (v4.0)

PAS 프레임워크 적용:
- Problem: 고객이 겪는 문제/불편함
- Agitation: 그 문제를 방치하면 어떻게 되는지
- Solution: 이 상품이 어떻게 해결해주는지

Gemini CTO 승인: "나중에 적용하되, 구조는 미리 만들어 두세요"
"""

import os
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass

from src.domain.crawler_models import SourcingCandidate, DetailPageContent


@dataclass
class ContentGeneratorConfig:
    """콘텐츠 생성기 설정"""
    use_ai: bool = True                 # AI 생성 사용 여부
    ai_model: str = "gemini-1.5-flash"  # 사용할 AI 모델
    language: str = "ko"                # 출력 언어


class ContentGenerator:
    """상세페이지 콘텐츠 생성기"""

    # PAS 프레임워크 시스템 프롬프트
    SYSTEM_PROMPT = """당신은 네이버 스마트스토어 판매 1위 상세페이지 기획자입니다.

[PAS 프레임워크]
- Problem: 고객이 겪는 문제/불편함을 짚어주세요
- Agitation: 그 문제를 방치하면 어떻게 되는지 경각심을 주세요
- Solution: 이 상품이 어떻게 해결해주는지 설명하세요

[작성 규칙]
1. 해요체 사용
2. 짧은 문장 (모바일 가독성)
3. 구체적인 숫자 사용
4. 네이버 금지어 회피 (최고, 1위, 100%, 완벽 등)
5. 과장/허위 표현 금지

[출력 형식]
반드시 아래 JSON 형식으로만 출력하세요. 마크다운이나 설명 없이 순수 JSON만 출력하세요.

{
    "title": "상품 제목 (50자 이내)",
    "headline": "후킹 헤드라인 (30자 이내)",
    "problem": "고객의 문제점 설명 (100자 이내)",
    "agitation": "문제 방치 시 결과 (100자 이내)",
    "solution": "상품의 해결책 (150자 이내)",
    "features": ["특징1", "특징2", "특징3"],
    "specs": {"규격": "값", "소재": "값"},
    "faq": [{"q": "질문", "a": "답변"}],
    "seo_keywords": ["키워드1", "키워드2"]
}
"""

    def __init__(self, config: ContentGeneratorConfig = None):
        self.config = config or ContentGeneratorConfig()
        self._gemini_client = None

    def _get_gemini_client(self):
        """Gemini 클라이언트 가져오기 (지연 로딩)"""
        if self._gemini_client is None:
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    self._gemini_client = genai.GenerativeModel(self.config.ai_model)
                except ImportError:
                    print("[ContentGenerator] google-generativeai 패키지 없음")
                    self._gemini_client = None
            else:
                print("[ContentGenerator] GOOGLE_API_KEY 없음")
                self._gemini_client = None
        return self._gemini_client

    async def generate(self, candidate: SourcingCandidate) -> DetailPageContent:
        """상세페이지 콘텐츠 생성

        Args:
            candidate: 소싱 후보 상품

        Returns:
            DetailPageContent: 생성된 콘텐츠
        """
        if self.config.use_ai:
            return await self._generate_with_ai(candidate)
        else:
            return self._generate_template(candidate)

    async def _generate_with_ai(self, candidate: SourcingCandidate) -> DetailPageContent:
        """AI로 콘텐츠 생성

        Args:
            candidate: 소싱 후보 상품

        Returns:
            DetailPageContent: AI 생성 콘텐츠
        """
        client = self._get_gemini_client()

        if not client:
            print("[ContentGenerator] AI 사용 불가, 템플릿 사용")
            return self._generate_template(candidate)

        try:
            user_prompt = f"""
상품명: {candidate.title_kr}
원본 제목: {candidate.source_title}
카테고리: {candidate.keyword}
추천 판매가: {candidate.recommended_price:,}원
경쟁사 평균가: {candidate.naver_avg_price:,}원
예상 마진율: {candidate.estimated_margin_rate:.0%}

위 정보를 바탕으로 상세페이지 콘텐츠를 PAS 프레임워크로 작성해주세요.
"""

            response = client.generate_content(
                self.SYSTEM_PROMPT + "\n\n" + user_prompt
            )

            # JSON 파싱
            response_text = response.text.strip()

            # JSON 블록 추출 (```json ... ``` 형식 처리)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            data = json.loads(response_text)

            return DetailPageContent(
                title=data.get("title", candidate.title_kr),
                headline=data.get("headline", ""),
                problem=data.get("problem", ""),
                agitation=data.get("agitation", ""),
                solution=data.get("solution", ""),
                features=data.get("features", []),
                specs=data.get("specs", {}),
                faq=data.get("faq", []),
                seo_keywords=data.get("seo_keywords", []),
            )

        except json.JSONDecodeError as e:
            print(f"[ContentGenerator] JSON 파싱 실패: {e}")
            return self._generate_template(candidate)
        except Exception as e:
            print(f"[ContentGenerator] AI 생성 실패: {e}")
            return self._generate_template(candidate)

    def _generate_template(self, candidate: SourcingCandidate) -> DetailPageContent:
        """템플릿 기반 콘텐츠 생성 (AI 없을 때)

        Args:
            candidate: 소싱 후보 상품

        Returns:
            DetailPageContent: 템플릿 기반 콘텐츠
        """
        # 키워드 기반 PAS 템플릿
        keyword = candidate.keyword
        title = candidate.title_kr

        # 카테고리별 템플릿
        templates = {
            "데스크 정리함": {
                "problem": "책상 위가 항상 어지럽고 필요한 물건을 찾기 힘드셨죠?",
                "agitation": "어지러운 책상은 집중력을 떨어뜨리고 업무 효율을 낮춥니다.",
                "solution": f"{title}으로 깔끔한 책상 환경을 만들어보세요. 수납력과 디자인을 모두 갖췄어요.",
            },
            "모니터 받침대": {
                "problem": "오랜 컴퓨터 작업으로 목과 어깨가 뻐근하셨죠?",
                "agitation": "잘못된 모니터 높이는 거북목과 만성 통증을 유발해요.",
                "solution": f"{title}으로 눈높이에 맞는 모니터 배치가 가능해요. 편안한 자세로 일해보세요.",
            },
            "틈새 수납장": {
                "problem": "좁은 공간에 수납할 곳이 부족해 답답하셨죠?",
                "agitation": "물건이 쌓이면 공간은 더 좁아 보이고 정리가 힘들어져요.",
                "solution": f"{title}은 자투리 공간을 알뜰하게 활용해요. 깔끔한 정리가 가능해요.",
            },
            "케이블 정리함": {
                "problem": "엉킨 케이블 때문에 책상이 지저분해 보이셨죠?",
                "agitation": "케이블 정리 안 하면 먼지가 쌓이고 합선 위험도 있어요.",
                "solution": f"{title}으로 케이블을 깔끔하게 정리해보세요. 안전하고 보기 좋아요.",
            },
            "화장품 정리함": {
                "problem": "화장품이 여기저기 흩어져서 찾기 힘드셨죠?",
                "agitation": "정리 안 된 화장대는 아침 준비 시간을 늘리고 스트레스를 줘요.",
                "solution": f"{title}으로 화장품을 한눈에 정리해보세요. 아침이 달라져요.",
            },
        }

        # 기본 템플릿
        default_template = {
            "problem": f"{keyword} 정리가 어려우셨죠?",
            "agitation": "정리가 안 되면 필요할 때 찾기 힘들고 스트레스받아요.",
            "solution": f"{title}으로 깔끔하게 정리해보세요. 일상이 편리해져요.",
        }

        template = templates.get(keyword, default_template)

        return DetailPageContent(
            title=title,
            headline=f"{keyword}, 이제 쉽게 정리하세요",
            problem=template["problem"],
            agitation=template["agitation"],
            solution=template["solution"],
            features=[
                "실용적인 디자인",
                "튼튼한 소재",
                "간편한 조립",
            ],
            specs={
                "소재": "고급 ABS 플라스틱",
                "사이즈": "상세 이미지 참조",
                "원산지": "중국 (국내 검수)",
            },
            faq=[
                {"q": "배송은 얼마나 걸리나요?", "a": "결제 후 2-3일 내 출고되며, 배송은 1-2일 소요돼요."},
                {"q": "AS는 가능한가요?", "a": "제품 수령 후 7일 이내 교환/반품 가능해요."},
            ],
            seo_keywords=[keyword, title.split()[0], "정리", "수납"],
        )

    def generate_sync(self, candidate: SourcingCandidate) -> DetailPageContent:
        """동기 버전 생성 (Streamlit용)

        Args:
            candidate: 소싱 후보 상품

        Returns:
            DetailPageContent: 생성된 콘텐츠
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 이미 이벤트 루프가 실행 중이면 새 스레드에서 실행
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.generate(candidate))
                    return future.result()
            else:
                return loop.run_until_complete(self.generate(candidate))
        except RuntimeError:
            return asyncio.run(self.generate(candidate))
