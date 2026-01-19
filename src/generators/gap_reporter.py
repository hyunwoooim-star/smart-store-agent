"""
gap_reporter.py - 기회 분석 리포트 생성기 (v3.1)

핵심 기능:
1. opportunity_report.md 생성
2. 종합 분석 리포트 출력
3. 마크다운/JSON 포맷 지원
"""

import os
import json
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any

# 다른 모듈 임포트 (타입 힌트용)
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from sourcing.margin_calculator import MarginResult, SourcingInput
    from importers.data_importer import KeywordData, ImportResult
    from analyzers.keyword_filter import FilterResult, ReviewData
    from analyzers.gemini_analyzer import GeminiAnalysisResult, ComplaintPattern, SemanticGap
    from analyzers.spec_validator import ValidationResult
except ImportError:
    # 독립 실행 시 임포트 실패 무시
    MarginResult = None
    SourcingInput = None
    KeywordData = None


@dataclass
class OpportunityScore:
    """기회 점수"""
    keyword_score: float = 0.0      # 키워드 기회 점수
    margin_score: float = 0.0       # 마진 점수
    competition_score: float = 0.0  # 경쟁 점수
    risk_score: float = 0.0         # 리스크 점수 (낮을수록 좋음)

    total_score: float = 0.0        # 종합 점수

    def calculate_total(self, weights: Dict[str, float] = None):
        """종합 점수 계산"""
        if weights is None:
            weights = {
                "keyword": 0.3,
                "margin": 0.4,
                "competition": 0.2,
                "risk": 0.1
            }

        self.total_score = (
            self.keyword_score * weights["keyword"] +
            self.margin_score * weights["margin"] +
            self.competition_score * weights["competition"] -
            self.risk_score * weights["risk"]
        )
        return self.total_score


@dataclass
class OpportunityReport:
    """기회 분석 리포트"""
    # 메타 정보
    report_id: str
    created_at: str
    product_name: str
    category: str

    # 점수
    opportunity_score: OpportunityScore

    # 키워드 분석
    target_keywords: List[Dict[str, Any]] = field(default_factory=list)
    keyword_summary: str = ""

    # 마진 분석
    margin_analysis: Dict[str, Any] = field(default_factory=dict)
    margin_summary: str = ""

    # 경쟁 분석
    competition_analysis: Dict[str, Any] = field(default_factory=dict)
    competition_summary: str = ""

    # 불만/기회 분석
    complaint_patterns: List[Dict[str, Any]] = field(default_factory=list)
    semantic_gaps: List[Dict[str, Any]] = field(default_factory=list)
    opportunity_summary: str = ""

    # 카피라이팅 제안
    copywriting_suggestions: List[Dict[str, Any]] = field(default_factory=list)

    # 스펙 체크리스트
    spec_checklist: List[Dict[str, Any]] = field(default_factory=list)

    # 검증 결과
    validation_summary: Dict[str, Any] = field(default_factory=dict)

    # 최종 추천
    final_recommendation: str = ""
    action_items: List[str] = field(default_factory=list)

    # 리스크
    risks: List[str] = field(default_factory=list)


