"""keyword_filter.py 테스트"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from analyzers.keyword_filter import (
    KeywordFilter,
    ReviewData,
    FilterResult,
    SentimentType
)


class TestKeywordFilter:
    """키워드 필터 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.filter = KeywordFilter()

    def test_negative_review_detection(self):
        """부정 리뷰 감지 테스트"""
        review = ReviewData(
            review_id="1",
            content="품질이 너무 별로예요. 사진과 다르고 실밥도 나와있음.",
            rating=1
        )

        result = self.filter.analyze_review(review)

        assert result.is_complaint == True
        assert result.sentiment == SentimentType.NEGATIVE
        assert len(result.matched_negative_keywords) > 0
        # complaint_categories는 매칭된 키워드의 카테고리를 반환
        assert len(result.complaint_categories) > 0

    def test_positive_review_detection(self):
        """긍정 리뷰 감지 테스트"""
        review = ReviewData(
            review_id="2",
            content="배송 빠르고 품질도 좋아요! 가성비 최고 추천합니다.",
            rating=5
        )

        result = self.filter.analyze_review(review)

        assert result.is_complaint == False
        assert result.sentiment == SentimentType.POSITIVE
        assert len(result.matched_positive_keywords) > 0

    def test_false_positive_defense(self):
        """False Positive 방어 테스트"""
        # "품질이 좋아요"는 긍정이어야 함
        review = ReviewData(
            review_id="3",
            content="생각보다 품질이 좋아요. 만족합니다.",
            rating=4
        )

        result = self.filter.analyze_review(review)

        assert result.is_complaint == False
        assert result.sentiment == SentimentType.POSITIVE

    def test_neutral_review(self):
        """중립 리뷰 테스트"""
        review = ReviewData(
            review_id="4",
            content="그냥 그래요. 보통이에요.",
            rating=3
        )

        result = self.filter.analyze_review(review)

        assert result.sentiment == SentimentType.NEUTRAL

    def test_filter_reviews_batch(self):
        """리뷰 배치 필터링 테스트"""
        reviews = [
            ReviewData(review_id="1", content="품질이 별로예요.", rating=1),
            ReviewData(review_id="2", content="배송 빠르고 좋아요!", rating=5),
            ReviewData(review_id="3", content="냄새가 심해요.", rating=2),
            ReviewData(review_id="4", content="그냥 그래요.", rating=3),
            ReviewData(review_id="5", content="추천합니다! 최고!", rating=5),
        ]

        result = self.filter.filter_reviews(reviews)

        assert isinstance(result, FilterResult)
        assert result.total_reviews == 5
        assert result.complaint_reviews >= 2  # 최소 2개 부정
        assert result.positive_reviews >= 2   # 최소 2개 긍정
        assert len(result.complaints) == result.complaint_reviews

    def test_complaint_categories(self):
        """불만 카테고리 분류 테스트"""
        reviews = [
            ReviewData(review_id="1", content="품질이 너무 별로", rating=1),
            ReviewData(review_id="2", content="배송이 너무 느려요", rating=2),
            ReviewData(review_id="3", content="냄새가 심해요", rating=2),
        ]

        result = self.filter.filter_reviews(reviews)

        # 카테고리별 분류 확인
        assert "품질" in result.complaint_categories or len(result.complaint_categories) > 0

    def test_get_complaints_for_gemini(self):
        """Gemini용 불만 텍스트 생성 테스트"""
        reviews = [
            ReviewData(review_id="1", content="품질이 별로예요.", rating=1),
            ReviewData(review_id="2", content="냄새가 심해요.", rating=2),
        ]

        result = self.filter.filter_reviews(reviews)
        gemini_text = self.filter.get_complaints_for_gemini(result, max_reviews=10)

        assert "불만 리뷰 분석 요청" in gemini_text
        assert "리뷰 목록" in gemini_text

    def test_negative_keywords_exist(self):
        """부정 키워드 사전 존재 테스트"""
        assert len(KeywordFilter.NEGATIVE_KEYWORDS) > 0
        assert "품질" in KeywordFilter.NEGATIVE_KEYWORDS
        assert "배송" in KeywordFilter.NEGATIVE_KEYWORDS
        assert "냄새" in KeywordFilter.NEGATIVE_KEYWORDS

    def test_positive_keywords_exist(self):
        """긍정 키워드 사전 존재 테스트"""
        assert len(KeywordFilter.POSITIVE_KEYWORDS) > 0
        assert "좋아요" in KeywordFilter.POSITIVE_KEYWORDS
        assert "추천" in KeywordFilter.POSITIVE_KEYWORDS


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
