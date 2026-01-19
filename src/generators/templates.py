"""
리포트 템플릿 시스템

다양한 형식의 리포트 템플릿을 지원:
- Markdown (기본)
- HTML (웹 뷰)
- JSON (API/데이터 교환)
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path


@dataclass
class ReportData:
    """리포트 데이터 구조"""
    report_id: str
    product_name: str
    category: str
    created_at: str

    # 점수
    total_score: float
    keyword_score: float
    margin_score: float
    competition_score: float
    risk_score: float

    # 마진 정보
    margin_percent: float
    total_cost: int
    profit: int
    breakeven_price: int
    target_margin_price: int
    is_viable: bool

    # 키워드
    keywords: List[Dict[str, Any]]

    # 불만 패턴
    complaint_patterns: List[Dict[str, Any]]

    # 리스크
    risks: List[str]

    # 추천
    recommendation: str
    action_items: List[str]


class ReportTemplate(ABC):
    """리포트 템플릿 추상 클래스"""

    @abstractmethod
    def render(self, data: ReportData) -> str:
        """템플릿 렌더링"""
        pass

    @abstractmethod
    def get_extension(self) -> str:
        """파일 확장자 반환"""
        pass

    def save(self, data: ReportData, filepath: str) -> str:
        """리포트 저장"""
        content = self.render(data)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath


class MarkdownTemplate(ReportTemplate):
    """마크다운 리포트 템플릿"""

    TEMPLATE = """# 📊 기회 분석 리포트

> **상품명**: {product_name}
> **카테고리**: {category}
> **생성일**: {created_at}
> **리포트 ID**: {report_id}

---

## 📈 종합 점수

| 항목 | 점수 | 등급 |
|------|------|------|
| **종합** | **{total_score:.1f}/100** | {total_grade} |
| 키워드 | {keyword_score:.1f}/100 | {keyword_grade} |
| 마진 | {margin_score:.1f}/100 | {margin_grade} |
| 경쟁강도 | {competition_score:.1f}/100 | {competition_grade} |
| 리스크 | {risk_score:.1f}/100 | {risk_grade} |

---

## 💰 마진 분석

| 항목 | 금액 |
|------|------|
| 총 비용 | {total_cost:,}원 |
| 순이익 | {profit:,}원 |
| **마진율** | **{margin_percent}%** |
| 손익분기 판매가 | {breakeven_price:,}원 |
| 목표마진(30%) 판매가 | {target_margin_price:,}원 |

**수익성**: {viability}

---

## 🔑 타겟 키워드

{keywords_table}

---

## 📝 불만 패턴 분석

{complaint_patterns_section}

---

## ⚠️ 리스크 요인

{risks_section}

---

## 🎯 최종 추천

{recommendation}

### 📌 액션 아이템

{action_items_section}

---