class GapReporter:
    """기회 분석 리포터"""

    def __init__(self, output_dir: str = "output"):
        """
        Args:
            output_dir: 출력 디렉토리
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _generate_report_id(self) -> str:
        """리포트 ID 생성"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _calculate_keyword_score(self, keywords: List[Dict]) -> float:
        """키워드 점수 계산 (0-100)"""
        if not keywords:
            return 0.0

        # 평균 기회 점수 기반
        avg_opportunity = sum(kw.get("opportunity_score", 0) for kw in keywords) / len(keywords)

        # 검색량 기반 보정
        max_volume = max(kw.get("monthly_search_volume", 0) for kw in keywords)
        volume_bonus = min(max_volume / 10000, 20)  # 최대 20점 보너스

        return min(avg_opportunity * 10 + volume_bonus, 100)

    def _calculate_margin_score(self, margin_percent: float) -> float:
        """마진 점수 계산 (0-100)"""
        if margin_percent < 0:
            return 0.0
        elif margin_percent >= 30:
            return 100.0
        elif margin_percent >= 20:
            return 80.0
        elif margin_percent >= 15:
            return 60.0
        elif margin_percent >= 10:
            return 40.0
        else:
            return margin_percent * 4  # 10% 미만은 비례 점수

    def _calculate_competition_score(self, competition_rate: float) -> float:
        """경쟁 점수 계산 (0-100, 낮은 경쟁일수록 높은 점수)"""
        if competition_rate <= 0.3:
            return 100.0
        elif competition_rate <= 0.5:
            return 80.0
        elif competition_rate <= 1.0:
            return 60.0
        elif competition_rate <= 2.0:
            return 40.0
        elif competition_rate <= 5.0:
            return 20.0
        else:
            return 10.0

    def _calculate_risk_score(self, risks: List[str]) -> float:
        """리스크 점수 계산 (0-100)"""
        base_risk = len(risks) * 15
        return min(base_risk, 100)

    def create_report(
        self,
        product_name: str,
        category: str,
        keywords: List[Dict[str, Any]] = None,
        margin_result: Dict[str, Any] = None,
        complaint_patterns: List[Dict[str, Any]] = None,
        semantic_gaps: List[Dict[str, Any]] = None,
        copywriting: List[Dict[str, Any]] = None,
        spec_checklist: List[Dict[str, Any]] = None,
        validation: Dict[str, Any] = None,
        risks: List[str] = None
    ) -> OpportunityReport:
        """
        기회 분석 리포트 생성

        Args:
            product_name: 상품명
            category: 카테고리
            keywords: 키워드 분석 결과
            margin_result: 마진 계산 결과
            complaint_patterns: 불만 패턴
            semantic_gaps: 시맨틱 갭
            copywriting: 카피라이팅 제안
            spec_checklist: 스펙 체크리스트
            validation: 검증 결과
            risks: 리스크 목록

        Returns:
            OpportunityReport: 생성된 리포트
        """
        keywords = keywords or []
        margin_result = margin_result or {}
        complaint_patterns = complaint_patterns or []
        semantic_gaps = semantic_gaps or []
        copywriting = copywriting or []
        spec_checklist = spec_checklist or []
        validation = validation or {}
        risks = risks or []

        # 점수 계산
        score = OpportunityScore(
            keyword_score=self._calculate_keyword_score(keywords),
            margin_score=self._calculate_margin_score(margin_result.get("margin_percent", 0)),
            competition_score=self._calculate_competition_score(
                keywords[0].get("competition_rate", 1.0) if keywords else 1.0
            ),
            risk_score=self._calculate_risk_score(risks)
        )
        score.calculate_total()

        # 요약 생성
        keyword_summary = self._generate_keyword_summary(keywords)
        margin_summary = self._generate_margin_summary(margin_result)
        opportunity_summary = self._generate_opportunity_summary(complaint_patterns, semantic_gaps)
        final_recommendation = self._generate_recommendation(score, margin_result, risks)
        action_items = self._generate_action_items(score, margin_result, complaint_patterns)

        report = OpportunityReport(
            report_id=self._generate_report_id(),
            created_at=datetime.now().isoformat(),
            product_name=product_name,
            category=category,
            opportunity_score=score,
            target_keywords=keywords,
            keyword_summary=keyword_summary,
            margin_analysis=margin_result,
            margin_summary=margin_summary,
            complaint_patterns=complaint_patterns,
            semantic_gaps=semantic_gaps,
            opportunity_summary=opportunity_summary,
            copywriting_suggestions=copywriting,
            spec_checklist=spec_checklist,
            validation_summary=validation,
            final_recommendation=final_recommendation,
            action_items=action_items,
            risks=risks
        )

        return report

    def _generate_keyword_summary(self, keywords: List[Dict]) -> str:
        """키워드 요약 생성"""
        if not keywords:
            return "키워드 데이터 없음"

        top_kw = keywords[0] if keywords else {}
        return f"대표 키워드 '{top_kw.get('keyword', 'N/A')}' 월간 검색량 {top_kw.get('monthly_search_volume', 0):,}회, 경쟁강도 {top_kw.get('competition_rate', 0)}"

    def _generate_margin_summary(self, margin: Dict) -> str:
        """마진 요약 생성"""
        if not margin:
            return "마진 분석 데이터 없음"

        margin_percent = margin.get("margin_percent", 0)
        is_viable = margin.get("is_viable", False)

        if is_viable:
            return f"예상 마진율 {margin_percent}% - 수익성 확보 가능"
        else:
            return f"예상 마진율 {margin_percent}% - 수익성 부족, 가격/비용 조정 필요"

    def _generate_opportunity_summary(self, patterns: List[Dict], gaps: List[Dict]) -> str:
        """기회 요약 생성"""
        if not patterns and not gaps:
            return "불만/기회 분석 데이터 없음"

        summaries = []
        if patterns:
            top_pattern = patterns[0] if patterns else {}
            summaries.append(f"주요 불만: {top_pattern.get('category', 'N/A')}")

        if gaps:
            top_gap = gaps[0] if gaps else {}
            summaries.append(f"주요 갭: {top_gap.get('gap_type', 'N/A')}")

        return " / ".join(summaries)

    def _generate_recommendation(self, score: OpportunityScore, margin: Dict, risks: List[str]) -> str:
        """최종 추천 생성"""
        total = score.total_score
        margin_percent = margin.get("margin_percent", 0)

        if total >= 70 and margin_percent >= 20:
            return "✅ 강력 추천 - 높은 기회 점수와 양호한 마진율. 소싱 진행 권장."
        elif total >= 50 and margin_percent >= 15:
            return "🟡 조건부 추천 - 기회 있으나 마진 개선 또는 리스크 관리 필요."
        elif total >= 30:
            return "⚠️ 신중 검토 필요 - 일부 기회 요소 있으나 리스크 높음."
        else:
            return "❌ 비추천 - 기회 점수 낮음. 다른 상품 검토 권장."

    def _generate_action_items(self, score: OpportunityScore, margin: Dict, patterns: List[Dict]) -> List[str]:
        """액션 아이템 생성"""
        items = []

        # 마진 기반 액션
        margin_percent = margin.get("margin_percent", 0)
        if margin_percent < 15:
            items.append("판매가 인상 또는 원가 절감 방안 검토")
            items.append("배송비 절감을 위한 해운 옵션 검토")

        # 불만 패턴 기반 액션
        if patterns:
            top_pattern = patterns[0] if patterns else {}
            if top_pattern.get("category") == "품질":
                items.append("품질 검수 강화 - 샘플 테스트 필수")
            if top_pattern.get("category") == "내구성":
                items.append("내구성 테스트 결과 확인 필요")

        # 기본 액션
        if score.keyword_score >= 60:
            items.append("SEO 최적화 - 타겟 키워드 상세페이지 반영")

        if not items:
            items.append("추가 시장 조사 진행")

        return items

    def to_markdown(self, report: OpportunityReport) -> str:
        """마크다운 형식으로 변환"""
        lines = [
            f"# 🎯 기회 분석 리포트",
            f"",
            f"**리포트 ID:** {report.report_id}",
            f"**생성일시:** {report.created_at}",
            f"",
            f"---",
            f"",
            f"## 📦 상품 정보",
            f"- **상품명:** {report.product_name}",
            f"- **카테고리:** {report.category}",
            f"",
            f"---",
            f"",
            f"## 📊 종합 점수",
            f"",
            f"| 항목 | 점수 |",
            f"|------|------|",
            f"| 키워드 기회 | {report.opportunity_score.keyword_score:.1f}/100 |",
            f"| 마진 점수 | {report.opportunity_score.margin_score:.1f}/100 |",
            f"| 경쟁 점수 | {report.opportunity_score.competition_score:.1f}/100 |",
            f"| 리스크 점수 | {report.opportunity_score.risk_score:.1f}/100 |",
            f"| **종합 점수** | **{report.opportunity_score.total_score:.1f}/100** |",
            f"",
            f"---",
            f"",
            f"## 🔑 키워드 분석",
            f"{report.keyword_summary}",
            f"",
        ]

        if report.target_keywords:
            lines.append("### 타겟 키워드")
            lines.append("| 키워드 | 월간 검색량 | 상품수 | 경쟁강도 | 기회점수 |")
            lines.append("|--------|------------|--------|----------|----------|")
            for kw in report.target_keywords[:5]:
                lines.append(f"| {kw.get('keyword', '')} | {kw.get('monthly_search_volume', 0):,} | {kw.get('total_products', 0):,} | {kw.get('competition_rate', 0)} | {kw.get('opportunity_score', 0):.1f} |")
            lines.append("")

        lines.extend([
            f"---",
            f"",
            f"## 💰 마진 분석",
            f"{report.margin_summary}",
            f"",
        ])

        if report.margin_analysis:
            ma = report.margin_analysis
            lines.extend([
                "### 비용 구조",
                f"- 상품원가: {ma.get('product_cost_krw', 0):,}원",
                f"- 배송비: {ma.get('shipping_agency_fee_krw', 0):,}원",
                f"- 관부가세: {ma.get('tariff_krw', 0) + ma.get('vat_krw', 0):,}원",
                f"- 총 비용: {ma.get('total_cost_krw', 0):,}원",
                f"- **예상 마진율: {ma.get('margin_percent', 0)}%**",
                f"- 손익분기 판매가: {ma.get('breakeven_price_krw', 0):,}원",
                "",
            ])

        lines.extend([
            f"---",
            f"",
            f"## 🔍 불만/기회 분석",
            f"{report.opportunity_summary}",
            f"",
        ])

        if report.complaint_patterns:
            lines.append("### 주요 불만 패턴")
            for i, p in enumerate(report.complaint_patterns[:3], 1):
                lines.append(f"{i}. **{p.get('category', '')}** - {p.get('description', '')}")
                if p.get('suggested_solution'):
                    lines.append(f"   - 해결방안: {p.get('suggested_solution')}")
            lines.append("")

        if report.semantic_gaps:
            lines.append("### 시맨틱 갭")
            for g in report.semantic_gaps[:3]:
                lines.append(f"- **{g.get('gap_type', '')}**: {g.get('customer_expectation', '')} vs {g.get('actual_reality', '')}")
            lines.append("")

        if report.copywriting_suggestions:
            lines.extend([
                f"---",
                f"",
                f"## ✍️ 카피라이팅 제안",
                "",
            ])
            for s in report.copywriting_suggestions[:3]:
                lines.append(f"- **불만:** {s.get('original_pain_point', '')}")
                lines.append(f"  - **제안 카피:** \"{s.get('suggested_copy', '')}\"")
            lines.append("")

        if report.spec_checklist:
            lines.extend([
                f"---",
                f"",
                f"## ✅ 스펙 체크리스트",
                "",
            ])
            for c in report.spec_checklist:
                lines.append(f"- [{c.get('category', '')}] {c.get('item', '')} - {c.get('reason', '')}")
            lines.append("")

        lines.extend([
            f"---",
            f"",
            f"## 🎯 최종 추천",
            f"",
            f"{report.final_recommendation}",
            f"",
            f"### 액션 아이템",
        ])
        for item in report.action_items:
            lines.append(f"- [ ] {item}")

        if report.risks:
            lines.extend([
                f"",
                f"### ⚠️ 리스크",
            ])
            for risk in report.risks:
                lines.append(f"- {risk}")

        lines.extend([
            f"",
            f"---",
            f"*Generated by Smart Store Agent v3.1*"
        ])

        return "\n".join(lines)

    def to_json(self, report: OpportunityReport) -> str:
        """JSON 형식으로 변환"""
        data = {
            "report_id": report.report_id,
            "created_at": report.created_at,
            "product_name": report.product_name,
            "category": report.category,
            "opportunity_score": {
                "keyword_score": report.opportunity_score.keyword_score,
                "margin_score": report.opportunity_score.margin_score,
                "competition_score": report.opportunity_score.competition_score,
                "risk_score": report.opportunity_score.risk_score,
                "total_score": report.opportunity_score.total_score
            },
            "keyword_summary": report.keyword_summary,
            "margin_summary": report.margin_summary,
            "opportunity_summary": report.opportunity_summary,
            "final_recommendation": report.final_recommendation,
            "action_items": report.action_items,
            "risks": report.risks,
            "target_keywords": report.target_keywords,
            "margin_analysis": report.margin_analysis,
            "complaint_patterns": report.complaint_patterns,
            "semantic_gaps": report.semantic_gaps,
            "copywriting_suggestions": report.copywriting_suggestions,
            "spec_checklist": report.spec_checklist,
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def save_report(self, report: OpportunityReport, filename: str = None) -> str:
        """리포트 저장"""
        if filename is None:
            filename = f"opportunity_report_{report.report_id}.md"

        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_markdown(report))

        return filepath


