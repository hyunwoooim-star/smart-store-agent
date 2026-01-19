"""
keyword_filter.py - 키워드 기반 리뷰 필터링 (v3.1)

핵심 기능:
1. 부정 키워드 기반 리뷰 필터링
2. False positive 패턴 방어
3. 감성 분석 준비 (Gemini 연동용)
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum


class SentimentType(Enum):
    """감성 유형"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class ReviewData:
    """리뷰 데이터"""
    review_id: str
    content: str
    rating: Optional[int] = None        # 1-5 별점
    date: Optional[str] = None
    product_name: Optional[str] = None

    # 분석 결과
    sentiment: Optional[SentimentType] = None
    matched_negative_keywords: List[str] = field(default_factory=list)
    matched_positive_keywords: List[str] = field(default_factory=list)
    is_complaint: bool = False
    complaint_categories: List[str] = field(default_factory=list)


@dataclass
class FilterResult:
    """필터링 결과"""
    total_reviews: int
    complaint_reviews: int
    positive_reviews: int
    neutral_reviews: int

    complaints: List[ReviewData] = field(default_factory=list)
    top_complaint_keywords: Dict[str, int] = field(default_factory=dict)
    complaint_categories: Dict[str, int] = field(default_factory=dict)


class KeywordFilter:
    """키워드 기반 리뷰 필터"""

    # 부정 키워드 (불만 패턴)
    NEGATIVE_KEYWORDS = {
        # 품질 관련
        "품질": ["품질이 별로", "품질 나쁨", "품질 떨어", "저렴한 느낌", "싸구려"],
        "내구성": ["금방 망가", "쉽게 부러", "내구성 약", "오래 못", "며칠 만에"],
        "마감": ["마감 별로", "마감 불량", "뜯어짐", "실밥", "접착 불량"],

        # 배송 관련
        "배송": ["배송 느림", "배송 늦", "배송 지연", "안 와", "분실"],
        "포장": ["포장 엉망", "포장 불량", "찢어져", "박스 훼손"],

        # 상품 설명 불일치
        "설명불일치": ["사진과 다름", "설명과 다름", "색상 다름", "사이즈 다름", "다른 제품"],

        # 사용성
        "불편": ["불편", "사용하기 어려", "복잡", "설명서 없"],
        "소음": ["소음", "시끄러", "삐걱"],
        "냄새": ["냄새", "악취", "화학 냄새"],

        # 가격 관련
        "가격": ["비싸", "가격 대비", "돈 아까", "환불"],

        # 일반 불만
        "실망": ["실망", "후회", "다신 안", "비추", "별로"],
    }

    # False Positive 방어 패턴 (부정 키워드가 있어도 긍정인 경우)
    FALSE_POSITIVE_PATTERNS = [
        r"품질이?\s*(좋|훌륭|최고)",
        r"품질\s*대비\s*(좋|괜찮|만족)",
        r"생각보다\s*(좋|괜찮|만족)",
        r"(좋|괜찮|만족).*품질",
        r"배송\s*(빠름|빨라|좋)",
        r"가격\s*대비\s*(좋|만족|훌륭)",
        r"(안|않|없).*불편",
        r"불편.*없",
    ]

    # 긍정 키워드
    POSITIVE_KEYWORDS = [
        "좋아요", "만족", "추천", "최고", "훌륭", "완벽",
        "가성비", "빠른 배송", "친절", "재구매", "굿",
    ]

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """정규식 패턴 컴파일"""
        self.false_positive_compiled = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.FALSE_POSITIVE_PATTERNS
        ]

    def _is_false_positive(self, text: str) -> bool:
        """False Positive 체크"""
        for pattern in self.false_positive_compiled:
            if pattern.search(text):
                return True
        return False

    def _find_negative_keywords(self, text: str) -> Tuple[List[str], List[str]]:
        """
        부정 키워드 찾기
        Returns: (매칭된 키워드 리스트, 카테고리 리스트)
        """
        matched_keywords = []
        matched_categories = []

        for category, keywords in self.NEGATIVE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    matched_keywords.append(keyword)
                    if category not in matched_categories:
                        matched_categories.append(category)

        return matched_keywords, matched_categories

    def _find_positive_keywords(self, text: str) -> List[str]:
        """긍정 키워드 찾기"""
        return [kw for kw in self.POSITIVE_KEYWORDS if kw in text]

    def analyze_review(self, review: ReviewData) -> ReviewData:
        """
        단일 리뷰 분석

        Args:
            review: 분석할 리뷰

        Returns:
            분석 결과가 추가된 리뷰
        """
        content = review.content

        # False Positive 체크
        if self._is_false_positive(content):
            review.sentiment = SentimentType.POSITIVE
            review.is_complaint = False
            return review

        # 부정 키워드 찾기
        neg_keywords, categories = self._find_negative_keywords(content)
        review.matched_negative_keywords = neg_keywords
        review.complaint_categories = categories

        # 긍정 키워드 찾기
        pos_keywords = self._find_positive_keywords(content)
        review.matched_positive_keywords = pos_keywords

        # 감성 판단
        if len(neg_keywords) > len(pos_keywords):
            review.sentiment = SentimentType.NEGATIVE
            review.is_complaint = True
        elif len(pos_keywords) > len(neg_keywords):
            review.sentiment = SentimentType.POSITIVE
            review.is_complaint = False
        else:
            # 별점 기반 판단 (있는 경우)
            if review.rating:
                if review.rating <= 2:
                    review.sentiment = SentimentType.NEGATIVE
                    review.is_complaint = True
                elif review.rating >= 4:
                    review.sentiment = SentimentType.POSITIVE
                else:
                    review.sentiment = SentimentType.NEUTRAL
            else:
                review.sentiment = SentimentType.NEUTRAL

        return review

    def filter_reviews(self, reviews: List[ReviewData]) -> FilterResult:
        """
        리뷰 리스트 필터링

        Args:
            reviews: 리뷰 리스트

        Returns:
            필터링 결과
        """
        result = FilterResult(
            total_reviews=len(reviews),
            complaint_reviews=0,
            positive_reviews=0,
            neutral_reviews=0
        )

        keyword_counts: Dict[str, int] = {}
        category_counts: Dict[str, int] = {}

        for review in reviews:
            analyzed = self.analyze_review(review)

            if analyzed.sentiment == SentimentType.NEGATIVE:
                result.complaint_reviews += 1
                result.complaints.append(analyzed)

                # 키워드 카운트
                for kw in analyzed.matched_negative_keywords:
                    keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

                # 카테고리 카운트
                for cat in analyzed.complaint_categories:
                    category_counts[cat] = category_counts.get(cat, 0) + 1

            elif analyzed.sentiment == SentimentType.POSITIVE:
                result.positive_reviews += 1
            else:
                result.neutral_reviews += 1

        # 상위 불만 키워드 정렬
        result.top_complaint_keywords = dict(
            sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        )
        result.complaint_categories = dict(
            sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        )

        return result

    def get_complaints_for_gemini(self, result: FilterResult, max_reviews: int = 50) -> str:
        """
        Gemini 분석용 불만 리뷰 텍스트 생성

        Args:
            result: 필터링 결과
            max_reviews: 최대 리뷰 수

        Returns:
            Gemini에 전달할 텍스트
        """
        complaints = result.complaints[:max_reviews]

        lines = [
            f"# 불만 리뷰 분석 요청 ({len(complaints)}건)",
            f"## 주요 불만 카테고리: {', '.join(result.complaint_categories.keys())}",
            "",
            "## 리뷰 목록:",
        ]

        for i, review in enumerate(complaints, 1):
            rating_str = f"[{review.rating}점]" if review.rating else ""
            categories = ", ".join(review.complaint_categories) if review.complaint_categories else "기타"
            lines.append(f"\n### 리뷰 {i} {rating_str} - {categories}")
            lines.append(review.content[:500])  # 최대 500자

        return "\n".join(lines)