*본 리포트는 Smart Store Agent v3.1에 의해 자동 생성되었습니다.*
"""

    def render(self, data: ReportData) -> str:
        """마크다운 렌더링"""

        def get_grade(score: float) -> str:
            if score >= 80:
                return "🟢 우수"
            elif score >= 60:
                return "🟡 양호"
            elif score >= 40:
                return "🟠 보통"
            else:
                return "🔴 미흡"

        # 키워드 테이블
        keywords_table = "| 키워드 | 월간 검색량 | 경쟁강도 | 기회점수 |\n|--------|-----------|---------|--------|\n"
        for kw in data.keywords[:10]:
            keywords_table += f"| {kw.get('keyword', '')} | {kw.get('monthly_search_volume', 0):,} | {kw.get('competition_rate', 0):.2f} | {kw.get('opportunity_score', 0):.1f} |\n"

        # 불만 패턴 섹션
        if data.complaint_patterns:
            complaint_section = ""
            for i, pattern in enumerate(data.complaint_patterns[:5], 1):
                complaint_section += f"### {i}. {pattern.get('category', '기타')}\n\n"
                complaint_section += f"- **설명**: {pattern.get('description', '')}\n"
                complaint_section += f"- **빈도**: {pattern.get('frequency', '')}\n"
                complaint_section += f"- **심각도**: {pattern.get('severity', '')}\n"
                complaint_section += f"- **해결책**: {pattern.get('suggested_solution', '')}\n\n"
        else:
            complaint_section = "*불만 패턴 데이터 없음*\n"

        # 리스크 섹션
        if data.risks:
            risks_section = "\n".join([f"- ⚠️ {risk}" for risk in data.risks])
        else:
            risks_section = "- ✅ 주요 리스크 없음"

        # 액션 아이템 섹션
        if data.action_items:
            action_items_section = "\n".join([f"- [ ] {item}" for item in data.action_items])
        else:
            action_items_section = "- [ ] 추가 분석 필요"

        return self.TEMPLATE.format(
            product_name=data.product_name,
            category=data.category,
            created_at=data.created_at,
            report_id=data.report_id,
            total_score=data.total_score,
            total_grade=get_grade(data.total_score),
            keyword_score=data.keyword_score,
            keyword_grade=get_grade(data.keyword_score),
            margin_score=data.margin_score,
            margin_grade=get_grade(data.margin_score),
            competition_score=data.competition_score,
            competition_grade=get_grade(data.competition_score),
            risk_score=data.risk_score,
            risk_grade=get_grade(100 - data.risk_score),  # 리스크는 낮을수록 좋음
            total_cost=data.total_cost,
            profit=data.profit,
            margin_percent=data.margin_percent,
            breakeven_price=data.breakeven_price,
            target_margin_price=data.target_margin_price,
            viability="✅ 사업 가능" if data.is_viable else "❌ 재검토 필요",
            keywords_table=keywords_table,
            complaint_patterns_section=complaint_section,
            risks_section=risks_section,
            recommendation=data.recommendation,
            action_items_section=action_items_section
        )

    def get_extension(self) -> str:
        return ".md"


class HTMLTemplate(ReportTemplate):
    """HTML 리포트 템플릿"""

    TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>기회 분석 리포트 - {product_name}</title>
    <style>
        :root {{
            --primary: #3b82f6;
            --success: #22c55e;
            --warning: #eab308;
            --danger: #ef4444;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #1e293b;
            --text-muted: #64748b;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
        }}

        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}

        .header {{
            text-align: center;
            margin-bottom: 2rem;
            padding: 2rem;
            background: linear-gradient(135deg, var(--primary), #6366f1);
            color: white;
            border-radius: 16px;
        }}

        .header h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}

        .meta {{
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 1rem;
            font-size: 0.9rem;
            opacity: 0.9;
        }}

        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        .card h2 {{
            font-size: 1.25rem;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--bg);
        }}

        .score-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
        }}

        .score-item {{
            text-align: center;
            padding: 1rem;
            background: var(--bg);
            border-radius: 8px;
        }}

        .score-item .value {{
            font-size: 2rem;
            font-weight: bold;
        }}

        .score-item .label {{
            font-size: 0.875rem;
            color: var(--text-muted);
        }}

        .score-excellent {{ color: var(--success); }}
        .score-good {{ color: var(--primary); }}
        .score-medium {{ color: var(--warning); }}
        .score-poor {{ color: var(--danger); }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th, td {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--bg);
        }}

        th {{
            font-weight: 600;
            color: var(--text-muted);
        }}

        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}

        .badge-success {{ background: #dcfce7; color: #166534; }}
        .badge-warning {{ background: #fef9c3; color: #854d0e; }}
        .badge-danger {{ background: #fee2e2; color: #991b1b; }}

        .pattern {{
            padding: 1rem;
            margin-bottom: 1rem;
            border-left: 4px solid var(--primary);
            background: var(--bg);
            border-radius: 0 8px 8px 0;
        }}

        .pattern h3 {{
            font-size: 1rem;
            margin-bottom: 0.5rem;
        }}

        .pattern p {{
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-bottom: 0.25rem;
        }}

        .risk-item {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem;
            background: #fef2f2;
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }}

        .recommendation {{
            background: linear-gradient(135deg, #ecfdf5, #d1fae5);
            padding: 1.5rem;
            border-radius: 12px;
            margin-top: 1rem;
        }}

        .action-items {{
            list-style: none;
        }}

        .action-items li {{
            padding: 0.5rem 0;
            padding-left: 1.5rem;
            position: relative;
        }}

        .action-items li::before {{
            content: "☐";
            position: absolute;
            left: 0;
        }}

        .footer {{
            text-align: center;
            margin-top: 2rem;
            padding: 1rem;
            color: var(--text-muted);
            font-size: 0.875rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 기회 분석 리포트</h1>
            <p>{product_name}</p>
            <div class="meta">
                <span>📁 {category}</span>
                <span>📅 {created_at}</span>
                <span>🔖 {report_id}</span>
            </div>
        </div>

        <div class="card">
            <h2>📈 종합 점수</h2>
            <div class="score-grid">
                <div class="score-item">
                    <div class="value {total_score_class}">{total_score:.1f}</div>
                    <div class="label">종합 점수</div>
                </div>
                <div class="score-item">
                    <div class="value {keyword_score_class}">{keyword_score:.1f}</div>
                    <div class="label">키워드</div>
                </div>
                <div class="score-item">
                    <div class="value {margin_score_class}">{margin_score:.1f}</div>
                    <div class="label">마진</div>
                </div>
                <div class="score-item">
                    <div class="value {competition_score_class}">{competition_score:.1f}</div>
                    <div class="label">경쟁강도</div>
                </div>
                <div class="score-item">
                    <div class="value {risk_score_class}">{risk_score:.1f}</div>
                    <div class="label">리스크</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>💰 마진 분석</h2>
            <table>
                <tr>
                    <th>항목</th>
                    <th>금액</th>
                </tr>
                <tr>
                    <td>총 비용</td>
                    <td>{total_cost:,}원</td>
                </tr>
                <tr>
                    <td>순이익</td>
                    <td>{profit:,}원</td>
                </tr>
                <tr>
                    <td><strong>마진율</strong></td>
                    <td><strong>{margin_percent}%</strong></td>
                </tr>
                <tr>
                    <td>손익분기 판매가</td>
                    <td>{breakeven_price:,}원</td>
                </tr>
                <tr>
                    <td>목표마진(30%) 판매가</td>
                    <td>{target_margin_price:,}원</td>
                </tr>
            </table>
            <p style="margin-top: 1rem;">
                <span class="{viability_badge}">{viability_text}</span>
            </p>
        </div>

        <div class="card">
            <h2>🔑 타겟 키워드</h2>
            <table>
                <tr>
                    <th>키워드</th>
                    <th>월간 검색량</th>
                    <th>경쟁강도</th>
                    <th>기회점수</th>
                </tr>
                {keywords_rows}
            </table>
        </div>

        <div class="card">
            <h2>📝 불만 패턴 분석</h2>
            {complaint_patterns_html}
        </div>

        <div class="card">
            <h2>⚠️ 리스크 요인</h2>
            {risks_html}
        </div>

        <div class="card">
            <h2>🎯 최종 추천</h2>
            <div class="recommendation">
                <p>{recommendation}</p>
            </div>
            <h3 style="margin-top: 1.5rem; margin-bottom: 0.75rem;">📌 액션 아이템</h3>
            <ul class="action-items">
                {action_items_html}
            </ul>
        </div>

        <div class="footer">
            <p>Smart Store Agent v3.1에 의해 자동 생성됨</p>
        </div>
    </div>
</body>
</html>
"""

    def render(self, data: ReportData) -> str:
        """HTML 렌더링"""

        def get_score_class(score: float) -> str:
            if score >= 80:
                return "score-excellent"
            elif score >= 60:
                return "score-good"
            elif score >= 40:
                return "score-medium"
            else:
                return "score-poor"

        # 키워드 행
        keywords_rows = ""
        for kw in data.keywords[:10]:
            keywords_rows += f"""
                <tr>
                    <td>{kw.get('keyword', '')}</td>
                    <td>{kw.get('monthly_search_volume', 0):,}</td>
                    <td>{kw.get('competition_rate', 0):.2f}</td>
                    <td>{kw.get('opportunity_score', 0):.1f}</td>
                </tr>
            """

        # 불만 패턴 HTML
        if data.complaint_patterns:
            complaint_html = ""
            for i, pattern in enumerate(data.complaint_patterns[:5], 1):
                complaint_html += f"""
                <div class="pattern">
                    <h3>{i}. {pattern.get('category', '기타')}</h3>
                    <p><strong>설명:</strong> {pattern.get('description', '')}</p>
                    <p><strong>빈도:</strong> {pattern.get('frequency', '')} | <strong>심각도:</strong> {pattern.get('severity', '')}</p>
                    <p><strong>해결책:</strong> {pattern.get('suggested_solution', '')}</p>
                </div>
                """
        else:
            complaint_html = "<p>불만 패턴 데이터 없음</p>"

        # 리스크 HTML
        if data.risks:
            risks_html = "".join([f'<div class="risk-item">⚠️ {risk}</div>' for risk in data.risks])
        else:
            risks_html = '<div class="risk-item" style="background: #dcfce7;">✅ 주요 리스크 없음</div>'

        # 액션 아이템 HTML
        if data.action_items:
            action_items_html = "".join([f"<li>{item}</li>" for item in data.action_items])
        else:
            action_items_html = "<li>추가 분석 필요</li>"

        return self.TEMPLATE.format(
            product_name=data.product_name,
            category=data.category,
            created_at=data.created_at,
            report_id=data.report_id,
            total_score=data.total_score,
            total_score_class=get_score_class(data.total_score),
            keyword_score=data.keyword_score,
            keyword_score_class=get_score_class(data.keyword_score),
            margin_score=data.margin_score,
            margin_score_class=get_score_class(data.margin_score),
            competition_score=data.competition_score,
            competition_score_class=get_score_class(data.competition_score),
            risk_score=data.risk_score,
            risk_score_class=get_score_class(100 - data.risk_score),
            total_cost=data.total_cost,
            profit=data.profit,
            margin_percent=data.margin_percent,
            breakeven_price=data.breakeven_price,
            target_margin_price=data.target_margin_price,
            viability_badge="badge badge-success" if data.is_viable else "badge badge-danger",
            viability_text="✅ 사업 가능" if data.is_viable else "❌ 재검토 필요",
            keywords_rows=keywords_rows,
            complaint_patterns_html=complaint_html,
            risks_html=risks_html,
            recommendation=data.recommendation,
            action_items_html=action_items_html
        )

    def get_extension(self) -> str:
        return ".html"


