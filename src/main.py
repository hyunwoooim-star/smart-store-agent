"""
main.py - Smart Store Agent 오케스트레이션 (v3.1)

AI 에이전트 기반 네이버 스마트스토어 자동화 시스템
"틈새 시장 발굴 → 소싱 검증 → 콘텐츠 생성" 과정 자동화

사용법:
    python src/main.py --excel data/keywords.xlsx --product "캠핑의자"
    python src/main.py --demo  # 데모 모드
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

# 경로 설정
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

# 모듈 임포트
from sourcing.margin_calculator import (
    MarginCalculator, SourcingInput, ProductDimensions, MarginResult
)
from importers.data_importer import DataImporter, KeywordData, ImportResult
from analyzers.keyword_filter import KeywordFilter, ReviewData, FilterResult
from analyzers.gemini_analyzer import (
    GeminiAnalyzer, MockGeminiAnalyzer, GeminiAnalysisResult, AnalysisType
)
from analyzers.spec_validator import SpecValidator, SpecData, ValidationResult
from generators.gap_reporter import GapReporter, OpportunityReport


class SmartStoreAgent:
    """스마트스토어 자동화 에이전트"""

    def __init__(self, use_mock_gemini: bool = True, output_dir: str = "output"):
        """
        Args:
            use_mock_gemini: True면 Mock Gemini 사용 (API 키 불필요)
            output_dir: 출력 디렉토리
        """
        self.margin_calculator = MarginCalculator()
        self.data_importer = DataImporter()
        self.keyword_filter = KeywordFilter()

        if use_mock_gemini:
            self.gemini_analyzer = MockGeminiAnalyzer()
        else:
            self.gemini_analyzer = GeminiAnalyzer()

        self.spec_validator = SpecValidator()
        self.reporter = GapReporter(output_dir=output_dir)

        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def analyze_product(
        self,
        product_name: str,
        category: str,
        wholesale_price_cny: float,
        actual_weight_kg: float,
        dimensions: tuple,  # (가로, 세로, 높이) cm
        moq: int,
        target_price_krw: int,
        keywords_file: str = None,
        reviews: list = None,
    ) -> OpportunityReport:
        """
        상품 종합 분석

        Args:
            product_name: 상품명
            category: 카테고리
            wholesale_price_cny: 도매가 (위안)
            actual_weight_kg: 실무게 (kg)
            dimensions: 박스 크기 (가로, 세로, 높이) cm
            moq: 최소 주문 수량
            target_price_krw: 목표 판매가 (원)
            keywords_file: 키워드 엑셀 파일 경로
            reviews: 리뷰 리스트 (ReviewData)

        Returns:
            OpportunityReport: 종합 분석 리포트
        """
        print(f"\n{'='*60}")
        print(f"🚀 Smart Store Agent v3.1 - 상품 분석 시작")
        print(f"{'='*60}")
        print(f"상품: {product_name}")
        print(f"카테고리: {category}")
        print(f"{'='*60}\n")

        # 1. 마진 계산
        print("📊 [1/5] 마진 분석 중...")
        sourcing_input = SourcingInput(
            product_name=product_name,
            wholesale_price_cny=wholesale_price_cny,
            actual_weight_kg=actual_weight_kg,
            dimensions=ProductDimensions(*dimensions),
            moq=moq,
            target_price_krw=target_price_krw,
            category=category
        )
        margin_result = self.margin_calculator.calculate(sourcing_input)
        self._print_margin_result(margin_result)

        # 2. 키워드 분석
        print("\n🔑 [2/5] 키워드 분석 중...")
        keywords = []
        if keywords_file and os.path.exists(keywords_file):
            import_result = self.data_importer.import_from_excel(keywords_file)
            if import_result.success:
                keywords = self.data_importer.to_dict_list(import_result.keywords[:10])
                print(f"  - {len(keywords)}개 키워드 로드 완료")
        else:
            # 샘플 키워드 (데모용)
            keywords = self._get_sample_keywords(product_name)
            print(f"  - 샘플 키워드 {len(keywords)}개 사용")

        # 3. 리뷰 분석
        print("\n📝 [3/5] 리뷰 분석 중...")
        filter_result = None
        if reviews:
            filter_result = self.keyword_filter.filter_reviews(reviews)
            print(f"  - 불만 리뷰 {filter_result.complaint_reviews}건 감지")
        else:
            # 샘플 리뷰 (데모용)
            sample_reviews = self._get_sample_reviews()
            filter_result = self.keyword_filter.filter_reviews(sample_reviews)
            print(f"  - 샘플 리뷰 분석 완료 (불만 {filter_result.complaint_reviews}건)")

        # 4. Gemini AI 분석
        print("\n🤖 [4/5] AI 분석 중...")
        gemini_result = None
        if filter_result and filter_result.complaints:
            reviews_text = self.keyword_filter.get_complaints_for_gemini(filter_result)
            gemini_result = self.gemini_analyzer.analyze_complaints(reviews_text)
            if gemini_result.success:
                print(f"  - {len(gemini_result.complaint_patterns)}개 불만 패턴 도출")
                print(f"  - {len(gemini_result.key_insights)}개 인사이트 발견")

        # 5. 리포트 생성
        print("\n📋 [5/5] 리포트 생성 중...")

        # 마진 결과를 딕셔너리로 변환
        margin_dict = {
            "product_cost_krw": margin_result.product_cost_krw,
            "shipping_agency_fee_krw": margin_result.shipping_agency_fee_krw,
            "tariff_krw": margin_result.tariff_krw,
            "vat_krw": margin_result.vat_krw,
            "total_cost_krw": margin_result.total_cost_krw,
            "profit_krw": margin_result.profit_krw,
            "margin_percent": margin_result.margin_percent,
            "is_viable": margin_result.is_viable,
            "breakeven_price_krw": margin_result.breakeven_price_krw,
            "target_margin_price_krw": margin_result.target_margin_price_krw,
            "recommendation": margin_result.recommendation,
            "volume_weight_kg": margin_result.volume_weight_kg,
            "billable_weight_kg": margin_result.billable_weight_kg,
        }

        # 불만 패턴 딕셔너리
        complaint_patterns = []
        if gemini_result and gemini_result.complaint_patterns:
            complaint_patterns = [
                {
                    "rank": p.rank,
                    "category": p.category,
                    "description": p.description,
                    "frequency": p.frequency,
                    "severity": p.severity,
                    "suggested_solution": p.suggested_solution
                }
                for p in gemini_result.complaint_patterns
            ]

        # 리스크 도출
        risks = self._identify_risks(margin_result, filter_result, moq)

        # 리포트 생성
        report = self.reporter.create_report(
            product_name=product_name,
            category=category,
            keywords=keywords,
            margin_result=margin_dict,
            complaint_patterns=complaint_patterns,
            risks=risks
        )

        # 리포트 저장
        filepath = self.reporter.save_report(report)
        print(f"  - 리포트 저장: {filepath}")

        # 결과 출력
        self._print_summary(report)

        return report

    def _print_margin_result(self, result: MarginResult):
        """마진 결과 출력"""
        print(f"  - 상품원가: {result.product_cost_krw:,}원")
        print(f"  - 배송비(청구무게 {result.billable_weight_kg}kg): {result.shipping_agency_fee_krw:,}원")
        print(f"  - 관부가세: {result.tariff_krw + result.vat_krw:,}원")
        print(f"  - 총 비용: {result.total_cost_krw:,}원")
        print(f"  - 예상 마진율: {result.margin_percent}%")
        print(f"  - 수익성: {'✅ 가능' if result.is_viable else '❌ 부족'}")

    def _get_sample_keywords(self, product_name: str) -> list:
        """샘플 키워드 생성"""
        return [
            {"keyword": product_name, "monthly_search_volume": 45000, "total_products": 25000, "competition_rate": 0.56, "opportunity_score": 8.0},
            {"keyword": f"초경량 {product_name}", "monthly_search_volume": 8500, "total_products": 3200, "competition_rate": 0.38, "opportunity_score": 17.7},
            {"keyword": f"{product_name} 추천", "monthly_search_volume": 5200, "total_products": 2100, "competition_rate": 0.40, "opportunity_score": 12.4},
        ]

    def _get_sample_reviews(self) -> list:
        """샘플 리뷰 생성"""
        return [
            ReviewData(review_id="1", content="품질이 너무 별로예요. 사진과 다르고 실밥도 나와있음.", rating=1),
            ReviewData(review_id="2", content="배송은 빠른데 냄새가 심해요. 환기 필요.", rating=2),
            ReviewData(review_id="3", content="일주일 만에 부러졌어요. 내구성 약함.", rating=1),
            ReviewData(review_id="4", content="가격 대비 좋아요! 추천합니다.", rating=5),
            ReviewData(review_id="5", content="그냥 그래요. 보통이에요.", rating=3),
        ]

    def _identify_risks(self, margin: MarginResult, filter_result: FilterResult, moq: int) -> list:
        """리스크 식별"""
        risks = []

        if margin.margin_percent < 0:
            risks.append(f"마진율 {margin.margin_percent}%로 현재 가격 구조로는 손실 발생")
        elif margin.margin_percent < 15:
            risks.append(f"마진율 {margin.margin_percent}%로 수익성 낮음")

        if margin.volume_weight_kg > margin.actual_weight_kg:
            risks.append(f"부피무게({margin.volume_weight_kg}kg)가 실무게보다 커서 배송비 증가")

        if moq >= 50:
            risks.append(f"MOQ {moq}개 - 초기 재고 리스크 높음")

        if filter_result and filter_result.complaint_reviews > filter_result.positive_reviews:
            risks.append("불만 리뷰가 긍정 리뷰보다 많음 - 품질 리스크")

        return risks

    def _print_summary(self, report: OpportunityReport):
        """결과 요약 출력"""
        print(f"\n{'='*60}")
        print(f"📊 분석 결과 요약")
        print(f"{'='*60}")
        print(f"종합 점수: {report.opportunity_score.total_score:.1f}/100")
        print(f"")
        print(f"🎯 최종 추천:")
        print(f"   {report.final_recommendation}")
        print(f"")
        print(f"📌 액션 아이템:")
        for item in report.action_items:
            print(f"   - {item}")
        if report.risks:
            print(f"")
            print(f"⚠️ 리스크:")
            for risk in report.risks:
                print(f"   - {risk}")
        print(f"{'='*60}\n")


def run_demo():
    """데모 실행"""
    agent = SmartStoreAgent(use_mock_gemini=True)

    # 캠핑의자 예시 (계획서 v3.1 시뮬레이션)
    report = agent.analyze_product(
        product_name="초경량 캠핑 의자",
        category="캠핑/레저",
        wholesale_price_cny=45,           # 약 8,550원
        actual_weight_kg=2.5,
        dimensions=(80, 20, 15),          # cm
        moq=50,
        target_price_krw=45000
    )

    return report


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="Smart Store Agent v3.1 - 스마트스토어 자동화 시스템"
    )
    parser.add_argument("--demo", action="store_true", help="데모 모드 실행")
    parser.add_argument("--product", type=str, help="상품명")
    parser.add_argument("--category", type=str, default="기타", help="카테고리")
    parser.add_argument("--price-cny", type=float, help="도매가 (위안)")
    parser.add_argument("--weight", type=float, help="무게 (kg)")
    parser.add_argument("--dimensions", type=str, help="박스 크기 '가로x세로x높이' (cm)")
    parser.add_argument("--moq", type=int, default=10, help="최소 주문 수량")
    parser.add_argument("--target-price", type=int, help="목표 판매가 (원)")
    parser.add_argument("--excel", type=str, help="키워드 엑셀 파일")
    parser.add_argument("--mock", action="store_true", default=True, help="Mock Gemini 사용")
    parser.add_argument("--output", type=str, default="output", help="출력 디렉토리")

    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    if not args.product or not args.price_cny or not args.target_price:
        print("필수 인자가 누락되었습니다.")
        print("사용법: python src/main.py --product '상품명' --price-cny 45 --target-price 45000")
        print("또는: python src/main.py --demo")
        parser.print_help()
        return

    # 박스 크기 파싱
    dimensions = (30, 30, 30)  # 기본값
    if args.dimensions:
        try:
            dims = args.dimensions.lower().split("x")
            dimensions = tuple(float(d) for d in dims)
        except:
            print("박스 크기 형식 오류. 기본값 사용.")

    agent = SmartStoreAgent(use_mock_gemini=args.mock, output_dir=args.output)

    agent.analyze_product(
        product_name=args.product,
        category=args.category,
        wholesale_price_cny=args.price_cny,
        actual_weight_kg=args.weight or 1.0,
        dimensions=dimensions,
        moq=args.moq,
        target_price_krw=args.target_price,
        keywords_file=args.excel
    )


if __name__ == "__main__":
    main()