# --- 테스트 실행 코드 ---
if __name__ == "__main__":
    print("="*60)
    print("🔍 키워드 필터 테스트 (v3.1)")
    print("="*60)

    filter = KeywordFilter()

    # 샘플 리뷰
    sample_reviews = [
        ReviewData(
            review_id="1",
            content="품질이 너무 별로예요. 사진과 다르고 실밥도 나와있음. 돈 아까워요.",
            rating=1
        ),
        ReviewData(
            review_id="2",
            content="배송 빠르고 품질도 좋아요! 가성비 최고 추천합니다.",
            rating=5
        ),
        ReviewData(
            review_id="3",
            content="생각보다 좋아요. 가격 대비 만족합니다.",
            rating=4
        ),
        ReviewData(
            review_id="4",
            content="냄새가 심해요. 화학 냄새 때문에 환기 필요. 내구성도 약한 것 같음.",
            rating=2
        ),
        ReviewData(
            review_id="5",
            content="그냥 그래요. 보통이에요.",
            rating=3
        ),
    ]

    result = filter.filter_reviews(sample_reviews)

    print(f"\n[분석 결과]")
    print(f"  - 총 리뷰: {result.total_reviews}건")
    print(f"  - 불만 리뷰: {result.complaint_reviews}건")
    print(f"  - 긍정 리뷰: {result.positive_reviews}건")
    print(f"  - 중립 리뷰: {result.neutral_reviews}건")

    print(f"\n[불만 카테고리]")
    for cat, count in result.complaint_categories.items():
        print(f"  - {cat}: {count}건")

    print(f"\n[주요 불만 키워드]")
    for kw, count in result.top_complaint_keywords.items():
        print(f"  - {kw}: {count}회")

    print("\n[불만 리뷰 상세]")
    for complaint in result.complaints:
        print(f"\n  리뷰 #{complaint.review_id} [{complaint.rating}점]")
        print(f"  내용: {complaint.content[:50]}...")
        print(f"  카테고리: {', '.join(complaint.complaint_categories)}")

    print("\n" + "="*60)
    print("✅ 키워드 필터 모듈 준비 완료")
    print("="*60 + "\n")