# --- 테스트 실행 코드 ---
if __name__ == "__main__":
    print("="*60)
    print("📝 리포트 생성기 테스트 (v3.1)")
    print("="*60)

    reporter = GapReporter(output_dir="output")

    # 샘플 데이터
    sample_keywords = [
        {"keyword": "캠핑의자", "monthly_search_volume": 45000, "total_products": 25000, "competition_rate": 0.56, "opportunity_score": 8.0},
        {"keyword": "초경량 캠핑의자", "monthly_search_volume": 8500, "total_products": 3200, "competition_rate": 0.38, "opportunity_score": 17.7},
    ]

    sample_margin = {
        "product_cost_krw": 8550,
        "shipping_agency_fee_krw": 16000,
        "tariff_krw": 684,
        "vat_krw": 2523,
        "total_cost_krw": 37482,
        "margin_percent": -28.0,
        "is_viable": False,
        "breakeven_price_krw": 57000,
        "recommendation": "❌ 수익성 부족"
    }

    sample_patterns = [
        {"rank": 1, "category": "품질", "description": "전체적인 품질 불만", "suggested_solution": "품질 검수 강화"},
        {"rank": 2, "category": "내구성", "description": "쉽게 부러짐", "suggested_solution": "내구성 테스트 필수"},
    ]

    sample_risks = [
        "마진율 -28%로 현재 가격 구조로는 손실",
        "부피무게로 인한 배송비 증가",
        "MOQ 50개 - 재고 리스크"
    ]

    # 리포트 생성
    report = reporter.create_report(
        product_name="초경량 캠핑 의자",
        category="캠핑/레저",
        keywords=sample_keywords,
        margin_result=sample_margin,
        complaint_patterns=sample_patterns,
        risks=sample_risks
    )

    print(f"\n[리포트 생성 완료]")
    print(f"  - 리포트 ID: {report.report_id}")
    print(f"  - 종합 점수: {report.opportunity_score.total_score:.1f}/100")
    print(f"  - 추천: {report.final_recommendation[:50]}...")

    # 마크다운 출력
    print("\n" + "-"*60)
    print(reporter.to_markdown(report)[:2000] + "\n...")
    print("-"*60)

    print("\n" + "="*60)
    print("✅ 리포트 생성기 모듈 준비 완료")
    print("="*60 + "\n")