class JSONTemplate(ReportTemplate):
    """JSON 리포트 템플릿"""

    def render(self, data: ReportData) -> str:
        """JSON 렌더링"""
        output = {
            "report_id": data.report_id,
            "product_name": data.product_name,
            "category": data.category,
            "created_at": data.created_at,
            "scores": {
                "total": data.total_score,
                "keyword": data.keyword_score,
                "margin": data.margin_score,
                "competition": data.competition_score,
                "risk": data.risk_score
            },
            "margin_analysis": {
                "margin_percent": data.margin_percent,
                "total_cost": data.total_cost,
                "profit": data.profit,
                "breakeven_price": data.breakeven_price,
                "target_margin_price": data.target_margin_price,
                "is_viable": data.is_viable
            },
            "keywords": data.keywords,
            "complaint_patterns": data.complaint_patterns,
            "risks": data.risks,
            "recommendation": data.recommendation,
            "action_items": data.action_items
        }

        return json.dumps(output, ensure_ascii=False, indent=2)

    def get_extension(self) -> str:
        return ".json"


class TemplateFactory:
    """템플릿 팩토리"""

    _templates = {
        "markdown": MarkdownTemplate,
        "md": MarkdownTemplate,
        "html": HTMLTemplate,
        "json": JSONTemplate,
    }

    @classmethod
    def create(cls, format_type: str) -> ReportTemplate:
        """템플릿 생성"""
        template_class = cls._templates.get(format_type.lower())
        if not template_class:
            raise ValueError(f"지원하지 않는 템플릿 형식: {format_type}")
        return template_class()

    @classmethod
    def supported_formats(cls) -> List[str]:
        """지원 형식 목록"""
        return list(set(cls._templates.keys()))


def convert_report_to_data(report) -> ReportData:
    """OpportunityReport를 ReportData로 변환"""
    return ReportData(
        report_id=report.report_id,
        product_name=report.product_name,
        category=report.category,
        created_at=report.created_at,
        total_score=report.opportunity_score.total_score,
        keyword_score=report.opportunity_score.keyword_score,
        margin_score=report.opportunity_score.margin_score,
        competition_score=report.opportunity_score.competition_score,
        risk_score=report.opportunity_score.risk_score,
        margin_percent=report.margin_analysis.get("margin_percent", 0),
        total_cost=report.margin_analysis.get("total_cost_krw", 0),
        profit=report.margin_analysis.get("profit_krw", 0),
        breakeven_price=report.margin_analysis.get("breakeven_price_krw", 0),
        target_margin_price=report.margin_analysis.get("target_margin_price_krw", 0),
        is_viable=report.margin_analysis.get("is_viable", False),
        keywords=report.target_keywords,
        complaint_patterns=report.complaint_patterns,
        risks=report.risks,
        recommendation=report.final_recommendation,
        action_items=report.action_items
    )
