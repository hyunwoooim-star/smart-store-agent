"""
product_filter.py - 상품 필터링 (v4.0)

3단계 필터링:
1. 기본 필터: 가격, 판매량, 평점
2. 마진 필터: 마진율, 손익분기점
3. 리스크 필터: 브랜드, KC인증, 금지품목
"""

from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

from src.domain.crawler_models import SourcingCandidate, CrawlRiskLevel


@dataclass
class FilterConfig:
    """필터링 설정"""
    # 1차 필터 (기본)
    min_price_cny: float = 5.0          # 최소 가격 (위안)
    max_price_cny: float = 500.0        # 최대 가격 (위안)
    min_sales_count: int = 10           # 최소 판매량
    min_shop_rating: float = 4.0        # 최소 샵 평점

    # 2차 필터 (마진)
    min_margin_rate: float = 0.30       # 최소 마진율 (30%)
    max_risk_level: str = "warning"     # 허용 최대 리스크 (danger 제외)

    # 3차 필터 (리스크)
    check_brand: bool = True            # 브랜드 체크
    check_kc: bool = True               # KC인증 체크
    check_forbidden: bool = True        # 금지품목 체크


class ProductFilter:
    """상품 필터링"""

    # 브랜드 키워드 (지재권 위험)
    BRAND_KEYWORDS = [
        # 글로벌 브랜드
        'nike', 'adidas', 'gucci', 'prada', 'chanel', 'louis vuitton', 'lv',
        'hermes', 'dior', 'apple', 'samsung', 'sony', 'nintendo',
        # 한글 브랜드
        '나이키', '아디다스', '구찌', '프라다', '샤넬', '루이비통', '에르메스',
        '디올', '애플', '삼성', '소니', '닌텐도',
        # 캐릭터
        'disney', 'marvel', 'dc', 'pokemon', 'sanrio', 'kakao', 'line',
        '디즈니', '마블', '포켓몬', '산리오', '카카오', '라인', '미키마우스',
        '헬로키티', '피카츄', '라이언', '어피치',
        # 스포츠
        'mlb', 'nba', 'nfl', 'fifa',
    ]

    # KC인증 필요 키워드
    KC_KEYWORDS = [
        '전자', '충전기', '충전', '배터리', '콘센트', '어댑터', '케이블',
        '유아', '아동', '아기', '어린이', '장난감', '완구',
        '전기', '가전', '히터', '선풍기',
    ]

    # 판매 금지/제한 품목
    FORBIDDEN_KEYWORDS = [
        '식품', '건강', '영양제', '비타민', '의약품', '의료기기',
        '화장품', '스킨케어', '마스크팩', '립스틱',
        '담배', '전자담배', '베이프', '액상',
        '주류', '술', '와인', '맥주',
        '무기', '칼', '총', '도검',
        '성인용품', '성인',
    ]

    def __init__(self, config: FilterConfig = None):
        self.config = config or FilterConfig()

    def apply_basic_filter(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """1차 필터: 기본 조건

        Args:
            products: 1688 검색 결과 리스트 (딕셔너리)

        Returns:
            필터링된 상품 리스트
        """
        filtered = []
        for p in products:
            price = float(p.get('price', 0) or 0)
            sales = int(p.get('sales_count', 0) or 0)
            rating = float(p.get('shop_rating', 0) or 0)

            if (self.config.min_price_cny <= price <= self.config.max_price_cny and
                sales >= self.config.min_sales_count and
                rating >= self.config.min_shop_rating):
                filtered.append(p)

        return filtered

    def apply_margin_filter(
        self,
        candidate: SourcingCandidate,
        naver_avg_price: int
    ) -> bool:
        """2차 필터: 마진 조건

        Args:
            candidate: 후보 상품
            naver_avg_price: 네이버 평균가

        Returns:
            통과 여부
        """
        # 마진율 체크
        if candidate.estimated_margin_rate < self.config.min_margin_rate:
            return False

        # 리스크 레벨 체크
        if candidate.risk_level == CrawlRiskLevel.DANGER:
            return False

        # 손익분기점 체크 (손익분기가 평균가보다 높으면 실패)
        if candidate.breakeven_price > 0 and naver_avg_price > 0:
            if candidate.breakeven_price > naver_avg_price:
                return False

        return True

    def apply_risk_filter(self, title: str, images: List[str] = None) -> Tuple[CrawlRiskLevel, List[str]]:
        """3차 필터: 리스크 체크

        Args:
            title: 상품명 (중국어 또는 한국어)
            images: 이미지 URL 리스트 (현재 미사용, 추후 AI 분석용)

        Returns:
            (리스크 레벨, 리스크 사유 리스트)
        """
        risks = []
        title_lower = title.lower()

        # 브랜드 체크
        if self.config.check_brand:
            for brand in self.BRAND_KEYWORDS:
                if brand.lower() in title_lower:
                    risks.append(f"브랜드명 포함: {brand}")

        # KC인증 체크
        if self.config.check_kc:
            for kc in self.KC_KEYWORDS:
                if kc in title:
                    risks.append(f"KC인증 필요 가능성: {kc}")
                    break  # 하나만 찾으면 충분

        # 금지품목 체크
        if self.config.check_forbidden:
            for forbidden in self.FORBIDDEN_KEYWORDS:
                if forbidden in title:
                    risks.append(f"판매 제한 품목: {forbidden}")

        # 리스크 레벨 결정
        if any("브랜드명" in r or "판매 제한" in r for r in risks):
            level = CrawlRiskLevel.DANGER
        elif risks:
            level = CrawlRiskLevel.WARNING
        else:
            level = CrawlRiskLevel.SAFE

        return level, risks

    def filter_candidate(
        self,
        candidate: SourcingCandidate,
        naver_avg_price: int = 0
    ) -> Tuple[bool, List[str]]:
        """전체 필터링 (2차 + 3차)

        Args:
            candidate: 후보 상품
            naver_avg_price: 네이버 평균가

        Returns:
            (통과 여부, 거부 사유 리스트)
        """
        reasons = []

        # 2차 필터: 마진
        if candidate.estimated_margin_rate < self.config.min_margin_rate:
            reasons.append(f"마진율 부족: {candidate.estimated_margin_rate:.1%} < {self.config.min_margin_rate:.0%}")

        if candidate.breakeven_price > naver_avg_price > 0:
            reasons.append(f"손익분기점 초과: {candidate.breakeven_price:,}원 > 평균가 {naver_avg_price:,}원")

        # 3차 필터: 리스크
        risk_level, risk_reasons = self.apply_risk_filter(candidate.source_title)
        candidate.risk_level = risk_level
        candidate.risk_reasons = risk_reasons

        if risk_level == CrawlRiskLevel.DANGER:
            reasons.extend(risk_reasons)

        passed = len(reasons) == 0
        return passed, reasons

    def get_filter_summary(self, original_count: int, filtered_count: int) -> str:
        """필터링 요약 메시지"""
        if original_count == 0:
            return "검색 결과 없음"

        filter_rate = (1 - filtered_count / original_count) * 100
        return f"총 {original_count}개 중 {filtered_count}개 통과 ({filter_rate:.0f}% 제외)"
